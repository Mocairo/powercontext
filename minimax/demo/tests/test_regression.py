"""BASE-001/BASE-002: immutable pre-existing behavior acceptance tests."""
import json


def ids(result):
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    return [ticket["id"] for ticket in json.loads(result.stdout)]


def test_list_all_stable_order(run_cli):
    assert ids(run_cli()) == [1, 2, 3, 4, 5, 6]


def test_list_preserves_data_fields(run_cli):
    result = run_cli()
    assert result.returncode == 0
    assert json.loads(result.stdout)[0] == {
        "id": 1, "title": "Login error", "owner": "alice", "status": "open"
    }


def test_owner_alice(run_cli):
    assert ids(run_cli("--owner", "alice")) == [1, 3, 5]


def test_owner_bob(run_cli):
    assert ids(run_cli("--owner", "bob")) == [2, 4]


def test_unknown_owner(run_cli):
    assert ids(run_cli("--owner", "nobody")) == []


def test_owner_case_sensitive(run_cli):
    assert ids(run_cli("--owner", "ALICE")) == []


def test_empty_owner(run_cli):
    assert ids(run_cli("--owner", "")) == []


def test_function_sorting_and_owner(ticket_module):
    assert [item["id"] for item in ticket_module.list_tickets()] == [1, 2, 3, 4, 5, 6]
    assert [item["id"] for item in ticket_module.list_tickets(owner="alice")] == [1, 3, 5]


def test_repeated_calls_do_not_mutate_results(ticket_module):
    before = ticket_module.list_tickets()
    ticket_module.list_tickets(owner="bob")
    assert ticket_module.list_tickets() == before
