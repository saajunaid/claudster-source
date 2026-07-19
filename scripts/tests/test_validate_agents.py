"""Tests for validate_agents.py MCP note/error separation.

Adding a new MCP tool to the server used to hard-fail the build: the "server has
new tools not in EXPECTED_MCP_TOOLS" message was appended to the error list, and
`main()` exits 1 on any error. It (and the "smoke test skipped" messages) are
NOTES — informational, non-fatal. Only genuine failures (a missing expected tool,
a protocol error) should fail the build.

validate_agents.py lives at the repo root and is import-safe (its body is behind
`if __name__ == "__main__"`).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location("validate_agents", _ROOT / "validate_agents.py")
va = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = va
_SPEC.loader.exec_module(va)  # type: ignore[union-attr]


def test_new_tool_is_a_note_not_an_error():
    errors, notes = va._diff_mcp_tools(
        registered={"a", "b", "brand_new_tool"}, expected={"a", "b"}
    )
    assert errors == []
    assert any("brand_new_tool" in n for n in notes)


def test_missing_expected_tool_is_an_error():
    errors, notes = va._diff_mcp_tools(registered={"a"}, expected={"a", "b"})
    assert any("b" in e for e in errors)
    assert notes == []


def test_exact_match_no_errors_no_notes():
    errors, notes = va._diff_mcp_tools(registered={"a", "b"}, expected={"a", "b"})
    assert errors == []
    assert notes == []


def test_missing_and_new_split_correctly():
    errors, notes = va._diff_mcp_tools(registered={"a", "extra"}, expected={"a", "b"})
    assert any("b" in e for e in errors)      # missing → error
    assert any("extra" in n for n in notes)   # new → note
