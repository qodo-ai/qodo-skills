"""App-level settings that belong to you, not to one work package: the layout, Page views, theme, menus and
your saved layouts. Kept in app-state.json in the data home, so every session and every server port shares them."""
from __future__ import annotations

import contextlib
import json
import threading

from .util import HOME, write_json

# the browser keys the page may keep here; anything else stays in that browser (a review's own notes and picks)
APP_KEYS = ("cockpit:theme", "cockpit:package-layout:4", "cockpit:page-view", "cockpit:widget-view:2", "cockpit:wide-widgets",
            "cockpit:fit-height", "cockpit:nav-submenus", "cockpit:nav-collapsed", "cockpit:ask-qodo:2", "cockpit:wizard-seen",
            "cockpit:layout-template:2", "cockpit:layout-rtext", "cockpit:layout-codechg", "cockpit:decision-filter", "cockpit:my-layouts", "cockpit:verdict-rules",
            "cockpit:layout-dividers", "cockpit:layout-icons", "cockpit:layout-rtext-in-rsum", "cockpit:welcome", "cockpit:reader-mode", "cockpit:reader-zoom", "cockpit:reader-pages")   # cockpit:welcome: the welcome page, {hide, last}
MAX_BYTES = 512_000   # the whole file: a few dozen layouts fit easily
_lock = threading.Lock()


def path():
    return HOME / "app-state.json"


def load() -> dict:
    """The saved settings, only the known keys; a missing or damaged file reads as none."""
    try:
        d = json.loads(path().read_text())
    except (OSError, ValueError):
        return {}
    return {k: v for k, v in d.items() if k in APP_KEYS} if isinstance(d, dict) else {}


@contextlib.contextmanager
def _locked():
    """Serialize the complete merge across threads and server processes, including Windows."""
    from .file_lock import file_lock
    with _lock, file_lock(path().with_name('.app-state.lock')):
        yield


def update(changes) -> dict:
    """Merge {key: value} into the file (None removes a key) and return the result. Raises ValueError on an
    unknown key or a file that would grow past MAX_BYTES."""
    if not isinstance(changes, dict):
        raise ValueError("send an object of settings")
    bad = [k for k in changes if k not in APP_KEYS]
    if bad:
        raise ValueError(f"not an app setting: {', '.join(map(str, bad))[:200]}")
    with _locked():   # read, merge and write as one step, so two ports never drop each other's change
        d = load()
        for k, v in changes.items():
            if v is None:
                d.pop(k, None)
            else:
                d[k] = v
        if len(json.dumps(d, ensure_ascii=False).encode()) > MAX_BYTES:
            raise ValueError("the app settings would be too large; delete a saved layout first")
        write_json(path(), d)
    return d
