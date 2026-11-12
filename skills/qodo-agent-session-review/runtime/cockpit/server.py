"""Local server for the review app. Binds to 127.0.0.1 only."""
from __future__ import annotations

import json
import re
import secrets
import threading
from contextlib import nullcontext
from http.cookies import CookieError, SimpleCookie
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit
from pathlib import Path

from .distill import distill, latest_state, load_events
from .memory import AMR, OKF, git_commit
from . import threads
from .util import EMOJI, ROOT, SESSIONS, gh, mem_path, memory_on, now_iso, session_config, set_sessions, write_json

APP = ROOT / "app"
_lock = threading.Lock()
_SID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,80}")
MAX_BODY = 2_000_000


class BodyError(ValueError):
    def __init__(self, message, code=400):
        super().__init__(message)
        self.code = code


def session_named(name) -> Path | None:
    """A session folder by its id, only when it sits directly under sessions/ (a name, never a path)."""
    if not isinstance(name, str) or not _SID.fullmatch(name) or ".." in name:
        return None
    start = getattr(Handler, "sdir", None)   # the package the server opened with stays reachable after a folder change
    for base in dict.fromkeys([SESSIONS] + ([start.parent] if start else [])):
        d = base / name
        if (d / "review-data.json").is_file():
            return d
    return None


def _friendly(title: str) -> str:
    """A PR title as a feature name: no "feat:" style prefix, no "- 2 of 3" part number."""
    t = re.sub(r"^\s*\w+(\([^)]*\))?!?:\s*", "", title)
    t = re.sub(r"\s*[-–(]\s*\d+\s*(of|/)\s*\d+\)?\s*$", "", t).strip()
    return t[:1].upper() + t[1:] if t else title


def list_sessions() -> list[dict]:
    """Every work package collected on this machine, newest first, for the page header's switcher."""
    from .view import package_name, title_of
    out = []
    for d in (SESSIONS.iterdir() if SESSIONS.is_dir() else []):
        if not session_named(d.name):
            continue
        try:
            data = json.loads((d / "review-data.json").read_text())
        except (OSError, ValueError):
            continue
        title = _friendly(title_of(data))
        if title == "PR review" and data.get("prs"):   # no story yet: the feature most of its PRs are named for
            names = [_friendly(p.get("title") or "") for p in data["prs"]]
            title = max(names, key=names.count) or title
        name = package_name(d)
        out.append({"id": d.name, "title": name or title, "auto": title, "named": bool(name), "prs": [p.get("key") for p in data.get("prs", [])],
                    "repos": len({p.get("repo") for p in data.get("prs", [])}), "stacks": len([c for c in (data.get("context") or {}).get("stacks") or [] if len(c) > 1]),
                    "path": str(d).replace(str(Path.home()), "~", 1),
                    "created": data.get("created", ""), "story": (d / "enrich.json").is_file(),
                    "demo": bool(data.get("demo")), "dummy": bool(data.get("dummy"))})
    return sorted(out, key=lambda s: (s["created"], s["id"]), reverse=True)


def _sources() -> dict:
    from . import util
    return {"sessions": str(util.SESSIONS), "default": str(util.HOME / "sessions"), "count": len(list_sessions()),
            "custom": util.SESSIONS != util.HOME / "sessions"}


def append_events(sdir: Path, events: list[dict], session: str, source: str = "app") -> int:
    from .product import enabled
    data_file = sdir / 'review-data.json'
    product = enabled(json.loads(data_file.read_text()) if data_file.is_file() else {})
    if product:
        events = [{**e, 'post': False} if e.get('type') == 'note' else e for e in events]
        from .secret_values import session_events
        events = session_events(sdir, events=events)
    from .session_activity import session_activity
    with session_activity(sdir) if product else nullcontext(), _lock, (sdir / "events.jsonl").open("a") as fh:
        for e in events:
            e.setdefault("ts", now_iso()); e.setdefault("session", session); e.setdefault("source", source)
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
    return len(events)


def build_review(sdir: Path, pr_key: str, emoji: dict, live_threads: dict | None = None) -> tuple[dict, list[str], list[dict]]:
    """What publishing posts for one PR, from un-posted notes marked `post`: the GitHub review payload (inline
    notes and the review body), the note ids it carries, and the replies: notes on a finding that has its own
    review thread, posted in that thread (and resolving it when the note asks). `live_threads` is the PR's
    thread state just read from GitHub ({first comment id: state}); without it, the state from collection."""
    raw = load_events(sdir)
    events = latest_state(raw)
    posted = {nid for e in raw if e.get("type") == "published" for nid in e.get("note_ids", [])}
    try:
        pr = next(p for p in json.loads((sdir / "review-data.json").read_text())["prs"] if p["key"] == pr_key)
    except (StopIteration, OSError, ValueError):
        pr = {}
    findings = {f["id"]: f for f in pr.get("findings") or []}
    comments, general, ids, replies = [], [], [], []
    for e in events:
        if e.get("type") != "note" or e.get("pr") != pr_key or not e.get("post") or e.get("posted"):
            continue
        if e.get("note_id") in posted:
            continue
        prefix = (emoji.get(e.get("emoji") or "") or {}).get("prefix")
        body = f"{prefix} {e['text']}" if prefix else e["text"]
        target = e.get("target") or {}
        f = findings.get(target.get("id")) if target.get("kind") == "finding" else None
        cid = threads.comment_id(f) if f else None
        th = (live_threads.get(cid) if live_threads is not None else (f or {}).get("thread")) if cid else None
        if th and th.get("can_reply", True):
            replies.append({"note_id": e.get("note_id"), "comment_id": cid, "thread_id": th.get("id"), "body": body,
                            "resolve": bool(e.get("resolve")), "resolved": bool(th.get("resolved")),
                            "can_resolve": bool(th.get("can_resolve")), "title": (f.get("title") or "")[:120],
                            "url": f.get("url") or f.get("thread_url")})
            continue
        if e.get("path") and e.get("line"):
            comments.append({"path": e["path"], "line": int(e["line"]), "side": "RIGHT", "body": body})
        else:
            label = target.get("label")
            general.append(f"- {body}" + (f"  _(on {label})_" if label else ""))
        ids.append(e.get("note_id"))
    # a reply that posted but whose thread didn't resolve: retry only the resolve, never the reply
    done = {e.get("thread_id") for e in raw if e.get("type") == "thread_resolved"}
    for e in raw:
        if e.get("type") != "published" or e.get("pr") != pr_key or not e.get("resolve_pending") or e.get("thread_id") in done:
            continue
        done.add(e.get("thread_id"))
        th = (live_threads or {}).get(e.get("reply_to")) or {}
        replies.append({"note_id": (e.get("note_ids") or [None])[0], "comment_id": e.get("reply_to"), "thread_id": e.get("thread_id"),
                        "body": "", "resolve": True, "resolve_only": True, "title": e.get("title") or "",
                        "resolved": bool(th.get("resolved")), "can_resolve": bool(th.get("can_resolve", True)), "url": e.get("url")})
    body = "\n".join(general) if general else ""
    if pr:   # the reviewer's plan, collapsed, so readers see what was read and what was safe to skip
        from .attention import plan_markdown
        pm = plan_markdown(pr)
        if pm:
            body += ("\n\n" if body else "") + pm
    body += f"\n\n<!-- pr-review-cockpit:{sdir.name} -->"
    return {"event": "COMMENT", "body": body.strip(), "comments": comments}, ids, replies


def _saved_recipes() -> list[dict]:
    from .styles import _recipes
    return [{"id": r["id"], "name": r["name"], "about": r.get("about", "")} for r in _recipes()]


class Handler(SimpleHTTPRequestHandler):
    sdir: Path
    cfg: dict
    style: str = "focus"   # what / shows; every style is also at /s/<name>, the app at /index.html
    boot: str = ""   # set per server start, so a switcher pick from an earlier run never outlives it

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(APP), **kw)

    def log_message(self, fmt, *args):  # quiet
        pass

    @property
    def _cookie(self) -> str:
        return f"ck_session_{self.server.server_address[1]}"

    def _pick_session(self) -> bool:
        """Point this request at its work package: the page's own (X-Cockpit-Session), else the one picked
        in the switcher since this server started (cookie), else the one it was started with."""
        head = self.headers.get("X-Cockpit-Session")
        if head is None:   # an <img> can't send a header, so a media URL names its package as ?s=
            head = parse_qs(urlsplit(self.path).query).get("s", [None])[0]
        if head is not None:
            d = session_named(head)
            if not d:
                return False   # a tab whose package is gone must not write into another one
        else:
            try:
                m = SimpleCookie(self.headers.get("Cookie") or "").get(self._cookie)
            except CookieError:
                m = None
            boot, _, name = (m.value if m else "").partition(".")
            d = session_named(name) if boot and boot == Handler.boot else None
        if d and d != Handler.sdir:
            self.sdir, self.cfg = d, session_config(d)
            self.cfg.setdefault("emoji", EMOJI)
        return True

    def _json(self, obj, code=200, cookie: str | None = None):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def _body(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise BodyError('Invalid Content-Length') from None
        if n < 0:
            raise BodyError('Invalid Content-Length')
        if n > MAX_BODY:
            raise BodyError('JSON request body is too large', 413)
        return json.loads(self.rfile.read(n) or b"{}")

    def _data(self):
        data = json.loads((self.sdir / "review-data.json").read_text())
        if getattr(getattr(self, 'server', None), 'product', False):
            data = {**data, 'product': True, 'provider_writes': False}
        from .product import enabled, project_data
        return project_data(data) if enabled(data) else data

    def _memory(self):
        amr, okf = AMR(mem_path(self.cfg, "amr")), OKF(mem_path(self.cfg, "okf"))
        return {"enabled": memory_on(self.cfg), "rules": amr.active_rules(self.cfg["distill"]["dismiss_threshold"]),
                "bullets": [{"text": b.text, "file": b.file, **b.meta} for b in amr.bullets()],
                "concepts": [c.as_dict() for c in okf.concepts()]}

    def _html(self, html: str, code=200):
        b = html.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(b)

    def _style(self, name: str):
        from .styles import APP, as_document, render, require
        try:
            name = require(name)
        except ValueError as e:
            return self._html(f"<!doctype html><meta charset=utf-8><title>Unknown style</title><p>{e}</p><p><a href='/index.html'>Open Agent Session Review</a></p>", 404)
        if name == APP:
            self.send_response(302); self.send_header("Location", "/index.html"); self.end_headers()
            return
        link = bool(getattr(self.server, 'access_key', None)) and getattr(self.server, 'product', False)   # Session auth: Open in external browser, for another browser
        return self._html(as_document(render(name, self.sdir, mode="serve", access_link=link)))

    def _origin_error(self):
        """The existing local host/same-origin request boundary, shared by product reads."""
        origin = self.headers.get('Origin')
        host = self.headers.get('Host', '')
        if host.rpartition(':')[0] not in ('127.0.0.1', 'localhost', '[::1]'):
            return 'unknown host'
        if origin and origin != 'http://' + host:
            return 'cross-origin request refused'
        return None

    def do_GET(self):
        from .product import enabled
        error = self._origin_error()
        if error and (enabled() or getattr(getattr(self, 'server', None), 'product', False)):
            return self._json({'error': error}, 403)
        route = self.path.split("?")[0]
        if route == "/api/health":   # the page's server check: answers before any package is picked, so a gone package can't hide a live server
            return self._json({"ok": True, "time": now_iso()})
        if route == '/_access':
            from .local_access import BOOTSTRAP
            return self._html(BOOTSTRAP)
        if not self._pick_session():
            return self._json({"error": "this work package is no longer on this machine; reload the page"}, 404)
        if error and json.loads((self.sdir / 'review-data.json').read_text()).get('product'):
            # Only inspect the selected session's mode before rejecting; no data projection or route runs.
            return self._json({'error': error}, 403)
        return self._session_request(lambda: self._get_selected(route))

    def _session_request(self, operation):
        from .product import enabled, scope
        try:
            saved = json.loads((self.sdir / 'review-data.json').read_text())
        except FileNotFoundError:
            return self._json({'error': 'This work package was moved; reload the page.'}, 404)
        is_product = enabled(saved) or getattr(self.server, 'product', False)
        if not is_product:
            return operation()
        from .local_access import authorized
        if not authorized(self):
            return self._json({'error': 'Reopen Agent Session Review from its launcher to authorize this browser.'}, 403)
        from .session_activity import session_activity
        from .session_writer import SessionBusy
        try:
            with session_activity(self.sdir), scope({'product': True}):
                if not (self.sdir / 'review-data.json').is_file():
                    return self._json({'error': 'This work package was moved; reload the page.'}, 404)
                return operation()
        except SessionBusy as e:
            return self._json({'error': str(e)}, 409)

    def _get_selected(self, route):
        if route == "/api/sessions":
            return self._json({"current": self.sdir.name, "sessions": list_sessions()})
        if route == "/api/sources":   # Settings › Work packages: the folder the switcher lists
            return self._json(_sources())
        if route == "/favicon.ico":   # the Qodo icon, for a browser that asks before reading the page's own link
            b = (ROOT / "app" / "favicon.svg").read_bytes()   # not APP: do_GET imports another APP from .styles below
            self.send_response(200); self.send_header("Content-Type", "image/svg+xml"); self.send_header("Content-Length", str(len(b))); self.end_headers()
            self.wfile.write(b)
            return
        if route == "/api/app-state":   # your app settings, shared by every session and port
            from . import appstate
            return self._json({"keys": list(appstate.APP_KEYS), "state": appstate.load(), "path": str(appstate.path())})
        if route == "/" and self.style != "cockpit":
            return self._style(self.style)
        if route.startswith("/s/"):
            return self._style(route[3:].strip("/"))
        if self.path == "/api/data":
            return self._json({**self._data(), "_dir": self.sdir.name})   # the folder the page's later calls must name
        if self.path.startswith("/api/events"):
            values = parse_qs(urlsplit(self.path).query).get('since', ['0'])
            if len(values) != 1 or not re.fullmatch(r'[0-9]{1,16}', values[0]):
                return self._json({'error': 'since must be one nonnegative event offset'}, 400)
            since = int(values[0])
            from .secret_values import session_events
            ev = session_events(self.sdir) if getattr(self.server, 'product', False) else load_events(self.sdir)
            return self._json({"events": ev[since:], "n": len(ev)})
        if self.path == "/api/recipes":   # your own styles, and the Describe requests still open
            from . import recipes as R
            return self._json({"recipes": R.load_all(), "requests": R.requests()})
        if self.path == "/api/styles":
            from .styles import APP, STYLES, missing_content
            data = self._data()   # a style whose content the skill hasn't written has nothing to open yet
            return self._json({"current": self.style, "styles": [{"id": k, "name": v["name"], "what": v["what"],
                               "url": None if k != APP and missing_content(k, data) else "/index.html" if k == APP else f"/s/{k}"}
                               for k, v in STYLES.items() if v["ready"]],
                               "recipes": _saved_recipes()})
        if self.path == "/api/memory":
            return self._json(self._memory())
        if self.path == "/api/live":
            return self._json(self._live())
        if self.path == "/api/refresh":
            return self._json(Handler._refreshing.get(self.sdir.name) or {"state": "idle"})
        if self.path.startswith("/media/"):
            return self._media(self.path[len("/media/"):].split("?")[0])
        return super().do_GET()

    _live_cache: dict = {}

    _refreshing: dict = {}   # session -> {"state": running|done|error, ...}: one refresh at a time
    _refresh_lock = __import__("threading").Lock()   # requests run on their own threads: check and start as one step

    def _live(self):
        """GitHub state of each PR vs this snapshot, cached for 150 s (demo sessions: none)."""
        import time
        data = self._data()
        if data.get("demo"):
            return {"prs": {}}
        hit = Handler._live_cache.get(self.sdir.name)
        if hit and time.time() - hit[0] < 150:
            return hit[1]
        from .collect import live_state
        res = {"prs": live_state(data["prs"], data.get("created", "")), "checked_at": now_iso()}
        Handler._live_cache[self.sdir.name] = (time.time(), res)
        return res

    def _reveal(self, target=None):
        """Open a folder in the system file manager (Finder on macOS): this session's (the default), the work package
        folder ("sessions") or the app settings file's ("app-state", the file selected). Never a path from the request."""
        import subprocess
        import sys
        from . import appstate, util
        if target not in (None, "", "sessions", "app-state") and not (isinstance(target, dict) and session_named(target.get("session"))):
            return {"error": "unknown folder"}
        p = session_named(target["session"]) if isinstance(target, dict) else util.SESSIONS if target == "sessions" else appstate.path() if target == "app-state" else self.sdir
        pick = target == "app-state" and p.is_file()   # select the file in its folder; before it exists, open the folder
        if target == "app-state" and not pick:
            p = p.parent
        if sys.platform == "darwin":
            argv = ["open", "-R", str(p)] if pick else ["open", str(p)]
        elif sys.platform == "win32":
            argv = ["explorer", f"/select,{p}"] if pick else ["explorer", str(p)]
        else:
            argv = ["xdg-open", str(p.parent if pick else p)]
        r = subprocess.run(argv, capture_output=True, text=True, timeout=10)
        if r.returncode and sys.platform != "win32":   # explorer exits 1 even when the folder opened
            return {"error": (r.stderr or "").strip() or f"{argv[0]} exited with {r.returncode}"}
        return {"ok": True, "path": str(p).replace(str(Path.home()), "~", 1)}

    def _trash(self, name):
        """Move a work package's folder to the Trash (macOS), else to trash/ in the data home: recoverable, never
        the package this page or this server has open, never a refresh in progress."""
        import shutil
        import sys
        from . import util
        d = session_named(name)
        if not d:
            return {"error": "unknown work package"}, 404
        if d in (self.sdir, Handler.sdir):
            return {"error": "this package is open here; switch to another before deleting it"}, 409
        bin_ = Path.home() / ".Trash" if sys.platform == "darwin" else util.HOME / "trash"
        from .session_activity import session_activity
        from .session_writer import SessionBusy, LOCK_NAME
        try:
            with session_activity(d, exclusive=True), Handler._refresh_lock:
                if (Handler._refreshing.get(d.name) or {}).get("state") == "running":
                    return {"error": "this package is refreshing; delete it once that finishes"}, 409
                if (d / LOCK_NAME).exists():
                    return {'error': 'This package is busy; retry after its writer finishes.'}, 409
                bin_.mkdir(parents=True, exist_ok=True)
                dest, n = bin_ / d.name, 2
                while dest.exists():
                    dest, n = bin_ / f"{d.name} {n}", n + 1
                shutil.move(str(d), str(dest))
        except SessionBusy as e:
            return {'error': str(e)}, 409
        return {"ok": True, "trash": str(dest).replace(str(Path.home()), "~", 1), "sessions": list_sessions()}, 200

    def _refresh(self, data):
        """Re-collect the session in the background (`cockpit refresh`): notes, marks and the story stay."""
        import threading
        if data.get("demo"):
            return {"error": "the demo has nothing to re-read from GitHub"}
        key, sdir, cfg = self.sdir.name, self.sdir, self.cfg
        with Handler._refresh_lock:
            if (Handler._refreshing.get(key) or {}).get("state") == "running":
                return {"ok": True, "state": "running"}
            Handler._refreshing[key] = {"state": "running", "started": now_iso()}

        admitted = threading.Event()
        def run():
            from .collect import refresh
            from .session_activity import session_activity
            try:
                # The request retains its lease until this thread owns a separate one.
                with session_activity(sdir):
                    admitted.set()
                    res = refresh(sdir, cfg)
                Handler._refreshing[key] = {"state": "done", "at": now_iso(), "session": key, "warnings": (res or {}).get("warnings", [])[:20]}
            except Exception as e:   # shown on the button's tooltip
                Handler._refreshing[key] = {"state": "error", "error": str(e)[:300]}
            finally:
                admitted.set()
            Handler._live_cache.pop(key, None)
        from contextvars import copy_context
        context = copy_context()
        threading.Thread(target=lambda: context.run(run), daemon=True).start()
        if not admitted.wait(5):
            return {"error": "Refresh worker has not started; check its status before retrying."}
        if (Handler._refreshing.get(key) or {}).get('state') == 'error':
            return Handler._refreshing[key]
        return {"ok": True, "state": "running"}

    def _media(self, name: str):
        """Screenshots and videos the skill saved into sessions/<id>/media/ (story beats)."""
        import mimetypes
        from urllib.parse import unquote
        root = (self.sdir / "media").resolve()
        p = (root / unquote(name)).resolve()
        if not p.is_relative_to(root) or not p.is_file():
            return self._json({"error": "not found"}, 404)
        b = p.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(p.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_POST(self):
        # Only accept same-origin JSON requests (blocks drive-by form posts from other sites).
        error = self._origin_error()
        if error:
            return self._json({'error': error}, 403)
        if self.path == '/api/access':
            from .local_access import authorized, cookie_name, redeem_invite
            if not (authorized(self) or redeem_invite(self)):
                return self._json({'error': 'Access expired; reopen Agent Session Review from its launcher.'}, 403)
            return self._json({'ok': True}, cookie=cookie_name(self) + '=' + self.server.access_key
                              + '; Path=/; SameSite=Strict; HttpOnly')
        if self.path == '/api/open-external':   # a signed-in browser asks to open this review in the default browser, signed in by a one-time link
            from .local_access import authorized, mint_invite
            if not (getattr(self.server, 'product', False) and authorized(self)):
                return self._json({'error': 'Reopen Agent Session Review from its launcher to authorize this browser.'}, 403)
            url = f"http://127.0.0.1:{self.server.server_address[1]}/_access#key={mint_invite(self.server)}"
            import webbrowser
            try:
                opened = bool(webbrowser.open(url))
            except Exception:
                opened = False
            return self._json({'opened': True} if opened else {'opened': False, 'url': url})   # the page gets the link only to copy by hand
        if "application/json" not in (self.headers.get("Content-Type") or ""):
            return self._json({"error": "JSON body required"}, 415)
        if not self._pick_session():
            return self._json({"error": "this work package is no longer on this machine; reload the page"}, 404)
        return self._session_request(self._post_selected)

    def _post_selected(self):
        try:
            body = self._body()
            data = self._data()
            if self.path == "/api/session":   # the switcher: page loads after this open the chosen package
                d = session_named((body or {}).get("session"))
                if not d:
                    return self._json({"error": "unknown work package"}, 404)
                return self._json({"ok": True, "session": d.name},
                                  cookie=f"{self._cookie}={Handler.boot}.{d.name}; Path=/; SameSite=Strict; HttpOnly")
            if self.path == "/api/event":
                evs = body if isinstance(body, list) else [body]
                return self._json({"ok": True, "n": append_events(self.sdir, evs, data["session"])})
            if self.path in ("/api/okf", "/api/finish") and not memory_on(self.cfg):
                return self._json({"error": "Memory is off (config memory.enabled)."}, 409)
            if self.path == "/api/okf":
                return self._json(self._okf(body, data))
            if self.path == "/api/publish":
                return self._json(self._publish(body, data))
            if self.path == "/api/refresh":
                return self._json(self._refresh(data))
            if self.path == "/api/sources":   # Settings › Work packages: change the folder, or "" for the default
                path = (body or {}).get("path") if isinstance(body, dict) else None
                if path is not None and not isinstance(path, str):
                    return self._json({"error": "the folder must be a path"}, 400)
                path = (path or "").strip()
                with Handler._refresh_lock:
                    if any((r or {}).get("state") == "running" for r in Handler._refreshing.values()):
                        return self._json({"error": "a refresh is running; change the folder once it finishes"}, 409)
                if path:
                    p = Path(path).expanduser()
                    if not p.is_absolute():
                        return self._json({"error": "use a full path, starting with / or ~"}, 400)
                    if not p.is_dir():
                        return self._json({"error": f"{p} is not a folder on this machine"}, 400)
                set_sessions(path)
                return self._json({"ok": True, **_sources()})
            if self.path == "/api/app-state":   # save app settings: {"set": {key: value or null}}
                from . import appstate
                try:
                    return self._json({"ok": True, "state": appstate.update((body or {}).get("set") if isinstance(body, dict) else None)})
                except ValueError as e:
                    return self._json({"error": str(e)}, 400)
            if self.path == "/api/reveal":   # Settings › Open the data folder: this package's session folder
                b = body if isinstance(body, dict) else {}
                return self._json(self._reveal({"session": b["session"]} if b.get("target") == "session" else b.get("target")))
            if self.path == "/api/session-rename":   # Manage work packages: a name of your own, or "" for the one the review gives it
                d, name = session_named((body or {}).get("session")), (body or {}).get("name")
                if not d or not isinstance(name, str):
                    return self._json({"error": "unknown work package"}, 404)
                name = name.strip()[:80]
                if name:
                    write_json(d / "package.json", {"name": name})
                else:
                    (d / "package.json").unlink(missing_ok=True)
                return self._json({"ok": True, "sessions": list_sessions()})
            if self.path == "/api/session-delete":   # Manage work packages: move a package's folder to the Trash
                return self._json(*self._trash((body or {}).get("session")))
            if self.path == "/api/recipes":   # save a recipe made in the page (Remix)
                from . import recipes as R
                try:
                    # the page picks its ids: a new style gets a free one, editing keeps its own, so this one replaces
                    clean, notes = R.save(body.get("recipe") if isinstance(body, dict) else None, replace=True)
                except ValueError as e:
                    return self._json({"error": str(e)}, 400)
                return self._json({"ok": True, "recipe": clean, "notes": notes})
            if self.path == "/api/recipe-request":   # Describe it, served: Claude Code turns the words into a recipe
                from . import recipes as R
                try:
                    req = R.add_request((body or {}).get("text"), (body or {}).get("base"), data.get("session"))
                except ValueError as e:
                    return self._json({"error": str(e)}, 400)
                return self._json({"ok": True, "request": req, "ask": f"/review-prs make my review style from request {req['id']}"})
            if self.path in ("/api/ask", "/api/ask/cancel") and body is not None and not isinstance(body, dict):
                return self._json({"error": "expected a JSON object"}, 400)
            if self.path == "/api/ask/cancel":   # the panel closed: end the running question so the next can start
                from .ask import cancel
                return self._json({"ok": True, "stopped": cancel((body or {}).get("id"))})
            if self.path == "/api/ask" and int(self.headers.get("Content-Length") or 0) > 2_000_000:
                return self._json({"error": "question too large"}, 413)
            if self.path == "/api/ask":   # Ask Qodo: Claude Code on this machine, read-only tools only
                from .ask import AskError, Busy, ask
                try:
                    return self._json(ask((body or {}).get("prompt"), self.sdir, (self.cfg.get("ask") or {}).get("agent", "auto"), qid=(body or {}).get("id"), qodo=(self.cfg.get("qodo_findings") or {}).get("command")))
                except Busy as e:
                    return self._json({"error": str(e)}, 429)
                except AskError as e:
                    return self._json({"error": str(e)}, 503)
            if self.path == "/api/finish":
                res = distill(self.sdir, self.cfg)
                commit = None
                if self.cfg["memory"].get("auto_commit"):
                    commit = git_commit([mem_path(self.cfg, "amr"), mem_path(self.cfg, "okf")],
                                        f"memory: review session {data['session']}",
                                        tuple(self.cfg["memory"].get("commit_branches", ["main", "master"])))
                return self._json({"ok": True, "result": res, "commit": commit, "memory": self._memory()})
        except BodyError as e:
            return self._json({'error': str(e)}, e.code)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self._json({'error': 'Invalid JSON request body'}, 400)
        except Exception as e:  # surface errors to the UI
            return self._json({"error": str(e)}, 500)
        return self._json({"error": "unknown endpoint"}, 404)

    def _okf(self, body, data):
        okf = OKF(mem_path(self.cfg, "okf"))
        who = self.cfg.get("reviewer") or data.get("reviewer") or data.get("reviewer_login") or "reviewer"
        act = body.get("action")
        if act == "propose":
            c = okf.propose(type_=body.get("type") or "Fact", title=body["title"], body=body.get("body") or body["title"],
                            paths=body.get("paths") or [], by=f"human:{who}",
                            sources=[{"resource": body.get("source") or f"session:{data['session']}"}],
                            description=body.get("description", ""))
            if body.get("confirm"):
                okf.confirm(c.path, who)
            rel, verdict = c.path, "propose"
        elif act in ("confirm", "reject"):
            rel = body["path"]
            if act == "confirm":
                okf.confirm(rel, who, body.get("edits")); verdict = "confirm"
            else:
                verdict = okf.reject(rel, who)
        else:
            raise ValueError("action must be propose, confirm or reject")
        okf.write_index()
        append_events(self.sdir, [{"type": "okf_verdict", "verdict": verdict, "pr": body.get("pr"),
                                   "target": {"kind": "concept", "id": rel}}], data["session"])
        return {"ok": True, "path": rel, "verdict": verdict, "memory": self._memory()}

    def _publish(self, body, data):
        from .product import enabled, NOTICE
        if enabled(data) or getattr(getattr(self, 'server', None), 'product', False):
            return {'ok': False, 'error': NOTICE, 'provider_writes': False}
        pr = next(p for p in data["prs"] if p["key"] == body["pr"])
        demo = data.get("demo")
        live_threads, thread_note = None, None
        if not demo:   # replies go by the thread's state now (deleted, resolved, locked since collection)
            try:
                live_threads = threads.fetch(pr["repo"], pr["number"])
            except (RuntimeError, ValueError, KeyError) as e:
                thread_note = f"Could not read the PR's review threads from GitHub ({str(e).split('failed: ')[-1][:120]}); showing their state from collection."
        payload, ids, replies = build_review(self.sdir, pr["key"], self.cfg["emoji"], live_threads)
        if not ids and not replies:
            return {"ok": False, "error": "No unposted notes marked 'Post to GitHub' for this PR."}
        # what the preview showed; publishing refuses a different set, so nothing posts that wasn't previewed
        expect = sorted([str(i) for i in ids] + [("resolve:" if r.get("resolve_only") else "") + str(r["note_id"]) for r in replies])
        if body.get("dry_run", True) or demo:
            return {"ok": True, "dry_run": True, "payload": payload if ids else None, "replies": replies,
                    "count": len(ids) + len(replies), "note": thread_note, "expect": expect}
        if body.get("expect") is not None and sorted(map(str, body["expect"])) != expect:
            return {"ok": False, "changed": True, "error": "Your notes changed since the preview. Preview again before publishing."}
        results, url = [], None
        live = (self._live().get("prs") or {}).get(pr["key"], {})
        for r in replies:   # each one recorded as it lands, so a retry after a failure never posts it twice
            if not r.get("resolve_only"):
                res = {"note_id": r["note_id"], "kind": "reply", "title": r["title"], "ok": False}
                try:
                    c = threads.reply(pr["repo"], pr["number"], r["comment_id"], r["body"] + f"\n\n<!-- pr-review-cockpit:{self.sdir.name} -->")
                except RuntimeError as e:
                    res["error"] = _gh_error(e, "reply")
                    results.append(res)
                    continue
                res.update(ok=True, url=c.get("html_url"))
                pending = r["resolve"] and not r["resolved"] and r["can_resolve"]
                append_events(self.sdir, [{"type": "published", "pr": pr["key"], "note_ids": [r["note_id"]], "url": c.get("html_url"),
                                           "github_ids": [c["id"]] if c.get("id") else [], "reply_to": r["comment_id"],
                                           **({"resolve_pending": True, "thread_id": r["thread_id"], "title": r["title"]} if pending else {})}],
                                  data["session"])
                if r["resolve"] and r["resolved"]:
                    res["resolve"] = "already resolved"
                elif r["resolve"] and not r["can_resolve"]:
                    res["resolve"] = "not allowed: you can't resolve threads on this repo"
                results.append(res)
                if not pending:
                    continue
            elif r["resolved"]:   # resolved on GitHub since the failure: nothing left to retry
                append_events(self.sdir, [{"type": "thread_resolved", "pr": pr["key"], "note_id": r["note_id"], "thread_id": r["thread_id"]}],
                              data["session"])
                continue
            res = {"note_id": r["note_id"], "kind": "resolve", "title": r["title"], "ok": False}
            try:
                threads.resolve(r["thread_id"])
            except RuntimeError as e:
                res["error"] = _gh_error(e, "resolve") + " The reply is on GitHub; publish again to retry the resolve."
                results.append(res)
                continue
            res["ok"] = True
            results.append(res)
            for o in replies:   # a second note on the same thread doesn't resolve it again
                if o["thread_id"] == r["thread_id"]:
                    o["resolved"] = True
            append_events(self.sdir, [{"type": "thread_resolved", "pr": pr["key"], "note_id": r["note_id"], "thread_id": r["thread_id"]}],
                          data["session"])
        if ids:
            # Inline comments are placed by line in the diff this review read; if the PR moved since, they would land on
            # the wrong lines (or GitHub rejects them with 422). Replies and a body-only review don't, so they still go.
            res = {"kind": "review", "note_ids": ids, "ok": False}
            if live.get("moved") and payload["comments"] and not body.get("force"):
                res["error"] = (f"{pr['key']} has new commits since this review ({(pr.get('head_sha') or '')[:7]} -> "
                                f"{(live.get('head') or '')[:7]}). Run `python3 -m cockpit refresh --session {self.sdir.name}` "
                                "and check your inline notes, then publish.")
                results.append(res)
            else:
                if live.get("moved"):
                    payload.pop("commit_id", None)   # no inline notes: the review goes on the PR's current head
                else:
                    payload["commit_id"] = pr.get("head_sha")
                try:
                    out = gh(["api", f"repos/{pr['repo']}/pulls/{pr['number']}/reviews", "--method", "POST", "--input", "-"],
                             input_text=json.dumps(payload))
                except RuntimeError as e:
                    msg = str(e)
                    res["error"] = ("GitHub rejected the review (422): an inline note is on a line that is not in the PR's current "
                                    "diff, or you have a pending review on this PR in GitHub. Move that note to the review body, "
                                    "refresh, or submit the pending review, then retry.") if ("422" in msg or "Unprocessable" in msg) else msg[:300]
                    results.append(res)
                else:
                    review = json.loads(out)
                    url = review.get("html_url")
                    # Remember what GitHub created, so `refresh` doesn't import these comments back as new notes.
                    github_ids = [review.get("id")]
                    try:
                        github_ids += json.loads(gh(["api", f"repos/{pr['repo']}/pulls/{pr['number']}/reviews/{review.get('id')}/comments",
                                                    "--jq", "[.[].id]"]) or "[]")
                    except (RuntimeError, ValueError):
                        pass
                    append_events(self.sdir, [{"type": "published", "pr": pr["key"], "note_ids": ids, "url": url,
                                               "github_ids": [g for g in github_ids if g]}], data["session"])
                    res.update(ok=True, url=url)
                    results.append(res)
        posted = sum(len(r.get("note_ids") or [1]) for r in results if r["ok"] and r["kind"] != "resolve")
        failed = [r for r in results if not r["ok"]]
        some = any(r["ok"] for r in results)
        error = ({"error": f"{len(failed)} of {len(results)} did not go through; the rest did. Publish again: "
                           "what posted won't post twice."} if some else
                 {"error": "Nothing was posted: " + "; ".join(r.get("error", "") for r in failed)[:400]}) if failed else {}
        return {"ok": not failed, "dry_run": False, "url": url, "count": posted, "results": results, **error}


def _gh_error(e: Exception, what: str) -> str:
    msg = str(e).split("failed: ")[-1]   # gh's message repeats the whole command first
    if "404" in msg or "Not Found" in msg:
        return "the thread is no longer on GitHub (its comment was deleted)."
    if "422" in msg or "Unprocessable" in msg:
        return (f"GitHub refused the {what} (422). If you have a pending review on this PR in GitHub, "
                "submit or discard it, then publish again.")
    if "403" in msg or "Forbidden" in msg or "Resource not accessible" in msg:
        return f"GitHub refused the {what}: no permission on this repo."
    return msg[:300]


def serve(sdir: Path, port: int | None = None, open_browser: bool = True, style: str | None = None):
    from .styles import require
    cfg = session_config(sdir)
    cfg.setdefault("emoji", EMOJI)
    Handler.sdir, Handler.cfg, Handler.boot = sdir, cfg, secrets.token_hex(4)
    Handler.style = require(style or cfg.get("style"))
    port = port or cfg.get("port", 8765)
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    port = httpd.server_address[1]
    from .product import enabled
    httpd.product = enabled()  # explicit launch profile, independent of the selected saved session
    httpd.access_key = secrets.token_urlsafe(32)
    httpd.access_invites, httpd.access_invites_lock = {}, threading.Lock()   # one-time links from Open in external browser (local_access.mint_invite)
    url = f"http://127.0.0.1:{port}/"
    print(f"Agent Session Review: {url}  (session {sdir.name}, style {Handler.style}; Ctrl+C to stop)")
    if Handler.style != "cockpit":
        print(f"  local notes and review: {url}index.html")
    if open_browser:
        import webbrowser
        access_url = url + '_access#key=' + httpd.access_key
        threading.Timer(0.5, lambda: webbrowser.open(access_url)).start()
    elif httpd.product:
        print('  Browser access is closed with --no-open; restart without it to authorize a browser.')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
