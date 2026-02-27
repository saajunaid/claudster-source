"""
validate_agents.py  —  Pre-publish gate for the junai agent pool.

Checks every .agent.md in .github/agents/ for structural compliance.
Called automatically by junai-release before publishing to the marketplace.

Exit codes:
  0  all checks passed
  1  one or more agents failed validation

Usage:
  python validate_agents.py                      # auto-discovers .github/agents/
  python validate_agents.py path/to/agents/      # explicit directory
"""

from __future__ import annotations
import json
import queue
import re
import subprocess
import sys
import threading
import yaml
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

AGENTS_DIR = Path(__file__).parent / ".github" / "agents"

KNOWN_MODELS: set[str] = {
    "Claude Opus 4.6",
    "Claude Sonnet 4.6",
    "Gemini 3.1 Pro (Preview)",
    "GPT-5.3-Codex",
    # Add new models here as they are introduced
}

# Agents exempt from the §9 Deferred Items check
ORCHESTRATOR_NAMES: set[str] = {"orchestrator"}

# Frontmatter fields that MUST be present
REQUIRED_FIELDS: list[str] = ["name", "description", "model"]


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def split_frontmatter(text: str) -> tuple[str, str]:
    """Return (frontmatter_block, body). Raises ValueError if no --- delimiters."""
    if not text.startswith("---"):
        raise ValueError("File does not start with '---' frontmatter delimiter")
    second = text.index("---", 3)
    return text[3:second], text[second + 3:]


def extract_fields(fm_text: str) -> dict:
    """
    Resilient frontmatter extractor.

    Many agent.md files contain colons inside prompt: values
    (e.g. "prompt: hotfix: read ...") which breaks strict YAML.
    We attempt yaml.safe_load first; on failure we fall back to a
    targeted regex pass that only extracts the fields we actually
    need for validation (name, description, model, handoffs[*].agent).
    """
    # ── Fast path: strict YAML ─────────────────────────────────────────────
    try:
        parsed = yaml.safe_load(fm_text) or {}
        if isinstance(parsed, dict) and parsed:
            return parsed
    except yaml.YAMLError:
        pass  # fall through to regex fallback

    # ── Fallback: targeted regex extraction ───────────────────────────────
    meta: dict = {}

    # Simple scalar fields on their own line
    for key in ("name", "description", "model"):
        m = re.search(rf"^{key}:\s*(.+)$", fm_text, re.MULTILINE)
        if m:
            meta[key] = m.group(1).strip().strip("\"'")

    # Handoff agent names — `    agent: <name>` lines inside the handoffs block
    handoff_agents = re.findall(r"^\s{2,}agent:\s+(.+)$", fm_text, re.MULTILINE)
    if handoff_agents:
        meta["handoffs"] = [
            {"agent": a.strip().strip("\"'")} for a in handoff_agents
        ]

    return meta


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_agent(path: Path, all_agent_slugs: set[str]) -> list[str]:
    """
    Run all checks on a single agent file.
    Returns a list of error strings (empty = pass).
    """
    errors: list[str] = []

    text = path.read_text(encoding="utf-8")
    agent_slug = path.stem.replace(".agent", "").lower()

    # ── Frontmatter parsing ────────────────────────────────────────────────
    try:
        fm_text, body = split_frontmatter(text)
    except ValueError as exc:
        return [f"Frontmatter error: {exc}"]

    meta = extract_fields(fm_text)

    # ── Required fields ────────────────────────────────────────────────────
    for field in REQUIRED_FIELDS:
        if field not in meta or not meta[field]:
            errors.append(f"Missing required frontmatter field: '{field}'")

    # ── Model validation ───────────────────────────────────────────────────
    model = str(meta.get("model", "")).strip()
    if model and model not in KNOWN_MODELS:
        errors.append(
            f"Unknown model '{model}' — add to KNOWN_MODELS in validate_agents.py "
            f"if intentional. Known: {', '.join(sorted(KNOWN_MODELS))}"
        )

    # ── §8 Completion Reporting ────────────────────────────────────────────
    if "### 8." not in body:
        errors.append("Missing §8 Completion Reporting Protocol (expected '### 8.' in body)")

    # ── §9 Deferred Items (skip orchestrator) ─────────────────────────────
    if agent_slug not in ORCHESTRATOR_NAMES:
        if "### 9." not in body:
            errors.append("Missing §9 Deferred Items Protocol (expected '### 9.' in body)")

    # ── Handoff agent references ───────────────────────────────────────────
    handoffs = meta.get("handoffs") or []
    if isinstance(handoffs, list):
        for hop in handoffs:
            if not isinstance(hop, dict):
                continue
            ref = str(hop.get("agent", "")).strip()
            if not ref:
                continue
            ref_slug = re.sub(r"\s+", "-", ref.lower())
            if ref_slug not in all_agent_slugs:
                errors.append(
                    f"Handoff references unknown agent: '{ref}' "
                    f"(slug '{ref_slug}' not found in agents/)"
                )

    return errors


# ---------------------------------------------------------------------------
# MCP Server smoke test
# ---------------------------------------------------------------------------

# Expected tools registered by server.py — update if tools are added/removed
EXPECTED_MCP_TOOLS: set[str] = {
    "notify_orchestrator",
    "validate_deferred_paths",
    "get_pipeline_status",
    "skip_stage",
    "set_pipeline_mode",
    "satisfy_gate",
    "pipeline_init",
    "pipeline_reset",
    "run_command",
}

def _read_lines_into_queue(stream, q: queue.Queue) -> None:
    """Thread target: read lines from stream and push to queue."""
    try:
        for line in stream:
            q.put(line)
    except Exception:
        pass
    finally:
        q.put(None)  # sentinel


def _send(proc: subprocess.Popen, msg: dict) -> None:
    proc.stdin.write(json.dumps(msg) + "\n")
    proc.stdin.flush()


def _recv(q: queue.Queue, timeout: float = 8.0) -> dict | None:
    """Read next non-empty line from the queue, parse as JSON."""
    deadline = timeout
    while deadline > 0:
        try:
            line = q.get(timeout=min(1.0, deadline))
        except queue.Empty:
            deadline -= 1.0
            continue
        if line is None:
            return None  # stream closed
        line = line.strip()
        if not line:
            deadline -= 0.05
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue  # log lines from FastMCP — skip and keep reading
    return None


def smoke_test_mcp_server() -> list[str]:
    """
    Start server.py via stdio, run initialize + tools/list, verify response.
    Returns list of error strings (empty = pass).
    """
    errors: list[str] = []

    # Resolve paths
    base = Path(__file__).parent
    server_py = base / ".github" / "tools" / "mcp-server" / "server.py"
    # Support both Windows (.venv/Scripts) and Unix (.venv/bin)
    python_exe = base / ".venv" / "Scripts" / "python.exe"
    if not python_exe.exists():
        python_exe = base / ".venv" / "bin" / "python"

    if not server_py.exists():
        return ["MCP smoke test skipped: server.py not found at .github/tools/mcp-server/server.py"]
    if not python_exe.exists():
        return ["MCP smoke test skipped: venv python not found — run: python -m venv .venv && pip install -r requirements.txt"]

    proc = None
    try:
        proc = subprocess.Popen(
            [str(python_exe), str(server_py)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        q: queue.Queue = queue.Queue()
        reader = threading.Thread(target=_read_lines_into_queue, args=(proc.stdout, q), daemon=True)
        reader.start()

        # ── 1. initialize ──────────────────────────────────────────────────
        _send(proc, {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "junai-smoke-test", "version": "1.0"},
            },
        })

        init_resp = _recv(q, timeout=10.0)
        if init_resp is None:
            errors.append("MCP server did not respond to initialize within 10s — startup error")
            return errors

        if "error" in init_resp:
            errors.append(f"MCP initialize error: {init_resp['error']}")
            return errors

        server_info = init_resp.get("result", {}).get("serverInfo", {})
        if not server_info.get("name"):
            errors.append("MCP initialize response missing serverInfo.name")

        # ── 2. notifications/initialized ──────────────────────────────────
        _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

        # ── 3. tools/list ─────────────────────────────────────────────────
        _send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})

        list_resp = _recv(q, timeout=8.0)
        if list_resp is None:
            errors.append("MCP server did not respond to tools/list within 8s")
            return errors

        if "error" in list_resp:
            errors.append(f"MCP tools/list error: {list_resp['error']}")
            return errors

        registered = {t["name"] for t in list_resp.get("result", {}).get("tools", [])}
        missing = EXPECTED_MCP_TOOLS - registered
        if missing:
            errors.append(f"MCP missing expected tools: {', '.join(sorted(missing))}")

        unexpected = registered - EXPECTED_MCP_TOOLS
        if unexpected:
            # Not a failure — just a note that EXPECTED_MCP_TOOLS needs updating
            errors.append(
                f"MCP has new tools not in EXPECTED_MCP_TOOLS (update the list): "
                f"{', '.join(sorted(unexpected))}"
            )

    except FileNotFoundError:
        errors.append("MCP smoke test failed: could not launch server.py (python not found)")
    except Exception as exc:
        errors.append(f"MCP smoke test exception: {exc}")
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()

    return errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    agents_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else AGENTS_DIR

    if not agents_dir.exists():
        print(f"\n  [ERROR]  Agents directory not found: {agents_dir}")
        sys.exit(1)

    agent_files = sorted(agents_dir.glob("*.agent.md"))
    if not agent_files:
        print(f"\n  [WARN]   No .agent.md files found in {agents_dir}")
        sys.exit(0)

    # Pre-build the set of known agent slugs for handoff cross-checks
    all_agent_slugs = {f.stem.replace(".agent", "").lower() for f in agent_files}

    print(f"\n  JUNAI AGENT VALIDATOR  ({len(agent_files)} agents)")
    print("  -----------------------------------------")

    results: dict[Path, list[str]] = {}
    for path in agent_files:
        results[path] = validate_agent(path, all_agent_slugs)

    failed = {p: errs for p, errs in results.items() if errs}

    for path, errs in results.items():
        label = path.stem.replace(".agent", "")
        if errs:
            print(f"  [FAIL]  {label}")
            for e in errs:
                print(f"            x  {e}")
        else:
            print(f"  [OK]    {label}")

    print("  -----------------------------------------")

    if not failed:
        print(f"  All {len(agent_files)} agents passed validation.")
    else:
        total_errors = sum(len(e) for e in failed.values())
        print(
            f"  {total_errors} error(s) in {len(failed)} agent(s). "
            f"Fix before publishing."
        )

    # ── MCP server smoke test ─────────────────────────────────────────────
    print("\n  MCP SERVER SMOKE TEST")
    print("  -----------------------------------------")
    mcp_errors = smoke_test_mcp_server()
    if not mcp_errors:
        print("  [OK]    server.py started, responded to initialize + tools/list")
    else:
        for e in mcp_errors:
            print(f"  [FAIL]  {e}")

    print("")

    if failed or mcp_errors:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
