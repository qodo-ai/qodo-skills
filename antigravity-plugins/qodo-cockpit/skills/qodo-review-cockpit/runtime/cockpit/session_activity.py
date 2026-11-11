"""Cross-process exclusion between active work-package operations and recoverable Trash."""
from contextlib import contextmanager
from contextvars import ContextVar
import os
import threading
import uuid

_HELD = ContextVar('cockpit_session_activity', default=())


@contextmanager
def session_activity(sdir, *, exclusive=False):
    from .session_writer import SessionBusy
    from .file_lock import file_lock
    owner = (str(sdir.resolve()), os.getpid(), threading.get_ident())
    held = _HELD.get()
    previous = next((kind for candidate, kind in held if candidate == owner), None)
    if previous is not None:
        if exclusive and not previous:
            raise SessionBusy('Work package busy; an active request cannot upgrade itself to Trash.')
        yield
        return
    # Requests share leases; only Trash is exclusive. Browser assets must load concurrently.
    # The guard survives moving the work package itself into Trash.
    guard = sdir.parent / '.cockpit-active' / sdir.name
    guard.mkdir(parents=True, exist_ok=True)
    with file_lock(guard / 'gate.lock'):
        if (guard / 'exclusive').exists() or (exclusive and any(guard.glob('lease-*'))):
            raise SessionBusy('Work package busy; retry after its current operation finishes. '
                              'A stale activity guard requires manual recovery: ' + str(guard))
        lease = guard / ('exclusive' if exclusive else f'lease-{owner[1]}-{owner[2]}-{uuid.uuid4().hex}')
        lease.mkdir()
    token = _HELD.set(held + ((owner, exclusive),))
    try:
        yield
    finally:
        _HELD.reset(token)
        lease.rmdir()
