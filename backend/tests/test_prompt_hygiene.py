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
def test_closed_tag_not_double_counted_as_unclosed():
    """Ensure a properly closed think tag is not also counted as unclosed.

    Regression: UNCLOSED_THINK_REGEX matched the opening side of any closed
    tag, inflating imitation risk to 0.80 for one closed tag instead of 0.65.
    """
    # Build tags with chr() to survive source inspection / tag stripping
    to = chr(60) + "think" + chr(62)       # 
    tc = chr(60) + "/think" + chr(62)      # 

    # Single closed tag: 0.45 + 0.2*1 + 0.15*0 = 0.65
    msgs = [
        PromptMessage(role="user", content="Q"),
        PromptMessage(role="assistant", content=to + "Trace." + tc + " Answer"),
    ]
    risk = PromptHygieneEngine.evaluate_imitation_risk(msgs)
    assert risk == 0.65

    # Two closed tags: 0.45 + 0.2*2 + 0.15*0 = 0.85
    two_closed = to + "First." + tc + to + "Second." + tc + " Final."
    msgs2 = [
        PromptMessage(role="user", content="Q"),
        PromptMessage(role="assistant", content=two_closed),
    ]
    risk2 = PromptHygieneEngine.evaluate_imitation_risk(msgs2)
    assert risk2 == 0.85

    # One closed + one genuinely unclosed: 0.45 + 0.2*1 + 0.15*1 = 0.80
    mixed = to + "Closed thought." + tc + to + "Unclosed thought"
    msgs3 = [
        PromptMessage(role="user", content="Q"),
        PromptMessage(role="assistant", content=mixed),
    ]
    risk3 = PromptHygieneEngine.evaluate_imitation_risk(msgs3)
    assert risk3 == 0.80

def test_extract_reasoning_with_custom_filter_tags():
    """Verify custom filter_tags restrict which tags are extracted.

    Only tags listed in filter_tags should be stripped; other tags pass through.
    """
    raw = chr(60) + "think" + chr(62) + "Hidden trace" + chr(60) + "/think" + chr(62) + "Visible output"
    # When only "thought" is in filter_tags,  tags should remain untouched
    clean, thoughts, has_tags = PromptHygieneEngine.extract_reasoning_blocks(raw, filter_tags=["thought"])
    assert has_tags is False
    assert thoughts is None
    assert clean == raw

    # When "think" is in filter_tags,  tags should be stripped
    clean2, thoughts2, has_tags2 = PromptHygieneEngine.extract_reasoning_blocks(raw, filter_tags=["think"])
    assert has_tags2 is True
    assert thoughts2 == "Hidden trace"
    assert clean2 == "Visible output"


def test_extract_reasoning_with_extended_filter_tags():
    """Verify a user-configured additional tag name is also handled."""
    raw = chr(60) + "scratchpad" + chr(62) + "Scratch reasoning" + chr(60) + "/scratchpad" + chr(62) + "Final answer"
    clean, thoughts, has_tags = PromptHygieneEngine.extract_reasoning_blocks(
        raw, filter_tags=["think", "thought", "scratchpad"]
    )
    assert has_tags is True
    assert thoughts == "Scratch reasoning"
    assert clean == "Final answer"


def test_extract_reasoning_with_empty_filter_tags():
    """Verify empty filter_tags is a no-op: no extraction, original content returned."""
    raw = chr(60) + "think" + chr(62) + "Trace" + chr(60) + "/think" + chr(62) + "Output"
    clean, thoughts, has_tags = PromptHygieneEngine.extract_reasoning_blocks(raw, filter_tags=[])
    assert has_tags is False
    assert thoughts is None
    assert clean == raw


def test_process_request_with_custom_filter_tags_strips_only_listed():
    """Verify process_request honors filter_tags for both sanitization and risk scoring."""
    raw_with_both = (
        chr(60) + "think" + chr(62) + "Think trace" + chr(60) + "/think" + chr(62) +
        chr(60) + "thought" + chr(62) + "Thought trace" + chr(60) + "/thought" + chr(62) +
        "Answer text"
    )
    req = PromptHygieneRequest(
        model_id="custom-tags",
        reinject_reasoning=False,
        messages=[
            PromptMessage(role="user", content="Question"),
            PromptMessage(role="assistant", content=raw_with_both),
        ],
        filter_tags=["think"],
    )
    res = PromptHygieneEngine.process_request(req)
    assert res.contains_think_tags is True
    # Only  tags stripped; <thought> block should remain in content
    stripped_content = res.sanitized_messages[1].content
    assert chr(60) + "think" not in stripped_content
    assert chr(60) + "thought" + chr(62) in stripped_content


def test_imitation_risk_respects_custom_filter_tags():
    """Verify imitation risk only counts tags within filter_tags."""
    content_with_unlisted = (
        chr(60) + "thought" + chr(62) + "Some trace" + chr(60) + "/thought" + chr(62) + "Answer"
    )
    msgs = [
        PromptMessage(role="user", content="Q"),
        PromptMessage(role="assistant", content=content_with_unlisted),
    ]
    # With default tags, should detect the tag
    risk_default = PromptHygieneEngine.evaluate_imitation_risk(msgs)
    assert risk_default >= 0.45

    # With only "think" in filter_tags, <thought> tags should not be counted
    risk_custom = PromptHygieneEngine.evaluate_imitation_risk(msgs, filter_tags=["think"])
    assert risk_custom == 0.0
