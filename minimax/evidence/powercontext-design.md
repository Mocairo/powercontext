# PowerContext integration contract

Runtime dependency: `powercontext[builtin]==1.4.1`, installed independently from PyPI. The ecosystem submission branch is not imported as PowerContext source. Upstream source and license: https://github.com/oceanbase/powercontext (Apache-2.0); exact package metadata: https://pypi.org/pypi/powercontext/1.4.1/json .

The adapter uses the installed package's actual `open_builtin_runtime(BuiltinConfig(database=SQLiteConfig(...)))`, `runtime.scopes.create(ScopeDraft(...))`, and scoped `runtime.records` APIs. No inference model, generation pipeline, or embedding credentials are configured. This is real in-process PowerContext backed by its own SQLite database, not an HTTP service mock. Engineering documents are separately indexed in real seekdb.

Each demo data directory owns `powercontext.sqlite3` and its scheduler database. Each task name maps to a persistent PowerContext Scope through a hashed idempotency key. A Scope contains one `atomic-memory` logical Artifact whose `kind` is `minimax-sdd-task-state`; the text is structured task state. Save creates the first revision or replaces the current revision using its revision ETag. Prior revisions remain in PowerContext. State text is capped at PowerContext's actual 8192 UTF-8 byte limit; test output belongs in evidence files, while exit codes, code hashes and paths belong in Memory.

Every load queries PowerContext for the current head and then fetches its content. The adapter writes no JSON cache or artifact-ID sidecar. `receipt` records scope, artifact, revision, content digest, process ID and a fresh client UUID. Reopening creates a fresh runtime/client, resolves the same persistent Scope, and reads the Artifact again. Process-restart verification must compare persistent identity/digest, ensure differing PID/client UUID, and derive the next action from the recovered `todo` rather than a hardcoded branch.

These APIs were checked against the actual 1.4.1 wheel; older competition implementation branches expose different Memory APIs and are not used.
