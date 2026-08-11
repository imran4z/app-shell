"""Assistant contract tests - no DB, no network.

Covers contract #4 (execute_tool never throws) and the message-rebuild /
orphan-healing / pending-approval logic the paused state depends on.
"""

from appshell.agents.assistant import build_messages, pending_tool_calls
from appshell.agents.assistant_tools import (
    EXECUTORS,
    MUTATING_TOOL_NAMES,
    NEEDS_APPROVAL_TOOL_NAMES,
    TOOLS_ALL,
    execute_tool,
)


def test_registries_are_consistent():
    names = {t["name"] for t in TOOLS_ALL}
    assert names == set(EXECUTORS)
    assert names >= MUTATING_TOOL_NAMES
    assert NEEDS_APPROVAL_TOOL_NAMES <= MUTATING_TOOL_NAMES


def test_execute_tool_unknown_never_throws():
    result, is_error = execute_tool("frobnicate", {}, session=None)  # type: ignore[arg-type]
    assert is_error
    assert "unknown tool" in result["error"]


def test_execute_tool_contains_executor_exceptions():
    # session=None makes every real executor blow up internally; the
    # contract says that surfaces as (error payload, True), not a raise.
    result, is_error = execute_tool("list_items", {"limit": 5}, session=None)  # type: ignore[arg-type]
    assert is_error
    assert "error" in result


def _turn(role, content="", tool_calls=None, tool_results=None):
    return {
        "id": 1,
        "role": role,
        "content": content,
        "tool_calls": tool_calls,
        "tool_results": tool_results,
    }


def test_build_messages_round_trip():
    turns = [
        _turn("user", "hi"),
        _turn(
            "assistant", "checking", tool_calls=[{"id": "t1", "name": "list_items", "input": {}}]
        ),
        _turn("tool", tool_results=[{"tool_use_id": "t1", "content": "{}", "is_error": False}]),
        _turn("assistant", "all done"),
    ]
    messages = build_messages(turns)
    assert [m["role"] for m in messages] == ["user", "assistant", "user", "assistant"]
    assert messages[1]["content"][1]["type"] == "tool_use"
    assert messages[2]["content"][0]["type"] == "tool_result"


def test_build_messages_heals_orphaned_tool_use():
    turns = [
        _turn("user", "hi"),
        _turn("assistant", "", tool_calls=[{"id": "t9", "name": "get_item_stats", "input": {}}]),
        _turn("user", "hello? are you there?"),  # crash left no tool turn
    ]
    messages = build_messages(turns)
    healed = messages[2]
    assert healed["role"] == "user"
    assert healed["content"][0]["type"] == "tool_result"
    assert healed["content"][0]["tool_use_id"] == "t9"
    assert healed["content"][0]["is_error"] is True


def test_pending_tool_calls_only_when_last_turn_is_unanswered():
    calls = [{"id": "t1", "name": "create_item", "input": {"title": "x"}}]
    assert (
        pending_tool_calls([_turn("user", "hi"), _turn("assistant", "", tool_calls=calls)]) == calls
    )
    assert (
        pending_tool_calls(
            [
                _turn("assistant", "", tool_calls=calls),
                _turn("tool", tool_results=[{"tool_use_id": "t1", "content": "{}"}]),
            ]
        )
        == []
    )
    assert pending_tool_calls([]) == []
