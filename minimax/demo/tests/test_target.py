"""STATUS-001 and STATUS-002 v2: identical tests before and after MiniMax."""
import json

import pytest


def ids(result):
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    return [ticket["id"] for ticket in json.loads(result.stdout)]


@pytest.mark.parametrize("status,expected", [
    ("open", [1, 4]), ("in_progress", [2, 5]), ("closed", [3, 6]),
])
def test_each_valid_status(run_cli, status, expected):
    assert ids(run_cli("--status", status)) == expected


@pytest.mark.parametrize("owner,status,expected", [
    ("alice", "open", [1]), ("alice", "in_progress", [5]),
    ("alice", "closed", [3]), ("bob", "closed", []),
    ("nobody", "open", []),
])
def test_combined_filters(run_cli, owner, status, expected):
    assert ids(run_cli("--owner", owner, "--status", status)) == expected


@pytest.mark.parametrize("status", ["OPEN", "unknown", "", " open", "open "])
def test_invalid_status_is_explicit(run_cli, status):
    result = run_cli("--status", status)
    assert result.returncode == 2
    assert result.stdout == ""
    assert "invalid status" in result.stderr.lower()
    for canonical in ("open", "in_progress", "closed"):
        assert canonical in result.stderr


def test_function_status_and_combination(ticket_module):
    assert [t["id"] for t in ticket_module.list_tickets(status="open")] == [1, 4]
    assert [t["id"] for t in ticket_module.list_tickets(owner="alice", status="open")] == [1]


def test_function_none_preserves_behavior(ticket_module):
    assert ticket_module.list_tickets(status=None) == ticket_module.list_tickets()
    assert ticket_module.list_tickets(owner="alice", status=None) == ticket_module.list_tickets(owner="alice")


@pytest.mark.parametrize("status", ["OPEN", "unknown", "", " open", "open "])
def test_function_invalid_status(ticket_module, status):
    with pytest.raises(ValueError):
        ticket_module.list_tickets(status=status)
