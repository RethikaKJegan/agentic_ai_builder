"""Start the real local backend with Socket Mode, Gmail and durable workers."""
from pathlib import Path
import argparse
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    from workflow_api.slack_gmail import environment, create_configured_app
    env = environment()
    for key, value in env.items():
        os.environ.setdefault(key, value)
    try:
        app = create_configured_app(env=env)
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=args.port)


if __name__ == '__main__':
    main()
