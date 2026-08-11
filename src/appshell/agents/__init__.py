"""Agents live here - one module per agent, no graph framework.

Pattern (BLUEPRINT.md §8): state = TypedDict(total=False); each stage is
`async def stage(state) -> state`; a top-level run_x() chains them. Prompts
are inline module-level triple-quoted strings. Every model call goes through
appshell.observability.llm_client.call_anthropic - never call the SDK
directly. Sanitize LLM output toward schema enums before pydantic validation.
"""
