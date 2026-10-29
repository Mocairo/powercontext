"""Real PowerContext integration: no fake runtime and no process-local reuse."""

import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from minimax_sdd.state import StateStore


def sample_state():
    return {
        "goal": "Add status filter",
        "stage": "A",
        "completed": ["regression passed", "target failed for missing status behavior"],
        "todo": ["call_minimax"],
        "test_results": {"regression": {"exit_code": 0}, "target": {"exit_code": 1}},
        "code_hash": "sha256:initial-version",
    }


def test_real_powercontext_revisions_and_scope_isolation(tmp_path):
    async def scenario():
        async with StateStore(tmp_path, "first") as store:
            assert await store.load() is None
            one = await store.save(sample_state())
            assert one["revision"] == 1
            assert await store.load() == sample_state()
            updated = {**sample_state(), "stage": "B", "todo": ["run_target_tests"]}
            two = await store.save(updated)
            assert two["revision"] == 2
            assert two["artifact_id"] == one["artifact_id"]
            assert two["content_digest"] != one["content_digest"]
            assert await store.load() == updated
        async with StateStore(tmp_path, "second") as other:
            assert await other.load() is None
            assert other.scope_id != one["scope_id"]
        async with StateStore(tmp_path, "first") as reopened:
            assert await reopened.load() == updated
            assert reopened.receipt["revision"] == 2
            assert reopened.receipt["client_instance_id"] != one["client_instance_id"]
    asyncio.run(scenario())


def test_real_powercontext_new_process_reads_and_uses_saved_todo(tmp_path):
    async def save():
        async with StateStore(tmp_path, "restart") as store:
            assert await store.load() is None
            return await store.save(sample_state())
    receipt = asyncio.run(save())
    code = """
import asyncio, json, sys
from minimax_sdd.state import StateStore
async def main():
    async with StateStore(sys.argv[1], 'restart') as store:
        state = await store.load()
        print(json.dumps({'state': state, 'receipt': store.receipt, 'next_action': state['todo'][0]}))
asyncio.run(main())
"""
    result = subprocess.run(
        [sys.executable, "-c", code, str(tmp_path)], capture_output=True, text=True, timeout=60, check=True
    )
    recovered = json.loads(result.stdout)
    assert recovered["state"] == sample_state()
    assert recovered["next_action"] == "call_minimax"
    assert recovered["receipt"]["pid"] != os.getpid()
    assert recovered["receipt"]["client_instance_id"] != receipt["client_instance_id"]
    for key in ("scope_id", "artifact_id", "revision", "content_digest"):
        assert recovered["receipt"][key] == receipt[key]
    assert (tmp_path / "powercontext.sqlite3").is_file()
    assert not list(tmp_path.glob("*.json"))


def test_invalid_state_rejected_before_write(tmp_path):
    async def scenario():
        async with StateStore(tmp_path, "invalid") as store:
            with pytest.raises(ValueError, match="requires"):
                await store.save({"stage": "A"})
            with pytest.raises(ValueError, match="8192"):
                await store.save({**sample_state(), "goal": "a" * 8193})
            assert await store.load() is None
    asyncio.run(scenario())
