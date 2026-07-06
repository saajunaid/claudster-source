"""Content-lint the /claudster:implement driver (A8.3).

The docket Implement lane spawns this command autonomously (no human present) and then
independently re-runs the tests + a code-review to decide success. The runner's safety
invariants (A8-MINI-PRD) only hold if the driver's own instructions never tell the model
to do the things the runner treats as tampering/escape. This is a content lint — it does
NOT prove model behavior (that needs the human A8.6 live smoke); it prevents the
safety-critical guarantees from being quietly removed from the command text.
"""

from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_IMPLEMENT = _REPO / "claude-harness" / "commands" / "implement.md"


def _text() -> str:
    return _IMPLEMENT.read_text(encoding="utf-8")


def test_implement_command_exists() -> None:
    assert _IMPLEMENT.is_file(), "claude-harness/commands/implement.md must exist (A8.3 driver)"


def test_headless_never_asks() -> None:
    lower = _text().lower()
    # No human is present — the driver must never interview or pause (the /prd-class failure).
    assert "never ask" in lower, "implement.md must state it NEVER asks a question"
    assert "askuserquestion" in lower, "implement.md must forbid AskUserQuestion"
    assert "no human" in lower, "implement.md must state no human is present"


def test_branch_isolation_rules_present() -> None:
    text = _text()
    lower = text.lower()
    # Invariant 1: never leave / switch / create branches; the runner enforces this at COMMIT.
    assert "only on the current branch" in lower, \
        "implement.md must say to work ONLY on the current branch"
    assert "git checkout" in lower and "git switch" in lower, \
        "implement.md must explicitly forbid git checkout / git switch"
    assert "DOCKET_BRANCH" in text, "implement.md must reference the DOCKET_BRANCH env var"
    assert "DOCKET_DEFAULT_BRANCH" in text, \
        "implement.md must reference DOCKET_DEFAULT_BRANCH (refuse the default branch)"


def test_no_remotes() -> None:
    lower = _text().lower()
    # Invariant: the runner never pushes; neither does the driver.
    assert "git push" in lower, "implement.md must forbid git push"
    assert "remote" in lower, "implement.md must forbid touching git remotes"
    assert "--no-verify" in lower, \
        "implement.md must forbid --no-verify (the pre-commit branch guard must run)"


def test_tamper_guard_present() -> None:
    text = _text()
    lower = text.lower()
    # Invariant 2: the session must not edit its own success criteria.
    assert "PROJECT-FACTS.md" in text, \
        "implement.md must name PROJECT-FACTS.md as off-limits (tamper guard)"
    assert "success criteria" in lower, \
        "implement.md must state it never edits its own success criteria"


def test_commit_per_phase_and_tracker() -> None:
    lower = _text().lower()
    assert "commit per phase" in lower, "implement.md must require a commit per phase"
    assert "tracker" in lower, "implement.md must require updating the plan's Tracker"
    assert "tdd" in lower or "red" in lower and "green" in lower, \
        "implement.md must drive TDD-first (RED/GREEN)"


def test_writes_review_and_runs_tests() -> None:
    text = _text()
    lower = text.lower()
    assert "DOCKET_REVIEW" in text, "implement.md must write to the DOCKET_REVIEW path"
    assert ".claudster/reviews/" in text, "implement.md must name the reviews dir"
    # It runs the tests itself (truthful reporting) even though the runner re-runs them.
    assert "run the tests yourself" in lower or "run the project's full test command" in lower, \
        "implement.md must tell the driver to run the tests itself"


def test_ends_with_json_block() -> None:
    text = _text()
    # The runner parses the final {"implemented":...} block via _implement_json.
    assert '"implemented"' in text and '"phases_done"' in text, \
        "implement.md must require the final implemented/phases_done JSON block"
    assert '"tests":"passed|failed"' in text or '"tests"' in text, \
        "implement.md must require the tests field in the JSON block"
    assert '"review"' in text, "implement.md must require the review path in the JSON block"
