"""Current engineering sources selected by real, parameterized seekdb SQL."""
from __future__ import annotations

import ast
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pylibseekdb
import pymysql


class StaleCatalogError(RuntimeError):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Catalog:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir).resolve()
        self.instance = None
        self.connection = None

    def __enter__(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.instance = pylibseekdb.open(str(self.data_dir))
        try:
            options = dict(self.instance.connection_options())
            options.update(autocommit=False, database="test", cursorclass=pymysql.cursors.DictCursor)
            self.connection = pymysql.connect(**options)
            with self.connection.cursor() as cursor:
                cursor.execute('CREATE TABLE IF NOT EXISTS minimax_sources (source_id VARCHAR(256) PRIMARY KEY, source_type VARCHAR(16) NOT NULL, path TEXT NOT NULL, symbol TEXT NOT NULL, spec_id VARCHAR(128), version VARCHAR(64) NOT NULL, content LONGTEXT NOT NULL, content_sha256 CHAR(64) NOT NULL, file_sha256 CHAR(64) NOT NULL, line_start INT NOT NULL, line_end INT NOT NULL, current_valid INT NOT NULL, imported_at VARCHAR(64) NOT NULL, search_text LONGTEXT NOT NULL)')
                cursor.execute('CREATE TABLE IF NOT EXISTS minimax_manifest (path VARCHAR(512) PRIMARY KEY, file_sha256 CHAR(64) NOT NULL)')
            self.connection.commit()
            return self
        except BaseException:
            if self.connection:
                self.connection.close()
            self.instance.close()
            raise

    def __exit__(self, *_):
        try:
            if self.connection:
                self.connection.close()
        finally:
            if self.instance:
                self.instance.close()

    def import_project(self, workspace: Path, spec_path: Path, tests_dir: Path) -> dict:
        spec_path = Path(spec_path).resolve()
        workspace = Path(workspace).resolve()
        tests_dir = Path(tests_dir).resolve()
        code_path = workspace / 'ticket_tool.py'
        paths = [spec_path, code_path, *sorted(tests_dir.glob('*.py'))]
        raw = {p: p.read_bytes() for p in paths}
        specs = json.loads(raw[spec_path])['entries']
        if not isinstance(specs, list) or not specs:
            raise ValueError('Specifications must contain a nonempty entries list.')
        ids = [entry['id'] for entry in specs]
        if len(set(ids)) != len(ids):
            raise ValueError('Duplicate specification ID.')
        now = datetime.now(timezone.utc).isoformat()
        rows = []
        for entry in specs:
            if not all(k in entry for k in ('id', 'version', 'content', 'symbols', 'tags', 'title')):
                raise ValueError('Incomplete specification entry.')
            content = json.dumps(entry, ensure_ascii=False, sort_keys=True)
            lines = raw[spec_path].decode().splitlines()
            start = next((i for i, line in enumerate(lines, 1) if json.dumps(entry['id']) in line), 1)
            rows.append((entry['id'], 'spec', str(spec_path), json.dumps(entry['symbols']), entry['id'], str(entry['version']), content, digest(content.encode()), digest(raw[spec_path]), start, start, 1, now, content))
        for path in paths[1:]:
            content = raw[path].decode('utf-8')
            tree = ast.parse(content, filename=str(path))
            symbols = [f'ticket_tool.py:{node.name}' for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))] if path == code_path else ['ticket_tool.py:*']
            # Whole source files preserve imports, module constants and test fixtures.
            rows.append((digest(str(path).encode()), 'code' if path == code_path else 'test', str(path), json.dumps(symbols), None, digest(raw[path]), content, digest(raw[path]), digest(raw[path]), 1, len(content.splitlines()), 1, now, content))
        try:
            with self.connection.cursor() as cursor:
                cursor.execute('DELETE FROM minimax_sources')
                cursor.execute('DELETE FROM minimax_manifest')
                cursor.executemany('INSERT INTO minimax_sources (source_id,source_type,path,symbol,spec_id,version,content,content_sha256,file_sha256,line_start,line_end,current_valid,imported_at,search_text) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)', rows)
                cursor.executemany('INSERT INTO minimax_manifest (path,file_sha256) VALUES (%s,%s)', [(str(p), digest(data)) for p, data in raw.items()])
            self.connection.commit()
        except BaseException:
            self.connection.rollback()
            raise
        return {'source_count': len(rows), 'file_count': len(paths), 'spec_ids': ids, 'imported_at': now, 'files': {str(p): digest(data) for p, data in raw.items()}, 'storage': 'real seekdb'}

    def query(self, task: dict) -> dict:
        evidence = []
        def execute(sql, params=()):
            with self.connection.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
            evidence.append({'sql': sql, 'params': list(params), 'rowcount': len(rows)})
            return list(rows)
        manifests = execute('SELECT path,file_sha256 FROM minimax_manifest ORDER BY path')
        if not manifests:
            raise StaleCatalogError('Catalog is empty; import project first.')
        for row in manifests:
            path = Path(row['path'])
            if not path.is_file() or digest(path.read_bytes()) != row['file_sha256']:
                raise StaleCatalogError(f'Stale source: {path}; re-import project before querying.')
        ids = task.get('spec_ids', [])
        tokens = task.get('query_tokens', [])
        if not isinstance(ids, list) or not isinstance(tokens, list) or any(not isinstance(x, str) or not x for x in [*ids, *tokens]):
            raise ValueError('spec_ids and query_tokens must be lists of nonempty strings.')
        clauses, params = [], []
        if ids:
            clauses.append('spec_id IN (' + ','.join(['%s'] * len(ids)) + ')')
            params.extend(ids)
        for token in tokens:
            clauses.append('search_text LIKE %s')
            params.append('%' + token.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%')
        specs = execute("SELECT * FROM minimax_sources WHERE current_valid=1 AND source_type='spec' AND (" + (' OR '.join(clauses) or '1=0') + ') ORDER BY spec_id', params)
        # The spec's symbol linkage chooses this small project's business file and
        # its complete test files; task names are never selection keys.
        linked = any(symbol.startswith('ticket_tool.py:') for row in specs for symbol in json.loads(row['symbol']))
        others = execute("SELECT * FROM minimax_sources WHERE current_valid=1 AND source_type IN ('code','test') AND symbol LIKE %s ORDER BY source_type,path", ('%ticket_tool.py:%',)) if linked else []
        version = execute('SELECT VERSION() AS version')[0]['version']
        sources = specs + others
        for row in sources:
            row['current'] = bool(row.pop('current_valid'))
            row['symbols'] = json.loads(row['symbol'])
            row.pop('search_text')
            if row['source_type'] in ('code', 'test'):
                tree = ast.parse(row['content'])
                row['symbol_locations'] = [{'name': node.name, 'line_start': node.lineno, 'line_end': node.end_lineno} for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
        self.connection.commit()
        return {'sources': sources, 'specifications': specs, 'code': [r for r in others if r['source_type'] == 'code'], 'tests': [r for r in others if r['source_type'] == 'test'], 'query_evidence': {'engine': 'seekdb', 'version': version, 'queries': evidence, 'source_rowcount': len(sources)}, 'task': task}
