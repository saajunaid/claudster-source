"""
tests/test_orchestrator_gaps.py
================================
Structural validation tests for orchestrator.agent.md changes introduced by
GAP-I3, GAP-I4, and GAP-I5.

Coverage requirements (from pipeline-state.json handoff_payload):
  CR-1  §9 table — 5 columns, 6 data rows, Recommended mode + Rationale values
  CR-2  §9 mode recommendation output block — format and instructions present
  CR-3  §9.1 Multi-Item Intake — classification table (7 rows), 5-step protocol,
         boundary definitions, decomposed-list code block
  CR-4  §13 Pipeline Halt & Recovery Protocol — halt format string, 5-cause
         recovery table, 5-step resumption, "All resumption must go through" sentinel
  CR-5  No regressions — §1–§8, §10–§12 headings still present
"""

from __future__ import annotations

import re
import textwrap
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# File fixture
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[4]
ORCHESTRATOR_PATH = REPO_ROOT / ".github" / "agents" / "orchestrator.agent.md"


@pytest.fixture(scope="module")
def doc() -> str:
    """Return the full text of orchestrator.agent.md."""
    assert ORCHESTRATOR_PATH.exists(), (
        f"orchestrator.agent.md not found at {ORCHESTRATOR_PATH}"
    )
    return ORCHESTRATOR_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_section(doc: str, heading: str) -> str:
    """
    Return all content from *heading* line up to (but not including) the next
    '---' horizontal rule or end of file.  Raises AssertionError if not found.
    """
    idx = doc.find(heading)
    assert idx != -1, f"Heading not found: {heading!r}"
    end = doc.find("\n---", idx)
    return doc[idx:] if end == -1 else doc[idx:end]


def _is_separator_row(line: str) -> bool:
    """Return True if the line is a Markdown table separator (|---|---|...|)."""
    stripped = line.strip()
    if not (stripped.startswith("|") and stripped.endswith("|")):
        return False
    # Remove all pipe characters; what remains must be only dashes, colons, spaces
    inner = stripped.replace("|", "")
    return bool(inner) and bool(re.match(r"^[\s\-:]+$", inner))


def _count_table_data_rows(section: str) -> int:
    """Count non-header, non-separator Markdown table rows in the FIRST table."""
    rows = 0
    in_table = False
    header_consumed = False
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            if _is_separator_row(stripped):
                continue
            if not header_consumed:
                # First non-separator pipe row = column header; skip it
                header_consumed = True
                in_table = True
                continue
            in_table = True
            rows += 1
        elif in_table:
            break  # table ended
    return rows


def _table_column_headers(section: str) -> list[str]:
    """Return normalised column header names from the first Markdown table found."""
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            return [c.strip().lower() for c in stripped.strip("|").split("|")]
    return []


# ===========================================================================
# CR-1  §9 Intake Protocol table (GAP-I3)
# ===========================================================================

class TestSection9Table:  # CR-1

    def test_section9_heading_present(self, doc: str) -> None:
        assert "### 9. Intake Protocol" in doc, "§9 Intake Protocol heading missing"

    def test_section9_table_has_five_columns(self, doc: str) -> None:
        section = _extract_section(doc, "### 9. Intake Protocol")
        headers = _table_column_headers(section)
        assert len(headers) == 5, (
            f"Expected 5 columns in §9 table, found {len(headers)}: {headers}"
        )

    def test_section9_table_has_six_data_rows(self, doc: str) -> None:
        section = _extract_section(doc, "### 9. Intake Protocol")
        # Pull just the table (up to blank line after table)
        rows = _count_table_data_rows(section)
        assert rows == 6, f"Expected 6 data rows in §9 table, found {rows}"

    def test_section9_table_recommended_mode_column_present(self, doc: str) -> None:
        section = _extract_section(doc, "### 9. Intake Protocol")
        headers = _table_column_headers(section)
        assert "recommended mode" in " ".join(headers).lower(), (
            f"'Recommended mode' column not found in §9 table headers: {headers}"
        )

    def test_section9_table_rationale_column_present(self, doc: str) -> None:
        section = _extract_section(doc, "### 9. Intake Protocol")
        headers = _table_column_headers(section)
        assert "rationale" in " ".join(headers).lower(), (
            f"'Rationale' column not found in §9 table headers: {headers}"
        )

    @pytest.mark.parametrize("expected_mode", ["supervised", "either", "assisted"])
    def test_section9_table_contains_mode_values(self, doc: str, expected_mode: str) -> None:
        section = _extract_section(doc, "### 9. Intake Protocol")
        assert expected_mode in section, (
            f"Expected mode value '{expected_mode}' not found in §9 table"
        )

    def test_section9_table_six_scenarios_cover_all_types(self, doc: str) -> None:
        """Verify key scenario phrases are present — guards against row deletion."""
        section = _extract_section(doc, "### 9. Intake Protocol")
        required_phrases = [
            "new feature",
            "need architecture",
            "need implementation",
            "known root cause",
            "unknown root cause",
            "deferred items",
        ]
        missing = [p for p in required_phrases if p.lower() not in section.lower()]
        assert not missing, f"Missing scenario phrases in §9 table: {missing}"


# ===========================================================================
# CR-2  §9 Mode recommendation output block (GAP-I3)
# ===========================================================================

class TestSection9ModeRecommendationBlock:  # CR-2

    def test_mode_recommendation_block_heading_present(self, doc: str) -> None:
        section = _extract_section(doc, "### 9. Intake Protocol")
        assert "Mode recommendation output" in section, (
            "§9 'Mode recommendation output' block heading missing"
        )

    def test_mode_recommendation_required_label(self, doc: str) -> None:
        section = _extract_section(doc, "### 9. Intake Protocol")
        assert "(required)" in section, (
            "§9 mode recommendation block must be labelled '(required)'"
        )

    def test_mode_recommendation_output_format_present(self, doc: str) -> None:
        """The agent must output a '> **Recommended mode:' blockquote."""
        section = _extract_section(doc, "### 9. Intake Protocol")
        assert "**Recommended mode:" in section, (
            "§9 mode recommendation output format '> **Recommended mode:' not found"
        )

    def test_mode_recommendation_switch_instruction_present(self, doc: str) -> None:
        section = _extract_section(doc, "### 9. Intake Protocol")
        assert "Switch pipeline to" in section, (
            "§9 mode recommendation block missing 'Switch pipeline to' switch instructions"
        )

    def test_mode_recommendation_agent_does_not_change_mode(self, doc: str) -> None:
        """Agent must NOT change pipeline_mode itself — only recommend."""
        section = _extract_section(doc, "### 9. Intake Protocol")
        assert "Do not change" in section, (
            "§9 must explicitly state agent does not change pipeline_mode"
        )


# ===========================================================================
# CR-3  §9.1 Multi-Item Intake (GAP-I5)
# ===========================================================================

class TestSection91MultiItemIntake:  # CR-3

    def test_section91_heading_present(self, doc: str) -> None:
        assert "### 9.1 Multi-Item Intake" in doc, "§9.1 heading missing"

    def test_section91_classification_table_has_seven_rows(self, doc: str) -> None:
        section = _extract_section(doc, "### 9.1 Multi-Item Intake")
        rows = _count_table_data_rows(section)
        assert rows == 7, (
            f"§9.1 classification table: expected 7 data rows, found {rows}"
        )

    @pytest.mark.parametrize("item_type", ["hotfix", "feature", "ad-hoc"])
    def test_section91_classification_table_contains_type(self, doc: str, item_type: str) -> None:
        section = _extract_section(doc, "### 9.1 Multi-Item Intake")
        assert item_type in section, (
            f"§9.1 classification table missing item type: '{item_type}'"
        )

    @pytest.mark.parametrize("step_label", [
        "Step 1",
        "Step 2",
        "Step 3",
        "Step 4",
        "Step 5",
    ])
    def test_section91_five_steps_present(self, doc: str, step_label: str) -> None:
        section = _extract_section(doc, "### 9.1 Multi-Item Intake")
        assert step_label in section, (
            f"§9.1 missing protocol step: {step_label}"
        )

    def test_section91_decomposed_list_code_block_present(self, doc: str) -> None:
        """The agent must output a numbered list code block for item decomposition."""
        section = _extract_section(doc, "### 9.1 Multi-Item Intake")
        # Code block should contain the decomposed-list pattern
        assert "```" in section, "§9.1 must contain a code block for decomposed list output"
        assert "Shall I start with item 1" in section, (
            "§9.1 code block must end with confirmation prompt 'Shall I start with item 1'"
        )

    def test_section91_boundary_what_counts_as_multiple_items(self, doc: str) -> None:
        section = _extract_section(doc, "### 9.1 Multi-Item Intake")
        assert "What counts as" in section or "more than one distinct work item" in section, (
            "§9.1 must define what counts as more than one distinct work item"
        )

    def test_section91_boundary_what_does_not_need_decomposition(self, doc: str) -> None:
        section = _extract_section(doc, "### 9.1 Multi-Item Intake")
        assert "does NOT need decomposition" in section or "does not need decomposition" in section.lower(), (
            "§9.1 must define what does NOT need decomposition"
        )

    def test_section91_one_pipeline_at_a_time_rule(self, doc: str) -> None:
        section = _extract_section(doc, "### 9.1 Multi-Item Intake")
        assert "one pipeline at a time" in section.lower(), (
            "§9.1 Step 4 must state 'Run one pipeline at a time'"
        )

    def test_section91_ad_hoc_no_pipeline_init_rule(self, doc: str) -> None:
        section = _extract_section(doc, "### 9.1 Multi-Item Intake")
        assert "Do not create or modify" in section, (
            "§9.1 must instruct agent NOT to create/modify pipeline-state.json for ad-hoc items"
        )


# ===========================================================================
# CR-4  §13 Pipeline Halt & Recovery Protocol (GAP-I4)
# ===========================================================================

class TestSection13HaltProtocol:  # CR-4

    def test_section13_heading_present(self, doc: str) -> None:
        assert "### 13. Pipeline Halt & Recovery Protocol" in doc, "§13 heading missing"

    def test_section13_halt_format_uses_stop_sign(self, doc: str) -> None:
        section = _extract_section(doc, "### 13. Pipeline Halt & Recovery Protocol")
        assert "⛔ Pipeline halted." in section, (
            "§13 halt output must contain exactly '⛔ Pipeline halted.'"
        )

    def test_section13_halt_format_shows_reason(self, doc: str) -> None:
        section = _extract_section(doc, "### 13. Pipeline Halt & Recovery Protocol")
        assert "Reason:" in section, "§13 halt format must include 'Reason:' field"

    def test_section13_halt_format_shows_stage(self, doc: str) -> None:
        section = _extract_section(doc, "### 13. Pipeline Halt & Recovery Protocol")
        assert "Stage:" in section, "§13 halt format must include 'Stage:' field"

    def test_section13_recovery_table_has_five_rows(self, doc: str) -> None:
        section = _extract_section(doc, "### 13. Pipeline Halt & Recovery Protocol")
        rows = _count_table_data_rows(section)
        assert rows == 5, (
            f"§13 recovery table: expected 5 data rows, found {rows}"
        )

    @pytest.mark.parametrize("cause_phrase", [
        "artefact_exists",
        "artefact_approved",
        "Gate unsatisfied",
        "retry budget exhausted",
        "Blocking escalation",
    ])
    def test_section13_recovery_table_contains_cause(self, doc: str, cause_phrase: str) -> None:
        section = _extract_section(doc, "### 13. Pipeline Halt & Recovery Protocol")
        assert cause_phrase in section, (
            f"§13 recovery table missing cause: '{cause_phrase}'"
        )

    def test_section13_resumption_five_numbered_steps(self, doc: str) -> None:
        """After user resolves, there should be a 5-step numbered list."""
        section = _extract_section(doc, "### 13. Pipeline Halt & Recovery Protocol")
        numbered = re.findall(r"^\s*\d+\.", section, re.MULTILINE)
        assert len(numbered) >= 5, (
            f"§13 resumption steps: expected at least 5 numbered steps, found {len(numbered)}"
        )

    def test_section13_all_resumption_through_orchestrator(self, doc: str) -> None:
        section = _extract_section(doc, "### 13. Pipeline Halt & Recovery Protocol")
        assert "All resumption must go through" in section, (
            "§13 must state 'All resumption must go through @Orchestrator'"
        )

    def test_section13_agents_must_never_self_resume(self, doc: str) -> None:
        section = _extract_section(doc, "### 13. Pipeline Halt & Recovery Protocol")
        assert "Agents must never self-resume" in section, (
            "§13 must contain the rule 'Agents must never self-resume'"
        )


# ===========================================================================
# CR-5  No regressions — core section headings still present
# ===========================================================================

class TestNoRegressions:  # CR-5

    @pytest.mark.parametrize("heading", [
        "## Core Responsibilities",
        "### 1. Read Pipeline State First",
        "### 2. Validate Artefact Contracts",
        "### 3. Routing Logic",
        "### 4. Supervision Gates",
        "### 5.",
        "### 6.",
        "### 7.",
        "### 8.",
        "### 9. Intake Protocol",
        "### 10. Pipeline Close Protocol",
        "### 11.",
        "### 12.",
    ])
    def test_core_section_present(self, doc: str, heading: str) -> None:
        assert heading in doc, f"Regression: section heading missing from orchestrator.agent.md: {heading!r}"

    def test_section1_read_state_first_rule_intact(self, doc: str) -> None:
        """§1 must still tell the agent to read pipeline-state.json first."""
        assert "Always** read `.github/pipeline-state.json`" in doc or \
               "**Always** read `.github/pipeline-state.json`" in doc, \
            "§1 'Always read pipeline-state.json' instruction missing or altered"

    def test_section10_pipeline_close_protocol_intact(self, doc: str) -> None:
        section = _extract_section(doc, "### 10. Pipeline Close Protocol")
        assert "review_approved" in section, (
            "§10 Pipeline Close Protocol: 'review_approved' gate reference missing"
        )
        assert "validate_deferred_paths" in section, (
            "§10 Pipeline Close Protocol: 'validate_deferred_paths' tool reference missing"
        )

    def test_output_contract_table_intact(self, doc: str) -> None:
        assert "## Output Contract" in doc, "Output Contract section missing"
        assert "pipeline-state.json" in doc.split("## Output Contract")[1][:500], (
            "Output Contract section appears truncated or altered"
        )

    def test_routing_decision_template_intact(self, doc: str) -> None:
        assert "## Routing Decision Template" in doc, "Routing Decision Template section missing"

    def test_frontmatter_agent_name_unchanged(self, doc: str) -> None:
        assert "name: Orchestrator" in doc, "Frontmatter 'name: Orchestrator' missing"

    def test_handoffs_still_declare_tester(self, doc: str) -> None:
        assert "agent: Tester" in doc, "Handoff to Tester agent removed from frontmatter"
