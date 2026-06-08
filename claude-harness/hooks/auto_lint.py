"""Auto-lint after Edit/Write. Runs ruff for .py, eslint for .ts/.tsx."""
import json
import os
import subprocess
import sys

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

if data.get("tool_name") not in ("Edit", "Write"):
    sys.exit(0)

file_path = data.get("tool_input", {}).get("file_path", "")
if not file_path or not os.path.isfile(file_path):
    sys.exit(0)

ext = os.path.splitext(file_path)[1].lower()

if ext == ".py":
    r = subprocess.run(
        ["ruff", "check", "--select", "E,F,W", "--quiet", file_path],
        capture_output=True, text=True,
    )
    if r.stdout.strip():
        print(f"[lint] ruff:\n{r.stdout.strip()}", flush=True)

elif ext in (".ts", ".tsx", ".js", ".jsx"):
    r = subprocess.run(
        ["npx", "--no", "eslint", "--format", "compact", file_path],
        capture_output=True, text=True,
    )
    if r.returncode != 0 and r.stdout.strip():
        print(f"[lint] eslint:\n{r.stdout.strip()[:600]}", flush=True)

sys.exit(0)
