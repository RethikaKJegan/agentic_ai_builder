"""Run trusted Builder background workers without exposing an HTTP listener."""
import asyncio
from pathlib import Path
import signal
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


async def run_app(app,stop):
    async with app.router.lifespan_context(app):
        await stop.wait()


async def serve():
    from workflow_api.live_providers import create_configured_app,environment
    env=environment();env['BUILDER_PROCESS_ROLE']='worker'
    app=create_configured_app(env)
    stop=asyncio.Event();loop=asyncio.get_running_loop()
    for name in (signal.SIGINT,signal.SIGTERM):loop.add_signal_handler(name,stop.set)
    await run_app(app,stop)


if __name__=='__main__':asyncio.run(serve())
