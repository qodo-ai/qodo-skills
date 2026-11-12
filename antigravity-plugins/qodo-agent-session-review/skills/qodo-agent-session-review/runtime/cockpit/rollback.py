"""Rollback: the changed files whose effects are hard to take back, and the plan the review writes for undoing the
work package. The files are found here, from paths alone; the plan is the skill's, and enrich checks it covers them."""
from __future__ import annotations

import re

MAX_COVERS = 100

KINDS = (   # (kind, what a reader calls it, path pattern): the first match wins
    ("terraform", "Terraform", r"\.tf(\.json)?$|\.tfvars(\.json)?$|\.terraform\.lock\.hcl$"),
    ("migration", "Database migration", r"(^|/)(migrations?|alembic/versions|db/migrate|schema_migrations)/|\.sql$"),
    ("helm", "Helm chart", r"(^|/)Chart\.ya?ml$|(^|/)(charts?|helm)/.*\.(ya?ml|tpl)$"),
    ("kubernetes", "Kubernetes manifest", r"(^|/)(k8s|kubernetes|manifests?|kustomize)/.*\.ya?ml$|(^|/)kustomization\.ya?ml$"),
    ("chef", "Chef", r"(^|/)(cookbooks|recipes)/.*\.rb$"),
    ("puppet", "Puppet", r"\.pp$"),
    ("ansible", "Ansible", r"(^|/)(playbooks?|roles)/.*\.ya?ml$|(^|/)ansible\.cfg$"),
    ("docker", "Container image", r"(^|/)Dockerfile[^/]*$|(^|/)docker-compose[^/]*\.ya?ml$|\.dockerfile$"),
    ("pipeline", "CI/CD pipeline", r"(^|/)\.github/workflows/.*\.ya?ml$|(^|/)\.gitlab-ci\.ya?ml$|(^|/)Jenkinsfile$|(^|/)\.circleci/|(^|/)azure-pipelines[^/]*\.ya?ml$|(^|/)\.azure-pipelines/|(^|/)bitbucket-pipelines\.ya?ml$|(^|/)\.buildkite/"),
    ("deploy", "Deployment values", r"(^|/)(clusters?|environments?|envs?|overlays|gitops|argocd|argo|flux|deploy(ments?)?)/.*\.ya?ml$|(^|/)[^/]*values[^/]*\.ya?ml$"),
    ("flags", "Feature flags and config", r"(^|/)(feature[_-]?flags?|flags)[^/]*\.(ya?ml|json|toml)$|(^|/)(config|settings)/[^/]*\.(ya?ml|json|toml)$|^(config|settings|appsettings)([._-][\w-]+)?\.(ya?ml|json|toml)$"),   # a root-level config.json too
)
_RX = [(k, label, re.compile(p, re.I)) for k, label, p in KINDS]
PARTS = ("before", "steps", "verify")
MAX_FILES = 60


def sensitive(prs: list[dict], limit: int | None = None) -> list[dict]:
    """Changed files whose effects outlive a revert of the code: infra, migrations, pipelines, flags."""
    out = []
    for p in prs:
        for f in p.get("files") or []:
            path = f.get("path") or ""
            for kind, label, rx in _RX:
                if rx.search(path):
                    out.append({"pr": p.get("key"), "path": path, "kind": kind, "label": label})
                    break
    return out[:limit] if limit else out   # every one is checked; only the page shows at most MAX_FILES


def normalize(raw, pr_keys: set[str]) -> tuple[dict | None, list[str]]:
    """The skill's plan: {before, steps, verify: [{text, prs?, covers?}], one_way: [{what, why}]}."""
    if raw is None:
        return None, []
    if not isinstance(raw, dict):
        return None, ["rollback: an object {before, steps, verify, one_way}"]
    plan, warn = {}, []
    for part in PARTS:
        items = raw.get(part) or []
        if not isinstance(items, list):
            warn.append(f"rollback.{part}: a list of steps"); items = []
        clean = []
        for i, s in enumerate(items):
            s = {"text": s} if isinstance(s, str) else s
            if not isinstance(s, dict) or not isinstance(s.get("text"), str) or not s["text"].strip():   # an instruction someone can follow
                warn.append(f"rollback.{part} {i + 1}: needs text"); continue
            raw_prs, raw_cov = s.get("prs") or [], s.get("covers") or []
            if not isinstance(raw_prs, list) or not isinstance(raw_cov, list):
                warn.append(f"rollback.{part} {i + 1}: prs and covers are lists"); raw_prs = raw_prs if isinstance(raw_prs, list) else []; raw_cov = raw_cov if isinstance(raw_cov, list) else []
            prs = [k for k in raw_prs if isinstance(k, str)]
            bad = [k for k in prs if k not in pr_keys]
            if bad:
                warn.append(f"rollback.{part} {i + 1}: unknown prs {bad}")
            cov = [c for c in raw_cov if isinstance(c, str)]
            if len(cov) > MAX_COVERS:   # said, not silently cut: the cut patterns would show up as uncovered files
                warn.append(f"rollback.{part} {i + 1}: {len(cov)} covers patterns; only the first {MAX_COVERS} count (use a glob like dir/** instead)")
            clean.append({"text": str(s["text"]).strip()[:400], "prs": [k for k in prs if k in pr_keys], "covers": cov[:MAX_COVERS]})
        plan[part] = clean
    if not plan["steps"]:
        warn.append("rollback: needs steps (how to undo the package, in order)")
    elif not plan["verify"]:
        warn.append("rollback: needs verify (how you'd know the rollback worked)")
    raw_one = raw.get("one_way") if raw.get("one_way") is not None else []
    if not isinstance(raw_one, list):
        warn.append("rollback.one_way: a list of {what, why}"); raw_one = []
    warn += [f"rollback.one_way {i}: needs what (the change a revert can't undo); left out" for i, o in enumerate(raw_one, 1)
             if not (isinstance(o, dict) and str(o.get("what") or "").strip())]
    plan["one_way"] = [{"what": str(o.get("what") or "").strip()[:200], "why": str(o.get("why") or "").strip()[:300]}
                       for o in raw_one if isinstance(o, dict) and str(o.get("what") or "").strip()]
    warn += [f"rollback.one_way {i}: needs why (what a revert can't restore)" for i, o in enumerate(plan["one_way"], 1) if not o["why"]]
    return plan, warn


def covers(pat: str, path: str) -> bool:
    """A step's covers entry against a path: `*` stays inside one directory and `**` crosses them, so config/*.yaml
    doesn't cover config/prod/secrets.yaml; a pattern ending in / covers everything below it."""
    pat = pat.strip()
    if pat.endswith("/"):
        pat += "**"
    rx = re.sub(r"\\\*\\\*/?|\\\*|\\\?", lambda m: {"\\*": "[^/]*", "\\?": "[^/]"}.get(m.group(0), "(?:.*/)?" if m.group(0).endswith("/") else ".*"), re.escape(pat))
    return re.fullmatch(rx, path) is not None


def uncovered(plan: dict | None, files: list[dict]) -> list[dict]:
    """Sensitive files no rollback step names (by path or glob in `covers`): preparing or checking isn't undoing."""
    if not plan:
        return list(files)
    pats = [c for s in plan.get("steps") or [] for c in s.get("covers") or []]
    return [f for f in files if not any(covers(c, f["path"]) for c in pats)]


def check(plan: dict | None, files: list[dict], level: str | None) -> list[str]:
    """What enrich says about the plan: missing where it matters, or leaving sensitive files out."""
    if not plan:
        if files:
            return [f"rollback: {len(files)} rollback-sensitive file(s) changed ({', '.join(sorted({f['label'] for f in files}))}) "
                    "and no rollback plan; write one (references/risk.md, Rollback plan)"]
        return ["rollback: Merge Risk is High and there's no rollback plan; write one (references/risk.md, Rollback plan)"] if level == "high" else []
    left = uncovered(plan, files)
    return [f"rollback: the plan doesn't cover {len(left)} rollback-sensitive file(s): " + ", ".join(f["path"] for f in left[:5])
            + (" …" if len(left) > 5 else "") + " (name them, or a glob, in a step's covers)"] if left else []
