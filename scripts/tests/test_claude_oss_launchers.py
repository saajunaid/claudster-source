"""Content-lint for the claude-oss / claude-glm launchers (Track A, Phase A2).

No live `claude` is invoked — these assert the launcher SOURCE has the required
shape: it resolves via oss_model.py, sets the ANTHROPIC_* env, passes args through,
restores/isolates env, and NEVER writes the key to stdout.
"""
from __future__ import annotations

from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "claude-harness" / "scripts"
PS1_PATH = SCRIPTS / "claude-oss.ps1"
SH_PATH = SCRIPTS / "claude-oss.sh"


def test_launchers_exist():
    assert PS1_PATH.is_file()
    assert SH_PATH.is_file()


def test_set_anthropic_env():
    for src in (PS1_PATH.read_text(encoding="utf-8"), SH_PATH.read_text(encoding="utf-8")):
        assert "ANTHROPIC_BASE_URL" in src
        assert "ANTHROPIC_AUTH_TOKEN" in src
        assert "ANTHROPIC_MODEL" in src


def test_call_the_shared_resolver():
    for src in (PS1_PATH.read_text(encoding="utf-8"), SH_PATH.read_text(encoding="utf-8")):
        assert "oss_model.py" in src


def test_pass_args_through():
    assert '"$@"' in SH_PATH.read_text(encoding="utf-8")
    ps1 = PS1_PATH.read_text(encoding="utf-8")
    assert "@rest" in ps1 or "@args" in ps1


def test_ps1_uses_args_not_param():
    # Learned bug: a param() block captures `-p` before claude sees it. Use $args.
    ps1 = PS1_PATH.read_text(encoding="utf-8").lower()
    assert "param(" not in ps1
    assert "$args" in ps1


def test_ps1_restores_env_on_exit():
    ps1 = PS1_PATH.read_text(encoding="utf-8").lower()
    assert "finally" in ps1


def test_glm_alias_present():
    for src in (PS1_PATH.read_text(encoding="utf-8"), SH_PATH.read_text(encoding="utf-8")):
        assert "claude-glm" in src


def test_never_writes_key_to_stdout():
    danger = ("echo ", "write-host", "write-output", "print(")
    secret_refs = ("anthropic_auth_token", "api_key", "cfg[2]", "cfg[3]")
    for src in (PS1_PATH.read_text(encoding="utf-8"), SH_PATH.read_text(encoding="utf-8")):
        for raw in src.splitlines():
            line = raw.strip().lower()
            if any(d in line for d in danger):
                assert not any(s in line for s in secret_refs), f"key echoed: {raw!r}"
