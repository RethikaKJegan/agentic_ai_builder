"""python -m connector_extension: separate launcher; never starts automatically."""
import argparse
import json
from pathlib import Path
from .catalog import CATALOG


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, help='Separate operator configuration JSON.')
    parser.add_argument('--port', type=int, default=8003)
    parser.add_argument('--state-dir', type=Path, help='Optional subdirectory under .local/connector-extension.')
    parser.add_argument('--catalog', action='store_true', help='Print canonical tool definitions without starting providers.')
    args = parser.parse_args()
    if args.catalog:
        print(json.dumps(list(CATALOG.values()), indent=2)); return
    if args.config is None: parser.error('--config is required unless --catalog is used')
    if args.port in {8000, 8002} or not 1024 <= args.port <= 65535:
        parser.error('Select an independent unprivileged port, such as 8003.')
    from .app import create_extension_app
    try: app = create_extension_app(args.config, args.state_dir, start_workers=True)
    except Exception:
        parser.exit(1, 'Extension configuration is invalid. See connector_extension/README.md; existing services were not changed.\n')
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=args.port)

if __name__ == '__main__': main()
