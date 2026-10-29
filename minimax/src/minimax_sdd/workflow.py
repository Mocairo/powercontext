"""Reproducible preparation and real-model continuation, with durable evidence."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET

from .catalog import Catalog
from .minimax_client import DEFAULT_CONFIG, MiniMaxClient, MiniMaxConfig
from .patches import apply_code_output, parse_code_output
from .state import StateStore

PROJECT = Path(__file__).resolve().parents[2]
DEMO = PROJECT / "demo"
RUN_MARKER = ".minimax-sdd-run"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def require_run(path: Path) -> Path:
    path = path.absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("演示目录及其父目录不能是符号链接")
    path = path.resolve()
    if path == PROJECT or path in PROJECT.parents:
        raise ValueError("不能将项目或其父目录作为演示数据目录")
    marker = path / RUN_MARKER
    if not marker.is_file() or marker.is_symlink() or marker.read_text() != "minimax-sdd-v1\n":
        raise ValueError("缺少本作品专用数据标记；先运行 init")
    for name in ("before", "specs", "catalog", "state", "evidence"):
        if (path / name).is_symlink():
            raise ValueError("演示数据子目录不能是符号链接")
    return path


def test_hashes() -> dict:
    return {str(p.relative_to(DEMO)): digest(p) for p in sorted((DEMO / "tests").glob("*.py"))}


def init_run(path: Path) -> dict:
    path = path.absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("演示目录及其父目录不能是符号链接")
    path = path.resolve()
    path.mkdir(parents=True, exist_ok=False)
    (path / RUN_MARKER).write_text("minimax-sdd-v1\n")
    (path / "before").mkdir()
    shutil.copy2(DEMO / "before/ticket_tool.py", path / "before/ticket_tool.py")
    (path / "before/.minimax-isolated-workspace").write_text("minimax-sdd\n")
    (path / "specs").mkdir()
    shutil.copy2(DEMO / "specs/requirements.json", path / "specs/requirements.json")
    task = read(DEMO / "task.json")
    dump(path / "task.json", task)
    manifest = {"created_at": now(), "run_id": uuid.uuid4().hex, "initial_code_sha256": digest(path / "before/ticket_tool.py"), "test_sha256": test_hashes()}
    dump(path / "manifest.json", manifest)
    return manifest


def import_project(path: Path, workspace: Path | None = None) -> dict:
    path = require_run(path)
    with Catalog(path / "catalog") as catalog:
        return catalog.import_project(workspace or path / "before", path / "specs/requirements.json", DEMO / "tests")


def update_spec(path: Path) -> dict:
    path = require_run(path)
    target = path / "specs/requirements.json"
    before = digest(target)
    shutil.copy2(DEMO / "specs/requirements_v2.json", target)
    return {"before_sha256": before, "after_sha256": digest(target), "changed_requirement": "STATUS-002", "version": 2}


async def load_state(path: Path) -> dict:
    path = require_run(path)
    async with StateStore(path / "state", read(path / "task.json")["id"]) as store:
        value = await store.load()
        return {"state": value, "receipt": store.receipt, "reader_pid": os.getpid()}


def next_action(state: dict | None, code_hash: str | None = None) -> str:
    if state is None:
        return "run_baseline_tests"
    if code_hash is not None and state["code_hash"] != code_hash:
        return "revalidate_changed_code"
    return state["todo"][0] if state["todo"] else "review_acceptance_report"


def query(path: Path) -> dict:
    path = require_run(path)
    task = read(path / "task.json")
    with Catalog(path / "catalog") as catalog:
        context = catalog.query(task)
    restored = asyncio.run(load_state(path))
    code = next((s for s in context["sources"] if s["source_type"] == "code"), None)
    code_hash = code["file_sha256"] if code else None
    context.update({"task": task, "progress": restored["state"], "state_receipt": restored["receipt"], "reader_pid": os.getpid(), "next_action": next_action(restored["state"], code_hash)})
    return context


def run_tests(path: Path, workspace: Path, name: str) -> dict:
    path = require_run(path)
    if test_hashes() != read(path / "manifest.json")["test_sha256"]:
        raise ValueError("固定验收测试内容已变化，拒绝继续")
    evidence = path / "evidence" / name
    evidence.mkdir(parents=True, exist_ok=False)
    results = {}
    # The child receives no inherited credentials, proxy headers or Python plugins.
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "C.UTF-8", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1", "DEMO_WORKSPACE": str(workspace.resolve())}
    for suite in ("regression", "target"):
        junit = evidence / f"{suite}.xml"
        command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(DEMO / f"tests/test_{suite}.py"), "--tb=short", f"--junitxml={junit}"]
        try:
            process = subprocess.run(command, cwd=workspace, env=env, text=True, capture_output=True, timeout=90, check=False)
        except subprocess.TimeoutExpired as error:
            for channel, value in (("stdout", error.stdout), ("stderr", error.stderr)):
                if isinstance(value, bytes):
                    value = value.decode("utf-8", errors="replace")
                (evidence / f"{suite}.{channel}.txt").write_text(value or "")
            dump(evidence / "timeout.json", {"command": command, "cwd": str(workspace), "timeout_seconds": 90, "exit_code": None, "code_sha256": digest(workspace / "ticket_tool.py"), "test_sha256": test_hashes(), "recovery": "Inspect candidate code for blocking behavior; retain model output and record repairs before rerunning the unchanged tests."})
            raise RuntimeError(f"Tests timed out; inspect {evidence / 'timeout.json'}") from None
        (evidence / f"{suite}.stdout.txt").write_text(process.stdout)
        (evidence / f"{suite}.stderr.txt").write_text(process.stderr)
        counts = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
        failures = []
        if junit.exists():
            root = ET.parse(junit).getroot()
            for item in root.iter("testsuite"):
                for key in counts:
                    counts[key] += int(item.get(key, "0"))
            failures = [f.text or "" for f in root.iter("failure")]
        counts["passed"] = counts["tests"] - counts["failures"] - counts["errors"] - counts["skipped"]
        results[suite] = {"command": command, "cwd": str(workspace), "exit_code": process.returncode, **counts, "failure_due_to_missing_status": bool(failures) and all("unrecognized arguments: --status" in f or "unexpected keyword argument 'status'" in f for f in failures), "stdout": str(evidence / f"{suite}.stdout.txt"), "junit": str(junit)}
    result = {"created_at": now(), "code_sha256": digest(workspace / "ticket_tool.py"), "test_sha256": test_hashes(), "results": results}
    dump(evidence / "results.json", result)
    if test_hashes() != read(path / "manifest.json")["test_sha256"]:
        raise ValueError("测试执行期间验收文件被修改，结果无效")
    return result


def valid_baseline(result: dict) -> bool:
    r, t = result["results"]["regression"], result["results"]["target"]
    return (r["exit_code"] == 0 and r["passed"] == 9 and t["exit_code"] == 1 and t["failures"] == 20 and t["failure_due_to_missing_status"] and all(x["errors"] == 0 and x["skipped"] == 0 for x in (r, t)))


def test_summary(result: dict) -> dict:
    return {k: {field: v[field] for field in ("exit_code", "tests", "passed", "failures", "errors", "skipped")} for k, v in result["results"].items()}


async def save_baseline(path: Path) -> dict:
    path = require_run(path)
    baseline = read(path / "evidence/baseline/results.json")
    if not valid_baseline(baseline):
        raise ValueError("修改前验证不满足9项回归通过/20项目标有效失败")
    if baseline["code_sha256"] != digest(path / "before/ticket_tool.py") or baseline["test_sha256"] != test_hashes():
        raise ValueError("代码或验收测试已变更，需要重新验证")
    task = read(path / "task.json")
    with Catalog(path / "catalog") as catalog:
        actual = catalog.query(task)
    if not any(s.get("spec_id") == "STATUS-002" and str(s["version"]) == "2" for s in actual["sources"]):
        raise ValueError("当前数据库未检索到 STATUS-002 v2，先更新规格并重新导入")
    state = {"goal": task["goal"], "stage": "awaiting_minimax", "completed": ["specifications_updated_to_v2", "real_database_context_retrieved", "baseline_regression_passed", "target_tests_failed_for_missing_status"], "todo": ["call_minimax", "run_unchanged_target_and_regression_tests", "review_acceptance_report"], "test_results": test_summary(baseline), "code_hash": baseline["code_sha256"]}
    async with StateStore(path / "state", task["id"]) as store:
        previous = await store.load()
        receipt = await store.save(state)
    return {"previous_state": previous, "state": state, "receipt": receipt}


def _child(path: Path, action: str, *, output: str) -> dict:
    destination = path / "evidence" / output
    command = [sys.executable, "-m", "minimax_sdd.cli", action, "--run-dir", str(path), "--output", str(destination)]
    process = subprocess.run(command, cwd=PROJECT, text=True, capture_output=True, timeout=180, check=False)
    dump(path / "evidence" / (output + ".process.json"), {"command": command, "exit_code": process.returncode, "stdout": process.stdout, "stderr": process.stderr})
    if process.returncode != 0:
        raise RuntimeError(f"子进程 {action} 失败，见 {destination}.process.json")
    return read(destination)


def stage_a(path: Path) -> dict:
    path = path.absolute()
    init_run(path)
    _child(path, "import", output="import-v1.json")
    first = _child(path, "query", output="context-v1.json")
    _child(path, "update-spec", output="spec-update.json")
    _child(path, "import", output="import-v2.json")
    second = _child(path, "query", output="context-v2.json")
    old = [s for s in first["sources"] if s.get("spec_id") == "STATUS-002"]
    new = [s for s in second["sources"] if s.get("spec_id") == "STATUS-002"]
    if len(old) != 1 or len(new) != 1 or int(old[0]["version"]) != 1 or int(new[0]["version"]) != 2 or old[0]["content_sha256"] == new[0]["content_sha256"]:
        raise RuntimeError("规格更新未反映到真实查询结果")
    baseline = _child(path, "baseline", output="baseline.json")
    if not valid_baseline(baseline):
        raise RuntimeError("初始测试未满足有效失败条件，查看测试日志")
    saved = _child(path, "state-save", output="state-written.json")
    restored = _child(path, "query", output="context-restored.json")
    if saved["previous_state"] is not None or restored["progress"] != saved["state"] or restored["next_action"] != "call_minimax":
        raise RuntimeError("状态未从全新任务正确保存并复用")
    a, b = saved["receipt"], restored["state_receipt"]
    if a["pid"] == b["pid"] or a["client_instance_id"] == b["client_instance_id"] or a["artifact_id"] != b["artifact_id"]:
        raise RuntimeError("未证明新进程、新客户端读取同一真实持久化 artifact")
    report = {"stage": "A", "status": "complete", "created_at": now(), "minimax_real_calls": 0, "spec_update_verified": True, "powercontext_restart_verified": True, "state_writer": a, "state_reader": b, "next_action": restored["next_action"], "baseline": test_summary(baseline), "code_sha256": baseline["code_sha256"], "test_sha256": baseline["test_sha256"], "pending": ["MiniMax真实参与代码修改", "修改后同一目标测试和回归全部通过", "最终完整验收和平台提测"], "evidence_dir": str(path / "evidence")}
    dump(path / "evidence/report.json", report)
    return report


async def _save_stage_b(path: Path, state: dict) -> dict:
    async with StateStore(path / "state", read(path / "task.json")["id"]) as store:
        return await store.save(state)


def stage_b(path: Path, config_path: Path = DEFAULT_CONFIG) -> dict:
    # Missing configuration stops here, before any service request or mutation.
    config = MiniMaxConfig.from_env_file(config_path)
    path = require_run(path)
    preparation = read(path / "evidence/report.json")
    if preparation.get("stage") != "A" or preparation.get("status") != "complete":
        raise ValueError("请先完成 stage-a 验证")
    if digest(path / "before/ticket_tool.py") != preparation["code_sha256"] or test_hashes() != preparation["test_sha256"]:
        raise ValueError("初始业务快照或固定验收测试与阶段A不一致")
    context = query(path)
    if context["next_action"] != "call_minimax":
        raise ValueError(f"持久化状态的下一步是 {context['next_action']}；请先检查已有记录")
    suffix = uuid.uuid4().hex[:12]
    evidence = path / "evidence" / f"stage-b-{suffix}"
    evidence.mkdir()
    candidate = path / f"candidate-{suffix}"
    candidate.mkdir()
    shutil.copy2(path / "before/ticket_tool.py", candidate / "ticket_tool.py")
    (candidate / ".minimax-isolated-workspace").write_text("minimax-sdd\n")
    dump(evidence / "context.json", context)
    client = MiniMaxClient(config)
    state = dict(context["progress"])
    report = {"stage": "B", "status": "failed", "created_at": now(), "model": config.model, "candidate": str(candidate), "human_or_codex_repairs": [], "evidence_dir": str(evidence)}
    try:
        dump(evidence / "service-check.json", client.check_service())
        generated = client.generate(context["task"]["goal"], context)
        dump(evidence / "minimax-final-output.json", generated)
        patch = apply_code_output(candidate, parse_code_output(generated["final_content"]))
        dump(evidence / "patch.json", patch)
        (evidence / "model.patch").write_text(patch["diff"])
        result = run_tests(path, candidate, f"stage-b-tests-{suffix}")
        dump(evidence / "tests.json", result)
        passed = all(v["exit_code"] == 0 and v["failures"] == 0 and v["errors"] == 0 and v["skipped"] == 0 for v in result["results"].values()) and result["results"]["regression"]["passed"] == 9 and result["results"]["target"]["passed"] == 20
        state.update({"stage": "verified" if passed else "model_patch_needs_review", "code_hash": result["code_sha256"], "test_results": test_summary(result), "completed": state["completed"] + ["real_minimax_output_applied"] + (["unchanged_tests_all_passed"] if passed else []), "todo": ["review_acceptance_report"] if passed else ["review_model_patch_and_record_repairs"]})
        dump(evidence / "import-after.json", import_project(path, candidate))
        report.update({"status": "tests_passed_pending_review" if passed else "tests_failed", "tests": test_summary(result), "code_sha256": result["code_sha256"], "test_sha256": result["test_sha256"]})
    except Exception as error:
        # Client and patch errors have safe messages; never record arbitrary HTTP bodies.
        from .minimax_client import MiniMaxError
        from .patches import PatchError
        safe = str(error) if isinstance(error, (MiniMaxError, PatchError)) else type(error).__name__ + ": see local execution; no raw exception persisted"
        report["error"] = safe.replace(config.api_key, "[REDACTED]")
        state.update({"stage": "stage_b_failed", "todo": ["inspect_stage_b_failure_record"]})
    report["minimax_requests_attempted"] = client.calls
    state["evidence"] = str(evidence.relative_to(path))
    dump(evidence / "report.json", report)
    try:
        report["state_receipt"] = asyncio.run(_save_stage_b(path, state))
    except Exception as error:
        report["status"] = "state_update_failed"
        report["state_update_error"] = type(error).__name__
        report["recovery"] = "Model output, patch and tests are preserved here. Restore PowerContext storage access and persist these actual results before declaring completion."
    dump(evidence / "report.json", report)
    (evidence / "ACCEPTANCE.md").write_text("# 阶段 B 实际执行报告\n\n" + json.dumps(report, ensure_ascii=False, indent=2) + "\n\n平台提测由参赛者操作；请审查模型差异和测试证据。\n")
    return report


def reset(path: Path) -> dict:
    path = require_run(path)
    shutil.rmtree(path)
    return {"removed_demo_directory": str(path)}
