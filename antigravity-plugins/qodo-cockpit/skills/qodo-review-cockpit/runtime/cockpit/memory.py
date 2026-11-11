"""Read/write both memories.

AMR (Agent Memory Repo): one-line bullets with `[key: value; ...]` metadata,
`MEMORY.md` entry point, `[[path]]` links.

OKF v0.2: one concept per .md file with YAML frontmatter (`type` required),
reserved `index.md` / `log.md`.
"""
from __future__ import annotations
from .memory_write import memory_write

import re
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .util import dump_frontmatter, glob_match, now_iso, parse_frontmatter, slug, today, write_text as atomic_text


def write_text(path, text):
    """Keep existing memory links/modes and ordinary creation permissions."""
    atomic_text(Path(path).resolve(), text, preserve_mode=True)

# ============================== AMR ==============================

BULLET = re.compile(r"^- (?P<text>.*?)(?:\s+\[(?P<meta>[^\[\]]*)\])?\s*$")

PREF_FILES = {
    "findings": "preferences/findings.md",
    "layout": "preferences/layout.md",
    "comments": "preferences/comments.md",
    "story": "preferences/story.md",
    "general": "preferences/general.md",
}


@dataclass
class Bullet:
    text: str
    meta: dict = field(default_factory=dict)
    file: str = ""

    @property
    def rule(self) -> str | None:
        return self.meta.get("rule")

    @property
    def evidence(self) -> int:
        try:
            return int(self.meta.get("evidence", 1))
        except ValueError:
            return 1

    def render(self) -> str:
        if not self.meta:
            return f"- {self.text}"
        meta = "; ".join(f"{k}: {v}" for k, v in self.meta.items() if v not in (None, ""))
        return f"- {self.text} [{meta}]"


def parse_bullet(line: str, file: str = "") -> Bullet | None:
    m = BULLET.match(line.rstrip())
    if not m:
        return None
    meta = {}
    if m.group("meta"):
        for part in m.group("meta").split(";"):
            k, sep, v = part.partition(":")
            if sep:
                meta[k.strip()] = v.strip()
    return Bullet(m.group("text").strip(), meta, file)


class AMR:
    def __init__(self, root: Path):
        self.root = root

    def ensure(self, reviewer: str):
        self.root.mkdir(parents=True, exist_ok=True)
        mem = self.root / "MEMORY.md"
        if not mem.exists():
            idx = "\n".join(f"- [[{p[:-3]}]]" for p in PREF_FILES.values())
            write_text(mem,
                f"# Memory: {reviewer} (PR review)\n"
                f"- Preferences are learned from review sessions in the cockpit [added: {today()}]\n"
                f"- Bullets with a `rule:` key are applied by the app once `evidence` reaches the threshold\n\n"
                f"## Index\n{idx}\n- [[reviews]]\n"
            )
        else:   # link preference files added after this memory was created
            text = mem.read_text()
            missing = [f"- [[{p[:-3]}]]" for p in PREF_FILES.values() if f"[[{p[:-3]}]]" not in text]
            if missing and "## Index" in text:
                write_text(mem, text.replace("## Index\n", "## Index\n" + "\n".join(missing) + "\n", 1))
        for name, rel in PREF_FILES.items():
            p = self.root / rel
            if not p.exists():
                p.parent.mkdir(parents=True, exist_ok=True)
                write_text(p, f"# {name.title()} preferences\n")
        (self.root / "reviews").mkdir(exist_ok=True)

    def bullets(self) -> list[Bullet]:
        out = []
        for p in sorted(self.root.rglob("*.md")):
            rel = p.relative_to(self.root).as_posix()
            for line in p.read_text().splitlines():
                if line.startswith("- "):
                    b = parse_bullet(line, rel)
                    if b:
                        out.append(b)
        return out

    def active_rules(self, threshold: int) -> list[dict]:
        rules = []
        for b in self.bullets():
            if b.rule and b.evidence >= threshold:
                rules.append({"rule": b.rule, "text": b.text, "file": b.file, "evidence": b.evidence,
                              **parse_rule(b.rule)})
        return rules

    def upsert(self, bullet: Bullet, key: str | None = None) -> str:
        """Add a bullet, or bump evidence on an existing one with the same rule (or text)."""
        path = self.root / bullet.file
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = path.read_text().splitlines() if path.exists() else [f"# {Path(bullet.file).stem}"]
        match_key = key or bullet.rule or bullet.text.lower()
        for i, line in enumerate(lines):
            b = parse_bullet(line, bullet.file) if line.startswith("- ") else None
            if not b:
                continue
            existing = b.rule or b.text.lower()
            if existing == match_key:
                b.meta["evidence"] = str(b.evidence + int(bullet.meta.get("evidence", 1)))
                b.meta["seen"] = today()
                if bullet.meta.get("source"):
                    b.meta["source"] = bullet.meta["source"]
                lines[i] = b.render()
                write_text(path, "\n".join(lines) + "\n")
                return "updated"
        lines.append(bullet.render())
        write_text(path, "\n".join(lines) + "\n")
        return "added"


RULE_RE = re.compile(r"(\w+)=([^\s]+)")


def parse_rule(rule: str) -> dict:
    """`collapse category=naming path=tests/**` -> {action, category, path}"""
    parts = rule.split(None, 1)
    out = {"action": parts[0]}
    if len(parts) > 1:
        out.update(dict(RULE_RE.findall(parts[1])))
    return out


# ============================== OKF ==============================

RESERVED = {"index.md", "log.md"}


@dataclass
class Concept:
    path: str          # bundle-relative, e.g. "invariants/prices-in-cents.md"
    meta: dict
    body: str

    def as_dict(self, now: str | None = None) -> dict:
        now = now or now_iso()
        stale_after = self.meta.get("stale_after")
        if hasattr(stale_after, "isoformat"):
            stale_after = stale_after.isoformat().replace("+00:00", "Z")
        verified = self.meta.get("verified")
        if isinstance(verified, dict):
            verified = [verified]
        tier = "unverified"
        if verified:
            tier = "human-reviewed" if any(str(v.get("by", "")).startswith("human:") for v in verified) else "machine-confirmed"
        return {
            "path": self.path, "type": self.meta.get("type"), "title": self.meta.get("title") or self.path,
            "description": self.meta.get("description", ""), "status": self.meta.get("status", "stable"),
            "tier": tier, "paths": self.meta.get("paths", []) or [], "tags": self.meta.get("tags", []) or [],
            "stale": bool(stale_after and str(stale_after) <= now), "body": self.body.strip(),
            "sources": self.meta.get("sources", []) or [],
        }


class OKF:
    def __init__(self, root: Path):
        self.root = root

    @memory_write
    def ensure(self):
        self.root.mkdir(parents=True, exist_ok=True)
        if not (self.root / "index.md").exists():
            self.write_index()
        if not (self.root / "log.md").exists():
            write_text(self.root / "log.md", "# Log\n")

    def concepts(self) -> list[Concept]:
        out = []
        for p in sorted(self.root.rglob("*.md")):
            if p.name in RESERVED:
                continue
            meta, body = parse_frontmatter(p.read_text())
            out.append(Concept(p.relative_to(self.root).as_posix(), meta or {}, body))
        return out

    def get(self, rel: str) -> Concept | None:
        p = self._safe(rel)
        if not p.exists():
            return None
        meta, body = parse_frontmatter(p.read_text())
        return Concept(rel, meta or {}, body)

    def _safe(self, rel: str) -> Path:
        p = (self.root / rel).resolve()
        if self.root.resolve() not in p.parents:
            raise ValueError(f"path escapes bundle: {rel}")
        return p

    @memory_write
    def write(self, c: Concept):
        p = self._safe(c.path)
        p.parent.mkdir(parents=True, exist_ok=True)
        write_text(p, dump_frontmatter(c.meta) + "\n" + c.body.strip() + "\n")

    @memory_write
    def propose(self, *, type_: str, title: str, body: str, paths: list[str], by: str,
                sources: list[dict], description: str = "", folder: str | None = None,
                tags: list[str] | None = None) -> Concept:
        # RiskArea -> risk-areas; a glossary is already a collection, so its folder stays singular
        name = slug(re.sub(r"(?<=[a-z])(?=[A-Z])", " ", type_))
        folder = folder or (name if name == "glossary" else name + "s")
        rel = f"{folder}/{slug(title)}.md"
        n = 2
        while (self.root / rel).exists():
            rel = f"{folder}/{slug(title)}-{n}.md"; n += 1
        meta = {"type": type_, "title": title, "description": description or body.split("\n")[0][:160],
                "tags": tags or None, "paths": paths or None, "sources": sources,
                "generated": {"by": by, "at": now_iso()}, "status": "draft"}
        c = Concept(rel, meta, body)
        self.write(c)
        self.log("Creation", rel, title, "draft")
        return c

    @memory_write
    def confirm(self, rel: str, reviewer: str, edits: dict | None = None) -> Concept:
        c = self.get(rel)
        if not c:
            raise FileNotFoundError(rel)
        if edits:
            for k in ("title", "description", "type"):
                if edits.get(k):
                    c.meta[k] = edits[k]
            if edits.get("body"):
                c.body = edits["body"]
            if "paths" in edits:
                c.meta["paths"] = edits["paths"]
        v = c.meta.get("verified") or []
        if isinstance(v, dict):
            v = [v]
        v.append({"by": f"human:{reviewer}", "at": now_iso()})
        c.meta["verified"] = v
        c.meta["status"] = "stable"
        self.write(c)
        self.log("Update", rel, c.meta.get("title", rel), f"verified by human:{reviewer}")
        return c

    @memory_write
    def reject(self, rel: str, reviewer: str) -> str:
        c = self.get(rel)
        if not c:
            raise FileNotFoundError(rel)
        if c.meta.get("status") == "draft" and not c.meta.get("verified"):
            self._safe(rel).unlink()
            self.log("Deletion", rel, c.meta.get("title", rel), f"rejected by human:{reviewer}")
            return "deleted"
        c.meta["status"] = "deprecated"
        self.write(c)
        self.log("Deprecation", rel, c.meta.get("title", rel), f"by human:{reviewer}")
        return "deprecated"

    def match(self, changed_paths: list[str]) -> list[Concept]:
        hits = []
        for c in self.concepts():
            globs = c.meta.get("paths") or []
            if isinstance(globs, str):
                globs = [globs]
            if c.meta.get("status") == "deprecated":
                continue
            if any(glob_match(p, g) for g in globs for p in changed_paths):
                hits.append(c)
        return hits

    @memory_write
    def log(self, verb: str, rel: str, title: str, note: str = ""):
        p = self.root / "log.md"
        text = p.read_text() if p.exists() else "# Log\n"
        head = f"## {today()}"
        entry = f"- **{verb}** [{title}](/{rel})" + (f": {note}" if note else "")
        lines = text.splitlines()
        if head in lines:
            i = lines.index(head)
            lines.insert(i + 1, entry)
        else:
            # newest first: insert right after the title line
            lines[1:1] = ["", head, entry]
        write_text(p, "\n".join(lines).rstrip() + "\n")

    @memory_write
    def write_index(self):
        groups: dict[str, list[Concept]] = {}
        for c in self.concepts():
            groups.setdefault(c.meta.get("type", "Other"), []).append(c)
        out = [dump_frontmatter({"okf_version": "0.2"}).rstrip(), "# Review knowledge", "",
               "Facts about the code learned while reviewing PRs. Drafts are unconfirmed.", ""]
        for t in sorted(groups):
            out.append(f"## {t}")
            for c in sorted(groups[t], key=lambda c: c.path):
                st = c.meta.get("status", "stable")
                flag = "" if st == "stable" else f" _({st})_"
                out.append(f"- [{c.meta.get('title', c.path)}]({c.path}){flag}: {c.meta.get('description', '')}")
            out.append("")
        write_text(self.root / "index.md", "\n".join(out).rstrip() + "\n")

    def validate(self) -> list[str]:
        problems = []
        for p in sorted(self.root.rglob("*.md")):
            rel = p.relative_to(self.root).as_posix()
            if p.name in RESERVED:
                continue
            meta, _ = parse_frontmatter(p.read_text())
            if meta is None:
                problems.append(f"{rel}: missing or unparseable frontmatter")
            elif not meta.get("type"):
                problems.append(f"{rel}: frontmatter has no non-empty `type`")
        return problems


def _toplevel(d: Path) -> Path | None:
    r = subprocess.run(["git", "-C", str(d), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return Path(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() else None


def _memory_repos(paths: list[Path]) -> dict[Path, list[Path]]:
    """Each memory folder with the git repo that holds it: the one it already sits in (the cockpit checkout, or a
    team repo), else a new one at the memory's own root (the folder both kinds share, such as <home>/memory), so
    commits never land in the code's repo by accident and never in a broad folder like $HOME."""
    out: dict[Path, list[Path]] = {}
    loose = []
    for p in paths:   # folders that exist: the repo they are in
        d = p if p.is_dir() else p.parent if p.exists() else None
        top = _toplevel(d) if d else None
        (out.setdefault(top, []).append(p) if top else loose.append(p))
    for p in list(loose):   # a kind not written yet goes with a repo that already holds its folder's place
        top = next((r for r in out if p.resolve().is_relative_to(r.resolve())), None) if out else None
        if top:
            out[top].append(p); loose.remove(p)
    if loose:
        parents = {p.parent for p in loose}
        # the shared parent becomes the repo only when it holds nothing but memory (such as <home>/memory), so a
        # folder like $HOME or /tmp is never turned into a repo; otherwise each memory folder gets its own
        shared = parents.pop() if len(parents) == 1 else None
        own = shared is not None and shared.is_dir() and all(x in loose or x.name == ".git" for x in shared.iterdir())
        roots = [(shared, loose)] if own else [(p, [p]) for p in loose if p.exists()]
        for root, ps in roots:
            if not any(p.exists() for p in ps):
                continue
            root.mkdir(parents=True, exist_ok=True)
            if subprocess.run(["git", "init", "-q", "-b", "main", str(root)], capture_output=True).returncode == 0:
                out.setdefault(root, []).extend(ps)
    return out


def git_commit(paths: list[Path], message: str, branches: tuple[str, ...] = ("main", "master")) -> str:
    """Commit memory only on a memory branch (main by default), so a feature branch never picks up
    review memory by accident. Elsewhere the files are written but left uncommitted. Memory kinds in
    different repos are committed in each."""
    try:
        repos = _memory_repos(paths)
        if not repos:
            return "git commit skipped: no repo for the memory"
        said = []
        for repo, ps in repos.items():
            cur = subprocess.run(["git", "-C", str(repo), "symbolic-ref", "--short", "-q", "HEAD"],   # names an unborn branch too
                                 capture_output=True, text=True).stdout.strip() or "(detached)"
            if branches and cur not in branches:
                said.append(f"not committed: on branch {cur}; memory commits only on {', '.join(branches)}")
                continue
            present = [str(p) for p in ps if p.exists()]   # a memory kind not written yet has no folder
            if not present:
                said.append("nothing to commit")
                continue
            subprocess.run(["git", "-C", str(repo), "add", *present], check=True, capture_output=True)
            p = subprocess.run(["git", "-C", str(repo), "commit", "-m", message], capture_output=True, text=True)
            said.append(p.stdout.strip().splitlines()[0] if p.returncode == 0 and p.stdout.strip() else "nothing to commit")
        return "; ".join(dict.fromkeys(said))
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        return f"git commit skipped: {e}"
