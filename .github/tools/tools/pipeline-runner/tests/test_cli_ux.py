from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
RUNNER_PATH = REPO_ROOT / ".github" / "tools" / "pipeline-runner" / "pipeline_runner.py"
REGISTRY_PATH = REPO_ROOT / ".github" / "tools" / "pipeline-runner" / "agents.registry.json"
TEMPLATE_PATH = REPO_ROOT / ".github" / "pipeline-state.template.json"


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(RUNNER_PATH), *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _create_workspace_with_template(tmp_path: Path) -> tuple[Path, Path]:
    workspace = tmp_path / "workspace"
    github_dir = workspace / ".github"
    github_dir.mkdir(parents=True)
    github_dir.joinpath("pipeline-state.template.json").write_text(
        TEMPLATE_PATH.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return workspace, github_dir / "pipeline-state.json"


def _seed_state_from_template(state_file: Path) -> None:
    payload = _load_json(TEMPLATE_PATH)
    payload["project"] = "agent-sandbox"
    payload["feature"] = "deterministic-routing"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def test_mode_round_trip_supervised_assisted_supervised(tmp_path: Path) -> None:
    state_file = tmp_path / ".github" / "pipeline-state.json"
    _seed_state_from_template(state_file)

    to_assisted = _run_cli("mode", "--state-file", str(state_file), "--value", "assisted")
    assert to_assisted.returncode == 0
    assert json.loads(to_assisted.stdout) == {"ok": True, "pipeline_mode": "assisted"}
    assert _load_json(state_file)["pipeline_mode"] == "assisted"

    to_supervised = _run_cli("mode", "--state-file", str(state_file), "--value", "supervised")
    assert to_supervised.returncode == 0
    assert json.loads(to_supervised.stdout) == {"ok": True, "pipeline_mode": "supervised"}
    assert _load_json(state_file)["pipeline_mode"] == "supervised"


def test_mode_invalid_value_fails(tmp_path: Path) -> None:
    state_file = tmp_path / ".github" / "pipeline-state.json"
    _seed_state_from_template(state_file)

    result = _run_cli("mode", "--state-file", str(state_file), "--value", "invalid")
    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is False


def test_gate_sets_all_known_gates_true(tmp_path: Path) -> None:
    state_file = tmp_path / ".github" / "pipeline-state.json"
    _seed_state_from_template(state_file)

    for gate in ["intent_approved", "adr_approved", "plan_approved", "review_approved"]:
        result = _run_cli("gate", "--state-file", str(state_file), "--name", gate)
        assert result.returncode == 0
        assert json.loads(result.stdout) == {
            "ok": True,
            "supervision_gate": gate,
            "satisfied": True,
        }

    gates = _load_json(state_file)["supervision_gates"]
    assert gates["intent_approved"] is True
    assert gates["adr_approved"] is True
    assert gates["plan_approved"] is True
    assert gates["review_approved"] is True


def test_gate_unknown_name_fails(tmp_path: Path) -> None:
    state_file = tmp_path / ".github" / "pipeline-state.json"
    _seed_state_from_template(state_file)

    result = _run_cli("gate", "--state-file", str(state_file), "--name", "unknown_gate")
    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is False


def test_init_creates_state_from_template_with_defaults(tmp_path: Path) -> None:
    _, state_file = _create_workspace_with_template(tmp_path)

    result = _run_cli(
        "init",
        "--state-file",
        str(state_file),
        "--project",
        "agent-sandbox",
        "--feature",
        "deterministic-routing",
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["project"] == "agent-sandbox"
    assert payload["feature"] == "deterministic-routing"
    assert payload["type"] is None
    assert Path(payload["state_file"]) == state_file

    written = _load_json(state_file)
    assert written["project"] == "agent-sandbox"
    assert written["feature"] == "deterministic-routing"
    assert written["pipeline_mode"] == "supervised"


def test_init_existing_file_fails_without_force(tmp_path: Path) -> None:
    _, state_file = _create_workspace_with_template(tmp_path)
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text("{}\n", encoding="utf-8")

    result = _run_cli(
        "init",
        "--state-file",
        str(state_file),
        "--project",
        "agent-sandbox",
        "--feature",
        "deterministic-routing",
    )
    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is False


def test_init_force_overwrites_existing_file(tmp_path: Path) -> None:
    _, state_file = _create_workspace_with_template(tmp_path)
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text("{\"junk\": true}\n", encoding="utf-8")

    result = _run_cli(
        "init",
        "--state-file",
        str(state_file),
        "--project",
        "customer360",
        "--feature",
        "hotfix-3",
        "--type",
        "hotfix",
        "--force",
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["type"] == "hotfix"

    written = _load_json(state_file)
    assert written["project"] == "customer360"
    assert written["feature"] == "hotfix-3"
    assert written["type"] == "hotfix"


def test_transitions_output_matches_registry() -> None:
    result = _run_cli("transitions")
    assert result.returncode == 0

    transitions_output = json.loads(result.stdout)
    assert isinstance(transitions_output, list)

    registry = _load_json(REGISTRY_PATH)
    expected = registry["transitions"]

    assert len(transitions_output) == len(expected)
    output_ids = {item["id"] for item in transitions_output}
    expected_ids = {item["id"] for item in expected}
    assert expected_ids.issubset(output_ids)


def test_unknown_state_keys_preserved_after_mode_and_gate(tmp_path: Path) -> None:
    state_file = tmp_path / ".github" / "pipeline-state.json"
    _seed_state_from_template(state_file)

    state = _load_json(state_file)
    state["hotfix_id"] = "HF-2026-0001"
    state["supervision_gates"]["custom_gate"] = False
    state["_notes"]["custom_note"] = {"x": 1}
    state_file.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    mode_result = _run_cli("mode", "--state-file", str(state_file), "--value", "assisted")
    assert mode_result.returncode == 0

    gate_result = _run_cli("gate", "--state-file", str(state_file), "--name", "plan_approved")
    assert gate_result.returncode == 0

    updated = _load_json(state_file)
    assert updated["hotfix_id"] == "HF-2026-0001"
    assert updated["supervision_gates"]["custom_gate"] is False
    assert updated["_notes"]["custom_note"] == {"x": 1}