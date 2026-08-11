"""Observability core - structured logging only.

This template deliberately ships without a monitoring/telemetry stack
(no OTel, no exporters). One rule survives from the blueprint: anything
observability-adjacent (like the llm_calls cost ledger) is best-effort -
it never breaks the primary path. If an app needs tracing later, add it
behind this package so call sites don't change.
"""

from __future__ import annotations

import logging

import structlog


def configure_logging(level: str = "INFO") -> None:
    """Structlog over stdlib logging; idempotent, safe to call anywhere."""
    logging.basicConfig(level=level, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        cache_logger_on_first_use=True,
    )
