"""Prompt hygiene and reasoning reinjection endpoints.

Addresses Issue #23339.
"""

from typing import Any, Dict
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.core.database import record_audit_log
from app.core.security import require_role
from app.models.schemas import PromptHygieneRequest, PromptHygieneResponse, User
from app.services.llm_adapters import LlmGatewayService
from app.services.prompt_hygiene import PromptHygieneEngine

router = APIRouter(prefix="/api/hygiene", tags=["Prompt Hygiene"])


class CompletionWithHygieneRequest(BaseModel):
    """Execution request combining hygiene sanitization with LLM adapter invocation."""
    prompt_request: PromptHygieneRequest
    system_instruction: str = "You are an AI assistant."


@router.post("/inspect", response_model=PromptHygieneResponse)
def inspect_and_sanitize(
    request: PromptHygieneRequest,
    current_user: User = Depends(require_role("viewer"))
) -> PromptHygieneResponse:
    """Analyze prompt history, extract thinking traces, and calculate imitation risk score."""
    return PromptHygieneEngine.process_request(request)


@router.post("/dispatch-completion")
async def dispatch_completion(
    req: CompletionWithHygieneRequest,
    current_user: User = Depends(require_role("operator")),
    settings: Settings = Depends(get_settings)
) -> Dict[str, Any]:
    """Sanitize prompt and route to configured LLM provider or deterministic offline fallback."""
    hygiene_result = PromptHygieneEngine.process_request(req.prompt_request)

    # Reconstruct combined prompt text from sanitized turns
    prompt_lines = []
    for msg in hygiene_result.sanitized_messages:
        prompt_lines.append(f"{msg.role.upper()}: {msg.content}")
    combined_prompt = "\n".join(prompt_lines)

    completion_result = await LlmGatewayService.generate_completion(
        prompt=combined_prompt,
        system_instruction=req.system_instruction,
        settings=settings
    )

    record_audit_log(
        user_id=current_user.id,
        action="DISPATCH_LLM_COMPLETION",
        resource_type="hygiene_completion",
        resource_id=req.prompt_request.model_id,
        details={
            "reinject_reasoning": req.prompt_request.reinject_reasoning,
            "token_savings_pct": hygiene_result.token_savings_pct,
            "provider": completion_result.get("provider")
        },
        settings=settings
    )

    return {
        "hygiene_summary": hygiene_result.model_dump(),
        "completion": completion_result
    }
