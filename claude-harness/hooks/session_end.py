"""Session-end nudge + token-usage digest on Stop.

Two jobs, both non-blocking (prints, exits 0; never fails a turn):
  1. Remind the operator to persist what survives context death (relay.md + lessons).
  2. Summarise this session's token usage from the transcript, print a digest, and
     append one line to `.claude/usage-log.jsonl` so spend is trackable over time.

The usage parse is fully defensive: any missing/odd field just drops the digest and
still prints the nudge. Cost is a rough ESTIMATE from an editable per-model rate table —
adjust PRICING_PER_MTOK to your actual plan/rates (or ignore cost and read the tokens).
Cross-platform (pure Python, stdlib only).
"""
import json
import os
import sys
from datetime import datetime, timezone

_reconfig = getattr(sys.stdout, "reconfigure", None)
if _reconfig:
    try:
        _reconfig(encoding="utf-8")
    except Exception:
        pass

# ── editable: approximate USD per 1M tokens (input, output). Cache read ≈ 0.1× input,
#    cache write ≈ 1.25× input. These are estimates — set them to your real rates. ──
PRICING_PER_MTOK = {
    "opus":   (15.0, 75.0),
    "sonnet": (3.0, 15.0),
    "haiku":  (1.0, 5.0),
}


def _tier(model: str) -> str:
    m = (model or "").lower()
    if "opus" in m:
        return "opus"
    if "sonnet" in m:
        return "sonnet"
    if "haiku" in m:
        return "haiku"
    return "sonnet"  # safe middle estimate for unknown/local models


def _read_input() -> dict:
    try:
        return json.load(sys.stdin) or {}
    except Exception:
        return {}


def _summarise(transcript_path: str) -> dict | None:
    """Sum token usage across assistant messages in the transcript JSONL."""
    if not transcript_path or not os.path.isfile(transcript_path):
        return None
    tot = {"input": 0, "output": 0, "cache_write": 0, "cache_read": 0}
    models: dict[str, int] = {}
    cost = 0.0
    found = False
    try:
        with open(transcript_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except Exception:
                    continue
                msg = ev.get("message") if isinstance(ev.get("message"), dict) else ev
                usage = msg.get("usage") if isinstance(msg, dict) else None
                if not isinstance(usage, dict):
                    continue
                found = True
                i = int(usage.get("input_tokens", 0) or 0)
                o = int(usage.get("output_tokens", 0) or 0)
                cw = int(usage.get("cache_creation_input_tokens", 0) or 0)
                cr = int(usage.get("cache_read_input_tokens", 0) or 0)
                tot["input"] += i
                tot["output"] += o
                tot["cache_write"] += cw
                tot["cache_read"] += cr
                model = (msg.get("model") if isinstance(msg, dict) else "") or ""
                if model:
                    models[model] = models.get(model, 0) + 1
                inp, outp = PRICING_PER_MTOK[_tier(model)]
                cost += (i * inp + cw * inp * 1.25 + cr * inp * 0.1 + o * outp) / 1_000_000
    except Exception:
        return None
    if not found:
        return None
    tot["billable_input"] = tot["input"] + tot["cache_write"] + tot["cache_read"]
    tot["est_cost_usd"] = round(cost, 4)
    tot["models"] = sorted(models)
    return tot


def _fmt(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}k"
    return str(n)


data = _read_input()

print(
    "\n[HARNESS] Session ending. Two things survive context death:\n"
    "  1. relay.md — refresh it so the next session resumes exactly (run /handoff).\n"
    "  2. Durable lessons — if you wrote or fixed code this session, dispatch the\n"
    "     knowledge-transfer subagent BEFORE relay.md. Don't skip it just because you\n"
    "     hand-wrote some docs. Record the outcome in relay.md's 'Learnings captured' line."
)

u = _summarise(data.get("transcript_path", ""))
if u:
    print(
        f"\n[USAGE] this session ~ in {_fmt(u['input'])} · out {_fmt(u['output'])} · "
        f"cache {_fmt(u['cache_write'] + u['cache_read'])} "
        f"({_fmt(u['cache_read'])} read) · est. ${u['est_cost_usd']:.2f} "
        f"(estimate — edit rates in session_end.py)"
    )
    try:
        os.makedirs(".claude", exist_ok=True)
        rec = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "session": data.get("session_id", ""),
            "input": u["input"], "output": u["output"],
            "cache_write": u["cache_write"], "cache_read": u["cache_read"],
            "est_cost_usd": u["est_cost_usd"], "models": u["models"],
        }
        with open(os.path.join(".claude", "usage-log.jsonl"), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
    except Exception:
        pass

sys.exit(0)
