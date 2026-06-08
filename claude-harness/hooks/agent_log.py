"""Append each subagent's verdict to agent-log.jsonl on SubagentStop.

One JSON line per dispatched subagent: timestamp, agent name, and a truncated verdict.
This is the data source for the /agent-log command (a flight recorder of subagent
activity). Failures are swallowed — logging must never break a session.
Cross-platform (pure Python).
"""
import datetime
import json
import sys

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

record = {
    "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "agent": data.get("agent_name", "unknown"),
    "verdict": str(data.get("result", ""))[:300],
}

try:
    with open("agent-log.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
except Exception:
    pass

sys.exit(0)
