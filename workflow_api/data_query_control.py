"""Request-local query controls; background monitor can cancel an active PG read."""
from contextlib import contextmanager
from contextvars import ContextVar
from threading import Event, Lock, Thread

from .service import ApiFailure

CURRENT = ContextVar('data_query_execution_control', default=None)


def checkpoint(stage=None, fragment=None):
    control = CURRENT.get()
    if control is not None:
        control.check()
        if stage is not None:
            control.progress(stage, fragment)


@contextmanager
def track_postgres(conn):
    control = CURRENT.get()
    if control is None:
        yield conn
        return
    with control.lock:
        control.connections.add(conn)
    try:
        control.check()
        yield conn
        control.check()
    finally:
        with control.lock:
            control.connections.discard(conn)


class QueryExecutionControl:
    def __init__(self, jobs, job):
        self.jobs, self.job = jobs, job
        self.lock, self.stop_event = Lock(), Event()
        self.connections, self.error = set(), None
        self.thread = None

    def check(self):
        with self.lock:
            error = self.error
        if error is not None:
            raise error

    def stop_with(self, error):
        with self.lock:
            if self.error is None:
                self.error = error
            connections = list(self.connections)
        for conn in connections:
            try:
                conn.cancel_safe(timeout=1)
            except Exception:
                pass  # The terminal claim/deadline checks still fence publication.

    def progress(self, stage, fragment):
        self.jobs.progress(self.job, stage, fragment)
        self.check()

    def __enter__(self):
        self.token = CURRENT.set(self)
        try:
            self.jobs.pulse(self.job)
            def monitor():
                while not self.stop_event.wait(self.jobs.heartbeat_interval):
                    try:
                        self.jobs.pulse(self.job)
                    except ApiFailure as error:
                        self.stop_with(error)
                        return
                    except Exception:
                        self.stop_with(ApiFailure('DATA_QUERY_LEASE_LOST', 'Query coordination became unavailable. No result was published.', 503))
                        return
            self.thread = Thread(target=monitor, name='builder-query-heartbeat', daemon=True)
            self.thread.start()
            return self
        except BaseException:
            CURRENT.reset(self.token)
            raise

    def __exit__(self, *_):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)
        CURRENT.reset(self.token)
