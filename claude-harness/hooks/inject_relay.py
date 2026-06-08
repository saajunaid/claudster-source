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
if os.path.isfile(RELAY):
    try:
        text = open(RELAY, encoding="utf-8").read().strip()
    except Exception:
        sys.exit(0)
    if text:
        print("\n=== relay.md (session resume — read before acting) ===\n")
        print(text)

sys.exit(0)
