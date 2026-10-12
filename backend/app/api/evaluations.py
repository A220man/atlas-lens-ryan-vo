"""Empirical AI/ML evaluation benchmark endpoints.

Provides reproducible measurement endpoints for prompt context bloat,
reasoning imitation suppression, and Chat DAG structural healing.
"""

import json
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import get_db_connection
from app.core.security import require_role
from app.models.schemas import EvaluationBenchmarkRequest, EvaluationMetricSummary, User
from app.services.eval_engine import EvaluationEngine

router = APIRouter(prefix="/api/evaluations", tags=["Evaluations"])


@router.post("/run", response_model=EvaluationMetricSummary)
def run_evaluation_benchmark(
    request: EvaluationBenchmarkRequest,
    current_user: User = Depends(require_role("operator"))
) -> EvaluationMetricSummary:
    """Execute reproducible empirical evaluation suite."""
    return EvaluationEngine.run_benchmark(sample_count=request.sample_count, user_id=current_user.id)


@router.get("", response_model=List[Dict[str, Any]])
def list_evaluations(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(require_role("viewer"))
) -> List[Dict[str, Any]]:
    """List historical benchmark runs."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            SELECT id, name, sample_count, results_json, created_at
            FROM evaluations
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,)
        )
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "sample_count": r["sample_count"],
                "created_at": r["created_at"],
                "results": json.loads(r["results_json"])
            }
            for r in cursor.fetchall()
        ]


@router.get("/{run_id}", response_model=Dict[str, Any])
def get_evaluation(
    run_id: str,
    current_user: User = Depends(require_role("viewer"))
) -> Dict[str, Any]:
    """Retrieve full results for a specific evaluation run."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            "SELECT id, name, sample_count, results_json, created_at FROM evaluations WHERE id = ?",
            (run_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evaluation run '{run_id}' not found.")
        return {
            "id": row["id"],
            "name": row["name"],
            "sample_count": row["sample_count"],
            "created_at": row["created_at"],
            "results": json.loads(row["results_json"])
        }
