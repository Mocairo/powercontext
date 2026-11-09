"""Re-audit the recorded live MiniMax delivery without making a model call."""
from __future__ import annotations

import argparse
import ast
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parent
DEMO = ROOT / "demo"
EVIDENCE = ROOT / "evidence" / "stage-b"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(message: str) -> None:
    raise RuntimeError(message)


def test_hashes() -> dict[str, str]:
    return {str(path.relative_to(DEMO)): digest(path) for path in sorted((DEMO / "tests").glob("*.py"))}


def model_code(receipt: dict) -> str:
    if receipt.get("source") != "real_minimax":
        fail("Recorded output is not marked as a real MiniMax response")
    if not receipt.get("response_id") or not receipt.get("response_model"):
        fail("Live response receipt lacks response_id or response_model")
    content = receipt.get("response_content", receipt.get("final_content"))
    if not isinstance(content, str) or "<think" in content.lower():
        fail("Final response is missing or contains private reasoning")
    try:
        payload = json.loads(content)
        files = payload["files"]
        code = files["ticket_tool.py"]
    except (TypeError, KeyError, json.JSONDecodeError):
        fail("Live response is not the recorded single-file JSON contract")
    if set(files) != {"ticket_tool.py"} or not isinstance(code, str):
        fail("Live response contains a file outside the allowlist")
    ast.parse(code, filename="ticket_tool.py")
    return code


def run_business_tests(after: Path, output: Path) -> dict:
    env = {key: value for key, value in os.environ.items() if not key.startswith("MINIMAX_")}
    env.update({"DEMO_WORKSPACE": str(after.parent.resolve()), "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1"})
    command = [sys.executable, "-m", "pytest", "-q", str(DEMO / "tests")]
    process = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, check=False, timeout=120)
    (output / "business-tests.log").write_text(process.stdout + process.stderr, encoding="utf-8")
    return {"command": command, "exit_code": process.returncode, "test_sha256": test_hashes(), "stdout_log": "business-tests.log"}


def fresh_stage_a(output: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="minimax-review-") as directory:
        run_dir = Path(directory) / "stage-a"
        env = {key: value for key, value in os.environ.items() if not key.startswith("MINIMAX_")}
        env.update({"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1"})
        command = [sys.executable, "-m", "minimax_sdd.cli", "stage-a", "--run-dir", str(run_dir)]
        process = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, check=False, timeout=240)
        (output / "fresh-stage-a.log").write_text(process.stdout + process.stderr, encoding="utf-8")
        return {"command": command, "exit_code": process.returncode, "stage_a_status": "complete" if process.returncode == 0 else "failed", "old_state_copied": False, "new_database_and_state": True}


def main() -> int:
    parser = argparse.ArgumentParser(description="credential-free delivery audit")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        print(f"Refusing to overwrite evidence directory: {output}", file=sys.stderr)
        return 2
    output.mkdir(parents=True)
    gates = {name: False for name in ("runnable", "minimax_participated", "context_correct", "database_used", "state_reused", "effective_code_change")}
    try:
        attempt = EVIDENCE / "attempt-03"
        if not attempt.is_dir():
            attempt = EVIDENCE / "attempt-02"
        if not attempt.is_dir():
            fail("No committed successful live attempt directory")
        receipt = load(attempt / "minimax-final-output.json")
        context = load(attempt / "context.json")
        after = DEMO / "after" / "ticket_tool.py"
        before = DEMO / "before" / "ticket_tool.py"
        if not after.is_file() or not before.is_file():
            fail("Committed before/after business snapshots are missing")
        generated = model_code(receipt)
        request = receipt.get("request")
        if not isinstance(request, dict) or not isinstance(request.get("messages"), list):
            fail("Live request receipt is incomplete")
        user_message = json.loads(request["messages"][1]["content"])
        if user_message.get("retrieved_context") != context:
            fail("Model request context differs from the committed retrieved context")
        if user_message.get("task") != context.get("task", {}).get("goal"):
            fail("Model request task differs from the committed task")
        if generated.encode() != after.read_bytes():
            fail("Delivered business code differs from the live MiniMax response")
        expected_diff = "".join(difflib.unified_diff(before.read_text().splitlines(True), generated.splitlines(True), fromfile="a/ticket_tool.py", tofile="b/ticket_tool.py"))
        if (attempt / "model.patch").read_text() != expected_diff:
            fail("Recorded model patch differs from the before/after snapshots")
        tests_record = load(attempt / "tests.json")
        if tests_record.get("test_sha256") != test_hashes():
            fail("Acceptance test hashes changed after the live run")
        if any(item.get("exit_code") != 0 or item.get("failures") or item.get("errors") or item.get("skipped") for item in tests_record.get("results", {}).values()):
            fail("Recorded target or regression test result is not fully passing")
        gates["minimax_participated"] = True
        gates["effective_code_change"] = digest(before) != digest(after)
        gates["runnable"] = run_business_tests(after, output)["exit_code"] == 0
        if context.get("query_evidence", {}).get("engine") != "seekdb":
            fail("Committed task context does not identify a real seekdb query")
        if not context.get("specifications") or not context.get("code") or not context.get("tests"):
            fail("Committed context is missing specification, code, or test sources")
        gates["context_correct"] = True
        gates["database_used"] = bool(context.get("query_evidence", {}).get("queries"))
        restart = load(EVIDENCE / "restart-verification.json")
        if not restart.get("same_artifact_and_revision") or not restart.get("different_process_and_client"):
            fail("Committed PowerContext restart evidence is incomplete")
        gates["state_reused"] = restart.get("next_action") == "review_acceptance_report"
        fresh = fresh_stage_a(output)
        if fresh["exit_code"] != 0:
            fail("Fresh database and state preparation failed")
        report = {
            "official_score": None,
            "all_required_gates_passed": all(gates.values()),
            "local_eligible_points": 20 if all(gates.values()) else 0,
            "gates": gates,
            "model": receipt.get("response_model"),
            "response_id": receipt.get("response_id"),
            "before_sha256": digest(before),
            "after_sha256": digest(after),
            "test_sha256": test_hashes(),
            "fresh_run": fresh,
            "business_tests": "business-tests.log",
            "model_receipt": str(attempt.relative_to(ROOT)),
            "no_live_request_made_by_audit": True,
        }
        (output / "delivery-audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"all_required_gates_passed": report["all_required_gates_passed"], "local_eligible_points": report["local_eligible_points"], "output": str(output)}, ensure_ascii=False))
        return 0 if report["all_required_gates_passed"] else 1
    except Exception as error:
        report = {"official_score": None, "all_required_gates_passed": False, "local_eligible_points": 0, "gates": gates, "error": f"{type(error).__name__}: {error}", "no_live_request_made_by_audit": True}
        (output / "delivery-audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
