"""Allowlisted full-file replacement; this is a file boundary, not a code sandbox."""
from __future__ import annotations

import ast
import difflib
import hashlib
import json
import os
import tempfile
from pathlib import Path


class PatchError(ValueError):
    pass


def parse_code_output(text: str) -> dict[str, str]:
    text = text.strip()
    if text.startswith('```json\n') and text.endswith('\n```'):
        text = text[8:-4]
    try:
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise PatchError('Duplicate JSON key in code output.')
                result[key] = value
            return result
        payload = json.loads(text, object_pairs_hook=unique)
    except (ValueError, TypeError) as exc:
        raise PatchError('Code output must be a JSON object with a files mapping.') from exc
    if not isinstance(payload, dict) or set(payload) != {'files'}:
        raise PatchError('Expected exactly a files mapping.')
    files = payload['files']
    if not isinstance(files, dict) or set(files) != {'ticket_tool.py'}:
        raise PatchError('Only ticket_tool.py may be replaced; tests and other paths are forbidden.')
    code = files['ticket_tool.py']
    if not isinstance(code, str) or not code.strip() or len(code.encode()) > 100_000:
        raise PatchError('Replacement must be nonempty Python source at most 100000 bytes.')
    try:
        ast.parse(code, filename='ticket_tool.py')
    except (SyntaxError, ValueError):
        raise PatchError('Replacement is not valid Python syntax.') from None
    return files


def apply_code_output(workspace: Path, files: dict[str, str]) -> dict:
    files = parse_code_output(json.dumps({'files': files}))
    workspace = Path(workspace).absolute()
    if any(path.is_symlink() for path in (workspace, *workspace.parents)):
        raise PatchError('Workspace and its parents must not be symbolic links.')
    marker = workspace / '.minimax-isolated-workspace'
    if not marker.is_file() or marker.is_symlink() or marker.read_text() != 'minimax-sdd\n':
        raise PatchError('Refusing to modify an unmarked workspace; use the demo initialization command.')
    target = workspace / 'ticket_tool.py'
    if target.is_symlink() or not target.is_file() or target.stat().st_nlink != 1:
        raise PatchError('Business target must be a regular, non-linked existing file.')
    before = target.read_text(encoding='utf-8')
    after = files['ticket_tool.py']
    diff = ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile='a/ticket_tool.py', tofile='b/ticket_tool.py'))
    if not diff:
        raise PatchError('Model returned unchanged code.')
    fd, temporary = tempfile.mkstemp(prefix='.minimax-', dir=workspace)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as stream:
            stream.write(after)
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return {'applied': True, 'files': ['ticket_tool.py'], 'diff': diff, 'before_sha256': hashlib.sha256(before.encode()).hexdigest(), 'after_sha256': hashlib.sha256(after.encode()).hexdigest()}
