"""Serial integration acceptance using real embedded seekdb, never a mock."""
import json

import pytest

from minimax_sdd.catalog import Catalog, StaleCatalogError


def test_real_catalog_current_sources_and_parameterized_selection(tmp_path):
    work = tmp_path / 'work'
    tests = tmp_path / 'tests'
    work.mkdir()
    tests.mkdir()
    (work / 'ticket_tool.py').write_text('def list_tickets():\n    return []\n')
    (tests / 'conftest.py').write_text('FIXTURE = [1, 2]\n')
    (tests / 'test_target.py').write_text('def test_status():\n    assert True\n')
    (tests / 'test_regression.py').write_text('def test_old():\n    assert True\n')
    spec = tmp_path / 'requirements.json'
    entries = [
        {'id': 'STATUS', 'version': 1, 'title': 'Status filter', 'content': 'OLD_REQUIREMENT uppercase accepted', 'symbols': ['ticket_tool.py:list_tickets'], 'tags': ['status']},
        {'id': 'OWNER', 'version': 1, 'title': 'Owner filter', 'content': 'Owner equals supplied name', 'symbols': ['ticket_tool.py:list_tickets'], 'tags': ['owner']},
    ]
    spec.write_text(json.dumps({'entries': entries}))
    with Catalog(tmp_path / 'real-seekdb') as catalog:
        imported = catalog.import_project(work, spec, tests)
        assert imported['source_count'] == 6
        first = catalog.query({'spec_ids': ['STATUS']})
        assert [s['spec_id'] for s in first['specifications']] == ['STATUS']
        assert len(first['code']) == 1 and len(first['tests']) == 3
        assert first['code'][0]['symbol_locations'][0]['line_start'] == 1
        assert first['query_evidence']['engine'] == 'seekdb'
        assert first['query_evidence']['version']
        assert 'OLD_REQUIREMENT' in json.dumps(first)
        changed = catalog.query({'query_tokens': ['Owner equals']})
        assert [s['spec_id'] for s in changed['specifications']] == ['OWNER']
        injected = "STATUS') OR 1=1 --"
        none = catalog.query({'spec_ids': [injected]})
        assert none['sources'] == []
        statement = next(q for q in none['query_evidence']['queries'] if 'spec_id IN' in q['sql'])
        assert injected not in statement['sql'] and injected in statement['params']
        entries[0]['version'] = 2
        entries[0]['content'] = 'NEW_REQUIREMENT lowercase only'
        spec.write_text(json.dumps({'entries': entries}))
        with pytest.raises(StaleCatalogError, match='re-import'):
            catalog.query({'spec_ids': ['STATUS']})
        catalog.import_project(work, spec, tests)
        second = catalog.query({'spec_ids': ['STATUS']})
        assert second['specifications'][0]['version'] == '2'
        assert 'NEW_REQUIREMENT' in json.dumps(second)
        assert 'OLD_REQUIREMENT' not in json.dumps(second)
        (tests / 'test_regression.py').unlink()
        with pytest.raises(StaleCatalogError):
            catalog.query({'spec_ids': ['STATUS']})
        entries.pop()
        spec.write_text(json.dumps({'entries': entries}))
        catalog.import_project(work, spec, tests)
        deleted = catalog.query({'spec_ids': ['STATUS']})
        assert len(deleted['tests']) == 2
        assert catalog.query({'spec_ids': ['OWNER']})['sources'] == []
        before = (work / 'ticket_tool.py').read_text()
        (work / 'ticket_tool.py').write_text(before + '\n# source changed\n')
        with pytest.raises(StaleCatalogError):
            catalog.query({'spec_ids': ['STATUS']})
