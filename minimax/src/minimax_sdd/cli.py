"""CLI entry; credentials are only read by explicit stage-b/check-config."""
import argparse
import asyncio
import json
from pathlib import Path
import sys

from .minimax_client import DEFAULT_CONFIG, MiniMaxConfig
from . import workflow as w


def main() -> int:
    parser = argparse.ArgumentParser(description="OceanBase MiniMax SDD context assistant")
    parser.add_argument("command", choices=["init", "import", "query", "update-spec", "baseline", "state-save", "state-read", "stage-a", "stage-b", "check-config", "reset"])
    parser.add_argument("--run-dir", type=Path, default=Path(".runs/demo-a"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    actions = {
        "init": lambda: w.init_run(args.run_dir),
        "import": lambda: w.import_project(args.run_dir),
        "query": lambda: w.query(args.run_dir),
        "update-spec": lambda: w.update_spec(args.run_dir),
        "baseline": lambda: w.run_tests(w.require_run(args.run_dir), args.run_dir.absolute() / "before", "baseline"),
        "state-save": lambda: asyncio.run(w.save_baseline(args.run_dir)),
        "state-read": lambda: asyncio.run(w.load_state(args.run_dir)),
        "stage-a": lambda: w.stage_a(args.run_dir),
        "stage-b": lambda: w.stage_b(args.run_dir, args.config),
        "reset": lambda: w.reset(args.run_dir),
    }
    try:
        if args.command == "check-config":
            config = MiniMaxConfig.from_env_file(args.config)
            result = {"configured": True, "model": config.model, "base_url": config.base_url, "requests_sent": 0}
        else:
            result = actions[args.command]()
        if args.output:
            w.dump(args.output, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if args.command != "stage-b" or result["status"] == "tests_passed_pending_review" else 1
    except Exception as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
