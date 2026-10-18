"""Run focused database regressions with a disposable PostgreSQL test server.

The CRUD and read-engine tests manage their own temporary MongoDB replica sets.
No saved source credentials, cloud datasets or managed services are accessed.
"""
import os
from pathlib import Path
import pwd
import shutil
import socket
import subprocess
import sys
import tempfile
from urllib.parse import quote


def main(tests=None, evidence_directory='.local/phase4-crud'):
    root = Path(__file__).resolve().parents[1]
    binary = Path('/usr/lib/postgresql/16/bin')
    if not (binary/'initdb').exists() or not shutil.which('mongod'):
        raise SystemExit('Install PostgreSQL 16 server tools and mongod for real isolated verification.')
    evidence = root/evidence_directory
    evidence.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix='pg-', dir=evidence))
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    data = directory/'data'
    started = False
    try:
        subprocess.run([str(binary/'initdb'), '-D', str(data), '--auth=trust', '--no-locale', '--encoding=UTF8'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        subprocess.run([str(binary/'pg_ctl'), '-D', str(data), '-l', str(directory/'postgres.log'), '-o', f'-F -h 127.0.0.1 -p {port} -k {directory}', '-w', 'start'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        started = True
        env = dict(os.environ)
        username = quote(pwd.getpwuid(os.getuid()).pw_name)
        env['BUILDER_TEST_POSTGRES_DSN'] = f'postgresql://{username}@127.0.0.1:{port}/postgres'
        tests = tests or ['test_data_operations', 'test_data_selection', 'test_data_queries', 'test_data_graph_v2',
                 'test_data_relationships', 'test_data_sources', 'test_data_query_jobs',
                 'test_data_query_pushdown', 'test_data_query_federation']
        with (evidence/'backend.log').open('w') as log:
            result = subprocess.run([sys.executable, '-m', 'pytest', '-q', *[f'tests/{name}.py' for name in tests]], cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT)
        print((evidence/'backend.log').read_text())
        return result.returncode
    finally:
        if started:
            subprocess.run([str(binary/'pg_ctl'), '-D', str(data), '-m', 'immediate', '-w', 'stop'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


if __name__ == '__main__':
    raise SystemExit(main())
