"""Chat DAG integrity validation and structural auto-repair engine.

Addresses upstream Issue #15189: Lack of Data Integrity Validation on Chat Model
Causes Silent Failure and Frontend Deadlock.

This engine:
1. Detects cycles in conversation graphs to prevent infinite recursion.
2. Identifies orphan messages (missing parentId or unlinked nodes).
3. Reconstructs bidirectional parentId <-> childrenIds integrity.
4. Synchronizes top-level messages array with history.messages mapping.
5. Linearizes the active conversational trajectory safely for frontend rendering.
"""

from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

from app.models.schemas import ChatMessage, ChatValidationReport


class ChatDagEngine:
    """Deterministic conversational tree validator and healing engine."""

    @staticmethod
    def extract_nodes(raw_chat: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Normalize and extract message map from multiple conversational formats."""
        nodes: Dict[str, Dict[str, Any]] = {}

        # Open WebUI standard: chat["history"]["messages"]
        history = raw_chat.get("history")
        if isinstance(history, dict) and isinstance(history.get("messages"), dict):
            for msg_id, msg_data in history["messages"].items():
                if isinstance(msg_data, dict):
                    nodes[str(msg_id)] = dict(msg_data)

        # Fallback / sync from chat["messages"] array
        messages_list = raw_chat.get("messages")
        if isinstance(messages_list, list):
            for msg in messages_list:
                if isinstance(msg, dict) and "id" in msg:
                    m_id = str(msg["id"])
                    if m_id not in nodes:
                        nodes[m_id] = dict(msg)

        return nodes

    @classmethod
    def validate_graph(cls, raw_chat: Dict[str, Any]) -> ChatValidationReport:
        """Perform deep structural diagnostics on conversation DAG."""
        nodes = cls.extract_nodes(raw_chat)
        total_messages = len(nodes)
        details: List[str] = []

        if total_messages == 0:
            return ChatValidationReport(
                is_valid=True,
                total_messages=0,
                cycles_detected=False,
                orphan_messages=[],
                missing_children_links=0,
                out_of_sync_count=0,
                repaired=False,
                details=["Empty chat graph."]
            )

        # 1. Cycle detection using Kahn's algorithm / DFS
        in_degree: Dict[str, int] = {nid: 0 for nid in nodes}
        adjacency: Dict[str, List[str]] = {nid: [] for nid in nodes}
        orphan_nodes: List[str] = []
        missing_children_links = 0

        # Build graph directed from parent to child
        for nid, data in nodes.items():
            pid = data.get("parentId")
            if pid is not None and pid != "":
                str_pid = str(pid)
                if str_pid in nodes:
                    adjacency[str_pid].append(nid)
                    in_degree[nid] = in_degree.get(nid, 0) + 1
                else:
                    # Parent ID does not exist in nodes map -> Orphan!
                    orphan_nodes.append(nid)
                    details.append(f"Node '{nid}' references non-existent parent '{str_pid}'.")
            else:
                # Top-level node without parent. If there are multiple, they are roots or orphans
                pass

        # Detect cycle in parent -> child references
        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
        visited_count = 0
        while queue:
            curr = queue.popleft()
            visited_count += 1
            for child in adjacency.get(curr, []):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        cycles_detected = (visited_count < len(nodes))
        if cycles_detected:
            details.append("Cycle detected in parent-child relationship graph.")

        # 2. Check childrenIds consistency
        for nid, data in nodes.items():
            claimed_children = set(str(c) for c in data.get("childrenIds", []) if c is not None)
            actual_children = set(adjacency.get(nid, []))
            if claimed_children != actual_children:
                missing_children_links += 1

        # 3. Check synchronization with flat messages array
        top_level_messages = raw_chat.get("messages")
        out_of_sync_count = 0
        if isinstance(top_level_messages, list):
            top_ids = {str(m.get("id")) for m in top_level_messages if isinstance(m, dict) and "id" in m}
            node_ids = set(nodes.keys())
            out_of_sync_count = len(node_ids.symmetric_difference(top_ids))
            if out_of_sync_count > 0:
                details.append(
                    f"Desynchronization: {out_of_sync_count} messages present in map but missing in flat list."
                )

        is_valid = (
            not cycles_detected and
            len(orphan_nodes) == 0 and
            missing_children_links == 0 and
            out_of_sync_count == 0
        )

        return ChatValidationReport(
            is_valid=is_valid,
            total_messages=total_messages,
            cycles_detected=cycles_detected,
            orphan_messages=orphan_nodes,
            missing_children_links=missing_children_links,
            out_of_sync_count=out_of_sync_count,
            repaired=False,
            details=details
        )

    @classmethod
    def repair_graph(cls, raw_chat: Dict[str, Any]) -> Tuple[Dict[str, Any], ChatValidationReport]:
        """Automatically repair malformed chat trees, restoring acyclic structure and consistency."""
        nodes = cls.extract_nodes(raw_chat)
        if not nodes:
            report = cls.validate_graph(raw_chat)
            report.repaired = True
            return raw_chat, report

        details: List[str] = []

        # Step 1: Break cycles by clearing parent links of cyclic nodes
        visited: Set[str] = set()
        path: Set[str] = set()

        def break_cycles(nid: str):
            visited.add(nid)
            path.add(nid)
            pid = nodes[nid].get("parentId")
            if pid and str(pid) in nodes:
                str_pid = str(pid)
                if str_pid in path:
                    # Cycle detected: break parent link
                    nodes[nid]["parentId"] = None
                    details.append(f"Severed cyclic link: parentId of '{nid}' cleared.")
                elif str_pid not in visited:
                    break_cycles(str_pid)
            path.remove(nid)

        for nid in list(nodes.keys()):
            if nid not in visited:
                break_cycles(nid)

        # Step 2: Repair orphan nodes missing valid parentId
        # Sort nodes by timestamp or discovery order
        sorted_nodes = sorted(
            nodes.items(),
            key=lambda item: float(item[1].get("timestamp") or 0)
        )

        root_id: Optional[str] = None
        for nid, data in sorted_nodes:
            pid = data.get("parentId")
            if pid is None or pid == "":
                if root_id is None:
                    # First node without parent becomes canonical root
                    root_id = nid
                    data["parentId"] = None
                else:
                    # Secondary orphan node: connect to the root or previous message
                    data["parentId"] = root_id
                    details.append(f"Repaired orphan node '{nid}': attached to root '{root_id}'.")
            elif str(pid) not in nodes:
                # Parent ID does not exist: attach to canonical root
                if root_id is None:
                    root_id = nid
                    data["parentId"] = None
                else:
                    data["parentId"] = root_id
                details.append(f"Repaired invalid parent '{pid}' on node '{nid}': reconnected to '{root_id}'.")

        # Step 3: Recompute all childrenIds bidirectionally
        for nid in nodes:
            nodes[nid]["childrenIds"] = []

        for nid, data in nodes.items():
            pid = data.get("parentId")
            if pid and str(pid) in nodes:
                nodes[str(pid)]["childrenIds"].append(nid)

        # Step 4: Ensure currentId points to a valid leaf or deepest node
        current_id = None
        if isinstance(raw_chat.get("history"), dict):
            current_id = raw_chat["history"].get("currentId")

        if not current_id or str(current_id) not in nodes:
            # Pick the most recent message by timestamp
            current_id = sorted_nodes[-1][0] if sorted_nodes else None
            details.append(f"Reset currentId to valid leaf node '{current_id}'.")

        # Step 5: Synchronize flat messages list
        flat_list = [dict(v) for _, v in sorted_nodes]

        repaired_chat = dict(raw_chat)
        repaired_chat["history"] = {
            "messages": nodes,
            "currentId": current_id
        }
        repaired_chat["messages"] = flat_list
        repaired_chat["updated_at"] = datetime.now(timezone.utc).timestamp()

        post_report = cls.validate_graph(repaired_chat)
        post_report.repaired = True
        post_report.details.extend(details)

        return repaired_chat, post_report

    @classmethod
    def linearize_trajectory(cls, raw_chat: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Walk backward from currentId to root to construct sequential dialogue turns."""
        nodes = cls.extract_nodes(raw_chat)
        if not nodes:
            return []

        current_id = None
        if isinstance(raw_chat.get("history"), dict):
            current_id = raw_chat["history"].get("currentId")

        if not current_id or str(current_id) not in nodes:
            # Pick latest
            sorted_nodes = sorted(
                nodes.items(),
                key=lambda item: float(item[1].get("timestamp") or 0)
            )
            current_id = sorted_nodes[-1][0]

        trajectory: List[Dict[str, Any]] = []
        visited = set()
        curr: Optional[str] = str(current_id)

        while curr and curr in nodes and curr not in visited:
            visited.add(curr)
            msg = dict(nodes[curr])
            trajectory.append(msg)
            pid = msg.get("parentId")
            curr = str(pid) if pid else None

        trajectory.reverse()
        return trajectory
