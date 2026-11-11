"""Portable product enrichment/refresh writer exclusion; local events are independent."""
from __future__ import annotations

import json
import os
import threading
from contextlib import contextmanager
from contextvars import ContextVar

_HELD = ContextVar('cockpit_session_writers', default=())
LOCK_NAME = '.cockpit-writer.lock'


class SessionBusy(RuntimeError):
    pass


@contextmanager
def session_writer(sdir):
    """One writer per session across processes; only this owner's nested calls reenter."""
    from .session_activity import session_activity
    with session_activity(sdir):
        with _writer(sdir):
            yield


@contextmanager
def _writer(sdir):
    owner = (str(sdir.resolve()), os.getpid(), threading.get_ident())
    held = _HELD.get()
    if owner in held:
        yield
        return
    lock = sdir / LOCK_NAME
    try:
        lock.mkdir()
    except FileExistsError:
        raise SessionBusy('Work package busy: enrichment or refresh already owns ' + str(lock) +
                          '. Retry after it finishes; a stale guard requires manual recovery.') from None
    token = None
    try:
        (lock / 'owner.json').write_text(json.dumps({'pid':owner[1], 'thread':owner[2]}))
        token = _HELD.set(held + (owner,))
        yield
    finally:
        if token is not None:
            _HELD.reset(token)
        (lock / 'owner.json').unlink(missing_ok=True)
        lock.rmdir()
