"""Serialize a shared optional memory bundle's mutations, including nested method calls."""
from contextvars import ContextVar
from contextlib import contextmanager
from functools import wraps
import hashlib
import os
import threading

_HELD = ContextVar('cockpit_memory_writers', default=())


@contextmanager
def memory_transaction(root):
    from .file_lock import file_lock
    root = root.resolve()
    owner = (str(root), os.getpid(), threading.get_ident())
    held = _HELD.get()
    if owner in held:
        yield
        return
    name = hashlib.sha256(str(root).encode()).hexdigest() + '.lock'
    with file_lock(root.parent / '.cockpit-memory-locks' / name):
        token = _HELD.set(held + (owner,))
        try:
            yield
        finally:
            _HELD.reset(token)


def memory_write(method):
    @wraps(method)
    def run(self, *args, **kwargs):
        with memory_transaction(self.root):
            return method(self, *args, **kwargs)
    return run
