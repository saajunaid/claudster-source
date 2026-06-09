"""Inject relay.md into context at SessionStart / PreCompact.

The harness loop treats relay.md as the durable session-resume doc. Printing it to
stdout from a SessionStart/PreCompact hook surfaces it in the next context window, so a
fresh session resumes with zero re-discovery. No-ops silently when relay.md is absent.
Cross-platform (pure Python) — works the same on Windows, Linux, and macOS.
"""
import json
import os
import sys

# relay.md may contain any Unicode; force UTF-8 so a narrow Windows console
# (cp1252/cp437) can't raise UnicodeEncodeError or mangle the output.
_reconfig = getattr(sys.stdout, "reconfigure", None)
if _reconfig:
    try:
        _reconfig(encoding="utf-8")
    except Exception:
        pass

# Drain the event payload on stdin (we don't need any fields, but reading avoids
# a broken pipe on some platforms).
try:
    json.load(sys.stdin)
except Exception:
    pass

RELAY = "relay.md"
INJECT_MAX_LINES = 120

def _truncate_relay(text: str) -> str:
    """Cap injected output at INJECT_MAX_LINES.

    Preserves the header, Current workstream, Done header (with count summary),
    Next step, and everything from Read first on resume to end.  The Done
    bullets are the unbounded part — they get replaced with a one-liner so the
    section that matters (Next step / Resume prompt) is never pushed off-screen.
    Graceful degradation: if section headers can't be found, returns text as-is.
    """
    lines = text.splitlines()
    if len(lines) <= INJECT_MAX_LINES:
        return text

    done_idx = next_step_idx = read_first_idx = None
    for i, line in enumerate(lines):
        s = line.strip()
        if done_idx is None and s.startswith("## Done"):
            done_idx = i
        elif next_step_idx is None and s.startswith("## Next step"):
            next_step_idx = i
        elif read_first_idx is None and s.startswith("## Read first on resume"):
            read_first_idx = i
            break

    if None in (done_idx, next_step_idx, read_first_idx):
        return text  # can't parse — print full rather than lose data

    done_bullets = [l for l in lines[done_idx + 1:next_step_idx] if l.strip().startswith("-")]
    omitted = len(done_bullets)
    summary = f"- [Done section truncated — {omitted} bullets omitted to save context; see git log]"
    truncated = lines[:done_idx + 1] + [summary, ""] + lines[next_step_idx:]
    return "\n".join(truncated)


if os.path.isfile(RELAY):
    try:
        text = open(RELAY, encoding="utf-8").read().strip()
    except Exception:
        sys.exit(0)
    if text:
        print("\n=== relay.md (session resume — read before acting) ===\n")
        print(_truncate_relay(text))

sys.exit(0)
