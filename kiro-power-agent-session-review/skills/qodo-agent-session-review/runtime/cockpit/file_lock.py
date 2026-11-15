"""OS-released process lock for the short shared-settings read/merge/write transaction."""
from contextlib import contextmanager
import os


@contextmanager
def file_lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b', buffering=0) as stream:   # unbuffered: a refused write leaves nothing queued to fail again on close
        if os.name == 'nt':
            import msvcrt
            if stream.seek(0, 2) == 0:
                try:   # another process may create the byte and lock it first: then it already exists
                    stream.write(b'\0')
                    stream.flush()
                except PermissionError:
                    pass
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
