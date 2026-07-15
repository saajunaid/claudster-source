# Inspection prompts

Operational, **internal** prompts for auditing this toolchain — deliberately kept OUT of the distributable
skill pool (`.github/prompts/` is the published pool with a frontmatter/model contract; these are not that).

## What's here
- **`fable-inspect-claudster.md`** — a deep, adversarial read-only inspection of the **claudster** repo.
- **`fable-inspect-docket.md`** — the same for **docket** (adds UI/UX and web-specific dimensions).

Both are written for **Fable** (`claude-fable-5`) but work with any capable model.

## How to run (pick one)

**A. Claude Code CLI, headless, from the target repo:**
```bash
# claudster
cd E:\Projects\claudster-source
claude --model claude-fable-5 -p "$(cat prompts/fable-inspect-claudster.md)"

# docket (run from the docket repo so file paths resolve)
cd E:\Projects\docket
claude --model claude-fable-5 -p "$(cat E:\Projects\claudster-source\prompts\fable-inspect-docket.md)"
```

**B. As a subagent from a claudster session:** ask the agent to "run the Fable inspection in
`prompts/fable-inspect-claudster.md` as a Fable subagent." (It will dispatch an Agent with `model: fable`.)

## Notes
- These are **read-only audits** — the prompts forbid changing code. Fixes are a separate, human-triaged step.
- Each run returns a **ranked findings report** (severity + file:line + fix). Save the output to
  `docs/analysis/` if you want it tracked.
- Re-run after fixes to confirm findings are resolved and nothing regressed.
