"""Unit tests for claude-harness/scripts/dream_capture.py — deterministic Dream Memory capture (5b).

Pure transcript → fact-candidate extraction + privacy redaction. Everything here is filesystem-free
(synthetic transcript records in → fact dicts out), so it tests directly; the wired Stop hook is
covered by a subprocess test in claude-harness/hooks/tests/test_hook_paths.py.

The privacy tests are the load-bearing ones: a secret must never reach the store's key or summary.
"""

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "claude-harness" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import dream_capture as dc  # noqa: E402
import dream_memory as dm  # noqa: E402


# --------------------------------------------------------------------------- #
# Transcript record builders (mimic the Claude Code JSONL shape).
# --------------------------------------------------------------------------- #
def _tool_use(tid, command, name="Bash"):
    return {"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "tool_use", "id": tid, "name": name, "input": {"command": command}},
    ]}}


def _tool_result(tid, output="", is_error=False):
    return {"type": "user", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": tid, "content": output, "is_error": is_error},
    ]}}


NOW = "2026-07-20T09:00:00Z"


# --------------------------------------------------------------------------- #
# Redaction — the privacy core.
# --------------------------------------------------------------------------- #
class TestRedact:
    def test_env_assignment_value_redacted(self):
        assert dc.redact("API_KEY=sk-abc123def456") == "API_KEY=***"
        assert dc.redact("export DB_PASSWORD='hunter2'") == "export DB_PASSWORD=***"
        assert dc.redact("SECRET_TOKEN = abcdef") == "SECRET_TOKEN=***"

    def test_url_credentials_redacted(self):
        assert dc.redact("git clone https://user:p4ss@github.com/x/y") == "git clone https://***:***@github.com/x/y"

    def test_flag_secret_redacted(self):
        out = dc.redact("curl --token mytoken123 https://api")
        assert "mytoken123" not in out
        assert "--token ***" in out

    def test_bearer_and_auth_header_redacted(self):
        assert "abc.def.ghi" not in dc.redact("curl -H 'Authorization: Bearer abc.def.ghi'")

    def test_known_token_prefixes_redacted(self):
        assert "ghp_" not in dc.redact("echo ghp_0123456789abcdefABCDEF")
        assert "AKIA" not in dc.redact("aws AKIAIOSFODNN7EXAMPLE")

    def test_long_high_entropy_blob_redacted(self):
        blob = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2"  # 44 chars, letters+digits
        assert blob not in dc.redact(f"deploy --sig {blob}")

    def test_mysql_attached_password_flag_redacted(self):
        # `-pVALUE` glued (MySQL/MariaDB) — no space/= separator.
        out = dc.redact("mysql -uroot -pSecretPass123 mydb")
        assert "SecretPass123" not in out
        assert "-p***" in out
        assert "Hunter2" not in dc.redact("mysqldump -pHunter2 db")  # value gone, cmd survives
        assert "S3cr3t" not in dc.redact('mariadb -p"S3cr3t pass" db')  # quoted value

    def test_attached_p_flag_not_over_redacted(self):
        # `-p` in non-mysql contexts must survive untouched.
        for cmd in ("cp -pr src dst", "mkdir -p a/b/c", "docker run -p 8080:80 img", "ssh -p22 host"):
            assert dc.redact(cmd) == cmd

    def test_aws_secret_access_key_space_separated_redacted(self):
        key = "wJalrXUtnFEMIK7MDENGbPxRfiCYEXAMPLEKEY"
        out = dc.redact(f"aws configure set aws_secret_access_key {key}")
        assert key not in out
        assert "aws_secret_access_key ***" in out
        # existing = form still redacts
        assert "abc" not in dc.redact("aws_secret_access_key=abcdefghij")

    def test_curl_basic_auth_redacted(self):
        out = dc.redact("curl -u admin:hunter2 https://api.example.com")
        assert "hunter2" not in out
        assert "admin:hunter2" not in out
        assert "-u ***" in out
        assert "s3cr3t" not in dc.redact("curl --user bob:s3cr3t https://x")

    def test_dash_u_flag_not_over_redacted(self):
        # `-u` outside curl (python, sort, docker uid) must survive.
        for cmd in ("python -u script.py", "sort -u file.txt", "docker run -u 1000:1000 img"):
            assert dc.redact(cmd) == cmd

    def test_plain_prose_and_paths_untouched(self):
        # No secret → unchanged; file paths must survive (the blob rule excludes '/').
        msg = "ModuleNotFoundError: No module named 'app' in src/app/main.py"
        assert dc.redact(msg) == msg

    def test_empty_is_empty(self):
        assert dc.redact("") == ""
        assert dc.redact(None) == ""


class TestTouchesSecret:
    def test_env_file_flagged(self):
        assert dc.touches_secret("cat .env")
        assert dc.touches_secret("vim backend/.env.production")

    def test_secrets_dir_flagged(self):
        assert dc.touches_secret("ls config/secrets/db.yml")

    def test_key_and_pem_files_flagged(self):
        assert dc.touches_secret("openssl rsa -in server.key")
        assert dc.touches_secret("cat certs/tls.pem")
        assert dc.touches_secret("ssh -i ~/.ssh/id_ed25519 host")

    def test_ordinary_command_not_flagged(self):
        assert not dc.touches_secret("pytest tests/")
        assert not dc.touches_secret("npm run build")


# --------------------------------------------------------------------------- #
# Text shaping
# --------------------------------------------------------------------------- #
class TestShaping:
    def test_command_head_collapses_and_caps(self):
        assert dc.command_head("  npm    run   build  ") == "npm run build"
        assert len(dc.command_head("x " * 100)) <= dc._HEAD_LEN

    def test_first_error_line_skips_blanks_and_caps(self):
        assert dc.first_error_line("\n\n  boom: it broke  \nmore") == "boom: it broke"
        assert dc.first_error_line("") == ""
        assert len(dc.first_error_line("z" * 500)) <= dc._ERR_LEN


# --------------------------------------------------------------------------- #
# extract_facts
# --------------------------------------------------------------------------- #
class TestExtractFailureMode:
    def test_failed_bash_becomes_failure_mode(self):
        recs = [
            _tool_use("t1", "pytest tests/test_api.py"),
            _tool_result("t1", "ImportError: cannot import name 'app'", is_error=True),
        ]
        facts = dc.extract_facts(recs, NOW)
        assert len(facts) == 1
        f = facts[0]
        assert f["kind"] == "failure-mode"
        assert f["source"] == "auto"
        assert "pytest tests/test_api.py" in f["summary"]
        assert "ImportError" in f["summary"]
        assert dm.is_valid_fact(f)

    def test_successful_bash_is_not_captured(self):
        recs = [_tool_use("t1", "pytest"), _tool_result("t1", "ok", is_error=False)]
        # No prior failure → not even a workflow-success.
        assert dc.extract_facts(recs, NOW) == []

    def test_noise_failures_skipped(self):
        recs = [
            _tool_use("t1", "grep needle haystack.txt"),
            _tool_result("t1", "", is_error=True),
            _tool_use("t2", "test -f missing"),
            _tool_result("t2", "", is_error=True),
        ]
        assert dc.extract_facts(recs, NOW) == []

    def test_one_candidate_per_distinct_command_per_session(self):
        recs = [
            _tool_use("t1", "npm run build"),
            _tool_result("t1", "error A", is_error=True),
            _tool_use("t2", "npm run build"),
            _tool_result("t2", "error B", is_error=True),
        ]
        facts = dc.extract_facts(recs, NOW)
        assert len(facts) == 1  # deduped within the session

    def test_non_bash_tool_failures_ignored(self):
        recs = [
            _tool_use("t1", "x", name="Edit"),
            _tool_result("t1", "boom", is_error=True),
        ]
        assert dc.extract_facts(recs, NOW) == []

    def test_unmatched_tool_result_ignored(self):
        recs = [_tool_result("orphan", "boom", is_error=True)]
        assert dc.extract_facts(recs, NOW) == []

    def test_cap_per_run(self):
        recs = []
        for i in range(dc.MAX_FACTS_PER_RUN + 10):
            recs.append(_tool_use(f"t{i}", f"cmd-{i} --do"))
            recs.append(_tool_result(f"t{i}", "err", is_error=True))
        assert len(dc.extract_facts(recs, NOW)) == dc.MAX_FACTS_PER_RUN


class TestExtractWorkflowSuccess:
    def test_red_then_green_build_test_captured(self):
        recs = [
            _tool_use("t1", "pytest tests/"),
            _tool_result("t1", "1 failed", is_error=True),
            _tool_use("t2", "pytest tests/"),
            _tool_result("t2", "5 passed", is_error=False),
        ]
        facts = dc.extract_facts(recs, NOW)
        kinds = {f["kind"] for f in facts}
        assert "workflow-success" in kinds
        succ = next(f for f in facts if f["kind"] == "workflow-success")
        assert "passes now" in succ["summary"]

    def test_green_without_prior_failure_not_captured(self):
        recs = [_tool_use("t1", "pytest tests/"), _tool_result("t1", "ok", is_error=False)]
        assert dc.extract_facts(recs, NOW) == []

    def test_non_build_command_recovery_not_captured(self):
        # A non-build/test command recovering is not a workflow-success (too low signal).
        recs = [
            _tool_use("t1", "mycli deploy"),
            _tool_result("t1", "boom", is_error=True),
            _tool_use("t2", "mycli deploy"),
            _tool_result("t2", "ok", is_error=False),
        ]
        facts = dc.extract_facts(recs, NOW)
        assert all(f["kind"] != "workflow-success" for f in facts)


class TestExtractPrivacy:
    def test_secret_touching_command_not_stored_at_all(self):
        recs = [
            _tool_use("t1", "cat .env && echo done"),
            _tool_result("t1", "boom", is_error=True),
        ]
        assert dc.extract_facts(recs, NOW) == []

    def test_inline_secret_redacted_from_summary_and_key(self):
        recs = [
            _tool_use("t1", "deploy --token ghp_0123456789abcdefABCDEF prod"),
            _tool_result("t1", "auth failed for ghp_0123456789abcdefABCDEF", is_error=True),
        ]
        facts = dc.extract_facts(recs, NOW)
        assert len(facts) == 1
        f = facts[0]
        assert "ghp_" not in f["summary"]
        assert "ghp_" not in f["key"]
        assert "***" in f["summary"]

    def test_env_assignment_secret_redacted_in_key(self):
        recs = [
            _tool_use("t1", "API_KEY=sk-supersecret123456 myapp run"),
            _tool_result("t1", "startup error", is_error=True),
        ]
        facts = dc.extract_facts(recs, NOW)
        assert facts and "sk-supersecret" not in facts[0]["key"]
        assert "sk-supersecret" not in facts[0]["summary"]


class TestExtractRobustness:
    def test_empty_records(self):
        assert dc.extract_facts([], NOW) == []

    def test_malformed_records_ignored(self):
        recs = ["not a dict", {"no": "content"}, {"message": "stringy"}, None]
        assert dc.extract_facts(recs, NOW) == []

    def test_list_form_tool_result_content(self):
        recs = [
            _tool_use("t1", "pytest"),
            {"type": "user", "message": {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "t1",
                 "content": [{"type": "text", "text": "AssertionError: nope"}], "is_error": True},
            ]}},
        ]
        facts = dc.extract_facts(recs, NOW)
        assert len(facts) == 1
        assert "AssertionError" in facts[0]["summary"]

    def test_candidates_feed_consolidation_cleanly(self):
        # End-to-end of the pure path: extract → consolidate must round-trip valid, reinforced facts.
        recs = [
            _tool_use("t1", "npm run build --prod"),
            _tool_result("t1", "build failed", is_error=True),
        ]
        cands = dc.extract_facts(recs, NOW)
        # A pre-existing store entry for the SAME command — a new-format store carries the full-command fp.
        existing = [dm.make_fact("failure-mode", dm.normalize_key(dc.command_head("npm run build --prod")),
                                 "old summary", "2026-07-19T09:00:00Z", source="auto",
                                 fp=dc.command_fp("npm run build --prod"))]
        out = dm.consolidate(existing + cands, NOW)
        assert len(out) == 1
        assert out[0]["hitCount"] == 2  # reinforced across "sessions"

    def test_shared_head_distinct_commands_stay_separate(self):
        # The hitCount-inflation fix: two DIFFERENT commands sharing an 80-char head must NOT collapse
        # into one inflated "lesson" (they dedup on the full-command fp, not the truncated head).
        prefix = "sleep 60; tail -4 " + "x" * 70  # > 80 chars → identical heads, differing tails
        recs = [
            _tool_use("t1", prefix + " AAA"), _tool_result("t1", "boom", is_error=True),
            _tool_use("t2", prefix + " BBB"), _tool_result("t2", "boom", is_error=True),
        ]
        facts = dc.extract_facts(recs, NOW)
        assert len({f["fp"] for f in facts}) == 2       # distinct fingerprints (old code collapsed to 1)
        assert len(dm.consolidate(facts, NOW)) == 2      # not merged into one inflated fact
