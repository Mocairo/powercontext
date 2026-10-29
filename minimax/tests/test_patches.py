"""Synthetic non-business code fixtures; never the final ticket filtering patch."""
import json
import os

import pytest

from minimax_sdd.patches import PatchError, apply_code_output, parse_code_output


def workspace(tmp_path):
    work = tmp_path / 'isolated'
    work.mkdir()
    (work / '.minimax-isolated-workspace').write_text('minimax-sdd\n')
    (work / 'ticket_tool.py').write_text('VALUE = 1\n')
    (work / 'test_guard.py').write_text('immutable\n')
    return work


def test_fixture_apply_and_diff(tmp_path):
    work = workspace(tmp_path)
    files = parse_code_output(json.dumps({'files': {'ticket_tool.py': 'VALUE = 2\n'}}))
    result = apply_code_output(work, files)
    assert result['applied']
    assert '-VALUE = 1' in result['diff'] and '+VALUE = 2' in result['diff']
    assert result['before_sha256'] != result['after_sha256']
    assert (work / 'ticket_tool.py').read_text() == 'VALUE = 2\n'
    assert (work / 'test_guard.py').read_text() == 'immutable\n'


@pytest.mark.parametrize('path', ['../ticket_tool.py', '/tmp/ticket_tool.py', 'tests/test_target.py', 'test_guard.py', 'other-task/ticket_tool.py'])
def test_forbidden_paths(path):
    with pytest.raises(PatchError):
        parse_code_output(json.dumps({'files': {path: 'VALUE = 2\n'}}))


def test_no_unmarked_workspace(tmp_path):
    work = workspace(tmp_path)
    (work / '.minimax-isolated-workspace').unlink()
    with pytest.raises(PatchError, match='unmarked'):
        apply_code_output(work, {'ticket_tool.py': 'VALUE = 2\n'})
    assert (work / 'ticket_tool.py').read_text() == 'VALUE = 1\n'


@pytest.mark.parametrize('link', ['symlink', 'hardlink'])
def test_linked_target_rejected(tmp_path, link):
    work = workspace(tmp_path)
    target = work / 'ticket_tool.py'
    target.unlink()
    protected = tmp_path / 'protected.py'
    protected.write_text('VALUE = 1\n')
    if link == 'symlink':
        target.symlink_to(protected)
    else:
        os.link(protected, target)
    with pytest.raises(PatchError, match='non-linked'):
        apply_code_output(work, {'ticket_tool.py': 'VALUE = 2\n'})
    assert protected.read_text() == 'VALUE = 1\n'


def test_invalid_python_and_duplicate_keys():
    with pytest.raises(PatchError):
        parse_code_output('{"files":{"ticket_tool.py":"bad syntax !"}}')
    with pytest.raises(PatchError):
        parse_code_output('{"files":{"ticket_tool.py":"a=1","ticket_tool.py":"a=2"}}')


def test_unchanged_patch_rejected(tmp_path):
    with pytest.raises(PatchError, match='unchanged'):
        apply_code_output(workspace(tmp_path), {'ticket_tool.py': 'VALUE = 1\n'})
