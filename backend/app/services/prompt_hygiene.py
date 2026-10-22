"""Prompt hygiene and reasoning reinjection prevention engine.

Addresses upstream Issue #23339: Model-level toggle to disable reinjecting
reasoning/thinking into prompts (prevents xxx tag imitation/parsing failures).

Provides deterministic reasoning extraction, token bloat analysis,
and imitation risk scoring without external dependencies.
"""

import math
import re
from typing import Any, Dict, List, Optional, Tuple

from app.models.schemas import (
    PromptHygieneRequest,
    PromptHygieneResponse,
    PromptMessage,
    SanitizedMessage,
)


DEFAULT_FILTER_TAGS = ["think", "thought"]

# Cache of compiled regex patterns keyed by sorted, lowercased tag tuple.
# Backreference ensures closing tags match opening tag names (e.g. <think>...</think>).
_PATTERN_CACHE: Dict[tuple, Tuple[re.Pattern, re.Pattern]] = {}


def _build_patterns(filter_tags: List[str]) -> Tuple[re.Pattern, re.Pattern]:
    """Build and cache regex patterns for the given set of tag names.

    The closed-block pattern uses a backreference so that an opening tag and
    its closing counterpart must share the same name (e.g. <think>...</think>
    but not <think>...</thought>). Patterns are cached to avoid recompilation
    on repeated requests with the same tag set.
    """
    key = tuple(sorted(t.lower() for t in filter_tags))
    if key in _PATTERN_CACHE:
        return _PATTERN_CACHE[key]

    tag_group = "|".join(re.escape(tag) for tag in key)
    closed = re.compile(rf"<({tag_group})>(.*?)</\1>", re.DOTALL | re.IGNORECASE)
    unclosed = re.compile(rf"<({tag_group})>(.*)", re.DOTALL | re.IGNORECASE)

    _PATTERN_CACHE[key] = (closed, unclosed)
    return closed, unclosed


class PromptHygieneEngine:
    """Sanitizes prompt history to prevent pathological tag imitation and token inflation."""

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Heuristic token estimator based on whitespace, word boundaries, and punctuation."""
        if not text:
            return 0
        # Approx 1 token per 3.8 characters or 0.75 words + punctuation bonus
        words = len(text.split())
        chars = len(text)
        punct = sum(1 for c in text if c in ",.!?;:()[]{}\"'-_/")
        estimated = int(math.ceil(max(words * 1.25, chars / 3.8) + punct * 0.2))
        return max(1, estimated)

    @classmethod
    def extract_reasoning_blocks(
        cls, content: str, filter_tags: Optional[List[str]] = None
    ) -> Tuple[str, Optional[str], bool]:
        """Extract reasoning traces and return clean content, isolated thoughts, and presence flag.

        Uses filter_tags to determine which tag names to search for. When None,
        defaults to DEFAULT_FILTER_TAGS. When empty, no tags are extracted.
        """
        if filter_tags is None:
            filter_tags = DEFAULT_FILTER_TAGS
        if not filter_tags:
            return content, None, False

        closed_regex, unclosed_regex = _build_patterns(filter_tags)

        has_tags = False
        extracted_thoughts: List[str] = []

        # Find closed blocks
        def replace_match(match: re.Match) -> str:
            nonlocal has_tags
            has_tags = True
            tag_content = match.group(2).strip()
            if tag_content:
                extracted_thoughts.append(tag_content)
            return ""

        clean_text = closed_regex.sub(replace_match, content)

        # Handle unclosed tags from truncated generation
        unclosed_match = unclosed_regex.search(clean_text)
        if unclosed_match:
            has_tags = True
            extracted_thoughts.append(unclosed_match.group(2).strip())
            clean_text = clean_text[:unclosed_match.start()]

        clean_text = clean_text.strip()
        combined_thoughts = "\n\n".join(extracted_thoughts) if extracted_thoughts else None
        return clean_text, combined_thoughts, has_tags

    @classmethod
    def evaluate_imitation_risk(
        cls, messages: List[PromptMessage], filter_tags: Optional[List[str]] = None
    ) -> float:
        """Calculate imitation probability score (0.0 to 1.0).

        When reasoning tags appear in prompt history, downstream autoregressive
        models heavily imitate them, leading to broken UI markdown parsing
        and recursive thought hallucinations. Uses filter_tags to determine
        which tag names to detect.
        """
        if filter_tags is None:
            filter_tags = DEFAULT_FILTER_TAGS
        if not filter_tags:
            return 0.0

        closed_regex, unclosed_regex = _build_patterns(filter_tags)

        tag_occurrences = 0
        unclosed_occurrences = 0
        assistant_turn_count = 0

        for msg in messages:
            if msg.role == "assistant":
                assistant_turn_count += 1
                closed_matches = len(closed_regex.findall(msg.content))
                if closed_matches > 0:
                    tag_occurrences += closed_matches
                # Check for unclosed tags only after removing closed blocks.
                # Otherwise the broad unclosed pattern also matches the opening
                # side of a properly closed tag, double-counting it as unclosed.
                clean_after_closed = closed_regex.sub("", msg.content)
                if unclosed_regex.search(clean_after_closed):
                    unclosed_occurrences += 1

        if tag_occurrences == 0 and unclosed_occurrences == 0:
            return 0.0

        # Score increases steeply with repeated occurrences in prompt history
        raw_score = 0.45 + (0.2 * min(tag_occurrences, 3)) + (0.15 * unclosed_occurrences)
        return min(0.99, round(raw_score, 2))

    @classmethod
    def process_request(cls, request: PromptHygieneRequest) -> PromptHygieneResponse:
        """Process messages according to model policy and compute hygiene metrics."""
        original_tokens = sum(cls.estimate_tokens(m.content) for m in request.messages)
        sanitized_messages: List[SanitizedMessage] = []
        any_think_tags = False

        for msg in request.messages:
            if msg.role == "assistant":
                clean_text, thoughts, has_tags = cls.extract_reasoning_blocks(msg.content, request.filter_tags)
                if has_tags:
                    any_think_tags = True

                if request.reinject_reasoning:
                    # Model toggle ON: reinject reasoning as raw tags
                    sanitized_messages.append(
                        SanitizedMessage(
                            role=msg.role,
                            content=msg.content,
                            stripped_reasoning=thoughts
                        )
                    )
                else:
                    # Model toggle OFF (Default & Recommended): strip reasoning from prompt history
                    sanitized_messages.append(
                        SanitizedMessage(
                            role=msg.role,
                            content=clean_text if clean_text else "(Response omitted thinking)",
                            stripped_reasoning=thoughts
                        )
                    )
            else:
                sanitized_messages.append(
                    SanitizedMessage(
                        role=msg.role,
                        content=msg.content,
                        stripped_reasoning=None
                    )
                )

        sanitized_tokens = sum(cls.estimate_tokens(m.content) for m in sanitized_messages)

        savings_pct = 0.0
        if original_tokens > 0 and original_tokens > sanitized_tokens:
            savings_pct = round(((original_tokens - sanitized_tokens) / original_tokens) * 100.0, 2)

        imitation_risk = cls.evaluate_imitation_risk(request.messages, request.filter_tags) if not request.reinject_reasoning else 0.85

        return PromptHygieneResponse(
            model_id=request.model_id,
            reinject_reasoning=request.reinject_reasoning,
            original_estimated_tokens=original_tokens,
            sanitized_estimated_tokens=sanitized_tokens,
            token_savings_pct=savings_pct,
            contains_think_tags=any_think_tags,
            imitation_risk_score=imitation_risk if any_think_tags else 0.0,
            sanitized_messages=sanitized_messages
        )
