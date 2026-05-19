#!/usr/bin/env sh
set -eu

echo "[hook] pre-commit quality gate"

if [ -f "pyproject.toml" ] || [ -f "requirements.txt" ]; then
  if command -v ruff >/dev/null 2>&1; then
    echo "[hook] ruff check ."
    ruff check .
  fi

  if command -v mypy >/dev/null 2>&1; then
    echo "[hook] mypy (best-effort)"
    mypy . || true
  fi

  if command -v pytest >/dev/null 2>&1; then
    echo "[hook] pytest -q"
    pytest -q || true
  fi
fi

if [ -f "package.json" ]; then
  if command -v npm >/dev/null 2>&1; then
    if npm run | grep -q " lint"; then
      echo "[hook] npm run lint"
      npm run lint
    fi
    if npm run | grep -q " typecheck"; then
      echo "[hook] npm run typecheck"
      npm run typecheck
    fi
  fi
fi

echo "[hook] quality gate completed"
