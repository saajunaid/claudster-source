"""Session-end nudge on Stop.

Reminds the operator to persist the two things that survive context death: the
relay.md resume doc and any durable lessons. Non-blocking — prints and exits 0.
Cross-platform (pure Python).
"""
import json
import sys

# Force UTF-8 stdout so the em-dash can't raise UnicodeEncodeError on a narrow
# Windows console (cp1252/cp437).
_reconfig = getattr(sys.stdout, "reconfigure", None)
if _reconfig:
    try:
        _reconfig(encoding="utf-8")
    except Exception:
        pass

try:
    json.load(sys.stdin)
except Exception:
    pass

print(
    "\n[HARNESS] Session ending — update relay.md so the next session resumes exactly, "
    "and extract any durable lessons to docs/gold-nuggets-log.md."
)

sys.exit(0)
