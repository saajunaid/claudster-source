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

    # tools: [val1, val2, ...] on a single line
    tools_m = re.search(r"^tools:\s*\[(.+?)\]\s*$", fm_text, re.MULTILINE)
    if tools_m:
        raw = tools_m.group(1)
        meta["tools"] = [t.strip().strip("\"'") for t in raw.split(",") if t.strip()]

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
    "update_notes",
    "replay_stage",
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
# Skill Reference Resolution Test
# ---------------------------------------------------------------------------

def validate_skill_references(agents_dir: Path) -> list[str]:
    """
    Parse all .agent.md files for skill paths and verify each resolves
    to an actual SKILL.md file on disk.
    Returns a list of error strings (empty = all references valid).
    """
    errors: list[str] = []
    base = agents_dir.parent.parent  # .github/agents/ -> repo root

    # Match paths like `.github/skills/.../SKILL.md`
    skill_re = re.compile(r"`(\.github/skills/[^`\s]+/SKILL\.md)`")

    for agent_file in sorted(agents_dir.glob("*.agent.md")):
        text = agent_file.read_text(encoding="utf-8")
        agent_label = agent_file.stem.replace(".agent", "")

        for match in skill_re.finditer(text):
            skill_path = match.group(1)
            # Skip template placeholders like {relevant-skill}
            if "{" in skill_path:
                continue
            resolved = base / skill_path
            if not resolved.exists():
                errors.append(f"{agent_label}: broken skill ref → {skill_path}")

    return errors


# ---------------------------------------------------------------------------
# Contract Consistency Test
# ---------------------------------------------------------------------------

def validate_contract_consistency(agents_dir: Path) -> list[str]:
    """
    Parse CONTRACT-REFERENCE.md for declared required_fields per agent,
    then verify each agent's Output Contract table in its .agent.md file
    mentions those fields.
    Returns a list of warning strings (empty = all contracts consistent).
    """
    errors: list[str] = []
    contract_ref = agents_dir.parent / "agent-docs" / "CONTRACT-REFERENCE.md"
    if not contract_ref.exists():
        return ["CONTRACT-REFERENCE.md not found — skipping contract consistency check"]

    ref_text = contract_ref.read_text(encoding="utf-8")

    # Parse CONTRACT-REFERENCE.md for agent contracts:
    # Pattern: **Agent** | <name>  and  `required_fields` | <fields>
    # Each contract block has a table with | **Agent** | <name> | and
    # | `required_fields` | <comma-separated fields> |
    agent_re = re.compile(r"\|\s*\*\*Agent\*\*\s*\|\s*(.+?)\s*\|")
    fields_re = re.compile(r"\|\s*`required_fields`\s*\|\s*(.+?)\s*\|")

    # Walk line-by-line to pair agents with their required_fields
    contracts: dict[str, set[str]] = {}
    current_agent: str | None = None

    for line in ref_text.splitlines():
        agent_match = agent_re.search(line)
        if agent_match:
            current_agent = agent_match.group(1).strip()
            continue
        fields_match = fields_re.search(line)
        if fields_match and current_agent:
            raw = fields_match.group(1).strip()
            if raw.upper() in ("N/A", "N/A (GOLDEN NUGGETS ARE ADDITIVE)",
                                "N/A (DIAGRAM FILE IS THE ARTEFACT)",
                                "N/A (PROMPT FILE IS THE ARTEFACT)") or raw.startswith("N/A"):
                current_agent = None
                continue
            fields = {f.strip().strip("`") for f in raw.split(",") if f.strip()}
            contracts[current_agent] = fields
            current_agent = None

    if not contracts:
        return ["Could not parse any contracts from CONTRACT-REFERENCE.md"]

    # Now check each agent's .agent.md for an Output Contract table
    # and verify the required_fields appear there
    for agent_name, expected_fields in contracts.items():
        # Convert agent name to file slug
        slug = re.sub(r"\s+", "-", agent_name.lower().strip())
        agent_file = agents_dir / f"{slug}.agent.md"
        if not agent_file.exists():
            # Try alternate slugs (e.g. "UI/UX Designer" -> "ui-ux-designer")
            slug = re.sub(r"[/\\]", "-", slug)
            agent_file = agents_dir / f"{slug}.agent.md"
        if not agent_file.exists():
            errors.append(f"{agent_name}: no matching .agent.md for contract check")
            continue

        text = agent_file.read_text(encoding="utf-8")
        # Find the Output Contract section
        contract_section = ""
        in_contract = False
        for line in text.splitlines():
            if re.match(r"#+\s*.*output\s*contract", line, re.IGNORECASE):
                in_contract = True
                continue
            if in_contract:
                if re.match(r"^#{1,3}\s", line) and "output contract" not in line.lower():
                    break
                contract_section += line + "\n"

        if not contract_section.strip():
            errors.append(f"{agent_name}: no Output Contract section found in agent file")
            continue

        # Check for each required field in the contract section
        contract_lower = contract_section.lower()
        for field in expected_fields:
            # Flexible match: field name may appear as `field`, field, or in prose
            if field.lower() not in contract_lower:
                errors.append(
                    f"{agent_name}: required_field '{field}' from CONTRACT-REFERENCE.md "
                    f"not found in agent's Output Contract section"
                )

    return errors


# ---------------------------------------------------------------------------
# Vocabulary Lint Test
# ---------------------------------------------------------------------------

# Blacklisted terms from GLOSSARY.md "DO NOT USE" column.
# Key = regex pattern (case-sensitive where needed), Value = suggested replacement.
_VOCAB_BLACKLIST: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bartifact\b", re.IGNORECASE), "artefact"),
    (re.compile(r"\bdeliverable\b", re.IGNORECASE), "artefact"),
    (re.compile(r"\boutput file\b", re.IGNORECASE), "artefact"),
    (re.compile(r"\bonboarding skill\b", re.IGNORECASE), "onboarding prompt"),
]

# Lines matching these patterns are excluded from vocabulary checks
# (e.g., the GLOSSARY reference itself, or "DO NOT USE" column headers).
_VOCAB_IGNORE_PATTERNS: list[re.Pattern] = [
    re.compile(r"DO NOT USE", re.IGNORECASE),
    re.compile(r"GLOSSARY\.md"),
    re.compile(r"\|\s*DO NOT", re.IGNORECASE),
    re.compile(r"<!--"),
]


# ---------------------------------------------------------------------------
# Read-Only Agent Tool Audit
# ---------------------------------------------------------------------------

# Agents considered read-only by design — should not have write-capable tools.
# (Their current tool lists may still include write tools; violations are WARNings,
#  not blocking errors, until the tools are formally removed.)
READONLY_AGENTS: set[str] = {"plan", "code-reviewer", "orchestrator"}

# Tools that can modify the filesystem or execute side-effects.
WRITE_CAPABLE_TOOLS: set[str] = {
    "editFiles", "edit/editFiles",
    "createFiles", "edit/createFiles",
    "runCommands", "execute/runInTerminal", "runInTerminal",
    # Note: MCP pipeline tools (satisfy_gate, pipeline_init, etc.) are
    # intentionally excluded — Orchestrator needs them for state management.
}


def validate_readonly_tools(agents_dir: Path) -> list[str]:
    """
    For agents declared read-only, verify their YAML tools: list
    doesn't include write-capable tools.
    Returns a list of warning strings.
    """
    errors: list[str] = []

    for agent_file in sorted(agents_dir.glob("*.agent.md")):
        agent_slug = agent_file.stem.replace(".agent", "").lower()
        if agent_slug not in READONLY_AGENTS:
            continue

        text = agent_file.read_text(encoding="utf-8")
        try:
            fm_text, _ = split_frontmatter(text)
        except ValueError:
            continue

        meta = extract_fields(fm_text)
        tools = meta.get("tools") or []
        if isinstance(tools, str):
            tools = [t.strip() for t in tools.split(",")]

        violations = [t for t in tools if t in WRITE_CAPABLE_TOOLS]
        for v in violations:
            errors.append(f"{agent_slug}: read-only agent has write-capable tool '{v}'")

    return errors


# ---------------------------------------------------------------------------
# Handoff Artifact Cross-Reference Test
# ---------------------------------------------------------------------------

# Expected artifact path patterns per agent — when these agents hand off,
# their prompt should reference the artifact they produced.
_ARTIFACT_PATH_HINTS: dict[str, list[str]] = {
    "architect": ["docs/architecture", "ADR-", "agentic-adr"],
    "plan": [".github/plans/", "plans/"],
    "prd": ["docs/prd", "prd.md"],
}


def validate_handoff_artifact_refs(agents_dir: Path) -> list[str]:
    """
    Check that handoff prompts from artifact-producing agents mention
    the expected artifact path or a recognizable reference to it.
    Returns a list of warning strings.
    """
    errors: list[str] = []

    for agent_file in sorted(agents_dir.glob("*.agent.md")):
        agent_slug = agent_file.stem.replace(".agent", "").lower()
        if agent_slug not in _ARTIFACT_PATH_HINTS:
            continue

        text = agent_file.read_text(encoding="utf-8")
        try:
            fm_text, _ = split_frontmatter(text)
        except ValueError:
            continue

        meta = extract_fields(fm_text)
        handoffs = meta.get("handoffs") or []
        if not isinstance(handoffs, list):
            continue

        hints = _ARTIFACT_PATH_HINTS[agent_slug]
        for hop in handoffs:
            if not isinstance(hop, dict):
                continue
            prompt = str(hop.get("prompt", ""))
            label = str(hop.get("label", ""))
            # Skip "Return to Orchestrator" — these are status reports, not artifact handoffs
            if "orchestrator" in label.lower() or "return" in label.lower():
                continue
            # Check if any expected artifact path hint appears in the prompt
            if not any(h in prompt for h in hints):
                errors.append(
                    f"{agent_slug}: handoff '{label}' prompt doesn't reference "
                    f"expected artifact path (expected one of: {hints})"
                )

    return errors


def validate_vocabulary(agents_dir: Path) -> list[str]:
    """
    Scan all .agent.md files for blacklisted terms from GLOSSARY.md.
    Reports violations with file and line number.
    Returns a list of warning strings (empty = clean vocabulary).
    """
    errors: list[str] = []

    for agent_file in sorted(agents_dir.glob("*.agent.md")):
        agent_label = agent_file.stem.replace(".agent", "")
        lines = agent_file.read_text(encoding="utf-8").splitlines()

        for line_num, line in enumerate(lines, start=1):
            # Skip lines that are themselves glossary references or tables
            if any(pat.search(line) for pat in _VOCAB_IGNORE_PATTERNS):
                continue

            for pattern, replacement in _VOCAB_BLACKLIST:
                match = pattern.search(line)
                if match:
                    errors.append(
                        f"{agent_label} L{line_num}: "
                        f"'{match.group()}' → use '{replacement}'"
                    )

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

    # ── Skill reference resolution test ───────────────────────────────────
    print("\n  SKILL REFERENCE RESOLUTION")
    print("  -----------------------------------------")
    skill_errors = validate_skill_references(agents_dir)
    if not skill_errors:
        print("  [OK]    All skill references resolve to existing SKILL.md files")
    else:
        for e in skill_errors:
            print(f"  [WARN]  {e}")

    # ── Contract consistency test ─────────────────────────────────────────
    print("\n  CONTRACT CONSISTENCY")
    print("  -----------------------------------------")
    contract_errors = validate_contract_consistency(agents_dir)
    if not contract_errors:
        print("  [OK]    All agent contracts consistent with CONTRACT-REFERENCE.md")
    else:
        for e in contract_errors:
            print(f"  [WARN]  {e}")

    # ── Vocabulary lint test ──────────────────────────────────────────────
    print("\n  VOCABULARY LINT")
    print("  -----------------------------------------")
    vocab_errors = validate_vocabulary(agents_dir)
    if not vocab_errors:
        print("  [OK]    No blacklisted terms found in agent files")
    else:
        for e in vocab_errors:
            print(f"  [WARN]  {e}")

    # ── Read-only tool audit ──────────────────────────────────────────────
    print("\n  READ-ONLY TOOL AUDIT")
    print("  -----------------------------------------")
    ro_errors = validate_readonly_tools(agents_dir)
    if not ro_errors:
        print("  [OK]    No write-capable tools on read-only agents")
    else:
        for e in ro_errors:
            print(f"  [WARN]  {e}")

    # ── Handoff artifact cross-reference ──────────────────────────────────
    print("\n  HANDOFF ARTIFACT CROSS-REFERENCE")
    print("  -----------------------------------------")
    handoff_errors = validate_handoff_artifact_refs(agents_dir)
    if not handoff_errors:
        print("  [OK]    All artifact-producing agent handoffs reference expected paths")
    else:
        for e in handoff_errors:
            print(f"  [WARN]  {e}")

    print("")

    if failed or mcp_errors:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
