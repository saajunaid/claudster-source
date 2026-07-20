"""Content-lint + syntax coverage for sync.ps1 (closes the Fable "no tests around
export/validate/sync.ps1" tail — export and validate already have suites).

No live git/network is touched — these assert the SOURCE has the required shape:
it parses as valid PowerShell, every `git push` site consults $LASTEXITCODE (the
Fable #8 class: a failed push must never be reported as success), the entry-point
functions exist, and no private / pre-rebrand markers are present.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

SYNC_PS1 = Path(__file__).resolve().parents[2] / "sync.ps1"
SOURCE = SYNC_PS1.read_text(encoding="utf-8-sig")
LINES = SOURCE.splitlines()


def test_exists():
    assert SYNC_PS1.is_file()


def test_utf8_bom_present():
    # sync.ps1 is dot-sourced by PowerShell profiles, including Windows
    # PowerShell 5.1, which misreads UTF-8 source without a BOM (real breakage:
    # non-ASCII in throw messages turns to mojibake mid-error).
    assert SYNC_PS1.read_bytes()[:3] == b"\xef\xbb\xbf"


def test_body_is_ascii():
    # Belt to the BOM's braces: an ASCII-only body means a stripped BOM can
    # never change behavior under 5.1 again.
    body = SYNC_PS1.read_bytes()[3:]
    non_ascii = sorted({b for b in body if b > 0x7F})
    assert not non_ascii, f"non-ASCII bytes in sync.ps1 body: {non_ascii}"


@pytest.mark.skipif(shutil.which("pwsh") is None, reason="pwsh not on PATH")
def test_parses_as_valid_powershell():
    path_sq = str(SYNC_PS1).replace("'", "''")
    check = (
        "$t=$null;$e=$null;"
        f"[System.Management.Automation.Language.Parser]::ParseFile('{path_sq}',[ref]$t,[ref]$e)|Out-Null;"
        "if($e.Count -gt 0){$e|ForEach-Object{$_.ToString()};exit 1}"
    )
    r = subprocess.run(
        ["pwsh", "-NoProfile", "-NonInteractive", "-Command", check],
        capture_output=True, text=True, timeout=120,
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_every_git_push_checks_lastexitcode():
    # Fable #8: a failed push must never be reported as success. Every push
    # SITE (a line that runs `git push`, not prose mentioning it) must consult
    # $LASTEXITCODE within the next 3 lines.
    unchecked = []
    for i, line in enumerate(LINES):
        if re.match(r"\s*git push\b", line):
            window = "\n".join(LINES[i + 1 : i + 4])
            if "$LASTEXITCODE" not in window:
                unchecked.append(f"line {i + 1}: {line.strip()}")
    assert not unchecked, "git push without an exit check:\n" + "\n".join(unchecked)


def test_entry_point_functions_defined():
    for fn in ("junai-pull", "junai-push", "junai-revert"):
        assert re.search(rf"^function {re.escape(fn)}\b", SOURCE, re.M), fn


def test_publish_is_opt_in():
    # Bare `junai-push` = mirror sync only; publishing hides behind -Publish.
    assert "[switch]$Publish" in SOURCE


def test_no_private_or_prerebrand_markers():
    lowered = SOURCE.lower()
    for marker in ("iegbcoppoc", "gitea.internal", "vmie_bot_token", "agent-sandbox"):
        assert marker not in lowered, f"marker present: {marker}"
