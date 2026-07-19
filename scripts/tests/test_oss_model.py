"""Tests for claude-harness/scripts/oss_model.py — the shared provider+keys resolver
for the model-switching launchers (Track A).

Keys are resolved, never hardcoded. Precedence: explicit env key -> keys file
(CLAUDSTER_KEYS_FILE, default ~/.claudster/keys.env) -> ConfigError. The provider
preset table mirrors oss_review.py; env always overrides.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "claude-harness" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import oss_model as om  # noqa: E402


def _keys_file(tmp_path: Path, body: str) -> str:
    p = tmp_path / "keys.env"
    p.write_text(body, encoding="utf-8")
    return str(p)


def test_preset_defaults_resolve():
    r = om.resolve("glm", {"GLM_API_KEY": "k"})
    assert r["base_url"] == om.PROVIDERS["glm"]["base_url"]
    assert r["model"] == om.PROVIDERS["glm"]["model"]
    assert r["api_key"] == "k"


def test_env_key_wins_over_keys_file(tmp_path):
    kf = _keys_file(tmp_path, "GLM_API_KEY=fromfile\n")
    r = om.resolve("glm", {"GLM_API_KEY": "fromenv", "CLAUDSTER_KEYS_FILE": kf})
    assert r["api_key"] == "fromenv"


def test_keys_file_fallback(tmp_path):
    kf = _keys_file(tmp_path, "GLM_API_KEY=fromfile\n")
    r = om.resolve("glm", {"CLAUDSTER_KEYS_FILE": kf})
    assert r["api_key"] == "fromfile"


def test_keys_file_ignores_comments_and_blanks(tmp_path):
    kf = _keys_file(tmp_path, "# a comment\n\n  \nDEEPSEEK_API_KEY = \"spaced\"  \n")
    r = om.resolve("deepseek", {"CLAUDSTER_KEYS_FILE": kf})
    assert r["api_key"] == "spaced"


def test_missing_key_raises_actionable(tmp_path):
    kf = _keys_file(tmp_path, "SOMETHING_ELSE=x\n")
    with pytest.raises(om.ConfigError) as ei:
        om.resolve("glm", {"CLAUDSTER_KEYS_FILE": kf})
    assert "GLM_API_KEY" in str(ei.value)


def test_unknown_provider_without_override_errors():
    with pytest.raises(om.ConfigError):
        om.resolve("bogus", {"OSS_API_KEY": "k"})


def test_unknown_provider_with_explicit_base_and_model_ok():
    r = om.resolve(
        "bogus",
        {"OSS_BASE_URL": "https://x.example/v1", "OSS_MODEL": "m", "OSS_API_KEY": "k"},
    )
    assert r["base_url"] == "https://x.example/v1"
    assert r["model"] == "m"
    assert r["api_key"] == "k"


def test_base_url_trailing_slash_trimmed():
    r = om.resolve(
        "bogus",
        {"OSS_BASE_URL": "https://x.example/v1/", "OSS_MODEL": "m", "OSS_API_KEY": "k"},
    )
    assert r["base_url"] == "https://x.example/v1"


def test_env_model_and_base_override_preset():
    r = om.resolve(
        "glm",
        {"GLM_API_KEY": "k", "OSS_MODEL": "custom-model", "OSS_BASE_URL": "https://alt/v9"},
    )
    assert r["model"] == "custom-model"
    assert r["base_url"] == "https://alt/v9"


def test_default_provider_is_deepseek():
    r = om.resolve(None, {"DEEPSEEK_API_KEY": "k"})
    assert r["base_url"] == om.PROVIDERS["deepseek"]["base_url"]


def test_generic_oss_api_key_fallback():
    # A single OSS_API_KEY works for any provider that lacks its specific key.
    r = om.resolve("glm", {"OSS_API_KEY": "generic"})
    assert r["api_key"] == "generic"


def test_resolve_never_returns_key_in_base_or_model():
    r = om.resolve("glm", {"GLM_API_KEY": "supersecret"})
    assert "supersecret" not in r["base_url"]
    assert "supersecret" not in r["model"]
