"""Build/start a separate copy of the existing UI without touching its build state."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile
import os


def prepare_ui(state, source=None):
    from .catalog import ROOT
    source = Path(source or ROOT / 'frontend')
    if not (source / 'node_modules').is_dir():
        raise ValueError('Install the existing frontend dependencies first.')
    target = Path(tempfile.mkdtemp(prefix='ui-', dir=state))
    excluded = {'node_modules', '.next', '.browser-cache', 'test-results', 'playwright-report'}
    for item in source.iterdir():
        if item.name in excluded or item.name.startswith('.env'): continue
        if item.is_symlink(): continue
        if item.is_dir(): shutil.copytree(item, target / item.name)
        else: shutil.copy2(item, target / item.name)
    (target / 'node_modules').symlink_to(source / 'node_modules', target_is_directory=True)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=3002)
    parser.add_argument('--api-port', type=int, default=8003)
    parser.add_argument('--state-dir', type=Path)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535 or not 1024 <= args.api_port <= 65535:
        parser.error('Select valid independent unprivileged ports.')
    if args.port in {3000, 3001} or args.api_port in {8000, 8002}:
        parser.error('Use independent ports, such as UI 3002 and API 8003.')
    from .app import state_directory
    try: target = prepare_ui(state_directory(args.state_dir))
    except Exception:
        parser.exit(1, 'Could not prepare the isolated UI. Check frontend dependencies and extension state.\n')
    env = {**os.environ, 'BUILDER_API_URL': f'http://127.0.0.1:{args.api_port}', 'NEXT_TELEMETRY_DISABLED': '1'}
    result = subprocess.run(['npm', 'run', 'build'], cwd=target, env=env)
    if result.returncode: raise SystemExit(result.returncode)
    print(f'Extension UI copy: {target}', flush=True)
    raise SystemExit(subprocess.call(['npm', 'run', 'start', '--', '--hostname', '127.0.0.1', '--port', str(args.port)], cwd=target, env=env))

if __name__ == '__main__': main()
