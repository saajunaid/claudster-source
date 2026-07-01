"""Unit tests for claude-harness/scripts/dream_memory.py — the Dream Memory consolidation engine.

Phase 5a: the pure consolidation core (merge / prune / conflicts / rank_for_surfacing) ported from
fann-core's consolidator.ts, plus the fail-open JSONL glue. The pure functions take dicts in and
return dicts out — no filesystem — so they test verbatim; the glue tests use tmp_path.

The module lives under claude-harness/scripts/ (NOT the repo-root scripts/), so the shim points there.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "claude-harness" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import dream_memory as dm  # noqa: E402


def _fact(kind, key, summary, *, hits=1, first="2026-07-01T09:00:00Z", last=None, source="auto", evidence=None):
    """Terse fact builder for tests. last defaults to first (single observation)."""
    f = {
        "kind": kind,
        "key": key,
        "summary": summary,
        "hitCount": hits,
        "firstSeen": first,
        "lastSeen": last or first,
        "source": source,
    }
    if evidence:
        f["evidence"] = evidence
    return f


# --------------------------------------------------------------------------- #
# Pure helpers
# --------------------------------------------------------------------------- #
class TestNormalizeAndFingerprint:
    def test_normalize_lowercases_trims_collapses_whitespace(self):
        assert dm.normalize_key("  Pytest   Import-Error\n") == "pytest import-error"

    def test_normalize_handles_empty_and_none(self):
        assert dm.normalize_key("") == ""
        assert dm.normalize_key(None) == ""

    def test_fingerprint_is_kind_scoped(self):
        a = _fact("failure-mode", "X", "s")
        b = _fact("workflow-success", "X", "s")
        assert dm.fingerprint(a) != dm.fingerprint(b)

    def test_fingerprint_normalizes_key(self):
        a = _fact("failure-mode", "Pytest Import", "s")
        b = _fact("failure-mode", "pytest   import", "s2")
        assert dm.fingerprint(a) == dm.fingerprint(b)

    def test_fingerprint_falls_back_to_summary_when_key_empty(self):
        a = _fact("repo-fact", "", "uses uv for deps")
        assert dm.fingerprint(a) == "repo-fact:uses uv for deps"


class TestParseIso:
    def test_parses_z_suffix(self):
        assert dm._parse_iso("2026-07-01T09:00:00Z").tzinfo is not None

    def test_unparseable_is_epoch_floor(self):
        assert dm._parse_iso("not-a-date") == dm._EPOCH
        assert dm._parse_iso("") == dm._EPOCH

    def test_naive_string_gets_utc(self):
        assert dm._parse_iso("2026-07-01T09:00:00").tzinfo is not None

    def test_ordering_is_chronological(self):
        assert dm._parse_iso("2026-07-01T08:00:00Z") < dm._parse_iso("2026-07-01T09:00:00Z")


class TestValidation:
    def test_well_formed_fact_is_valid(self):
        assert dm.is_valid_fact(_fact("failure-mode", "k", "s"))

    def test_missing_field_is_invalid(self):
        f = _fact("failure-mode", "k", "s")
        del f["lastSeen"]
        assert not dm.is_valid_fact(f)

    def test_unknown_kind_is_invalid(self):
        assert not dm.is_valid_fact(_fact("random-kind", "k", "s"))

    def test_non_dict_is_invalid(self):
        assert not dm.is_valid_fact("nope")
        assert not dm.is_valid_fact(None)

    def test_bad_hitcount_is_invalid(self):
        assert not dm.is_valid_fact(_fact("failure-mode", "k", "s", hits=0))
        assert not dm.is_valid_fact(_fact("failure-mode", "k", "s", hits="3"))
        # bool is not a valid hitCount even though bool is a subclass of int
        assert not dm.is_valid_fact(_fact("failure-mode", "k", "s", hits=True))

    def test_blank_summary_is_invalid(self):
        assert not dm.is_valid_fact(_fact("failure-mode", "k", "   "))

    def test_make_fact_is_valid_single_hit(self):
        f = dm.make_fact("failure-mode", "k", "s", "2026-07-01T09:00:00Z")
        assert dm.is_valid_fact(f)
        assert f["hitCount"] == 1
        assert f["firstSeen"] == f["lastSeen"] == "2026-07-01T09:00:00Z"

    def test_make_fact_omits_empty_evidence(self):
        assert "evidence" not in dm.make_fact("repo-fact", "k", "s", "2026-07-01T09:00:00Z")
        assert dm.make_fact("repo-fact", "k", "s", "2026-07-01T09:00:00Z", evidence="t.py")["evidence"] == "t.py"


# --------------------------------------------------------------------------- #
# merge — reinforce + dedup
# --------------------------------------------------------------------------- #
class TestMerge:
    def test_distinct_fingerprints_pass_through(self):
        facts = [_fact("failure-mode", "a", "sa"), _fact("repo-fact", "b", "sb")]
        out = dm.merge(facts)
        assert len(out) == 2

    def test_same_fingerprint_sums_hitcount(self):
        facts = [
            _fact("failure-mode", "pytest", "fails", hits=1),
            _fact("failure-mode", "pytest", "fails", hits=1),
            _fact("failure-mode", "pytest", "fails", hits=2),
        ]
        out = dm.merge(facts)
        assert len(out) == 1
        assert out[0]["hitCount"] == 4

    def test_firstseen_is_min_lastseen_is_max(self):
        facts = [
            _fact("failure-mode", "x", "s", first="2026-07-01T10:00:00Z", last="2026-07-01T10:00:00Z"),
            _fact("failure-mode", "x", "s", first="2026-07-01T08:00:00Z", last="2026-07-01T12:00:00Z"),
        ]
        out = dm.merge(facts)
        assert out[0]["firstSeen"] == "2026-07-01T08:00:00Z"
        assert out[0]["lastSeen"] == "2026-07-01T12:00:00Z"

    def test_newest_summary_wins(self):
        facts = [
            _fact("failure-mode", "x", "old summary", last="2026-07-01T08:00:00Z"),
            _fact("failure-mode", "x", "new summary", last="2026-07-01T12:00:00Z"),
        ]
        out = dm.merge(facts)
        assert out[0]["summary"] == "new summary"

    def test_older_member_does_not_overwrite_newer_summary(self):
        # Order: newer first, then older — the older must NOT clobber the summary/source.
        facts = [
            _fact("failure-mode", "x", "new", last="2026-07-01T12:00:00Z", source="knowledge-transfer"),
            _fact("failure-mode", "x", "old", last="2026-07-01T08:00:00Z", source="auto"),
        ]
        out = dm.merge(facts)
        assert out[0]["summary"] == "new"
        assert out[0]["source"] == "knowledge-transfer"

    def test_evidence_carried_from_newest(self):
        facts = [
            _fact("failure-mode", "x", "s", last="2026-07-01T08:00:00Z", evidence="old.py"),
            _fact("failure-mode", "x", "s", last="2026-07-01T12:00:00Z", evidence="new.py"),
        ]
        out = dm.merge(facts)
        assert out[0]["evidence"] == "new.py"

    def test_insertion_order_of_first_appearance_preserved(self):
        facts = [
            _fact("repo-fact", "z", "sz"),
            _fact("failure-mode", "a", "sa"),
            _fact("repo-fact", "z", "sz2", last="2026-07-01T12:00:00Z"),
        ]
        out = dm.merge(facts)
        assert [f["key"] for f in out] == ["z", "a"]

    def test_inputs_not_mutated(self):
        original = _fact("failure-mode", "x", "s", hits=1)
        snapshot = dict(original)
        dm.merge([original, _fact("failure-mode", "x", "s", hits=1)])
        assert original == snapshot

    def test_empty_input(self):
        assert dm.merge([]) == []


# --------------------------------------------------------------------------- #
# prune — decay + cap
# --------------------------------------------------------------------------- #
class TestPrune:
    NOW = "2026-07-20T09:00:00Z"

    def test_single_hit_older_than_14_days_decays(self):
        facts = [_fact("failure-mode", "old", "s", hits=1, last="2026-07-01T09:00:00Z")]
        assert dm.prune(facts, self.NOW) == []  # 19 days old, one hit → gone

    def test_single_hit_within_window_survives(self):
        facts = [_fact("failure-mode", "fresh", "s", hits=1, last="2026-07-18T09:00:00Z")]
        assert len(dm.prune(facts, self.NOW)) == 1

    def test_reinforced_fact_never_decays(self):
        # Two hits, 19 days old — survives because decay only removes single-hit noise.
        facts = [_fact("failure-mode", "old", "s", hits=2, last="2026-07-01T09:00:00Z")]
        assert len(dm.prune(facts, self.NOW)) == 1

    def test_cap_keeps_top_by_hitcount_then_recency(self):
        facts = [
            _fact("repo-fact", "a", "sa", hits=1, last="2026-07-19T09:00:00Z"),
            _fact("repo-fact", "b", "sb", hits=5, last="2026-07-10T09:00:00Z"),
            _fact("repo-fact", "c", "sc", hits=3, last="2026-07-19T09:00:00Z"),
        ]
        out = dm.prune(facts, self.NOW, cap=2)
        assert [f["key"] for f in out] == ["b", "c"]  # hitCount desc wins over recency

    def test_cap_breaks_ties_by_recency(self):
        facts = [
            _fact("repo-fact", "older", "s", hits=2, last="2026-07-10T09:00:00Z"),
            _fact("repo-fact", "newer", "s2", hits=2, last="2026-07-19T09:00:00Z"),
        ]
        out = dm.prune(facts, self.NOW, cap=1)
        assert out[0]["key"] == "newer"

    def test_now_accepts_datetime(self):
        now = datetime(2026, 7, 20, 9, 0, 0, tzinfo=timezone.utc)
        facts = [_fact("failure-mode", "old", "s", hits=1, last="2026-07-01T09:00:00Z")]
        assert dm.prune(facts, now) == []

    def test_inputs_not_mutated(self):
        facts = [_fact("repo-fact", "a", "s", hits=1, last="2026-07-19T09:00:00Z")]
        snapshot = [dict(f) for f in facts]
        dm.prune(facts, self.NOW)
        assert facts == snapshot

    def test_empty_input(self):
        assert dm.prune([], self.NOW) == []


# --------------------------------------------------------------------------- #
# conflicts
# --------------------------------------------------------------------------- #
class TestConflicts:
    def test_same_fingerprint_different_summary_flagged(self):
        facts = [
            _fact("failure-mode", "build", "run vite build first"),
            _fact("failure-mode", "build", "delete node_modules first"),
        ]
        out = dm.conflicts(facts)
        assert len(out) == 1
        assert out[0]["key"] == "build"
        assert len(out[0]["summaries"]) == 2

    def test_same_summary_modulo_whitespace_is_not_a_conflict(self):
        facts = [
            _fact("failure-mode", "build", "Run Vite  Build"),
            _fact("failure-mode", "build", "run vite build"),
        ]
        assert dm.conflicts(facts) == []

    def test_different_fingerprints_never_conflict(self):
        facts = [
            _fact("failure-mode", "a", "sa"),
            _fact("failure-mode", "b", "sb"),
        ]
        assert dm.conflicts(facts) == []

    def test_summaries_in_first_seen_order(self):
        facts = [
            _fact("failure-mode", "x", "first version"),
            _fact("failure-mode", "x", "second version"),
        ]
        assert dm.conflicts(facts)[0]["summaries"] == ["first version", "second version"]

    def test_empty_input(self):
        assert dm.conflicts([]) == []


# --------------------------------------------------------------------------- #
# rank_for_surfacing
# --------------------------------------------------------------------------- #
class TestRankForSurfacing:
    def test_limits_to_n(self):
        facts = [_fact("repo-fact", str(i), f"s{i}", hits=1) for i in range(10)]
        assert len(dm.rank_for_surfacing(facts, 5)) == 5

    def test_weighted_kinds_outrank_equal_hitcount(self):
        facts = [
            _fact("repo-fact", "plain", "plain", hits=2),
            _fact("failure-mode", "danger", "danger", hits=2),
        ]
        out = dm.rank_for_surfacing(facts, 2)
        assert out[0]["kind"] == "failure-mode"  # 2x weight breaks the tie

    def test_hitcount_dominates_within_a_weight_class(self):
        facts = [
            _fact("repo-fact", "low", "low", hits=1),
            _fact("repo-fact", "high", "high", hits=9),
        ]
        out = dm.rank_for_surfacing(facts, 2)
        assert out[0]["key"] == "high"

    def test_now_applies_recency_decay(self):
        # Same kind & hitCount; with `now`, the more recent fact wins on recency.
        facts = [
            _fact("repo-fact", "stale", "stale", hits=3, last="2026-06-01T09:00:00Z"),
            _fact("repo-fact", "fresh", "fresh", hits=3, last="2026-07-19T09:00:00Z"),
        ]
        out = dm.rank_for_surfacing(facts, 2, now="2026-07-20T09:00:00Z")
        assert out[0]["key"] == "fresh"

    def test_recency_can_outweigh_hitcount_with_now(self):
        # A very stale high-hit fact can fall behind a fresh lower-hit one once decay applies.
        facts = [
            _fact("repo-fact", "ancient", "ancient", hits=4, last="2026-01-01T09:00:00Z"),
            _fact("repo-fact", "today", "today", hits=2, last="2026-07-20T09:00:00Z"),
        ]
        out = dm.rank_for_surfacing(facts, 2, now="2026-07-20T09:00:00Z")
        assert out[0]["key"] == "today"

    def test_deterministic_stable_ordering(self):
        facts = [_fact("repo-fact", f"k{i}", f"s{i}", hits=1, last="2026-07-01T09:00:00Z") for i in range(5)]
        assert dm.rank_for_surfacing(facts, 5) == dm.rank_for_surfacing(list(reversed(facts)), 5)

    def test_empty_input(self):
        assert dm.rank_for_surfacing([], 5) == []


# --------------------------------------------------------------------------- #
# consolidate — merge then prune
# --------------------------------------------------------------------------- #
class TestConsolidate:
    def test_merges_then_prunes(self):
        facts = [
            _fact("failure-mode", "x", "s", hits=1, last="2026-07-19T09:00:00Z"),
            _fact("failure-mode", "x", "s", hits=1, last="2026-07-19T10:00:00Z"),
            _fact("repo-fact", "old", "s", hits=1, last="2026-07-01T09:00:00Z"),  # decays
        ]
        out = dm.consolidate(facts, "2026-07-20T09:00:00Z")
        assert len(out) == 1
        assert out[0]["key"] == "x"
        assert out[0]["hitCount"] == 2

    def test_merge_rescues_a_would_be_decayed_fact(self):
        # Two single observations of the same old fact merge to hitCount=2 → survives decay.
        facts = [
            _fact("failure-mode", "x", "s", hits=1, last="2026-07-01T09:00:00Z"),
            _fact("failure-mode", "x", "s", hits=1, last="2026-07-01T09:30:00Z"),
        ]
        out = dm.consolidate(facts, "2026-07-20T09:00:00Z")
        assert len(out) == 1
        assert out[0]["hitCount"] == 2


# --------------------------------------------------------------------------- #
# Filesystem glue — fail-open & silent.
# --------------------------------------------------------------------------- #
class TestLoadTunables:
    def test_defaults_when_no_config(self, tmp_path):
        t = dm.load_tunables(tmp_path)
        assert t == {"prune_age_days": dm.PRUNE_AGE_DAYS, "max_facts": dm.MAX_FACTS,
                     "surface_limit": dm.SURFACE_LIMIT}

    def test_reads_overrides(self, tmp_path):
        (tmp_path / ".claudster").mkdir()
        (tmp_path / ".claudster" / "config.toml").write_text(
            "[dream_memory]\nprune_age_days = 30\nmax_facts = 50\nsurface_limit = 8\n", encoding="utf-8")
        t = dm.load_tunables(tmp_path)
        assert t == {"prune_age_days": 30, "max_facts": 50, "surface_limit": 8}

    def test_partial_override_keeps_other_defaults(self, tmp_path):
        (tmp_path / ".claudster").mkdir()
        (tmp_path / ".claudster" / "config.toml").write_text(
            "[dream_memory]\nsurface_limit = 3\n", encoding="utf-8")
        t = dm.load_tunables(tmp_path)
        assert t["surface_limit"] == 3
        assert t["max_facts"] == dm.MAX_FACTS  # untouched key keeps its default

    def test_bad_value_falls_back(self, tmp_path):
        (tmp_path / ".claudster").mkdir()
        (tmp_path / ".claudster" / "config.toml").write_text(
            '[dream_memory]\nmax_facts = "lots"\n', encoding="utf-8")
        assert dm.load_tunables(tmp_path)["max_facts"] == dm.MAX_FACTS


class TestLoadSave:
    def test_missing_file_returns_empty(self, tmp_path):
        assert dm.load_facts(tmp_path / "nope.jsonl") == []

    def test_round_trips_valid_facts(self, tmp_path):
        store = tmp_path / "memory.jsonl"
        facts = [_fact("failure-mode", "a", "sa"), _fact("repo-fact", "b", "sb", evidence="t.py")]
        assert dm.save_facts(store, facts) is True
        loaded = dm.load_facts(store)
        assert loaded == facts

    def test_skips_blank_and_malformed_lines(self, tmp_path):
        store = tmp_path / "memory.jsonl"
        good = '{"kind":"failure-mode","key":"a","summary":"s","hitCount":1,' \
               '"firstSeen":"2026-07-01T09:00:00Z","lastSeen":"2026-07-01T09:00:00Z","source":"auto"}'
        store.write_text("\n".join(["", good, "{not json", "  ", '{"kind":"bad"}']), encoding="utf-8")
        loaded = dm.load_facts(store)
        assert len(loaded) == 1
        assert loaded[0]["key"] == "a"

    def test_save_empty_writes_empty_file(self, tmp_path):
        store = tmp_path / "memory.jsonl"
        assert dm.save_facts(store, []) is True
        assert dm.load_facts(store) == []

    def test_save_creates_parent_dirs(self, tmp_path):
        store = tmp_path / ".claudster" / "memory.jsonl"
        assert dm.save_facts(store, [_fact("repo-fact", "a", "s")]) is True
        assert store.exists()

    def test_unicode_preserved_round_trip(self, tmp_path):
        store = tmp_path / "memory.jsonl"
        f = _fact("failure-mode", "build", "run `vite` first — don't poll ⚠")
        dm.save_facts(store, [f])
        assert dm.load_facts(store)[0]["summary"] == f["summary"]


class TestFormatSurface:
    def test_weighted_kinds_get_warning_mark(self):
        lines = dm._format_surface([_fact("failure-mode", "x", "danger", hits=3)])
        assert "⚠" in lines[0]
        assert "(×3)" in lines[0]

    def test_single_hit_has_no_count_suffix(self):
        lines = dm._format_surface([_fact("repo-fact", "x", "plain", hits=1)])
        assert "×" not in lines[0]
        assert "⚠" not in lines[0]
