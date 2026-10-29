"""Task progress persisted through the real PowerContext 1.4.1 runtime."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4

from powercontext.builtin.persistence.sqlite import SQLiteConfig
from powercontext.builtin.records import ArtifactWrite
from powercontext.builtin.runtime import BuiltinConfig, open_builtin_runtime
from powercontext.builtin.scope.models import ScopeDraft


class StateStore:
    """One task scope; every read resolves the current persistent Memory revision.

    No task state or artifact identity is cached in local files. Scope lookup uses
    PowerContext's persisted idempotency key. ``receipt`` is observation metadata.
    """

    def __init__(self, data_dir: str | Path, scope_name: str):
        if not scope_name or len(scope_name) > 100:
            raise ValueError("scope_name must contain 1 to 100 characters")
        self.data_dir = Path(data_dir).resolve()
        self.scope_name = scope_name
        self.client_instance_id = uuid4().hex
        self.receipt: dict | None = None
        self._manager = None
        self._runtime = None
        self._records = None
        self.scope_id = None

    async def __aenter__(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        config = BuiltinConfig(
            database=SQLiteConfig(url=f"sqlite+aiosqlite:///{self.data_dir / 'powercontext.sqlite3'}")
        )
        self._manager = open_builtin_runtime(
            config, scheduler_path=self.data_dir / "powercontext.scheduler.sqlite3"
        )
        self._runtime = await self._manager.__aenter__()
        try:
            scope = await self._runtime.scopes.create(
                ScopeDraft(
                    title=self.scope_name,
                    summary="MiniMax SDD demo task progress",
                    idempotency_key="minimax-sdd:" + hashlib.sha256(self.scope_name.encode()).hexdigest(),
                )
            )
            self.scope_id = scope.scope_id
            self._records = self._runtime.records.for_scope(self.scope_id)
        except BaseException:
            await self.close()
            raise
        return self

    async def __aexit__(self, *exc):
        await self.close()

    async def close(self):
        if self._manager is not None:
            manager, self._manager = self._manager, None
            self._records = None
            self._runtime = None
            await manager.__aexit__(None, None, None)

    async def _current(self):
        if self._records is None:
            raise RuntimeError("Use 'async with StateStore(...) as store'")
        page = await self._records.query_artifacts("atomic-memory", limit=2, cursor=None)
        if len(page.items) > 1 or page.next_cursor:
            raise RuntimeError("Task scope contains multiple state artifacts; use a dedicated demo scope")
        if not page.items:
            return None
        return await self._records.get_artifact("atomic-memory", page.items[0].artifact_id)

    def _receipt(self, record):
        self.receipt = {
            "backend": "PowerContext 1.4.1 / SQLite",
            "scope_id": record.scope_id,
            "scope_name": self.scope_name,
            "family": record.family,
            "artifact_id": record.artifact_id,
            "revision": record.revision,
            "content_digest": record.content_digest,
            "client_instance_id": self.client_instance_id,
            "pid": os.getpid(),
        }
        return self.receipt

    async def load(self) -> dict | None:
        record = await self._current()
        if record is None:
            self.receipt = None
            return None
        if record.content.get("kind") != "minimax-sdd-task-state":
            raise RuntimeError("Unexpected Memory kind in dedicated task scope")
        state = json.loads(record.content["text"])
        if not isinstance(state, dict):
            raise RuntimeError("Persisted task state is not an object")
        self._receipt(record)
        return state

    async def save(self, state: dict) -> dict:
        required = {"goal", "stage", "completed", "todo", "test_results", "code_hash"}
        if not isinstance(state, dict) or not required.issubset(state):
            raise ValueError("Task state requires goal, stage, completed, todo, test_results, code_hash")
        text = json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        if len(text.encode("utf-8")) > 8192:
            raise ValueError("State exceeds PowerContext's 8192-byte Memory limit; store test summaries and evidence paths")
        current = await self._current()
        write = ArtifactWrite(content={"kind": "minimax-sdd-task-state", "text": text})
        if current is None:
            created = await self._records.create_artifact("atomic-memory", write)
            record = await self._records.get_artifact("atomic-memory", created.artifact_id)
        else:
            record = await self._records.replace_artifact(
                "atomic-memory", current.artifact_id, f'"revision:{current.revision}"', write
            )
        return self._receipt(record)
