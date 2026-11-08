"""Ask Qodo, served: answer a reviewer's question with a local coding agent (config `ask.agent`) that has no
file or network access of its own; it asks, and the cockpit runs only checked reads: the session's files and
Qodo's read catalog."""
from __future__ import annotations

import itertools
import json
import re
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path

AGENTS = ("claude", "codex")
DEADLINE, ROUNDS, CALLS, OUT_CHARS, CALL_TIMEOUT, GREP_SECONDS = 240, 3, 4, 6000, 60, 5
MAX_PROMPT = 600_000   # characters: a large review's index fits; anything bigger isn't a question
_ONE = threading.Lock()   # one question at a time: each holds an agent process for up to DEADLINE seconds
_NOW = {"proc": None, "cancelled": False, "id": None}   # the running question and its agent, so closing its panel can end it
# Claude Code with no built-in tools and no MCP servers; Codex with no shell, apps, browser or computer use
CLAUDE_FLAGS = ["--tools", "", "--strict-mcp-config", "--output-format", "json"]
CODEX_OFF = ["shell_tool", "apps", "browser_use", "browser_use_external", "computer_use", "in_app_browser"]
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["answer", "cites", "covered", "code", "calls"],
          "properties": {"answer": {"type": "string"},
                         "calls": {"type": "array", "maxItems": CALLS, "items": {"type": "object", "additionalProperties": False,
                                   "required": ["tool", "args"], "properties": {"tool": {"type": "string"}, "args": {"type": "string"}}}},
                         "cites": {"type": "array", "items": {"type": "string"}, "maxItems": 4},
                         "covered": {"type": "boolean"},
                         "code": {"type": "array", "maxItems": 3, "items": {"type": "object", "additionalProperties": False,
                                  "required": ["path", "why"], "properties": {"path": {"type": "string"}, "why": {"type": "string"}}}}}}
SESSION_TOOLS = {   # the session's own files, read by the cockpit for the agent; nothing outside the session folder
    "session ls": {"description": "List the review session's files", "params": [], "required": []},
    "session read": {"description": "Read a session file (review-data.json holds every PR's diff, findings and story)",
                     "params": ["path", "start", "lines"], "required": ["path"]},
    "session grep": {"description": "Search the session's files for a regular expression; matching lines with file and line number",
                     "params": ["pattern", "path"], "required": ["pattern"]}}


class AskError(Exception):
    pass


class Busy(AskError):
    pass


def cancel(qid) -> bool:
    """End the question with this id, if it is the one being answered: its agent stops and the next can start.
    Another page's question is left alone."""
    if not qid or qid != _NOW["id"]:
        return False
    _NOW["cancelled"] = True
    p = _NOW["proc"]
    if p and p.poll() is None:
        p.terminate()
        return True
    return False


def pick(want: str = "auto") -> str:
    """The agent to ask: the configured one if it's installed, else the first installed."""
    if want not in ("auto", *AGENTS):
        raise AskError(f"ask.agent is {want!r}: use auto, claude or codex")
    if want in AGENTS:
        if not shutil.which(want):
            raise AskError(f"{'Claude Code' if want == 'claude' else 'Codex'} isn't installed on this machine")
        return want
    for a in AGENTS:
        if shutil.which(a):
            return a
    raise AskError("no coding agent here: install Claude Code or Codex to ask with the code")


_CATALOG: dict | None = None
_MISSED: list = [None]   # when the catalog last came back empty; tried again after RETRY_SECONDS
RETRY_SECONDS = 60
_QODO = {"cmd": "qodo"}   # the configured command (qodo_findings.command), as the findings adapter uses it


def qodo_bin() -> str | None:
    return shutil.which(_QODO["cmd"]) or (_QODO["cmd"] if Path(_QODO["cmd"]).is_file() else None)


def catalog() -> dict:
    """Qodo's read catalog, "group leaf" -> {description, params, required}; only tools it marks non-mutating."""
    global _CATALOG
    if _CATALOG is not None:
        return _CATALOG
    if _MISSED[0] is not None and time.monotonic() - _MISSED[0] < RETRY_SECONDS:
        return {}
    from .product import enabled
    product = enabled()
    from .adapters.managed import Client, decode_result, ReadError
    qodo, cat = (Client().command if product else qodo_bin()), {}
    if qodo:
        try:
            r = subprocess.run([qodo, "read", "tools", "--json"], capture_output=True, text=True, timeout=CALL_TIMEOUT)
            if product:
                doc = decode_result(r, 'read', 'tools')
            else:
                doc, _ = json.JSONDecoder().raw_decode(r.stdout.strip())   # older CLI may append a trace line
            tools = doc.get("tools") if isinstance(doc, dict) else None
            for t in tools if isinstance(tools, list) else []:
                if not isinstance(t, dict) or t.get("access") != "read" or t.get("mutating") or not (t.get("group") and t.get("leaf")):
                    continue
                ps = t.get("parameters") if isinstance(t.get("parameters"), dict) else {}
                props, req = ps.get("properties"), ps.get("required")
                cat[f"{t['group']} {t['leaf']}"] = {"description": str(t.get("description") or ""),
                                                   "params": sorted(props) if isinstance(props, dict) else [],
                                                   "required": [x for x in req if isinstance(x, str)] if isinstance(req, list) else []}
        except PermissionError:
            if product:
                raise
            cat = {}
        except ReadError:
            cat = {}
        except (OSError, subprocess.TimeoutExpired, ValueError, TypeError, AttributeError):
            cat = {}
    if cat:   # an empty answer may be an outage: try again a minute later instead of keeping it
        _CATALOG = cat
    else:
        _MISSED[0] = time.monotonic()
    return cat


def _cut(out: str) -> str:
    return out if len(out) <= OUT_CHARS else out[:OUT_CHARS] + f"\n… cut at {OUT_CHARS} characters; narrow the query for more"


def _inside(sdir: Path, rel) -> Path | None:
    """A session file, only if the path resolves inside the session folder."""
    if not isinstance(rel, str) or not rel.strip():
        return None
    root = sdir.resolve()
    p = root / rel
    return p.resolve() if not p.is_symlink() and p.resolve().is_file() and p.resolve().is_relative_to(root) else None


def _files(sdir: Path) -> list[Path]:
    """The session's own files: regular files that resolve inside it, never through a symlink."""
    root = sdir.resolve()
    return [p for p in sorted(root.rglob("*")) if not p.is_symlink() and p.is_file() and p.resolve().is_relative_to(root)]


def _session(tool: str, args: dict, sdir: Path) -> str:
    root = sdir.resolve()
    if tool == "session ls":
        return "\n".join(str(p.relative_to(root)) for p in _files(sdir))[:OUT_CHARS]
    if tool == "session read":
        p = _inside(sdir, args.get("path"))
        if not p:
            return "refused: path must name a file inside the review session"
        start, n = max(int(args.get("start") or 1), 1), min(int(args.get("lines") or 200), 400)
        with p.open(errors="replace") as fh:   # line by line: a big file is never loaded whole
            rows = [f"{i}: {l.rstrip()[:2000]}" for i, l in enumerate(itertools.islice(fh, start - 1, start - 1 + n), start)]
        return _cut("\n".join(rows))
    pattern = str(args.get("pattern"))
    if len(pattern) > 200:
        return "refused: keep the pattern under 200 characters"
    try:
        rx = re.compile(pattern)
    except re.error as e:
        return f"refused: bad pattern ({e})"
    stop = time.monotonic() + GREP_SECONDS   # a slow pattern ends the search early instead of holding the question
    if args.get("path") and not _inside(sdir, args["path"]):
        return "refused: path must name a file inside the review session"
    files = [_inside(sdir, args["path"])] if args.get("path") else _files(sdir)
    hits = []
    for p in filter(None, files):
        with p.open(errors="replace") as fh:
            for i, l in enumerate(fh, 1):
                if time.monotonic() > stop:
                    hits.append(f"… stopped after {GREP_SECONDS} s; narrow the pattern or the path")
                    return _cut("\n".join(hits))
                if rx.search(l[:2000]):
                    hits.append(f"{p.relative_to(root)}:{i}: {l.rstrip()[:300]}")
                    if len(hits) >= 200:
                        break
    return _cut("\n".join(hits) or "no matches")


def _product_session(sdir):
    from .product import enabled
    if enabled():
        return True
    if not sdir or not (sdir / 'review-data.json').is_file():
        return False
    try:
        data = json.loads((sdir / 'review-data.json').read_text())
    except ValueError:
        return False  # standalone session tools may intentionally read non-JSON text
    return isinstance(data, dict) and enabled(data)


def run_read(call: dict, cat: dict, sdir: Path | None = None, timeout: float = CALL_TIMEOUT) -> str:
    """One of the agent's calls, only if it names a known read tool with known, plain arguments."""
    tool = str(call.get("tool") or "").strip()
    tools = {**cat, **(SESSION_TOOLS if sdir else {})}
    if tool not in tools:
        return f"refused: {tool!r} isn't a session tool or in Qodo's read catalog"
    raw = call.get("args")
    try:
        args = raw if isinstance(raw, dict) else json.loads(raw or "{}")
    except (ValueError, TypeError):
        return "refused: args must be a JSON object"
    if not isinstance(args, dict) or any(k not in tools[tool]["params"] for k in args) or \
            any(not isinstance(v, (str, int, float, bool)) for v in args.values()):
        return f"refused: args must be an object of {', '.join(tools[tool]['params']) or 'nothing'} with plain values"
    missing = [k for k in tools[tool]["required"] if k not in args]
    if missing:
        return f"refused: missing {', '.join(missing)}"
    if tool in SESSION_TOOLS:
        try:
            return _session(tool, args, sdir)
        except (OSError, ValueError) as e:
            return f"failed: {e}"
    group, leaf, qodo = *tool.split(" ", 1), qodo_bin()
    from .product import enabled
    product = _product_session(sdir)
    if product:
        from .adapters.managed import Client, ReadBudget, ReadError
        try:
            result = Client(budget=ReadBudget(seconds=max(0, timeout))).read(group, leaf, **args)
        except ReadError as error:
            return f'failed: {error}'
        return _cut(json.dumps(result))
    if not qodo:   # the catalog is cached, but the CLI can go away since
        return "failed: Qodo's CLI isn't available now"
    try:
        r = subprocess.run([qodo, "read", group, leaf, "--args", json.dumps(args), "--json"],
                           capture_output=True, text=True, timeout=max(1, timeout))
    except (OSError, subprocess.TimeoutExpired) as e:
        return f"failed: {e}"
    return _cut((r.stdout if r.returncode == 0 else f"failed ({r.returncode}): {r.stderr or r.stdout}").strip())


def _tools_text(cat: dict) -> str:
    tools = {**SESSION_TOOLS, **cat}
    lines = [f"- {k}: {v['description'][:140]} (args: {', '.join((p + '*') if p in v['required'] else p for p in v['params']) or 'none'})" for k, v in tools.items()]
    return ("TOOLS: you have no file, shell or network access. To look further, return \"calls\": up to "
            f"{CALLS} items of {{\"tool\": \"<name>\", \"args\": \"<JSON object as a string>\"}} with an empty answer; the "
            "cockpit runs them and you answer in the next round. Session tools read this review's own files; the others "
            "are Qodo's read-only tools for the code, other repos and pull requests. Use them only when the index can't "
            "answer. * marks a required argument. If you use something outside the index, list it in \"code\" "
            "[{\"path\": \"repo/path\", \"why\": \"one line\"}], at most 3; otherwise \"code\": []. Reply with JSON only, "
            f"in this shape: {json.dumps(SCHEMA)}\n" + "\n".join(lines))


def _run(argv: list[str], text: str, cwd: Path, timeout: float) -> subprocess.CompletedProcess:
    if timeout <= 1:
        raise AskError(f"no answer within {DEADLINE} s")
    if _NOW["cancelled"]:
        raise AskError("cancelled")
    try:
        p = _NOW["proc"] = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(cwd), text=True)
        out, err = p.communicate(text, timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill(); p.communicate()
        raise AskError(f"no answer within {DEADLINE} s")
    except OSError as e:
        raise AskError(str(e))
    finally:
        _NOW["proc"] = None
    if _NOW["cancelled"]:
        raise AskError("cancelled")
    r = subprocess.CompletedProcess(argv, p.returncode, out, err)
    if r.returncode:
        raise AskError((r.stderr or r.stdout).strip()[-300:] or "the agent failed")
    return r


def _turn(who: str, text: str, cwd: Path, timeout: float) -> str:
    """One round with the agent; its reply text (the JSON it was asked for)."""
    if who == "claude":
        try:
            out = json.loads(_run([shutil.which("claude"), "-p", *CLAUDE_FLAGS], text, cwd, timeout).stdout)
        except ValueError:
            raise AskError("Claude Code's reply wasn't JSON")
        if not isinstance(out, dict):
            raise AskError("Claude Code's reply wasn't the JSON object it sends")
        if out.get("is_error"):
            raise AskError(str(out.get("result") or "Claude Code reported an error")[:300])
        res = out.get("result", "")
        return res if isinstance(res, str) else json.dumps(res)
    with tempfile.TemporaryDirectory() as t:
        schema, last = Path(t) / "schema.json", Path(t) / "answer.txt"
        schema.write_text(json.dumps(SCHEMA))
        argv = [shutil.which("codex"), "exec", "--sandbox", "read-only", "--skip-git-repo-check", "--ephemeral", "--color", "never",
                "--ignore-user-config", *[x for f in CODEX_OFF for x in ("--disable", f)], "-C", str(cwd),
                "--output-schema", str(schema), "-o", str(last), "-"]
        _run(argv, text, cwd, timeout)
        return last.read_text() if last.exists() else ""


def _calls(reply: str) -> list:
    m = re.search(r"\{[\s\S]*\}", reply or "")
    try:
        calls = json.loads(m.group(0)).get("calls") if m else []
    except (ValueError, AttributeError):
        return []
    return [c for c in calls if isinstance(c, dict)][:CALLS] if isinstance(calls, list) else []


def _has_answer(reply: str) -> bool:
    m = re.search(r"\{[\s\S]*\}", reply or "")
    try:
        v = json.loads(m.group(0)) if m else {}
    except ValueError:
        return False
    return isinstance(v, dict) and isinstance(v.get("answer"), str) and bool(v["answer"].strip())


def ask(prompt: str, sdir: Path, agent: str = "auto", deadline: float = DEADLINE, qid: str | None = None, qodo: str | None = None) -> dict:
    if not isinstance(prompt, str) or not prompt.strip():
        raise AskError("no question")
    if len(prompt) > MAX_PROMPT:
        raise AskError(f"the question and its report index are over {MAX_PROMPT // 1000} k characters")
    from .product import enabled, activate
    if _product_session(sdir):
        activate()
    who = pick(agent)
    global _CATALOG
    if qodo and qodo != _QODO["cmd"]:
        _QODO["cmd"], _CATALOG = qodo, None
    if not _ONE.acquire(blocking=False):
        raise Busy("another question is still being answered; try again in a moment")
    _NOW.update(cancelled=False, id=qid)
    try:
        end, used, cat = time.monotonic() + deadline, [], catalog()
        with tempfile.TemporaryDirectory() as empty:   # the agent works from an empty folder: nothing to read there
            transcript = f"{prompt}\n\n{_tools_text(cat)}"
            for n in range(1, ROUNDS + 1):
                reply = _turn(who, transcript, Path(empty), end - time.monotonic())
                calls = _calls(reply)
                if calls and n == ROUNDS and not _has_answer(reply):   # still asking to read when the rounds ran out
                    raise AskError(f"the agent wanted more reads than {ROUNDS} rounds allow; ask a narrower question")
                if not calls or n == ROUNDS:
                    return {"answer": reply, "how": "local", "agent": who, "qodo": used}
                results = []
                for c in calls:
                    if _NOW["cancelled"]:
                        raise AskError("cancelled")
                    got = run_read(c, cat, sdir, min(CALL_TIMEOUT, end - time.monotonic()))
                    results.append(f"### {c.get('tool')} {c.get('args')}\n{got}")
                    if not got.startswith(("refused", "failed")):   # a refused or failed read isn't something it looked at
                        used.append(str(c.get("tool")))
                transcript += f"\n\nROUND {n} RESULTS (from the calls you asked for):\n" + "\n\n".join(results) + \
                    ("\n\nThis is the last round: answer now, with calls: []." if n + 1 == ROUNDS else "")
        return {"answer": "", "how": "local", "agent": who, "qodo": used}
    finally:
        _NOW["id"] = None
        _ONE.release()
