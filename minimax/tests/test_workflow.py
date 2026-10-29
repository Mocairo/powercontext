"""Workflow unit tests; MiniMax, retrieval and state fixtures are not real acceptance evidence."""

import json
from pathlib import Path

import pytest

from minimax_sdd import workflow as w
from minimax_sdd.minimax_client import MiniMaxError


def test_missing_config_does_not_contact_services_or_create_run(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Missing config must stop before database, state, or network access")
    monkeypatch.setattr(w, "query", forbidden)
    monkeypatch.setattr(w, "MiniMaxClient", forbidden)
    run = tmp_path / "not-created"
    with pytest.raises(MiniMaxError, match="configuration missing"):
        w.stage_b(run, tmp_path / "absent.env")
    assert not run.exists()


def test_fixed_tests_cannot_change_between_initialization_and_execution(tmp_path, monkeypatch):
    run = tmp_path / "run"
    w.init_run(run)
    monkeypatch.setattr(w, "test_hashes", lambda: {"tests/test_target.py": "changed"})
    def forbidden(*args, **kwargs):
        pytest.fail("Changed acceptance tests must stop before execution")
    monkeypatch.setattr(w.subprocess, "run", forbidden)
    with pytest.raises(ValueError, match="固定验收测试"):
        w.run_tests(run, run / "before", "rejected")
    assert not (run / "evidence/rejected").exists()


def test_reset_only_removes_marked_demo_not_sibling_or_symlink_target(tmp_path):
    protected = tmp_path / "other-task"
    protected.mkdir()
    (protected / "precious.txt").write_text("keep")
    with pytest.raises(ValueError, match="专用数据标记"):
        w.reset(protected)
    run = tmp_path / "run"
    w.init_run(run)
    (run / "state").symlink_to(protected, target_is_directory=True)
    with pytest.raises(ValueError, match="符号链接"):
        w.reset(run)
    (run / "state").unlink()
    w.reset(run)
    assert not run.exists()
    assert (protected / "precious.txt").read_text() == "keep"


def test_restored_state_controls_next_action_and_code_mismatch():
    assert w.next_action(None) == "run_baseline_tests"
    state = {"code_hash": "original", "todo": ["review_actual_failure"]}
    assert w.next_action(state, "original") == "review_actual_failure"
    assert w.next_action(state, "changed") == "revalidate_changed_code"
    assert w.next_action({**state, "todo": []}, "original") == "review_acceptance_report"


@pytest.mark.parametrize("state_failure", [False, True])
def test_fixture_stage_b_auth_failure_records_attempt_and_preserves_before(tmp_path, monkeypatch, state_failure):
    """Explicit fixtures prove failure handling only, never a real MiniMax call."""
    run = tmp_path / "run"
    manifest = w.init_run(run)
    before = (run / "before/ticket_tool.py").read_bytes()
    w.dump(run / "evidence/report.json", {
        "stage": "A", "status": "complete", "code_sha256": manifest["initial_code_sha256"],
        "test_sha256": manifest["test_sha256"],
    })
    config = tmp_path / "fixture.env"
    config.write_text("MINIMAX_BASE_URL=https://api.minimaxi.com/v1\nMINIMAX_API_KEY=fixture-secret-not-real\nMINIMAX_MODEL=fixture-model\n")
    state = {"goal": "fixture goal", "stage": "awaiting_minimax", "completed": [], "todo": ["call_minimax"], "test_results": {}, "code_hash": manifest["initial_code_sha256"]}
    monkeypatch.setattr(w, "query", lambda path: {"next_action": "call_minimax", "progress": state, "task": {"goal": "fixture goal"}})
    class FixtureClient:
        calls = 0
        def __init__(self, config):
            self.config = config
        def check_service(self):
            self.calls += 1
            raise MiniMaxError("fixture authentication failed: fixture-secret-not-real")
        def generate(self, *args):
            pytest.fail("Authentication failure must stop generation")
    monkeypatch.setattr(w, "MiniMaxClient", FixtureClient)
    saved = []
    async def fixture_save(path, state):
        saved.append(state)
        if state_failure:
            raise OSError("fixture storage unavailable: fixture-secret-not-real")
        return {"source": "fixture_only"}
    monkeypatch.setattr(w, "_save_stage_b", fixture_save)
    report = w.stage_b(run, config)
    expected_status = "state_update_failed" if state_failure else "failed"
    assert report["status"] == expected_status
    if state_failure:
        assert report["state_update_error"] == "OSError"
        assert "Restore PowerContext" in report["recovery"]
    assert report["minimax_requests_attempted"] == 1
    assert "[REDACTED]" in report["error"]
    assert saved[0]["todo"] == ["inspect_stage_b_failure_record"]
    assert (run / "before/ticket_tool.py").read_bytes() == before
    evidence = Path(report["evidence_dir"])
    assert json.loads((evidence / "report.json").read_text())["status"] == expected_status
    for path in evidence.iterdir():
        if path.is_file():
            assert "fixture-secret-not-real" not in path.read_text()
    assert not (evidence / "minimax-final-output.json").exists()


def test_fixture_test_timeout_preserves_command_hashes_and_partial_output(tmp_path, monkeypatch):
    run = tmp_path / "run"
    manifest = w.init_run(run)
    def timeout(command, **kwargs):
        raise w.subprocess.TimeoutExpired(command, 90, output=b"fixture partial output", stderr=b"fixture blocked")
    monkeypatch.setattr(w.subprocess, "run", timeout)
    with pytest.raises(RuntimeError, match="timed out"):
        w.run_tests(run, run / "before", "timeout-fixture")
    evidence = run / "evidence/timeout-fixture"
    metadata = json.loads((evidence / "timeout.json").read_text())
    assert metadata["timeout_seconds"] == 90
    assert metadata["exit_code"] is None
    assert metadata["code_sha256"] == manifest["initial_code_sha256"]
    assert metadata["test_sha256"] == manifest["test_sha256"]
    assert (evidence / "regression.stdout.txt").read_text() == "fixture partial output"
    assert (evidence / "regression.stderr.txt").read_text() == "fixture blocked"
    assert not (evidence / "results.json").exists()
