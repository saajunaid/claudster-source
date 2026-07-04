"""Guard the headless-mode convention in the interview-style commands.

A live smoke (2026-07-04) found headless `/prd` would INTERVIEW on a terse one-line
card (bare title, no description) instead of writing the artifact — breaking the core
OLID use case. The fix strengthened the `## Headless mode` sections to never ask and to
write a best-effort artifact with gaps captured under an open-questions section. This is
a content lint: it does NOT prove model behavior (that needs a live `claude -p` smoke),
it prevents the never-ask guarantees from being quietly removed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_COMMANDS = _REPO / "claude-harness" / "commands"

# (file, gaps-section-heading it must route unknowns into)
_HEADLESS_COMMANDS = [
    ("prd.md", "Open questions"),
    ("feature-plan.md", "Constraints & decisions"),
]


@pytest.mark.parametrize("filename,gaps_section", _HEADLESS_COMMANDS)
def test_headless_section_forbids_interview(filename: str, gaps_section: str) -> None:
    text = (_COMMANDS / filename).read_text(encoding="utf-8")
    assert "## Headless mode" in text, f"{filename}: missing '## Headless mode' section"
    assert "HEADLESS RUN RULES" in text, f"{filename}: missing the HEADLESS RUN RULES marker"

    lower = text.lower()
    # Hard never-ask guarantees (the OLID robustness the live smoke proved is needed).
    assert "never ask" in lower, f"{filename}: must state it NEVER asks in headless mode"
    assert "bare title" in lower, f"{filename}: must state a bare title is sufficient input"
    assert "assumption" in lower, f"{filename}: must tell the model to make explicit assumptions"
    assert "askuserquestion" in lower, f"{filename}: must forbid AskUserQuestion"
    # Gaps go to a section, not to the user; and a highlights block always terminates the run.
    assert gaps_section.lower() in lower, f"{filename}: must route unknowns into '## {gaps_section}'"
    assert "highlights block" in lower, f"{filename}: must require the final json highlights block"
