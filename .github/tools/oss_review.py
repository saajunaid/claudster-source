#!/usr/bin/env python3
"""Cross-vendor code review via any OpenAI-compatible chat-completions endpoint.

A different vendor's model has different blind spots, so a second model reviewing your diff
catches bugs a same-vendor reviewer misses. This tool is provider-agnostic: point it at
DeepSeek (default — cheapest + most architecturally distinct from Claude), GLM, OpenRouter,
or any OpenAI-compatible `/chat/completions` endpoint via three env vars.

Config (CLI flag overrides env; env is the norm):
  REVIEW_BASE_URL   base URL, no trailing /chat/completions   (default https://api.deepseek.com)
  REVIEW_API_KEY    bearer token                              (REQUIRED — no key ⇒ exit 3)
  REVIEW_MODEL      model id                                  (default deepseek-chat)

Usage:
  python oss_review.py [--range <git range>] [--cwd <repo>] [--base-url U] [--model M]
    --range   e.g. origin/main..HEAD   (default: the working tree, i.e. staged+unstaged)

Exit codes (fail-closed):
  0  REVIEW: CLEAN      — no blocking issues
  1  REVIEW: BLOCKING   — one or more blocking issues
  2  error              — no diff verdict parsed, git failure, or endpoint/parse failure
  3  misconfigured      — REVIEW_API_KEY missing (actionable message on stderr)

Stdlib-only (urllib) so it runs anywhere with no pip install.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

EXIT_CLEAN = 0
EXIT_BLOCKING = 1
EXIT_ERROR = 2
EXIT_CONFIG = 3

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"


class ConfigError(Exception):
    """Raised when required configuration (an API key) is absent."""


def resolve_config(args: argparse.Namespace, env: dict[str, str]) -> tuple[str, str, str]:
    """(base_url, api_key, model) from flags-over-env. Raises ConfigError if no key."""
    base_url = (args.base_url or env.get("REVIEW_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    model = args.model or env.get("REVIEW_MODEL") or DEFAULT_MODEL
    api_key = (env.get("REVIEW_API_KEY") or "").strip()
    if not api_key:
        raise ConfigError(
            "REVIEW_API_KEY is not set. Export your provider key first, e.g.\n"
            "  PowerShell:  $env:REVIEW_API_KEY = <your-provider-key>\n"
            "  bash:        export REVIEW_API_KEY=<your-provider-key>"
        )
    return base_url, api_key, model


def get_diff(rng: str | None, cwd: str) -> str:
    """The unified diff for `rng` (e.g. 'origin/main..HEAD'), or the working tree when None.

    Working tree = staged + unstaged against HEAD (`git diff HEAD`). Raises on git failure so
    main() maps it to EXIT_ERROR rather than reviewing an empty diff as CLEAN.
    """
    cmd = ["git", "diff", rng] if rng else ["git", "diff", "HEAD"]
    out = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=30)
    if out.returncode != 0:
        raise RuntimeError(f"git diff failed: {out.stderr.strip()}")
    return out.stdout


def current_branch(cwd: str) -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd, capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip() or "the current branch"
    except Exception:
        return "the current branch"


def build_review_prompt(diff_text: str, branch: str, rng: str | None) -> str:
    """Adversarial review prompt — ported from docket runner._review_prompt (kept in sync).

    Self-contained: the criteria are inline so a real review always happens, and it ends with
    a single machine-parseable verdict line the caller maps to an exit code.
    """
    scope = rng or "the working tree (staged + unstaged changes)"
    return (
        f"Perform an adversarial code review of the changes on branch '{branch}' ({scope}). "
        "The unified diff is provided below. Judge, in priority order: (1) correctness — logic "
        "bugs, wrong results, missed edge cases; (2) tests — would a test fail without this "
        "change, and are the stated behaviors covered; (3) security — injection, auth, secret "
        "exposure, unvalidated input; (4) conventions — the repo's stated rules; (5) simplicity. "
        "Classify each issue as blocking (must fix before merge), should-fix, or nit. Be "
        "specific: cite the file and line. Do not invent issues; if the diff is clean, say so.\n\n"
        "End with EXACTLY one line and nothing after it: `REVIEW: CLEAN` (no blocking issues) or "
        "`REVIEW: BLOCKING` (one or more blocking issues).\n\n"
        "----- BEGIN DIFF -----\n"
        f"{diff_text}\n"
        "----- END DIFF -----"
    )


def classify_verdict(text: str) -> bool | None:
    """CLEAN→True, BLOCKING→False, neither→None. Fail-closed: any blocking signal wins."""
    u = text.upper()
    if "REVIEW: BLOCKING" in u:
        return False
    if "REVIEW: CLEAN" in u:
        return True
    return None


def call_llm(base_url: str, api_key: str, model: str, prompt: str, timeout: int = 180) -> str:
    """POST to {base_url}/chat/completions (OpenAI-compatible) → the assistant message text.

    Raises on transport, HTTP, or response-shape failure so main() maps it to EXIT_ERROR.
    """
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"unexpected response shape from endpoint: {exc}") from exc


def main(argv: list[str] | None = None, env: dict[str, str] | None = None) -> int:
    env = os.environ if env is None else env
    parser = argparse.ArgumentParser(description="Cross-vendor code review via an OpenAI-compatible endpoint.")
    parser.add_argument("--range", dest="range", default=None,
                        help="git range to review (e.g. origin/main..HEAD); default = working tree")
    parser.add_argument("--cwd", default=".", help="repo directory (default: cwd)")
    parser.add_argument("--base-url", dest="base_url", default=None, help="override REVIEW_BASE_URL")
    parser.add_argument("--model", default=None, help="override REVIEW_MODEL")
    args = parser.parse_args(argv)

    try:
        base_url, api_key, model = resolve_config(args, env)
    except ConfigError as exc:
        sys.stderr.write(f"{exc}\n")
        return EXIT_CONFIG

    try:
        diff_text = get_diff(args.range, args.cwd)
    except Exception as exc:
        sys.stderr.write(f"could not read diff: {exc}\n")
        return EXIT_ERROR

    if not diff_text.strip():
        print("No changes to review.")
        print("REVIEW: CLEAN")
        return EXIT_CLEAN

    branch = current_branch(args.cwd)
    prompt = build_review_prompt(diff_text, branch, args.range)

    try:
        review = call_llm(base_url, api_key, model, prompt)
    except (urllib.error.URLError, urllib.error.HTTPError, RuntimeError, ValueError, TimeoutError) as exc:
        sys.stderr.write(f"review request failed ({model} @ {base_url}): {exc}\n")
        return EXIT_ERROR

    print(review)
    verdict = classify_verdict(review)
    if verdict is True:
        return EXIT_CLEAN
    if verdict is False:
        return EXIT_BLOCKING
    sys.stderr.write("no REVIEW: CLEAN|BLOCKING verdict line found in the model output\n")
    return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
