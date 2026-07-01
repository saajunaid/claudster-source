"""Unit tests for claude-harness/scripts/claudster_config.py — the shared config reader.

Fail-open by contract: a missing file, malformed TOML, a missing section, or a wrong-typed value
must all degrade to the caller's default, never raise.
"""

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "claude-harness" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claudster_config as cc  # noqa: E402


def _write_cfg(root: Path, text: str) -> None:
    d = root / ".claudster"
    d.mkdir(parents=True, exist_ok=True)
    (d / "config.toml").write_text(text, encoding="utf-8")


class TestLoadConfig:
    def test_missing_file_returns_empty(self, tmp_path):
        assert cc.load_config(tmp_path, "guard") == {}

    def test_reads_section(self, tmp_path):
        _write_cfg(tmp_path, "[doc_coverage]\nclaude_md_budget = 400\n")
        assert cc.load_config(tmp_path, "doc_coverage") == {"claude_md_budget": 400}

    def test_missing_section_returns_empty(self, tmp_path):
        _write_cfg(tmp_path, "[guard]\nallow = []\n")
        assert cc.load_config(tmp_path, "dream_memory") == {}

    def test_malformed_toml_returns_empty(self, tmp_path):
        _write_cfg(tmp_path, "this is not = valid = toml [[[")
        assert cc.load_config(tmp_path, "guard") == {}

    def test_non_table_section_returns_empty(self, tmp_path):
        _write_cfg(tmp_path, "doc_coverage = 5\n")  # a scalar, not a table
        assert cc.load_config(tmp_path, "doc_coverage") == {}


class TestCoercion:
    def test_get_int_valid(self):
        assert cc.get_int({"n": 42}, "n", 10) == 42

    def test_get_int_rejects_bool_zero_and_nonint(self):
        assert cc.get_int({"n": True}, "n", 10) == 10   # bool is not a valid int here
        assert cc.get_int({"n": 0}, "n", 10) == 10       # must be >= 1
        assert cc.get_int({"n": "5"}, "n", 10) == 10     # string, not int
        assert cc.get_int({}, "n", 10) == 10             # missing

    def test_get_str_valid_and_fallbacks(self):
        assert cc.get_str({"s": "x.ts"}, "s", "d") == "x.ts"
        assert cc.get_str({"s": "   "}, "s", "d") == "d"  # blank falls back
        assert cc.get_str({"s": 5}, "s", "d") == "d"      # non-str falls back
        assert cc.get_str({}, "s", "d") == "d"

    def test_get_str_list_valid_and_fallbacks(self):
        assert cc.get_str_list({"l": ["/a", "/b"]}, "l", []) == ["/a", "/b"]
        assert cc.get_str_list({"l": ["/a", 3]}, "l", ["/d"]) == ["/d"]  # mixed types → default
        assert cc.get_str_list({"l": "notalist"}, "l", ["/d"]) == ["/d"]
        assert cc.get_str_list({}, "l", ["/d"]) == ["/d"]
