"""LLM wrapper tests using the fake client - the real wrapper, TTFT
capture, and pricing all execute; only the network is faked. DB
persistence is best-effort so no database is needed here."""

from appshell.observability.llm_client import (
    MODEL_PRICES,
    _cost_usd,
    call_anthropic,
    pipeline_context,
    pipeline_id_var,
)


def test_call_returns_message_and_generation_id(fake_anthropic):
    response, gen_id = call_anthropic(
        fake_anthropic,
        {"model": "claude-opus-5", "max_tokens": 64, "messages": []},
        agent_name="test-agent",
    )
    assert gen_id.startswith("gen_")
    assert response.content[0].text == fake_anthropic.canned
    assert fake_anthropic.calls[0]["model"] == "claude-opus-5"


def test_cost_known_and_unknown_models():
    class Usage:
        input_tokens = 1_000_000
        output_tokens = 0
        cache_read_input_tokens = 0
        cache_creation_input_tokens = 0

    assert _cost_usd("claude-opus-5", Usage()) == MODEL_PRICES["claude-opus-5"][0]
    assert _cost_usd("model-from-the-future", Usage()) == 0.0  # warn, never raise


def test_pipeline_context_sets_and_resets():
    assert pipeline_id_var.get() == ""
    with pipeline_context(pipeline_id="pipe_123"):
        assert pipeline_id_var.get() == "pipe_123"
    assert pipeline_id_var.get() == ""
