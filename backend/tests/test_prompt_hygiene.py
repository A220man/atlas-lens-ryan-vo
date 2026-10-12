"""Tests for Prompt Hygiene, reasoning tag extraction, and reinjection toggle."""

from app.models.schemas import PromptHygieneRequest, PromptMessage
from app.services.prompt_hygiene import PromptHygieneEngine


def test_extract_think_blocks():
    """Verify extraction of <think> tags separates reasoning from final answer."""
    raw = "<think>Analyzing user question and preparing explanation.</think>Here is the final answer."
    clean, thoughts, has_tags = PromptHygieneEngine.extract_reasoning_blocks(raw)
    assert has_tags is True
    assert thoughts == "Analyzing user question and preparing explanation."
    assert clean == "Here is the final answer."


def test_extract_thought_blocks():
    """Verify extraction of <thought> variant tags."""
    raw = "<thought>Internal deliberation trace.</thought>Output text."
    clean, thoughts, has_tags = PromptHygieneEngine.extract_reasoning_blocks(raw)
    assert has_tags is True
    assert thoughts == "Internal deliberation trace."
    assert clean == "Output text."


def test_extract_unclosed_tag():
    """Handle unclosed <think> tag caused by token limit truncation."""
    raw = "<think>Truncated chain of thought that was cut off"
    clean, thoughts, has_tags = PromptHygieneEngine.extract_reasoning_blocks(raw)
    assert has_tags is True
    assert thoughts == "Truncated chain of thought that was cut off"
    assert clean == ""


def test_reinject_reasoning_disabled_by_default():
    """Ensure reinject_reasoning=False suppresses thinking tags in prompt history."""
    req = PromptHygieneRequest(
        model_id="qwen-coder",
        reinject_reasoning=False,
        messages=[
            PromptMessage(role="user", content="Write a sort function"),
            PromptMessage(role="assistant", content="<think>Considering quicksort vs timsort</think>Here is timsort.")
        ]
    )
    res = PromptHygieneEngine.process_request(req)
    assert res.reinject_reasoning is False
    assert res.contains_think_tags is True
    assert res.token_savings_pct > 0.0
    assert "<think>" not in res.sanitized_messages[1].content
    assert res.sanitized_messages[1].stripped_reasoning == "Considering quicksort vs timsort"


def test_reinject_reasoning_enabled():
    """Ensure reinject_reasoning=True preserves thinking tags in prompt history."""
    req = PromptHygieneRequest(
        model_id="deepseek-r1",
        reinject_reasoning=True,
        messages=[
            PromptMessage(role="user", content="Query"),
            PromptMessage(role="assistant", content="<think>Reasoning</think>Answer")
        ]
    )
    res = PromptHygieneEngine.process_request(req)
    assert res.reinject_reasoning is True
    assert "<think>" in res.sanitized_messages[1].content
    assert res.imitation_risk_score > 0.5


def test_imitation_risk_score():
    """Ensure imitation risk is 0 for clean prompts and high for prompts containing reasoning tags."""
    clean_messages = [PromptMessage(role="user", content="Hello"), PromptMessage(role="assistant", content="Hi!")]
    risk_clean = PromptHygieneEngine.evaluate_imitation_risk(clean_messages)
    assert risk_clean == 0.0

    tainted_messages = [
        PromptMessage(role="user", content="Question"),
        PromptMessage(role="assistant", content="<think>Trace</think>Answer")
    ]
    risk_tainted = PromptHygieneEngine.evaluate_imitation_risk(tainted_messages)
    assert risk_tainted >= 0.45
