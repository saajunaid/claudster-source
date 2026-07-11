"""Content-lint the digression workstream-stack commands (/digress + /resume).

These commands manipulate `.claudster/workstreams.json` and realign relay.md. They run
inside a live Claude session, so this is a content lint (not a behavior proof): it locks
the safety-critical guarantees into the command text so they can't be quietly removed —
the schema contract, the empty-stack handling, and the no-destructive-git rule.
"""

from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_CMDS = _REPO / "claude-harness" / "commands"
_DIGRESS = _CMDS / "digress.md"
_RESUME = _CMDS / "resume.md"
_HANDOFF = _CMDS / "handoff.md"

_DESTRUCTIVE = ("git checkout", "git reset", "git stash")


def test_command_files_exist() -> None:
    assert _DIGRESS.is_file(), "claude-harness/commands/digress.md must exist"
    assert _RESUME.is_file(), "claude-harness/commands/resume.md must exist"


def test_digress_mentions_schema_fields() -> None:
    text = _DIGRESS.read_text(encoding="utf-8")
    # The frame contract the hook and /resume both depend on.
    for field in ("resumePointer", "pushedAt", "plan", "phase", "reason", "repo"):
        assert field in text, f"digress.md must document the schema field '{field}'"
    assert "workstreams.json" in text, "digress.md must name the state file"


def test_digress_documents_idempotency_guard() -> None:
    # Improvement #2: parking the same plan twice updates in place, never duplicates.
    assert "idempotency" in _DIGRESS.read_text(encoding="utf-8").lower(), \
        "digress.md must document the idempotency guard (no duplicate frames for the same plan)"


def test_resume_handles_empty_stack_explicitly() -> None:
    assert "Nothing is parked" in _RESUME.read_text(encoding="utf-8"), \
        "resume.md must handle the empty/absent-stack case with the exact words 'Nothing is parked'"


def test_resume_pops_lifo() -> None:
    lower = _RESUME.read_text(encoding="utf-8").lower()
    assert "lifo" in lower or "last element" in lower, \
        "resume.md must state it pops the LIFO top-of-stack frame"


def test_commands_never_instruct_destructive_git() -> None:
    for path in (_DIGRESS, _RESUME):
        lower = path.read_text(encoding="utf-8").lower()
        for bad in _DESTRUCTIVE:
            # The commands may only mention these under an explicit prohibition ("never ... git checkout").
            if bad in lower:
                assert "never" in lower, (
                    f"{path.name} references '{bad}' — it must only appear inside a "
                    f"'never run a destructive git action' prohibition"
                )


def test_handoff_suggests_digress() -> None:
    assert "/digress" in _HANDOFF.read_text(encoding="utf-8"), \
        "handoff.md must point an abandoned mid-flight plan at /digress"
