# Harness memory model — how claudster remembers across turns, sessions, and repos

claudster layers **four** memory stores, ephemeral → durable. Each has a distinct lifespan, owner,
and trigger. The short-term layer is fully automatic; the durable layers are curated (but prompted).

## The four layers

| Layer | File | Lifespan | Written by | Surfaced by |
|---|---|---|---|---|
| Session relay | `.claudster/relay.md` | one session → next | `/handoff` (you) | `inject_relay.py` @ SessionStart / PreCompact |
| Dream Memory | `.claudster/memory.jsonl` | days, self-decaying | **hooks (automatic)** | `inject_relay.py` @ SessionStart (top ≤5) |
| KB (this dir) | `.claudster/kb/*.md` + `DOC-MAP.md` | project lifetime | you / knowledge-transfer agent | `inject_relay.py` prints a "read DOC-MAP first" pointer |
| Cross-repo memory | `~/.claude/projects/<slug>/memory/*.md` + `MEMORY.md` | forever, all repos | the agent | loaded into context each session |

**Design intent:** a fact starts ephemeral in Dream Memory; if it keeps recurring it is *promoted*
up into the KB or cross-repo memory, then allowed to *decay* out of the jsonl — short-term working
memory that reinforces or forgets.

## What's automatic (Dream Memory) — no commands

Wired in the plugin's `hooks/hooks.json`, active in every repo where claudster is enabled:

- **Capture** — on `Stop`, `session_end.py` → `dream_capture.py` mines the transcript for two
  LLM-free, high-confidence kinds: `failure-mode` (a Bash command that errored) and
  `workflow-success` (a build/test command that went red → green in the same session).
- **Consolidate** — the same Stop hook runs `merge → prune`: dedup by fingerprint, reinforce
  (`hitCount++`) on recurrence, decay single-hit facts after 14 days, cap at 200.
- **Surface** — on `SessionStart` / `PreCompact`, the top ≤5 reinforced facts print
  (failure-modes / rejected-approaches weighted up).
- **Privacy** — commands touching secret files (`.env`, `*.pem`, `secrets/`) are skipped entirely;
  inline tokens/keys are redacted before storage. Safe to surface and commit.
- **Fail-open** — every step is wrapped and silent; memory must never slow or break a turn.

The store auto-creates on the first qualifying event — nothing to seed.

## What's curated (relay / KB / cross-repo)

- **relay.md** — `/handoff` writes it; the Stop hook nudges you.
- **KB notes** — `.claudster/kb/<topic>.md`, written by you or the knowledge-transfer subagent.
  Index each as a link in `DOC-MAP.md` or the gate warns (orphan). The richer fact kinds
  (`rejected-approach`, `repo-fact`) that can't be inferred without an LLM also come from that agent.
- **Cross-repo memory** — durable facts that apply across projects (preferences, conventions).

## Discipline / gate

`claude-harness/scripts/check_doc_coverage.py` (pre-push): every DOC-MAP link must resolve
(dangling = **hard failure**); a KB note not indexed in DOC-MAP **warns** (orphan). Only
`.claudster/kb/*.md` is governed — the wider repo docs are not policed. Maintain the index with
`/kb` (`--reindex` to add/scaffold, `--prune` to remove dangling rows).

## Known limits

Accepted trade-offs (prune scope, discovery-on-create, concurrent-session races) live in
[`docs/known-limits.md`](../../docs/known-limits.md) — read it before "fixing" one as a bug.

## Fact schema (memory.jsonl)

One JSON object per line: `kind`, `key` (dedup), `summary`, `hitCount`, `firstSeen`, `lastSeen`,
`source` (`auto` | `knowledge-transfer` | `manual`), optional `evidence`. Fingerprint =
`kind + ":" + normalize(key)`. Inspect/compact manually with
`python claude-harness/scripts/dream_memory.py --consolidate` (the Stop hook already does this).

## Source

Engine: `claude-harness/scripts/dream_memory.py` (pure consolidation core) + `dream_capture.py`
(transcript mining). Hooks: `claude-harness/hooks/{session_end,inject_relay}.py`. Ported from
fann-core's `consolidator.ts`; design doc referenced as `.claudster/plans/dream-memory-design.md`
(a deployed-project artifact, not in this source repo).
