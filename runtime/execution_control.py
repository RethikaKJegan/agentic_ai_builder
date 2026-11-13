"""Durable execution fencing around synchronous provider adapters.

Python cannot kill an arbitrary in-flight SDK call safely. The caller returns on
stop/deadline, late results are discarded, and subsequent dispatch is fenced.
External submissions interrupted after dispatch require provider reconciliation.
"""
from contextvars import ContextVar, copy_context
from queue import Queue, Empty
from threading import Thread
import time

from .service import RuntimeFailure

_execution_check = ContextVar('runtime_execution_check', default=None)
model_limits_required = ContextVar('runtime_model_limits_required', default=False)


def check_execution():
    check = _execution_check.get()
    if check is not None:
        check()


def guarded_call(check, invoke, *, timeout, timeout_code, cancel=None):
    check()
    if timeout <= 0:
        raise RuntimeFailure(timeout_code, 'The invocation deadline is exhausted.')
    result = Queue(maxsize=1)
    token = _execution_check.set(check)
    context = copy_context()
    _execution_check.reset(token)

    def execute():
        try:
            check_execution()
            value = invoke()
            result.put((True, value))
        except BaseException as error:
            result.put((False, error))

    thread = Thread(target=lambda: context.run(execute), name='runtime-bounded-invocation', daemon=True)
    started = time.monotonic()
    thread.start()
    try:
        while True:
            check()
            remaining = timeout - (time.monotonic() - started)
            if remaining <= 0:
                raise RuntimeFailure(timeout_code, 'The invocation deadline is exhausted.')
            try:
                success, value = result.get(timeout=min(.1, remaining))
            except Empty:
                continue
            check()
            if success:
                return value
            raise value
    except BaseException:
        if cancel is not None:
            try:
                cancel()
            except Exception:
                pass  # A cancellation request never proves a provider rollback.
        raise

_provider_request = ContextVar('runtime_provider_request', default=None)


def controlled_response(client, **arguments):
    """Apply an enclosing operation's durable accounting at a provider boundary."""
    check_execution()
    hook = _provider_request.get()
    if hook is not None:
        return hook(lambda options: client.responses.create(**options), arguments)
    result = client.responses.create(**arguments)
    check_execution()
    return result

policy_resolver = ContextVar('runtime_policy_resolver', default=None)


def resource_allowed(identifier, kind):
    resolve = policy_resolver.get()
    return resolve is None or identifier not in resolve().get('restricted_' + kind, [])


def check_source(identifier):
    if not resource_allowed(identifier, 'sources'):
        raise RuntimeFailure('SOURCE_RESTRICTED', 'This source is restricted by effective workspace policy.', 403)

request_method = ContextVar('runtime_request_method', default=None)

retry_reserver = ContextVar('runtime_retry_reserver', default=None)

def reserve_retry():
    reserve = retry_reserver.get()
    if reserve is not None:
        reserve()
