# Providers & keys

This page explains the **three model lanes**, the two paid providers behind them, where your keys live, and how to switch models without ever getting confused about billing.

## The core idea (removes all confusion)

**An API key is just identity — the command and endpoint decide the model and the billing.** You don't manage keys per task; each command is wired to the right endpoint and reads its key for you.

| Lane | You run | Model | Billing |
|---|---|---|---|
| **Primary** | `claude` | Anthropic | your Claude plan |
| **Coding fallback** | `claude-glm` | GLM Coding Plan | flat monthly **subscription** |
| **Reviewer** | `/claudster:cross-review` (or `oss_review.py`) | DeepSeek | **pay-per-token** (pennies) |

"Switching models" = which of those you type. That's the whole model.

## The two providers

| | **GLM Coding Plan (Z.ai)** | **DeepSeek** |
|---|---|---|
| Role | Coding fallback / bulk work | Cross-vendor reviewer |
| Billing | Flat **subscription** (e.g. Lite ~$18/mo) | **Pay-per-token** (~$0.003 per review) |
| Why this one | Best in-harness tool-caller; native Anthropic-compatible endpoint → drop-in for Claude Code | Most *architecturally different* from Claude → catches different bugs; strong reasoning; bursty + cheap |
| Endpoint | `https://api.z.ai/api/anthropic` (Claude Code) / `.../coding/paas/v4` | `https://api.deepseek.com` |

**Why GLM for coding, DeepSeek for review?** It's strengths-to-role matching, not just cost. GLM is Claude-Code-native and the most reliable tool-caller, which is what a *coding driver* needs — and a flat subscription suits the high-volume role. DeepSeek is the most different lens from Claude (the point of a *second opinion*), reasons well about what could go wrong in a diff, and its pay-per-token model is perfect for bursty, low-volume review.

## Where keys live

Every tool resolves keys the same way, never hardcoded — precedence: an explicit env var
(`GLM_API_KEY` / `DEEPSEEK_API_KEY` / `OPENROUTER_API_KEY`, or the generic `OSS_API_KEY`) wins;
otherwise a **keys file** at `$CLAUDSTER_KEYS_FILE` (default **`~/.claudster/keys.env`**), `KEY=VALUE`
lines, `#` comments allowed:

```
# deepseek
DEEPSEEK_API_KEY=sk-…            # ← cross-review + claude-oss deepseek read this

# z.ai GLM Coding Plan
GLM_API_KEY=…                    # ← claude-glm / claude-oss glm reads this
```

- **DeepSeek key** → pay-per-token from your prepaid balance → used by cross-review / `claude-oss deepseek`.
- **GLM Coding Plan key** → draws down your flat subscription quota → used by `claude-glm` / `claude-oss glm`.

Both are "API keys"; they bill completely differently because of the plan behind each. No key ever
prints to the console — a missing key exits with a message naming the exact env var to set.

## How to switch — the three commands

```powershell
# Primary — your normal session on Anthropic
claude

# Coding fallback — same Claude Code, running on GLM (subscription)
claude-glm                 # interactive
claude-glm -p "refactor X" # headless
claude-oss glm -p "..."    # equivalent, explicit form (any provider: claude-oss <provider>)
# (claude-harness/scripts/claude-oss.{sh,ps1} — resolves the key, sets the endpoint for
#  THIS process only, restores env on exit, so your normal `claude` stays on Anthropic.
#  See /claudster:use-model for the full reference.)

# Reviewer — a second-vendor review of the current diff (DeepSeek by default)
$env:REVIEW_API_KEY = <deepseek-key>
python .github/tools/oss_review.py                     # working tree
python .github/tools/oss_review.py --range origin/main..HEAD
```

First-time install (adds `claude-oss`/`claude-glm` to your shell): `/setup-project-ai` prints the
one-liner for your platform — it never silently edits your shell profile.

Cross-review exit codes: **0 = clean, 1 = blocking, 2 = error, 3 = no key**.

## Switching the reviewer's model (and future-proofing)

The cross-review tool ships **provider presets** so you never memorize URLs:

```powershell
python .github/tools/oss_review.py --provider glm          # review with GLM instead of DeepSeek
python .github/tools/oss_review.py --provider openrouter   # or OpenRouter
```

Model names churn. Two layers keep it from ever breaking:

1. **The preset table** in `oss_review.py` is the single place a renamed model/URL is edited.
2. **Env always wins** — `REVIEW_MODEL` / `REVIEW_BASE_URL` override any preset, so you can point at a brand-new model id with **zero code change**:

```powershell
$env:REVIEW_MODEL = "deepseek-v5-turbo"   # whatever the current id is
```

The default DeepSeek model is `deepseek-v4-flash` (the older `deepseek-chat` name was retired).

## Good to know

- **DeepSeek peak pricing.** DeepSeek charges 2× during peak UTC windows (`01:00–04:00` and `06:00–10:00`). For reviews this is *negligible* (half a cent vs a quarter-cent) — don't optimize for it. Your heavy lane (GLM) is a flat subscription and is unaffected.
- **Rotate a leaked key.** If a key ever ends up somewhere public, regenerate it in the provider console and update your `$CLAUDSTER_KEYS_FILE` (or the env var, if that's how you set it). Every tool reads it fresh each run, so nothing else needs changing.
- **docket harnesses are separate.** docket's own pipeline picks a model CLI via `agent_track.harness` (claude-code / gemini / antigravity / codex). That's independent of these terminal lanes — see the **docket** tab.
