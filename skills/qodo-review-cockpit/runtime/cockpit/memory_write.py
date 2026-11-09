"""Serialize a shared optional memory bundle's mutations, including nested method calls."""
from contextvars import ContextVar
from functools import wraps
import hashlib
import os
import threading

_HELD = ContextVar('cockpit_memory_writers', default=())


def memory_write(method):
    @wraps(method)
    def run(self, *args, **kwargs):
        from .file_lock import file_lock
        root = self.root.resolve()
        owner = (str(root), os.getpid(), threading.get_ident())
        held = _HELD.get()
        if owner in held:
            return method(self, *args, **kwargs)
        name = hashlib.sha256(str(root).encode()).hexdigest() + '.lock'
        with file_lock(root.parent / '.cockpit-memory-locks' / name):
            token = _HELD.set(held + (owner,))
            try:
                return method(self, *args, **kwargs)
            finally:
                _HELD.reset(token)
    return run
