"""The single instrumented LLM wrapper (BLUEPRINT.md §8, contract #3).

Every model call in the app goes through call_anthropic(). It provides:
  - contextvars-based context propagation (pipeline_id/phase/template), each
    defaulting to an env var read at import - CLI subprocesses inherit the
    orchestrator's context with zero plumbing.
  - internal streaming even for non-streaming callers, so TTFT is captured
    and callers can watch tokens live via on_text (the assistant drawer);
    the final message is reassembled so call sites see the normal shape.
  - cost computed from MODEL_PRICES (unknown model -> warn + $0, never raise).
  - one best-effort row per call into llm_calls (never breaks the primary
    path). This is a cost ledger, not monitoring - the template ships
    without a telemetry stack by design.
"""

from __future__ import annotations

import contextlib
import contextvars
import os
import time
import uuid
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

import structlog

_logger = structlog.get_logger()

# --- Context propagation -------------------------------------------------
# Env-var defaults mean a subprocess spawned with these vars set inherits
# the orchestrator's context without any function-argument plumbing.

pipeline_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "pipeline_id", default=os.environ.get("APPSHELL_PIPELINE_ID", "")
)
phase_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "phase", default=os.environ.get("APPSHELL_PHASE", "")
)
prompt_template_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "prompt_template", default=""
)


@contextlib.contextmanager
def pipeline_context(**overrides: str) -> Iterator[None]:
    """Set/reset the ContextVars above for the duration of a block."""
    tokens = []
    known = {
        "pipeline_id": pipeline_id_var,
        "phase": phase_var,
        "prompt_template": prompt_template_var,
    }
    for name, value in overrides.items():
        var = known.get(name)
        if var is not None:
            tokens.append((var, var.set(value)))
    try:
        yield
    finally:
        for var, token in tokens:
            var.reset(token)


# --- Pricing -------------------------------------------------------------
# USD per million tokens: (input, output, cache_write, cache_read).
# Cache write = 1.25x input (5m TTL); cache read = 0.1x input.

MODEL_PRICES: dict[str, tuple[float, float, float, float]] = {
    "claude-opus-5": (5.00, 25.00, 6.25, 0.50),
    "claude-opus-4-8": (5.00, 25.00, 6.25, 0.50),
    "claude-sonnet-5": (3.00, 15.00, 3.75, 0.30),
    "claude-sonnet-4-6": (3.00, 15.00, 3.75, 0.30),
    "claude-haiku-4-5": (1.00, 5.00, 1.25, 0.10),
    "claude-fable-5": (10.00, 50.00, 12.50, 1.00),
}

DEFAULT_MODEL = os.environ.get("APPSHELL_MODEL", "claude-opus-5")


def _cost_usd(model: str, usage: Any) -> float:
    prices = MODEL_PRICES.get(model)
    if prices is None:
        # Try prefix match for dated snapshot ids
        for known, p in MODEL_PRICES.items():
            if model.startswith(known):
                prices = p
                break
    if prices is None:
        _logger.warning("llm.unknown_model_price", model=model)
        return 0.0
    inp, out, cw, cr = prices
    m = 1_000_000
    return (
        getattr(usage, "input_tokens", 0) / m * inp
        + getattr(usage, "output_tokens", 0) / m * out
        + (getattr(usage, "cache_creation_input_tokens", 0) or 0) / m * cw
        + (getattr(usage, "cache_read_input_tokens", 0) or 0) / m * cr
    )


def _classify_error(exc: Exception) -> str:
    """Coarse buckets by class-name/message matching - deliberately not
    importing the SDK exception hierarchy."""
    name = type(exc).__name__.lower()
    msg = str(exc).lower()
    if "ratelimit" in name or "rate limit" in msg:
        return "rate_limit"
    if "timeout" in name or "timed out" in msg:
        return "timeout"
    if "context" in msg and ("length" in msg or "window" in msg):
        return "context_length"
    if "auth" in name or "api key" in msg or "authentication" in msg:
        return "auth"
    if "internalserver" in name or "overloaded" in name or "5" in name[:1]:
        return "server_error"
    return "unknown"


# --- The wrapper ---------------------------------------------------------


def call_anthropic(
    client: Any,
    request: dict[str, Any],
    *,
    agent_name: str,
    prompt_template: str | None = None,
    tags: dict[str, Any] | None = None,
    on_text: Callable[[str], None] | None = None,
) -> tuple[Any, str]:
    """Make one model call: TTFT + cost + durable row.

    `request` is the kwargs dict for messages.create/stream (model,
    max_tokens, system, messages, ...). `on_text` receives each streamed
    text chunk (the assistant drawer's live deltas). Returns
    (final_message, generation_id). Raises the SDK error after recording.
    """
    generation_id = f"gen_{uuid.uuid4().hex[:12]}"
    model = request.get("model", DEFAULT_MODEL)
    template = prompt_template or prompt_template_var.get()
    row: dict[str, Any] = {
        "generation_id": generation_id,
        "agent_name": agent_name,
        "model": model,
        "pipeline_id": pipeline_id_var.get() or None,
        "phase": phase_var.get() or None,
        "prompt_template": template or None,
    }

    started = time.monotonic()
    ttft_ms: int | None = None
    error: Exception | None = None
    response = None

    try:
        # Always stream internally so we can timestamp TTFT on the first
        # delta, even for callers that want a plain response.
        with client.messages.stream(**request) as stream:
            for chunk in stream.text_stream:
                if ttft_ms is None:
                    ttft_ms = int((time.monotonic() - started) * 1000)
                if on_text is not None:
                    on_text(chunk)
            response = stream.get_final_message()
    except Exception as exc:  # noqa: BLE001 - recorded then re-raised
        error = exc
        row["error_type"] = _classify_error(exc)
        _logger.warning(
            "llm.call_failed",
            agent=agent_name,
            model=model,
            error_type=row["error_type"],
            error=str(exc)[:300],
        )

    row["duration_ms"] = int((time.monotonic() - started) * 1000)
    row["ttft_ms"] = ttft_ms
    if response is not None:
        usage = response.usage
        row["input_tokens"] = getattr(usage, "input_tokens", 0)
        row["output_tokens"] = getattr(usage, "output_tokens", 0)
        row["cache_read_tokens"] = getattr(usage, "cache_read_input_tokens", 0) or 0
        row["cache_write_tokens"] = getattr(usage, "cache_creation_input_tokens", 0) or 0
        row["cost_usd"] = round(_cost_usd(model, usage), 6)

    _persist_row(row)

    if error is not None:
        raise error
    return response, generation_id


def _persist_row(row: dict[str, Any]) -> None:
    """Best-effort, no-throw persistence - observability writes never break
    the primary path (BLUEPRINT.md §0.6)."""
    try:
        from appshell.storage import LlmCallRepository, session_scope

        with session_scope() as session:
            LlmCallRepository().record(session, row)
    except Exception as exc:  # noqa: BLE001
        _logger.debug("llm.row_persist_failed", error=str(exc)[:200])
