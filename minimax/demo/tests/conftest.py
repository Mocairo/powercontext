"""Fixed acceptance harness; never copied into the model-writable workspace."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.fixture
def business_path():
    root = Path(os.environ.get("DEMO_WORKSPACE", Path(__file__).parents[1] / "before"))
    path = root.resolve() / "ticket_tool.py"
    assert path.is_file(), f"Missing business module: {path}"
    return path


@pytest.fixture
def run_cli(business_path):
    def run(*args):
        return subprocess.run(
            [sys.executable, str(business_path), *args],
            text=True, capture_output=True, timeout=10, check=False,
        )
    return run


@pytest.fixture
def ticket_module(business_path):
    spec = importlib.util.spec_from_file_location("ticket_acceptance_subject", business_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
