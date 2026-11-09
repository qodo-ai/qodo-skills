import json
import shutil
import tempfile
import unittest
from pathlib import Path

from cockpit import collect as C
from cockpit.adapters import qodo_cli

# Tests never reach a real `qodo` CLI or the network: the CLI source answers "unavailable" unless a test says otherwise.
qodo_cli._real_fetch, qodo_cli.fetch = qodo_cli.fetch, lambda pr, cfg: None
from cockpit import threads
threads._real_fetch, threads.fetch = threads.fetch, lambda repo, number: {}   # ...nor GitHub's review threads
C.other_work = lambda prs, cfg, session=None: ([], [])   # ...nor other PRs' diffs (tests/test_overlaps.py covers it)
from cockpit.adapters import qodo_local
qodo_local.STORE = Path(tempfile.mkdtemp()) / "local-findings"   # ...nor the local reviews kept in your data home
from cockpit.adapters import qodo_comments as Q
from cockpit.distill import distill, path_glob
from cockpit.dream import dream
from cockpit.memory import AMR, OKF, Bullet, parse_bullet, parse_rule
from cockpit.server import build_review
from cockpit.util import EMOJI, ROOT, gh_json, dump_frontmatter, glob_match, load_config, parse_frontmatter


def no_home_env():
    """A data home set in the environment wins over everything; tests of the other ways need it unset."""
    import os
    from unittest import mock
    return mock.patch.dict(os.environ, {k: v for k, v in os.environ.items() if k not in ("REVIEW_COCKPIT_HOME", "PR_COCKPIT_HOME")}, clear=True)



def popen_from(fake):
    """A Popen that answers through the same fake as subprocess.run, for code that runs agents cancellably."""
    class FakePopen:
        def __init__(self, argv, **kw):
            self.argv, self.kw, self.returncode = argv, kw, None
        def communicate(self, inp=None, timeout=None):
            r = fake(self.argv, input=inp, cwd=self.kw.get("cwd"))
            self.returncode = r.returncode
            return r.stdout, r.stderr
        def poll(self):
            return self.returncode
        def terminate(self):
            self.returncode = -15
        kill = terminate
    return FakePopen

class FormatTests(unittest.TestCase):
    def test_amr_bullet_roundtrip(self):
        b = parse_bullet("- Dismisses naming [source: session:x; added: 2026-10-05; rule: collapse category=naming path=**/test*/**; evidence: 4]")
        self.assertEqual(b.text, "Dismisses naming")
        self.assertEqual(b.evidence, 4)
        self.assertEqual(parse_rule(b.rule), {"action": "collapse", "category": "naming", "path": "**/test*/**"})
        self.assertEqual(parse_bullet(b.render()).meta, b.meta)

    def test_frontmatter_roundtrip(self):
        meta = {"type": "Invariant", "title": "A: b", "paths": ["src/**"], "generated": {"by": "x", "at": "2026-01-01T00:00:00Z"},
                "okf_version": "0.2", "status": "draft"}
        got, body = parse_frontmatter(dump_frontmatter(meta) + "\nbody")
        self.assertEqual(got, meta)
        self.assertEqual(body.strip(), "body")

    def test_frontmatter_quotes_yaml_indicators(self):
        for v in ["`Code` first", "*bold", "- dash", "yes", "it's", 'say "hi"', "&anchor", "%x"]:
            got, _ = parse_frontmatter(dump_frontmatter({"type": "Fact", "description": v}))
            self.assertEqual(got["description"], v)

    def test_memory_commits_only_on_memory_branches(self):
        from unittest import mock
        from cockpit import memory as M
        ran = []
        def fake(args, **kw):
            ran.append(args)
            return mock.Mock(stdout="feature-x\n", returncode=0)
        mem = Path(tempfile.mkdtemp()) / "memory" / "amr"   # a memory folder of its own, not this checkout's
        mem.mkdir(parents=True)
        with mock.patch.object(M.subprocess, "run", side_effect=fake):
            out = M.git_commit([mem], "m")
        self.assertIn("not committed: on branch feature-x", out)
        self.assertFalse(any("commit" in a or "add" in a for a in ran))   # looked up the repo and branch, wrote nothing

    def test_memory_gets_its_own_repo_outside_any(self):
        import os, subprocess, tempfile
        from unittest import mock
        from cockpit import memory as M
        fixture = tempfile.TemporaryDirectory()
        self.addCleanup(fixture.cleanup)
        tmp = Path(fixture.name)
        amr = tmp / "home" / "memory" / "amr"; amr.mkdir(parents=True); (amr / "MEMORY.md").write_text("x")
        who = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        with mock.patch.dict(os.environ, who):
            out = M.git_commit([amr, tmp / "home" / "memory" / "okf"], "memory: s1")
        log = subprocess.run(["git", "-C", str(tmp / "home" / "memory"), "log", "--format=%s"], capture_output=True, text=True).stdout
        self.assertEqual(log.strip(), "memory: s1", out)   # committed in a repo of its own, not the code's

    def test_data_home(self):
        import os, tempfile
        from unittest import mock
        from cockpit import util as U
        code = Path(tempfile.mkdtemp())
        with mock.patch.object(U, "ROOT", code), mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("REVIEW_COCKPIT_HOME", None); os.environ.pop("PR_COCKPIT_HOME", None)
            self.assertEqual(U.data_home(), U.DEFAULT_HOME)   # a fresh install (e.g. a plugin): ~/.qodo/review-cockpit
            (code / "sessions").mkdir()
            self.assertEqual(U.data_home(), code)              # a checkout with its reviews keeps them in place
            (code / "config.local.json").write_text(json.dumps({"home": str(code / "elsewhere")}))
            self.assertEqual(U.data_home(), code / "elsewhere")
            os.environ["REVIEW_COCKPIT_HOME"] = str(code / "env")
            self.assertEqual(U.data_home(), code / "env")
            os.environ.pop("REVIEW_COCKPIT_HOME")
        shutil.rmtree(code)

    def test_migrate_copies_and_points_without_deleting(self):
        import tempfile
        from unittest import mock
        from cockpit import home as H, util as U
        code = Path(tempfile.mkdtemp())
        (code / "sessions" / "s1").mkdir(parents=True); (code / "sessions" / "s1" / "review-data.json").write_text("{}")
        (code / "memory" / "amr").mkdir(parents=True); (code / "memory" / "amr" / "MEMORY.md").write_text("prefs")
        (code / "config.local.json").write_text(json.dumps({"reviewer": "me"}))
        with mock.patch.object(U, "ROOT", code), no_home_env():
            out = H.migrate(code.parent / (code.name + "-home"))
            dst = Path(out["home"])
            self.assertEqual(sorted(out["copied"]), ["config.local.json → config.json", "memory/amr", "sessions/s1"])
            self.assertEqual((dst / "memory" / "amr" / "MEMORY.md").read_text(), "prefs")
            self.assertEqual(json.loads((dst / "config.json").read_text()), {"reviewer": "me"})
            self.assertTrue((code / "sessions" / "s1" / "review-data.json").exists())
            self.assertEqual(U.data_home(), dst)
            self.assertEqual(H.migrate(dst)["kept"], [str(dst / "sessions" / "s1"), str(dst / "memory" / "amr")])
            self.assertEqual(json.loads((code / "config.local.json.before-migrate").read_text()), {"reviewer": "me"})   # the first backup survives
            (dst / "sessions" / "s2").mkdir(); (dst / "memory" / "amr" / "new.md").write_text("learned since")
            out2 = H.migrate(code.parent / (code.name + "-home2"))   # a second move starts from the active home
            dst2 = Path(out2["home"])
            self.assertEqual(out2["from"], str(dst))
            self.assertTrue((dst2 / "sessions" / "s2").is_dir() and (dst2 / "memory" / "amr" / "new.md").exists())
            self.assertEqual(json.loads((dst2 / "config.json").read_text()), {"reviewer": "me"})
            self.assertIn("restore config.local.json.before-migrate", out2["undo"])
        shutil.rmtree(code); shutil.rmtree(dst); shutil.rmtree(dst2)

    def test_migrate_copies_each_relative_memory_folder(self):
        import tempfile
        from unittest import mock
        from cockpit import home as H, util as U
        code, far = Path(tempfile.mkdtemp()), Path(tempfile.mkdtemp())
        (code / "team" / "amr").mkdir(parents=True); (code / "team" / "amr" / "MEMORY.md").write_text("prefs")
        (code / "config.local.json").write_text(json.dumps({"memory": {"amr": "team/amr", "okf": str(far / "okf")}}))
        with mock.patch.object(U, "ROOT", code), no_home_env():
            out = H.migrate(code.parent / (code.name + "-home"))
        dst = Path(out["home"])
        self.assertIn("team/amr", out["copied"])   # a custom relative folder moves, the absolute one stays put
        self.assertEqual((dst / "team" / "amr" / "MEMORY.md").read_text(), "prefs")
        shutil.rmtree(code); shutil.rmtree(far); shutil.rmtree(dst)

    def test_migrate_follows_the_env_home(self):
        import os, tempfile
        from unittest import mock
        from cockpit import home as H, util as U
        code = Path(tempfile.mkdtemp()); env = code.parent / (code.name + "-env")
        (code / "sessions" / "s1").mkdir(parents=True)
        with mock.patch.object(U, "ROOT", code), mock.patch.dict(os.environ, {"REVIEW_COCKPIT_HOME": str(env)}):
            self.assertIn("REVIEW_COCKPIT_HOME", H.migrate(code.parent / "elsewhere")["error"])   # a pointer the env var would override
            out = H.migrate()
        self.assertEqual(out["home"], str(env.resolve()))
        self.assertTrue((env / "sessions" / "s1").is_dir())
        shutil.rmtree(code); shutil.rmtree(env)

    def test_memory_commits_in_each_repo_and_never_inits_a_broad_folder(self):
        import os, subprocess, tempfile
        from unittest import mock
        from cockpit import memory as M
        fixture = tempfile.TemporaryDirectory()
        self.addCleanup(fixture.cleanup)
        tmp = Path(fixture.name)
        who = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        a, b = tmp / "ra", tmp / "rb"
        for r in (a, b):
            r.mkdir(); subprocess.run(["git", "init", "-q", "-b", "main", str(r)], check=True)
        (a / "amr").mkdir(); (a / "amr" / "x.md").write_text("x"); (b / "okf").mkdir(); (b / "okf" / "y.md").write_text("y")
        with mock.patch.dict(os.environ, who):
            M.git_commit([a / "amr", b / "okf"], "memory: s2")
        for r in (a, b):   # one commit in each repo, not a failed add of both in one
            self.assertEqual(subprocess.run(["git", "-C", str(r), "log", "--format=%s"], capture_output=True, text=True).stdout.strip(), "memory: s2")
        c, d = tmp / "x" / "deep" / "amr", tmp / "y" / "okf"   # loose folders in separate trees: each gets its own repo
        c.mkdir(parents=True); (c / "z.md").write_text("z"); d.mkdir(parents=True); (d / "w.md").write_text("w")
        with mock.patch.dict(os.environ, who):
            M.git_commit([c, d], "memory: s3")
        self.assertFalse((tmp / ".git").exists())
        self.assertTrue((c / ".git").is_dir() and (d / ".git").is_dir())
        e, f = tmp / "amr", tmp / "okf"   # side by side in a folder that holds other things too: still no repo there
        for x in (e, f):
            x.mkdir(); (x / "m.md").write_text("m")
        with mock.patch.dict(os.environ, who):
            M.git_commit([e, f], "memory: s4")
        self.assertFalse((tmp / ".git").exists())
        self.assertTrue((e / ".git").is_dir() and (f / ".git").is_dir())
        g = tmp / "home" / "memory"   # a parent that holds only memory becomes the one repo
        for k in ("amr", "okf"):
            (g / k).mkdir(parents=True); (g / k / "m.md").write_text("m")
        with mock.patch.dict(os.environ, who):
            M.git_commit([g / "amr", g / "okf"], "memory: s5")
        self.assertTrue((g / ".git").is_dir())

    def test_qodo_findings_source(self):
        from unittest import mock
        from cockpit import adapters as A
        pr = {"key": "o/r#12", "url": "https://github.com/o/r/pull/12", "number": 12, "repo": "o/r", "_raw_comments": []}
        cli = {"review_session": {"id": "s"}, "findings": [
            {"id": "3da5f3a8-2059-4e45-ae85-022961428477", "attribution_status": "pending", "action_level": "high", "category": "Bug",
             "title": "Key outlives expiry", "location": {"path": "gw.py", "start_line": 263}},
            {"id": "8b4b3003-1aae-452a-9409-5e136e60703a", "attribution_status": "dismissed", "action_level": "low",
             "title": "Name", "dismissal": {"reason": "intentional"}}]}
        cfg = {"adapters": ["qodo_comments"]}
        with mock.patch.object(qodo_cli, "fetch", return_value=cli), mock.patch.object(A.qodo_comments, "collect", return_value=["from comments"]):
            fs = A.qodo_findings(dict(pr), cfg)
            self.assertEqual([(f["id"], f["severity"], f.get("status"), f.get("path"), f.get("line")) for f in fs],
                             [("q-o-r-12-3da5f3a8-2059-4e45-ae85-022961428477", "high", None, "gw.py", 263),
                              ("q-o-r-12-8b4b3003-1aae-452a-9409-5e136e60703a", "low", "dismissed", None, None)])   # same ids as the comments give
            self.assertEqual(fs[1]["status_why"], "intentional")
            self.assertEqual(A.qodo_findings(dict(pr), {**cfg, "qodo_findings": {"source": "comments"}}), ["from comments"])
        with mock.patch.object(qodo_cli, "fetch", return_value=None), mock.patch.object(A.qodo_comments, "collect", return_value=["from comments"]):
            p = dict(pr)
            self.assertEqual(A.qodo_findings(p, cfg), ["from comments"])   # auto: no CLI review -> what we did before
            self.assertEqual(p["qodo_source"], "comments")
            self.assertEqual(A.qodo_findings(dict(pr), {**cfg, "qodo_findings": {"source": "cli"}}), [])   # cli: no fallback

    def test_qodo_cli_findings_wire_details(self):
        from unittest import mock
        from cockpit import adapters as A
        pr = {"key": "o/r#12", "url": "https://github.com/o/r/pull/12", "number": 12, "repo": "o/r", "_raw_comments": []}
        u = "3da5f3a8-2059-4e45-ae85-022961428477"
        cli = {"review_session": {"id": "s"}, "findings": [
            {"id": u, "attribution_status": "implemented", "title": "Fixed one"},
            {"id": "8b4b3003-1aae-452a-9409-5e136e60703a", "attribution_status": "dismissed", "title": "Name",
             "dismiss_reason": "intentional", "dismiss_explanation": "kept for the old clients"},
            {"title": "No id A", "path": "a.py", "line": 1}, {"title": "No id B", "path": "a.py", "line": 9}]}
        comment = {"id": f"q-o-r-12-{u}", "url": "https://github.com/o/r/pull/12#discussion_r1", "qodo_url": "https://app.qodo.ai/findings/" + u}
        with mock.patch.object(qodo_cli, "fetch", return_value=cli), mock.patch.object(A.qodo_comments, "collect", return_value=[comment]):
            fs = A.qodo_findings(dict(pr), {})
        self.assertEqual(fs[0]["status"], "resolved")                                   # `implemented` is closed
        self.assertEqual((fs[0]["url"], fs[0]["qodo_url"]), (comment["url"], comment["qodo_url"]))   # links from the comment
        self.assertEqual(fs[1]["status_why"], "intentional: kept for the old clients")  # the producer's flat fields
        self.assertEqual(len({f["id"] for f in fs}), 4)                                 # id-less findings stay apart
        self.assertTrue(all("qodo_id" not in f for f in fs[2:]))
        empty = {"review_session": {"id": "s"}, "findings": []}
        with mock.patch.object(qodo_cli, "fetch", return_value=empty), mock.patch.object(A.qodo_comments, "collect", return_value=[comment]):
            p = dict(pr)
            self.assertEqual(A.qodo_findings(p, {}), [comment])                         # auto: empty DB, comments have some
            self.assertEqual(p["qodo_source"], "comments")
            self.assertEqual(A.qodo_findings(dict(pr), {"qodo_findings": {"source": "cli"}}), [])   # cli means cli
        with mock.patch.object(qodo_cli, "fetch", return_value=empty), mock.patch.object(A.qodo_comments, "collect", return_value=[]):
            p = dict(pr)
            self.assertEqual((A.qodo_findings(p, {}), p["qodo_source"]), ([], "cli"))  # a genuinely clean review
        with mock.patch.object(qodo_cli, "fetch", return_value=None):
            p = dict(pr, _raw_comments=[{"id": 1, "author": "qodo-merge-pro[bot]", "body": "<h3>PR Summary by Qodo</h3> what it does"}])
            self.assertEqual((A.qodo_findings(p, {}), p["qodo_source"]), ([], "none"))   # a summary is not a review
            p["_raw_comments"].append({"id": 2, "author": "qodo-merge-pro[bot]", "body": "No reviewable changes."})
            self.assertEqual((A.qodo_findings(p, {}), p["qodo_source"]), ([], "comments"))   # it reviewed and found nothing

    def test_local_findings_from_kept_reviews(self):
        from unittest import mock
        from cockpit import adapters as A
        store = Path(tempfile.mkdtemp()) / "lf"
        pr = {"key": "o/r#12", "url": "https://github.com/o/r/pull/12", "number": 12, "repo": "o/r", "head": "feat", "head_sha": "c2", "_raw_comments": []}
        a, b, c, d = ("aaaa1111-0000-4000-8000-00000000000" + x for x in "1234")
        # the review producer's shape: diff_reference, git_sha, full findings in finding_state
        fa = {"id": a, "local_review_id": "r1", "action_level": "action_required", "title": "Token leaks", "git_sha": "c1", "branch_name": "feat",
              "git_organization_name": "o", "git_repo_name": "r", "diff_reference": {"file_path": "gw.py", "start_line": 9, "end_line": 11, "side": "right"},
              "evidence": {"explanation": "The token is logged."}, "finding_source": "SecurityFinding"}
        fb = {"id": b, "local_review_id": "r1", "title": "Name", "git_sha": "c1", "diff_reference": {"file_path": "gw.py", "start_line": 30}}
        first = {"findings": [fa, fb], "finding_state": {"introduced": [fa, fb]}, "meta": {"checkpoint": {"id": "cp1", "created_at": "2026-10-01T10:00:00Z", "sequence": 1}}}
        second = {"findings": [], "meta": {"checkpoint": {"created_at": "2026-10-02T10:00:00Z", "sequence": 2}},
                  "finding_state": {"resolved": [{"id": a, "local_review_id": "r1"}],   # sparse: only the disposition
                                    "dismissed": [{"finding_id": b, "local_review_id": "r1", "dismiss_reason": "intentional", "dismiss_explanation": "kept for old clients"}],
                                    "still_open": [{"id": c, "local_review_id": "r2", "title": "Retry storm", "git_sha": "c2", "diff_reference": {"file_path": "q.py", "start_line": 4}},
                                                   {"id": d, "local_review_id": "r2", "title": "Removed guard", "git_sha": "c2", "diff_reference": {"file_path": "q.py", "start_line": 2, "side": "left"}}]}}
        with mock.patch.object(qodo_local, "STORE", store):
            with self.assertRaises(ValueError):
                qodo_local.add({"meta": {}}, pr="o/r#12")                                   # not a review result
            with self.assertRaises(ValueError):
                qodo_local.add(first, pr="12")                                              # not a PR reference
            with mock.patch.object(qodo_local, "_git", return_value=None), self.assertRaises(ValueError):
                qodo_local.add({"findings": [{"id": a}]})                                   # no PR, no branch: refuse
            with self.assertRaises(ValueError):
                qodo_local.add({"findings": [{"id": a}]}, cwd=str(ROOT))                    # never the cockpit's own checkout
            qodo_local.add(second, pr="https://github.com/O/R/pull/12")                     # handed over first; ran later
            self.assertEqual(qodo_local.records()[0]["pr"], "O/R#12")
            r1 = qodo_local.add(first, cwd=None)                                            # repo and branch from the findings
            self.assertEqual((r1["repo"], r1["branch"], r1["local_review_id"], r1["commit"]), ("o/r", "feat", "cp1", None))
            self.assertEqual([r["ran_at"] for r in qodo_local.records()], ["2026-10-01T10:00:00Z", "2026-10-02T10:00:00Z"])   # by when they ran
            self.assertEqual(qodo_local.records()[0]["local_review_id"], "cp1")             # its checkpoint, not a replayed finding's id
            qodo_local.add(first, cwd=None)
            self.assertEqual(len(qodo_local.records()), 2)                                  # the same result twice is one review
            self.assertEqual(qodo_local._review_id({"findings": [], "finding_state": {"still_open": [{"id": "x", "local_review_id": "r2"}, {"id": "y", "local_review_id": "r1"}]}}), "r1")   # a tie, by name
            fs = {f["title"]: f for f in qodo_local.collect(pr, {})}                         # PR keys match case-insensitively
            self.assertEqual({t: f.get("status", "open") for t, f in fs.items()},
                             {"Token leaks": "resolved", "Name": "dismissed", "Retry storm": "open", "Removed guard": "open"})
            tl = fs["Token leaks"]
            self.assertEqual((tl["severity"], tl["path"], tl.get("line"), tl["local"]["line"], tl["body"]),
                             ("high", "gw.py", None, 9, "The token is logged."))
            self.assertEqual(tl["qodo_type"], "Security issue")            # sparse entry kept the details; reviewed c1, not the head
            self.assertEqual(fs["Name"]["local"]["reason"], "intentional: kept for old clients")
            self.assertEqual((fs["Retry storm"]["line"], fs["Retry storm"]["source"]), (4, "qodo-local"))   # reviewed at the PR head: anchored
            self.assertNotIn("path", fs["Removed guard"])                                   # a removed (left-side) line isn't in the new file
            self.assertEqual(qodo_local.collect({**pr, "key": "o/r#13", "head": "other"}, {}), [])   # another PR sees none of it
            self.assertEqual(qodo_local.count(first), 2)
            # the same finding carried into the PR review stays one finding, marked as found before the PR
            pr_side = [{"id": f"q-o-r-12-{c}", "qodo_id": c, "source": "qodo", "title": "Retry storm", "severity": "medium"},
                       {"id": f"q-o-r-12-{b}", "qodo_id": b, "source": "qodo", "title": "Name", "severity": "low"}]
            with mock.patch.object(A, "qodo_findings", return_value=pr_side):
                got = A.collect_findings(dict(pr), {"adapters": ["qodo_comments", "qodo_local"]})
            self.assertEqual(len([f for f in got if f["qodo_id"] == c]), 1)
            self.assertEqual(next(f for f in got if f["qodo_id"] == c)["local"]["status"], "open")
            self.assertEqual(next(f for f in got if f["qodo_id"] == b)["local"]["reason"], "intentional: kept for old clients")   # the author's reason travels
            self.assertEqual(len(got), 4)
        shutil.rmtree(store.parent)

    def test_qodo_cli_names_the_finding_kind(self):
        pr = {"key": "o/r#1", "url": "https://github.com/o/r/pull/1"}
        kind = lambda src: qodo_cli.to_finding(pr, {"id": "x", "title": "t", "finding_source": src}).get("qodo_type")
        self.assertEqual([kind("ComplianceRule"), kind("IssueFinding"), kind("CrossRepoFinding")],
                         ["Rule violation", "Bug", "Cross-repo conflict"])
        # every source the review producer emits gets a name; rule and skill agents read as conventions
        self.assertEqual([kind("ComplianceAgentFileRule"), kind("ComplianceTicketRule"), kind("SkillsFinding"), kind("SpecFinding")],
                         ["Rule violation", "Requirement gap", "Skill insight", "Requirement gap"])
        self.assertEqual([kind("UIFinding"), kind("UIRuntimeFinding"), kind("PersonaFinding"), kind("SecurityFinding")],
                         ["UX issue", "UI issue", "Team insight", "Security issue"])   # the producer's own labels
        self.assertEqual([kind("SomethingNew"), kind(None)], ["Suggestion", None])

    def test_local_findings_name_their_kind_like_the_db(self):
        pr = {"key": "o/r#1", "repo": "o/r", "head_sha": "h"}
        f = qodo_local.to_finding(pr, {"local_review_id": "r"}, {"id": "a", "title": "t", "finding_source": "ComplianceRule"}, None)
        self.assertEqual((f["qodo_type"], f["category"]), ("Rule violation", "general"))   # a rule with the default category

    def test_linter_annotations_can_say_lint(self):
        from cockpit.adapters import scanners as SC
        from unittest import mock
        pr = {"key": "o/r#1", "repo": "o/r", "number": 1, "files": []}
        ann = [{"path": "a.py", "line": 3, "level": "warning", "title": "E501 line too long", "message": "", "check": "ruff"}]
        with mock.patch.object(SC, "_annotations", return_value=ann):
            self.assertEqual(SC.check_annotations(pr, [], {"name": "Ruff", "kind": "lint"})[0]["scanner"]["kind"], "lint")
            self.assertEqual(SC.check_annotations(pr, [], {"name": "Codacy"})[0]["scanner"]["kind"], "sast")   # unchanged default

    def test_local_review_kept_before_the_rename_counts_once(self):
        from unittest import mock
        store = Path(tempfile.mkdtemp()) / "lf"
        store.mkdir()
        result = {"findings": [{"id": "f1", "local_review_id": "r1", "title": "T"}]}
        legacy = store / "r1.json"   # how a review was named before content digests
        legacy.write_text(json.dumps({"local_review_id": "r1", "pr": "o/r#1", "added_at": "2026-10-01T00:00:00Z", "result": result}))
        with mock.patch.object(qodo_local, "STORE", store):
            (store / "copy.json").write_text(legacy.read_text())
            self.assertEqual(len(qodo_local.records()), 1)                     # the same result under two names reads once
            qodo_local.add(result, pr="o/r#1")
            self.assertEqual(len(qodo_local.records()), 1)
            self.assertFalse(legacy.exists() or (store / "copy.json").exists())   # re-adding replaces the old copies
            qodo_local.add({**result, "meta": {"checkpoint": {"id": "cp2"}}}, pr="o/r#1")
            self.assertEqual(len(qodo_local.records()), 2)                     # a different result is its own review
        shutil.rmtree(store.parent)

    def test_qodo_cli_fetch_gives_up_quietly(self):
        from unittest import mock
        pr = {"key": "o/r#1", "url": "https://github.com/o/r/pull/1"}
        with mock.patch.object(qodo_cli.shutil, "which", return_value=None):
            self.assertIsNone(qodo_cli._real_fetch(pr, {}))   # not installed
        run = lambda out, rc=0: mock.Mock(stdout=out, returncode=rc)
        with mock.patch.object(qodo_cli.shutil, "which", return_value="/bin/qodo"):
            with mock.patch.object(qodo_cli.subprocess, "run", return_value=run("", 1)):
                self.assertIsNone(qodo_cli._real_fetch(pr, {}))   # not logged in / repo not in scope
            with mock.patch.object(qodo_cli.subprocess, "run", return_value=run(json.dumps({"review_session": None, "findings": []}))):
                self.assertIsNone(qodo_cli._real_fetch(pr, {}))   # no review on this deployment
            with mock.patch.object(qodo_cli.subprocess, "run", return_value=run(json.dumps({"review_session": {}, "findings": [], "qar_operation_result_truncated": True}))):
                self.assertIsNone(qodo_cli._real_fetch(pr, {}))   # incomplete read
            for odd in ("null", "[]", json.dumps({"review_session": {"id": "s"}}), json.dumps({"review_session": {"id": "s"}, "findings": None})):
                with mock.patch.object(qodo_cli.subprocess, "run", return_value=run(odd)):
                    self.assertIsNone(qodo_cli._real_fetch(pr, {}), odd)   # not the documented envelope: fall back
            ok = {"review_session": {"id": "s"}, "findings": []}
            with mock.patch.object(qodo_cli.subprocess, "run", return_value=run(json.dumps(ok))) as r:
                self.assertEqual(qodo_cli._real_fetch(pr, {}), ok)
                self.assertEqual(r.call_args[0][0], ["qodo", "read", "pr-review-session", "findings", "--pr-url", pr["url"], "--extended", "--json"])

    def test_glob(self):
        self.assertTrue(glob_match("tests/test_a.py", "**/test*/**"))
        self.assertTrue(glob_match("pkg/tests/test_a.py", "**/test*/**"))
        self.assertTrue(glob_match("src/payments/x.py", "src/payments/**"))
        self.assertFalse(glob_match("src/cache/x.py", "src/payments/**"))
        self.assertEqual(path_glob("src/payments/discounts.py"), "src/payments/**")
        self.assertEqual(path_glob("tests/test_x.py"), "**/test*/**")

    def test_parse_diff(self):
        d = "diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ -1,2 +1,3 @@\n a\n-b\n+c\n+d\n"
        h = C.parse_diff(d)["x.py"][0]["lines"]
        self.assertEqual(h, [[" ", 1, 1, "a"], ["-", 2, None, "b"], ["+", None, 2, "c"], ["+", None, 3, "d"]])


class FlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self._sessions = C.SESSIONS
        C.SESSIONS = self.tmp / "sessions"
        self.cfg = load_config()
        shutil.copytree(ROOT / "fixtures" / "demo-memory", self.tmp / "mem")
        self.cfg["memory"] = {"amr": str(self.tmp / "mem/amr"), "okf": str(self.tmp / "mem/okf"), "auto_commit": False}
        fx = json.loads((ROOT / "fixtures" / "demo-prs.json").read_text())
        self.session, self.sdir = C.build(fx["prs"], self.cfg, demo=True, session="t1", reviewer_login="demo-reviewer")
        self.data = json.loads((self.sdir / "review-data.json").read_text())

    def tearDown(self):
        C.SESSIONS = self._sessions
        shutil.rmtree(self.tmp)

    def ev(self, *events):
        with (self.sdir / "events.jsonl").open("a") as fh:
            for e in events:
                fh.write(json.dumps(e) + "\n")

    def test_collect_matches_concepts_overlaps_and_imports_own_comments(self):
        keys = {p["key"]: p for p in self.data["prs"]}
        self.assertIn("invariants/prices-in-cents.md", keys["qodo-ai/shop-demo#102"]["concepts"])
        self.assertEqual(self.data["overlaps"]["files"][0]["path"], "src/payments/checkout.py")
        self.assertEqual(len(self.data["prefs"]["rules"]), 3)  # evidence >= 3 only
        lines = (self.sdir / "events.jsonl").read_text().splitlines()
        self.assertEqual(json.loads(lines[0])["source"], "github")

    def test_related_prs_across_repos(self):
        from unittest import mock
        prs = [{"key": "o/cockpit#57", "repo": "o/cockpit", "number": 57, "url": "https://github.com/o/cockpit/pull/57", "title": "fix: x", "head": "fix/wf-1182-x", "base": "main",
                "body": "Consumer compatibility for Example-org/review-engine#7636. See also #12 here. Tracks WF-1182."}]
        ctx = C.context(prs)
        self.assertEqual([r["key"] for r in ctx["related"]], ["Example-org/review-engine#7636"])   # owner/repo#N, not a same-repo guess
        self.assertEqual([m["same_repo_guess"] for m in ctx["mentions"]], ["o/cockpit#12"])
        self.assertEqual(C.context([{**prs[0], "body": "Same as O/Cockpit#57."}])["related"], [])   # its own PR, however it's cased
        twice = C.context([{**prs[0], "body": "See o/Engine#9 and O/engine#9."}])["related"]
        self.assertEqual(len(twice), 1)   # one sister PR, however each description spells it
        odd = C.context([{**prs[0], "body": "Docs: https://gitlab.com/team/docs/-/blob/main/a#12 and https://github.com/x/y/pull/3"}])["related"]
        self.assertEqual([r["key"] for r in odd], ["x/y#3"])   # a path inside another URL isn't a PR; a github PR link is
        search = [{"repository": {"nameWithOwner": "o/runtime"}, "number": 701, "title": "fix: runtime", "url": "https://github.com/o/runtime/pull/701", "isDraft": False, "body": "Tracks wf-1182."},   # lowercase still counts
                  {"repository": {"nameWithOwner": "o/ide"}, "number": 17, "title": "fix: ide", "url": "https://github.com/o/ide/pull/17", "isDraft": True, "body": "branch WF-1182-fix"},
                  {"repository": {"nameWithOwner": "o/bot"}, "number": 4, "title": "bump", "url": "u", "isDraft": False, "body": "WF-11820 and WF-1182abc"},
                  {"repository": {"nameWithOwner": "o/other"}, "number": 9, "title": "Bump sdk to 1.24", "url": "u", "isDraft": False, "body": "PR 1182 of the bot"},
                  {"repository": {"nameWithOwner": "o/cockpit"}, "number": 57, "title": "self", "url": "u", "isDraft": False}]
        view = {"title": "fix: engine", "url": "https://github.com/Example-org/review-engine/pull/7636", "state": "OPEN", "isDraft": False}
        def run(argv, **kw):
            out = search if argv[1] == "search" else view
            return mock.Mock(returncode=0, stdout=json.dumps(out))
        calls = []
        with mock.patch("subprocess.run", side_effect=lambda argv, **kw: (calls.append(argv), run(argv))[1]):
            rel = {r["key"]: r for r in C.related_elsewhere(prs, ctx)}
        owners = sorted(c[c.index("--owner") + 1] for c in calls if c[1] == "search")
        self.assertEqual(owners, ["Example-org", "o"])   # only the owners this work lives in, one per call (older gh takes one --owner)
        self.assertEqual(set(rel), {"Example-org/review-engine#7636", "o/runtime#701", "o/ide#17"})   # never the session's own PR, nor a mere "1182"
        self.assertEqual(rel["o/runtime#701"]["why"], "names WF-1182")
        self.assertEqual(rel["Example-org/review-engine#7636"]["title"], "fix: engine")
        with mock.patch.object(C, "RELATED_BUDGET", 0), mock.patch("subprocess.run", side_effect=AssertionError("no lookup past the budget")):
            self.assertEqual([r["key"] for r in C.related_elsewhere(prs, ctx)], ["Example-org/review-engine#7636"])   # out of time: the named ones stay
        with mock.patch("subprocess.run", side_effect=OSError):
            self.assertEqual([r["key"] for r in C.related_elsewhere(prs, ctx)], ["Example-org/review-engine#7636"])   # a failed lookup is skipped

    def test_rebuild_skips_already_imported_github_comments(self):
        before = [e for e in C._events(self.sdir) if e.get("github_id")]
        self.assertTrue(before)
        fx = json.loads((ROOT / "fixtures" / "demo-prs.json").read_text())
        C.build(fx["prs"], self.cfg, demo=True, session="t1", reviewer_login="demo-reviewer",
                skip_github_ids={e["github_id"] for e in before})
        self.assertEqual(len([e for e in C._events(self.sdir) if e.get("github_id")]), len(before))

    def test_refresh_skips_comments_published_from_the_cockpit(self):
        from unittest import mock
        self.ev({"type": "published", "pr": "qodo-ai/shop-demo#101", "note_ids": ["n1"], "github_ids": [777, 778]})
        fx = json.loads((ROOT / "fixtures" / "demo-prs.json").read_text())
        pr = json.loads(json.dumps(fx["prs"][0]))
        pr["_raw_comments"] = pr.get("_raw_comments", []) + [
            {"id": 778, "author": "demo-reviewer", "body": "my posted note", "path": "src/cache/price_cache.py", "line": 20, "url": "u"}]
        before = len(C._events(self.sdir))
        prs = {p["number"]: p for p in fx["prs"]}
        prs[pr["number"]] = pr
        fresh = lambda repo, number, checks=None: json.loads(json.dumps(prs[number]))
        with mock.patch.object(C, "fetch_pr", side_effect=fresh), mock.patch.object(C, "gh", return_value="demo-reviewer\n"):
            C.refresh(self.sdir, self.cfg)
        new = C._events(self.sdir)[before:]
        self.assertFalse(any(e.get("github_id") == 778 for e in new))

    def test_distill_dismissals_become_rule_after_threshold(self):
        f = [x for p in self.data["prs"] for x in p["findings"] if x["category"] == "style"][0]
        for _ in range(3):  # three sessions' worth of dismissals collapse to one latest verdict per finding...
            self.ev({"type": "finding_verdict", "pr": f["pr"], "target": {"kind": "finding", "id": f["id"]}, "verdict": "dismiss"})
        res = distill(self.sdir, self.cfg)
        b = [x for x in res["amr"] if x["rule"] and "style" in x["rule"]][0]
        self.assertEqual(b["evidence"], 1)  # ...so evidence is 1, not 3
        amr = AMR(Path(self.cfg["memory"]["amr"]))
        for _ in range(2):
            amr.upsert(Bullet(b["text"], {"rule": b["rule"], "evidence": "1"}, "preferences/findings.md"))
        active = [r["rule"] for r in amr.active_rules(3)]
        self.assertIn(b["rule"], active)

    def test_make_memories_twice_at_once_counts_once(self):
        import threading
        self.ev(*[{"type": "fold", "id": "rbk", "open": True, "default_open": False} for _ in range(3)])
        out = []
        ts = [threading.Thread(target=lambda: out.append(distill(self.sdir, self.cfg))) for _ in range(4)]
        [t.start() for t in ts]; [t.join() for t in ts]
        credited = sum(r["evidence"] for res in out for r in res["amr"] if r["rule"] == "open-fold id=rbk")
        self.assertEqual(credited, 3)   # four overlapping runs, one credit
        self.assertFalse(any(p.name.endswith(".lock") for p in Path(self.cfg["memory"]["amr"]).rglob("*")))   # nothing for auto-commit to pick up

    def test_one_review_counts_every_signal_of_a_rule(self):
        fs = [x for p in self.data["prs"] for x in p["findings"] if x["category"] == "naming"][:2]
        self.assertEqual(len(fs), 2)
        self.ev(*[{"type": "mark", "pr": f["pr"], "target": {"kind": "finding", "id": f["id"]}, "emoji": "🧹"} for f in fs])
        res = {r["rule"]: r["evidence"] for r in distill(self.sdir, self.cfg)["amr"]}
        self.assertEqual(res["collapse category=naming"], 2)   # two nits in one review count 2, not 1

    def test_style_page_signals_become_memory(self):
        f = [x for p in self.data["prs"] for x in p["findings"] if x["category"] == "style"][0]
        evs = [{"type": "fold", "id": "rbk", "open": True, "default_open": False} for _ in range(3)]
        evs += [{"type": "fold", "id": "f:abc", "open": True, "default_open": False}]   # one finding's fold: not a habit
        evs += [{"type": "fold", "id": "fq0", "open": True, "default_open": False} for _ in range(3)]   # this review's own question fold: neither
        evs += [{"type": "ask", "q": "what if it fails?", "about": {"kind": "rollback plan", "title": "If it goes wrong"}}]
        evs += [{"type": "note", "note_id": f"n{i}", "pr": f["pr"], "text": "meh", "emoji": "🧹", "finding_id": f["id"]} for i in range(2)]
        evs += [{"type": "note", "note_id": "d1", "pr": f["pr"], "text": "Accepted as decided: cache falls back to the DB",
                 "decision": "accept", "decision_text": "The cache falls back to the DB on a miss", "path": "src/cache/price_cache.py"}]
        self.ev(*evs)
        res = distill(self.sdir, self.cfg)
        rules = {r["rule"]: r["evidence"] for r in res["amr"]}
        self.assertEqual(rules.get("open-fold id=rbk"), 3)
        self.assertFalse(any(r and ("f:abc" in r or "fq0" in r) for r in rules))
        self.assertEqual(rules.get("ask-about kind=rollback-plan"), 1)
        self.assertEqual(rules.get("collapse category=style"), 2)   # a 🧹 note on a finding counts as calling it a nit
        self.assertTrue(any("cache-falls-back" in c for c in res["okf"]))   # an accepted decision is a knowledge draft
        self.ev({"type": "note", "note_id": "f1", "pr": f["pr"], "text": "fact: The cache falls back to the DB on a miss"})
        self.assertTrue(any(c.startswith("facts/") for c in distill(self.sdir, self.cfg)["okf"]))   # a Fact isn't blocked by a Decision of the same title
        again = distill(self.sdir, self.cfg)   # Make memories twice: nothing is counted twice
        self.assertEqual(again["amr"], []); self.assertEqual(again["okf"], [])
        self.ev({"type": "fold", "id": "rbk", "open": True, "default_open": False})
        self.assertEqual({r["rule"]: r["evidence"] for r in distill(self.sdir, self.cfg)["amr"]}.get("open-fold id=rbk"), 1)   # only what's new
        amr = AMR(Path(self.cfg["memory"]["amr"]))
        self.assertIn("open-fold id=rbk", [r["rule"] for r in amr.active_rules(3)])
        from cockpit.view import view_data
        prefs = view_data(self.sdir)["prefs"]   # read now from the session's memory, not at collect time
        from cockpit.styles import render
        shared = render("focus", self.sdir, mode="snapshot")
        self.assertNotIn("open-fold id=rbk", shared)   # a shared page carries none of the exporter's preferences
        self.assertIn("open-fold id=rbk", render("focus", self.sdir, mode="serve"))
        from cockpit.export import build
        app = build(self.sdir)
        self.assertNotIn("what if it fails?", app)   # the questions you asked Qodo stay yours
        self.assertNotIn("Opens the How to roll back fold", app)   # so do your preferences
        self.assertIn("cache-falls-back", app)   # a decision drafted by this review's Make memories is in its own shared page
        self.ev({"type": "finding_verdict", "pr": "x", "target": {"kind": "finding", "id": "secret-verdict-id"}, "verdict": "dismiss"})
        self.assertNotIn("secret-verdict-id", build(self.sdir))   # nor your decisions on findings
        from cockpit.distill import _lock_path
        import os, stat
        lp = _lock_path(Path(self.cfg["memory"]["amr"]))
        if hasattr(os, "getuid"):
            self.assertFalse(stat.S_IMODE(os.stat(lp.parent).st_mode) & 0o077)   # POSIX mode bits
        else:
            self.assertTrue(lp.parent.is_dir())   # Windows has no POSIX ownership/mode contract
        self.assertTrue(prefs["enabled"]); self.assertIn("open-fold", [r["action"] for r in prefs["rules"]])

    def test_marks_notes_and_facts(self):
        f = self.data["prs"][1]["findings"][0]
        self.ev({"type": "mark", "pr": f["pr"], "target": {"kind": "finding", "id": f["id"]}, "emoji": "🚫"},
                {"type": "mark", "pr": f["pr"], "target": {"kind": "panel", "id": "diagram"}, "emoji": "👎"},
                {"type": "view", "pr": f["pr"], "panel": "files"},
                {"type": "note", "pr": f["pr"], "note_id": "n1", "text": "remember: always check rounding in money code", "target": {"kind": "pr", "id": f["pr"]}},
                {"type": "note", "pr": f["pr"], "note_id": "n2", "text": "fact: discounts are applied after line totals", "path": "src/payments/checkout.py", "line": 16, "target": {"kind": "line", "id": "x"}},
                {"type": "note", "pr": f["pr"], "note_id": "n3", "text": "drop me", "target": {"kind": "pr", "id": f["pr"]}},
                {"type": "note", "pr": f["pr"], "note_id": "n3", "undo": True})
        res = distill(self.sdir, self.cfg)
        texts = [x["text"] for x in res["amr"]]
        self.assertIn("Finds the diagram panel unhelpful", texts)
        self.assertIn("Opens the files panel first", texts)
        self.assertIn("always check rounding in money code", texts)
        self.assertTrue(any(f"{f['category']} findings as blocking" in t for t in texts))
        self.assertEqual(len(res["okf"]), 1)
        okf = OKF(Path(self.cfg["memory"]["okf"]))
        c = okf.get(res["okf"][0])
        self.assertEqual(c.meta["status"], "draft")
        self.assertEqual(c.meta["paths"], ["src/payments/checkout.py"])
        log = (Path(self.cfg["memory"]["amr"]) / res["review_log"]).read_text()
        self.assertNotIn("drop me", log)
        self.assertEqual(okf.validate(), [])

    def test_okf_confirm_reject(self):
        okf = OKF(Path(self.cfg["memory"]["okf"]))
        c = okf.propose(type_="Decision", title="Use LRU for price cache", body="x", paths=["src/cache/**"], by="claude/test", sources=[{"resource": "s"}])
        okf.confirm(c.path, "demo-reviewer")
        d = okf.get(c.path).as_dict()
        self.assertEqual((d["status"], d["tier"]), ("stable", "human-reviewed"))
        self.assertTrue(okf.propose(type_="Glossary", title="Ghost text", body="x", paths=[], by="a", sources=[]).path.startswith("glossary/"))
        self.assertTrue(okf.propose(type_="RiskArea", title="Hot path", body="x", paths=[], by="a", sources=[]).path.startswith("risk-areas/"))
        c2 = okf.propose(type_="Fact", title="Wrong", body="x", paths=[], by="a", sources=[])
        self.assertEqual(okf.reject(c2.path, "demo-reviewer"), "deleted")
        self.assertIn("Deletion", (okf.root / "log.md").read_text())

    def test_build_review_payload(self):
        pr = "qodo-ai/shop-demo#102"
        self.ev({"type": "note", "pr": pr, "note_id": "a", "text": "float math", "emoji": "🐛", "post": True, "path": "src/payments/discounts.py", "line": 8, "target": {"kind": "line", "id": "x"}},
                {"type": "note", "pr": pr, "note_id": "b", "text": "nice tests", "emoji": "👏", "post": True, "target": {"kind": "pr", "id": pr}},
                {"type": "note", "pr": pr, "note_id": "c", "text": "private", "post": False, "target": {"kind": "pr", "id": pr}})
        payload, ids, replies = build_review(self.sdir, pr, EMOJI)
        self.assertEqual(sorted(ids), ["a", "b"])
        self.assertEqual(replies, [])
        self.assertEqual(payload["comments"], [{"path": "src/payments/discounts.py", "line": 8, "side": "RIGHT", "body": "**Bug:** float math"}])
        self.assertIn("👏 nice tests", payload["body"])
        self.assertNotIn("private", payload["body"])

    def test_dream_merges_and_flags_stale(self):
        p = Path(self.cfg["memory"]["amr"]) / "preferences/findings.md"
        p.write_text(p.read_text() + "- Treats security findings as blocking [rule: prioritize category=security; evidence: 2; added: 2026-10-01]\n")
        rep = dream(self.cfg)
        self.assertEqual(rep["merged"], 1)
        self.assertEqual(p.read_text().count("prioritize category=security"), 1)
        self.assertEqual(rep["invalid"], [])


class ThreadTests(unittest.TestCase):
    """Notes on a finding that has its own GitHub review thread are posted there as replies, and can resolve it."""
    setUp, tearDown, ev = FlowTests.setUp, FlowTests.tearDown, FlowTests.ev
    PR = "qodo-ai/shop-demo#102"
    URL = "https://github.com/qodo-ai/shop-demo/pull/102#discussion_r"

    def threaded(self, **state):
        """Give the PR's first two findings review threads (ids 11, 22) and make the session a real one."""
        data = json.loads((self.sdir / "review-data.json").read_text())
        data["demo"] = False
        pr = next(p for p in data["prs"] if p["key"] == self.PR)
        th = {11: {"id": "T11", "resolved": False, "outdated": False, "can_reply": True, "can_resolve": True, **state},
              22: {"id": "T22", "resolved": False, "outdated": False, "can_reply": True, "can_resolve": True}}
        pr["findings"][0]["url"], pr["findings"][1]["url"] = self.URL + "11", self.URL + "22"
        from cockpit import threads
        threads.attach(pr["findings"], th)
        (self.sdir / "review-data.json").write_text(json.dumps(data))
        return data, pr["findings"], th

    def note(self, nid, f, text, **kw):
        self.ev({"type": "note", "pr": self.PR, "note_id": nid, "text": text, "post": True,
                 "target": {"kind": "finding", "id": f["id"], "label": f["title"][:40]}, **kw})

    def handler(self, moved=False):
        from cockpit import server as srv
        h = srv.Handler.__new__(srv.Handler)
        h.sdir, h.cfg = self.sdir, {**load_config(), "emoji": EMOJI}
        h._live = lambda: {"prs": {self.PR: {"moved": moved, "head": "new"}}}
        return h

    def test_comment_ids_and_attach(self):
        from cockpit import threads
        self.assertEqual(threads.comment_id({"url": self.URL + "42"}), 42)
        self.assertEqual(threads.comment_id({"url": "https://github.com/o/r/pull/1#issuecomment-5", "thread_url": self.URL + "7"}), 7)
        self.assertIsNone(threads.comment_id({"url": "https://github.com/o/r/pull/1#issuecomment-5"}))   # a summary item: no thread
        fs = [{"url": self.URL + "1"}, {"url": self.URL + "2", "thread": {"stale": 1}}]
        threads.attach(fs, {1: {"id": "T", "resolved": True}})
        self.assertEqual(fs[0]["thread"], {"comment_id": 1, "id": "T", "resolved": True})
        self.assertNotIn("thread", fs[1])   # gone from GitHub since: the old state doesn't linger

    def test_fetch_pages_and_errors(self):
        from unittest import mock
        from cockpit import threads
        def node(i, **kw):
            return {"id": f"T{i}", "isResolved": False, "isOutdated": False, "viewerCanReply": True, "viewerCanResolve": False,
                    "comments": {"nodes": [{"databaseId": i}]}, **kw}
        pages = [{"data": {"repository": {"pullRequest": {"reviewThreads": {"pageInfo": {"hasNextPage": True, "endCursor": "c1"}, "nodes": [node(1)]}}}}},
                 {"data": {"repository": {"pullRequest": {"reviewThreads": {"pageInfo": {"hasNextPage": False}, "nodes": [node(2, isResolved=True), {"id": "T3", "comments": {"nodes": []}}]}}}}}]
        calls = []
        def gh(args):
            calls.append(args)
            return json.dumps(pages[len(calls) - 1])
        with mock.patch.object(threads, "gh", side_effect=gh):
            got = threads._real_fetch("o/123", 5)
        self.assertEqual(sorted(got), [1, 2])
        self.assertTrue(got[2]["resolved"])
        self.assertIn("after=c1", calls[1])
        self.assertIn("r=123", calls[0])   # a numeric repo name stays a string (-f)
        with mock.patch.object(threads, "gh", return_value=json.dumps({"errors": [{"message": "nope"}]})):
            with self.assertRaises(RuntimeError):
                threads._real_fetch("o/r", 5)

    def test_collect_survives_a_thread_read_failure(self):
        from unittest import mock
        from cockpit import threads
        def gh_json(args):
            return {"number": 9, "title": "t", "url": "u", "files": []} if args[:2] == ["pr", "view"] else []
        with mock.patch.object(C, "gh_json", side_effect=gh_json), mock.patch.object(C, "gh", return_value=""), \
             mock.patch.object(C, "prior_bases", return_value=[]), mock.patch.object(threads, "fetch", side_effect=RuntimeError("gh api graphql -f query=... failed: HTTP 403")):
            p = C.fetch_pr("o/r", 9)
        self.assertIsNone(p["_threads"])

    def test_routing(self):
        _, fs, th = self.threaded()
        self.note("r1", fs[0], "agree, fixing", emoji="🐛", resolve=True)
        self.note("r2", fs[2], "no thread for this one")   # fs[2] has no thread: review body
        self.ev({"type": "note", "pr": self.PR, "note_id": "l1", "text": "inline", "post": True, "path": "a.py", "line": 3, "target": {"kind": "line", "id": "a.py:3"}})
        payload, ids, replies = build_review(self.sdir, self.PR, EMOJI)
        self.assertEqual(sorted(ids), ["l1", "r2"])
        self.assertEqual([(r["note_id"], r["comment_id"], r["thread_id"], r["resolve"]) for r in replies], [("r1", 11, "T11", True)])
        self.assertTrue(replies[0]["body"].startswith("**Bug:**"))
        self.assertIn("no thread for this one", payload["body"])
        # the thread is gone or locked on GitHub now: the note falls back to the review body
        for live in ({22: th[22]}, {11: {**th[11], "can_reply": False}}):
            payload, ids, replies = build_review(self.sdir, self.PR, EMOJI, live)
            self.assertEqual((sorted(ids), replies), (["l1", "r1", "r2"], []))

    def publish(self, h, **kw):
        from unittest import mock
        from cockpit import server as srv, threads
        data = json.loads((self.sdir / "review-data.json").read_text())
        rec = {"reply": [], "resolve": [], "review": []}
        live = kw.pop("live", None)
        def reply(repo, number, cid, body):
            rec["reply"].append((cid, body))
            if cid in kw.get("fail", ()):
                raise RuntimeError("gh api ... failed: HTTP 404 Not Found")
            return {"id": 900 + cid, "html_url": f"https://x/r{cid}"}
        def resolve(t):
            rec["resolve"].append(t)
            if kw.get("resolve_fails"):
                raise RuntimeError("gh api graphql failed: HTTP 502")
        def gh(args, input_text=None):
            if "--method" in args:
                rec["review"].append(json.loads(input_text))
                return json.dumps({"id": 5, "html_url": "https://x/review"})
            return "[51]"
        with mock.patch.object(threads, "fetch", return_value=live if live is not None else {r: v for r, v in self.th.items()}), \
             mock.patch.object(threads, "reply", side_effect=reply), \
             mock.patch.object(threads, "resolve", side_effect=resolve), mock.patch.object(srv, "gh", side_effect=gh):
            return h._publish({"pr": self.PR, "dry_run": kw.get("dry", False), **({"expect": kw["expect"]} if "expect" in kw else {})}, data), rec

    def test_publish_replies_resolves_once_and_never_reposts(self):
        _, fs, self.th = self.threaded()
        self.note("r1", fs[0], "first", resolve=True)
        self.note("r2", fs[0], "second", resolve=True)   # same thread: resolved once
        self.note("r3", fs[1], "fails")
        prev, _ = self.publish(self.handler(), dry=True)
        self.assertTrue(prev["dry_run"])
        self.assertIsNone(prev["payload"])   # only replies: no review made of the plan alone
        self.assertEqual(len(prev["replies"]), 3)
        res, rec = self.publish(self.handler(), fail=(22,))
        self.assertFalse(res["ok"])
        self.assertEqual(rec["resolve"], ["T11"])
        self.assertEqual(rec["review"], [])
        self.assertEqual([(r["kind"], r["ok"], r.get("resolve")) for r in res["results"]],
                         [("reply", True, None), ("resolve", True, None), ("reply", True, "already resolved"), ("reply", False, None)])
        self.assertIn("no longer on GitHub", res["results"][3]["error"])
        self.assertIn("the rest did", res["error"])
        self.assertTrue(all("pr-review-cockpit:" in b for _, b in rec["reply"]))
        # again: only the failed one goes out, and the replies posted stay out of `refresh`'s imports
        res, rec = self.publish(self.handler())
        self.assertEqual([c for c, _ in rec["reply"]], [22])
        self.assertTrue(res["ok"])
        pub = [e for e in C._events(self.sdir) if e.get("type") == "published"]
        self.assertEqual(sorted(g for e in pub for g in e["github_ids"]), [911, 911, 922])

    def test_publish_skips_resolve_when_not_allowed_or_already_done(self):
        _, fs, self.th = self.threaded(can_resolve=False)
        self.note("r1", fs[0], "x", resolve=True)
        res, rec = self.publish(self.handler())
        self.assertEqual((rec["resolve"], res["results"][0]["resolve"][:11]), ([], "not allowed"))
        self.note("r2", fs[1], "y", resolve=True)
        res, rec = self.publish(self.handler(), live={22: {**self.th[22], "resolved": True}})   # resolved by someone since
        self.assertEqual((rec["resolve"], res["results"][0]["resolve"]), ([], "already resolved"))

    def test_moved_pr_blocks_inline_notes_only(self):
        _, fs, self.th = self.threaded()
        self.note("r1", fs[0], "reply")
        self.ev({"type": "note", "pr": self.PR, "note_id": "b1", "text": "body note", "post": True, "target": {"kind": "pr", "id": self.PR}})
        res, rec = self.publish(self.handler(moved=True))
        self.assertTrue(res["ok"])
        self.assertEqual(len(rec["reply"]), 1)
        self.assertNotIn("commit_id", rec["review"][0])   # body only: goes on the PR's current head
        self.ev({"type": "note", "pr": self.PR, "note_id": "l1", "text": "inline", "post": True, "path": "a.py", "line": 3, "target": {"kind": "line", "id": "a.py:3"}})
        self.note("r2", fs[1], "reply next to a blocked inline note")
        res, rec = self.publish(self.handler(moved=True))
        self.assertEqual([c for c, _ in rec["reply"]], [22])   # the reply doesn't depend on a diff line: it goes
        self.assertEqual(rec["review"], [])
        self.assertIn("new commits", res["results"][-1]["error"])
        self.assertIn("the rest did", res["error"])

    def test_failed_resolve_is_retried_without_reposting(self):
        _, fs, self.th = self.threaded()
        self.note("r1", fs[0], "fixed", resolve=True)
        res, rec = self.publish(self.handler(), resolve_fails=True)
        self.assertEqual([(r["kind"], r["ok"]) for r in res["results"]], [("reply", True), ("resolve", False)])
        self.assertFalse(res["ok"])
        prev, _ = self.publish(self.handler(), dry=True)   # the next publish offers the resolve alone
        self.assertEqual([(r["note_id"], r.get("resolve_only")) for r in prev["replies"]], [("r1", True)])
        res, rec = self.publish(self.handler())
        self.assertEqual((rec["reply"], rec["resolve"], res["ok"]), ([], ["T11"], True))
        prev, _ = self.publish(self.handler(), dry=True)
        self.assertFalse(prev["ok"])   # nothing left

    def test_publish_refuses_notes_the_preview_did_not_show(self):
        _, fs, self.th = self.threaded()
        self.note("r1", fs[0], "seen in the preview")
        prev, _ = self.publish(self.handler(), dry=True)
        self.note("r2", fs[1], "added after the preview")
        res, rec = self.publish(self.handler(), expect=prev["expect"])
        self.assertTrue(res.get("changed"))
        self.assertEqual(rec["reply"], [])
        prev, _ = self.publish(self.handler(), dry=True)
        res, rec = self.publish(self.handler(), expect=prev["expect"])
        self.assertTrue(res["ok"])

    def test_nothing_posted_says_so(self):
        _, fs, self.th = self.threaded()
        self.note("r1", fs[0], "to a deleted thread")
        res, _ = self.publish(self.handler(), fail=(11,))
        self.assertTrue(res["error"].startswith("Nothing was posted"))

    def test_cli_inline_comment_id_finds_the_thread(self):
        from cockpit import threads
        f = qodo_cli.to_finding({"key": "o/r#1"}, {"id": "u1", "title": "t", "inline_comment_id": "gh1:PRRT_x:4200082015"})
        self.assertEqual(threads.comment_id(f), 4200082015)
        self.assertIsNone(threads.comment_id({"inline_comment_id": "gh1:PRRT_x:abc"}))


class QodoCommentsTests(unittest.TestCase):
    """Formats from real Qodo comments (2026-10), content replaced with synthetic text."""
    FX = Path(__file__).resolve().parent / "fixtures" / "qodo"

    def pr(self, *comments):
        raw = [{"id": i, "author": "qodo-pentest-1[bot]", "url": f"https://github.com/acme/shop/pull/12#c{i}",
                "path": c.get("path"), "line": c.get("line"), "start_line": c.get("start_line"),
                "body": (self.FX / c["fx"]).read_text()} for i, c in enumerate(comments)]
        raw.append({"id": 99, "author": "snyk-io[bot]", "body": "Security scan found 3 issues", "url": None, "path": None, "line": None})
        return {"key": "acme/shop#12", "_raw_comments": raw}

    def test_review_comment_splits_into_findings(self):
        pr = self.pr({"fx": "review.md"}, {"fx": "summary.md"}, {"fx": "updated.md"})
        every = Q.collect(pr, load_config())
        fs = [f for f in every if f.get("status", "open") == "open"]
        self.assertEqual([f["title"] for f in fs], ["Refunds skip the ledger lock", "Cache key ignores currency", "Test repeats fixture values"])
        closed = {f["title"]: f["status"] for f in every if f.get("status", "open") != "open"}
        self.assertEqual(closed, {"Refund amount uses floats": "resolved", "Old endpoint still registered": "outdated"})
        self.assertEqual([f["severity"] for f in fs], ["high", "medium", "low"])
        self.assertEqual([f["category"] for f in fs], ["rule", "bug", "general"])
        a, b, _ = fs
        self.assertEqual((a["path"], a["line"], a["end_line"], a["side"]), ("src/payments/refunds.py", 40, 44, "RIGHT"))
        self.assertEqual((b["path"], b["line"], b["end_line"]), ("src/cache/prices.py", 17, 17))
        self.assertEqual(a["rule"], {"id": "101", "title": "Take the account lock before any ledger write"})
        self.assertEqual(a["qodo_url"], "https://app.qodo.ai/findings/11111111-1111-4111-8111-111111111111")
        self.assertEqual(a["url"], "https://github.com/acme/shop/pull/12#c0")
        self.assertIn("`issue_refund` writes the ledger row", a["body"])
        self.assertIn("**Fix.** Move `ledger.write` inside", a["body"])
        self.assertNotIn("<", a["body"])
        self.assertEqual(b["labels"], ["New"])
        self.assertIn("2 lower-priority findings omitted", pr["qodo"]["omitted"])

    def test_inline_merges_by_uuid_and_resolved_inline_is_dropped(self):
        pr = self.pr({"fx": "review.md"},
                     {"fx": "inline-open.md", "path": "src/payments/refunds.py", "line": 44, "start_line": 41},
                     {"fx": "inline-resolved.md", "path": "src/payments/money.py", "line": 3})
        fs = [f for f in Q.collect(pr, load_config()) if f.get("status", "open") == "open"]
        self.assertEqual(len(fs), 3)
        a = fs[0]
        self.assertEqual((a["category"], a["qodo_aspect"], a["line"], a["end_line"]), ("security", "Security", 41, 44))
        self.assertEqual(a["url"], "https://github.com/acme/shop/pull/12#c1")   # inline comment wins
        self.assertEqual(a["rule"]["id"], "101")                               # summary details kept

    def test_notice_comments_skipped_and_outdated_inline_marked(self):
        pr = self.pr({"fx": "review.md"}, {"fx": "inline-resolved.md", "path": "src/old.py", "line": None})
        pr["_raw_comments"][1]["outdated"] = True
        pr["_raw_comments"].append({"id": 7, "author": "qodo-pentest-1[bot]", "body": "No reviewable changes.",
                                    "url": "u", "path": None, "line": None})
        pr["_raw_comments"][1]["body"] = pr["_raw_comments"][1]["body"].replace("Refund amount uses floats", "Old helper leaks")
        fs = Q.collect(pr, load_config())
        self.assertNotIn("No reviewable changes.", [f["title"] for f in fs])
        old = [f for f in fs if f.get("status") == "outdated" and f.get("path")]
        self.assertEqual([(f["title"], f["path"], f["line"]) for f in old], [("Old helper leaks", "src/old.py", None)])

    def test_linkless_inline_struck_title_and_dismissed_reply(self):
        body = ('<img src="https://img.shields.io/badge/High-CE2C31?style=flat-square" alt="Action required">\n\n'
                '<s>2\\. Edge reads load every result</s> <code>📘 Rule violation</code> <code>➹ Performance</code>\n\n<pre><s>x</s></pre>')
        open_body = body.replace("<s>2\\. Edge reads load every result</s>", "1\\. Ids leak hidden repos").replace("➹ Performance", "⛨ Security")
        raw = [{"id": 1, "author": "qodo-pentest-1[bot]", "path": "a.py", "line": 5, "url": "u1", "body": body},
               {"id": 2, "author": "qodo-pentest-1[bot]", "path": "b.py", "line": 9, "url": "u2", "body": open_body},
               {"id": 3, "author": "shay", "path": "b.py", "line": 9, "url": "u3", "reply_to": 2, "body": "Not changed: onboarding reads all repos."},
               {"id": 4, "author": "qodo-pentest-1[bot]", "path": "b.py", "line": 9, "url": "u4", "reply_to": 2, "body": "Dismissed — intentional."}]
        fs = {f["title"]: f for f in Q.collect({"key": "o/r#1", "_raw_comments": raw}, load_config())}
        self.assertEqual(set(fs), {"Edge reads load every result", "Ids leak hidden repos"})
        self.assertEqual(fs["Edge reads load every result"]["status"], "resolved")
        leak = fs["Ids leak hidden repos"]
        self.assertEqual((leak["severity"], leak["category"], leak["status"], leak["status_why"]), ("high", "security", "dismissed", "Dismissed — intentional."))
        self.assertEqual([r["author"] for r in leak["replies"]], ["shay", "qodo-pentest-1[bot]"])

    def test_struck_title_in_open_group_and_title_merge_without_ids(self):
        review = ('<h3>Code Review by Qodo</h3>\n<img src="https://img.shields.io/badge/Bugs-634FD1?style=flat-square" alt="x">\n'
                  '<details>\n<summary>  1.  Cache key ignores currency <code>🐞 Bug</code></summary>\n<pre>x</pre>\n</details>\n'
                  '<details>\n<summary>  2.  <s>Old bug</s> <code>✓ Resolved</code></summary>\n</details>\n')
        inline = ('<img src="https://img.shields.io/badge/High-634FD1?style=flat-square" alt="Action required">\n\n'
                  '1\\. Cache key ignores currency <code>🐞 Bug</code> <code>≡ Correctness</code>\n\n<pre>x</pre>\n\n'
                  '[View ↗](https://app.qodo.ai/findings/55555555-5555-4555-8555-555555555555)')
        pr = {"key": "o/r#3", "_raw_comments": [
            {"id": 1, "author": "qodo-pentest-2[bot]", "path": None, "line": None, "url": "u1", "body": review},
            {"id": 2, "author": "qodo-pentest-2[bot]", "path": "src/c.py", "line": 4, "url": "u2", "body": inline}]}
        fs = Q.collect(pr, load_config())
        self.assertEqual(sorted((f["title"], f.get("status", "open")) for f in fs),
                         [("Cache key ignores currency", "open"), ("Old bug", "resolved")])   # one, not two
        cache = next(f for f in fs if f["title"].startswith("Cache"))
        self.assertEqual((cache["path"], cache["severity"]), ("src/c.py", "high"))
        rv = Q.parse_review(review)[0]
        self.assertTrue(rv[0].get("severity_guessed"))

    def test_summary_becomes_pr_context(self):
        ctx = Q.pr_context(self.pr({"fx": "summary.md"}), load_config())
        self.assertEqual(ctx["headline"], "Make refunds idempotent")
        self.assertEqual(ctx["labels"], ["Enhancement", "Tests", "10-20 Minutes"])
        self.assertIn("• Add an idempotency key", ctx["description"])
        self.assertTrue(ctx["diagram"]["mermaid"].startswith("sequenceDiagram"))

    def test_legacy_qodo_merge_review_falls_back_to_keywords(self):
        for head in ("## PR Reviewer Guide 🔍", "<h3>PR Code Suggestions ✨</h3>"):
            pr = {"key": "a/b#1", "_raw_comments": [{"id": 5, "author": "qodo-merge-pro[bot]", "path": None, "line": None, "url": None,
                                                      "body": head + "\nSecurity: possible SQL injection in query builder"}]}
            (f,) = Q.collect(pr, load_config())
            self.assertEqual((f["category"], f["severity"]), ("security", "high"))

    def test_comments_without_a_findings_header_are_ignored(self):
        notice = ("> ### \u26a0\ufe0f Important\n> The `/improve` command by Qodo was deprecated on the 1st of November 2026 "
                  "and is no longer available. We recommend switching to the latest Qodo review capabilities. "
                  "[Learn more](https://docs.qodo.ai)")   # PR Agent's tier-2 withdrawal notice
        raw = [{"id": i, "author": "qodo-merge-pro[bot]", "path": None, "line": None, "url": None, "body": body}
               for i, body in enumerate([notice, "Security: possible SQL injection in query builder",
                                         "**Ask** ❓ what does this do?\n\n**Answer:** it validates the refund amount.",
                                         "**Answer:** the ## PR Reviewer Guide 🔍 comment above lists the risks."])]
        self.assertEqual(Q.collect({"key": "a/b#1", "_raw_comments": raw}, load_config()), [])
        inline = {"id": 9, "author": "qodo-merge-pro[bot]", "path": "src/a.py", "line": 3, "url": None,
                  "body": "Possible null dereference when the cart is empty"}   # anchored to a line: still a finding
        (f,) = Q.collect({"key": "a/b#1", "_raw_comments": raw + [inline]}, load_config())
        self.assertEqual((f["path"], f["line"]), ("src/a.py", 3))

    def test_gh_json_joins_paginated_arrays(self):
        from unittest import mock
        with mock.patch("cockpit.util.gh", return_value='[{"id":1}]\n[{"id":2}]'):
            self.assertEqual(gh_json(["api", "x", "--paginate"]), [{"id": 1}, {"id": 2}])
        with mock.patch("cockpit.util.gh", return_value='{"login":"me"}'):
            self.assertEqual(gh_json(["api", "user"]), {"login": "me"})


class SemanticDiffTests(unittest.TestCase):
    DIFF = """diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -1,9 +1,4 @@
 import os
-def helper(x):
-    total = compute(x)
-    return total * 2
-
 def main():
-    return  run( 1 )
+    return run(1)
-    value = load(path, retries=3)
+    value = load(path, retries=5)
diff --git a/b.py b/b.py
--- a/b.py
+++ b/b.py
@@ -1,1 +1,4 @@
 x = 1
+def helper(x):
+    total = compute(x)
+    return total * 2
"""

    def test_indentation_and_string_spaces_are_not_formatting(self):
        from cockpit.semantic import annotate
        diff = """diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -1,4 +1,4 @@
 if x:
-    run()
+run()
-msg = "a  b"
+msg = "a b"
"""
        files = [{"path": p, "hunks": h} for p, h in C.parse_diff(diff).items()]
        annotate(files)
        self.assertFalse(any(len(l) > 4 and l[4].get("ws") for l in files[0]["hunks"][0]["lines"]))

    def test_moves_whitespace_and_token_spans(self):
        from cockpit.semantic import annotate
        files = [{"path": p, "hunks": h} for p, h in C.parse_diff(self.DIFF).items()]
        st = annotate(files)
        a, b = files[0]["hunks"][0]["lines"], files[1]["hunks"][0]["lines"]
        moved = [l for l in a if len(l) > 4 and l[4].get("move")]
        self.assertEqual(len(moved), 3)
        self.assertEqual(moved[0][4]["to"], {"path": "b.py", "line": 2})
        self.assertEqual([l[4]["from"]["path"] for l in b if len(l) > 4 and l[4].get("move")], ["a.py"] * 3)
        ws = [l for l in a if len(l) > 4 and l[4].get("ws")]
        self.assertEqual([l[0] for l in ws], ["-", "+"])
        edit = [l for l in a if len(l) > 4 and l[4].get("spans")]
        self.assertEqual([l[3][slice(*l[4]["spans"][0])] for l in edit], ["3", "5"])
        self.assertEqual((st["moved"], st["whitespace"], st["meaningful"]), (6, 2, 3))


class AttentionTests(unittest.TestCase):
    DIFF = """diff --git a/src/api.py b/src/api.py
--- a/src/api.py
+++ b/src/api.py
@@ -1,2 +1,3 @@
 def get(x):
-    return x
+    check(x)
+    return x
diff --git a/tests/test_api.py b/tests/test_api.py
--- a/tests/test_api.py
+++ b/tests/test_api.py
@@ -1,1 +1,4 @@
 def test_get():
+    assert get(1) == 1
+def test_more():
+    assert get(2) == 2
diff --git a/tests/test_old.py b/tests/test_old.py
--- a/tests/test_old.py
+++ b/tests/test_old.py
@@ -1,3 +1,2 @@
 def test_status():
-    assert status() == 500
+    status()
diff --git a/package-lock.json b/package-lock.json
--- a/package-lock.json
+++ b/package-lock.json
@@ -1,1 +1,1 @@
-{"v": 1}
+{"v": 2}
"""

    def pr(self, **kw):
        from cockpit.semantic import annotate
        files = [{"path": p, "hunks": h, "additions": 0, "deletions": 0} for p, h in C.parse_diff(self.DIFF).items()]
        annotate(files)
        return {"key": "o/r#1", "files": files, "findings": [], "checks": [{"name": "ci", "state": "SUCCESS"}], **kw}

    def tiers(self, att):
        """(tier, reason) per file; deep counts as review here (deep is a subset of what must be read)."""
        out = {}
        for r in att["ranges"]:
            out.setdefault(r["path"], set()).add(("review" if r["tier"] == "deep" else r["tier"], r["reason"]))
        return out

    def test_deep_read_is_the_riskiest_part_within_budget(self):
        from cockpit.attention import compute, DEEP_MIN_LINES
        pr = self.pr(findings=[{"path": "src/api.py", "line": 2, "severity": "high", "status": "open"}])
        att, _ = compute(pr)
        deep = [b for b in att["blocks"] if b["tier"] == "deep"]
        self.assertTrue(deep)
        self.assertEqual(att["must_read"][0], deep[0]["id"])                 # deep comes first
        self.assertIn("open high finding", deep[0]["why"])
        self.assertLessEqual(sum(b["lines"] for b in deep), max(DEEP_MIN_LINES, att["summary"]["total"] // 20))
        att2, _ = compute(self.pr(), overrides=[{"path": "src/api.py", "tier": "deep", "reason": "the core change"}])
        self.assertIn("deep (agent)", next(b for b in att2["blocks"] if b["path"] == "src/api.py")["why"])

    def test_deep_zooms_into_the_signal_and_needs_one(self):
        from cockpit.attention import compute
        from cockpit.enrich import story_anchors
        body = "".join(f"+x{i} = {i}\n" for i in range(1, 401))
        diff = f"diff --git a/src/big.py b/src/big.py\n--- a/src/big.py\n+++ b/src/big.py\n@@ -0,0 +1,400 @@\n{body}"
        files = [{"path": p, "hunks": h} for p, h in C.parse_diff(diff).items()]
        pr = {"key": "o/r#3", "files": files, "findings": [], "checks": []}
        att, _ = compute(pr)
        self.assertEqual(att["summary"]["deep"], 0)                          # plain code: nothing earns a deep read
        pr["findings"] = [{"path": "src/big.py", "line": 300, "severity": "medium", "status": "open"}]
        att, _ = compute(pr)
        deep = [b for b in att["blocks"] if b["tier"] == "deep"]
        self.assertEqual(len(deep), 1)
        self.assertTrue(deep[0]["from"] <= 300 <= deep[0]["to"])             # zoomed around the finding
        self.assertLessEqual(att["summary"]["deep"], 20)                     # 5% of 400
        self.assertEqual(att["summary"]["deep"] + att["summary"]["review"], 400)
        pr["findings"] = []
        anchors = story_anchors(pr, [{"kind": "views", "views": [{"beats": [{"kind": "code", "path": "src/big.py", "from": 50, "to": 55}]}]}])
        att, _ = compute(pr, anchors=anchors)
        deep = [b for b in att["blocks"] if b["tier"] == "deep"]
        self.assertEqual(deep[0]["why"], ["the story points here"])
        self.assertTrue(deep[0]["from"] <= 50 and 55 <= deep[0]["to"])

    def test_overrides_reach_removed_lines(self):
        from cockpit.attention import compute
        att, _ = compute(self.pr(), overrides=[{"path": "src/api.py", "side": "old", "from": 1, "to": 9, "tier": "skip", "reason": "dead helper"}])
        t = {(r["side"], r["tier"]) for r in att["ranges"] if r["path"] == "src/api.py"}
        self.assertIn(("old", "skip"), t)
        self.assertNotIn(("new", "skip"), t)   # a ranged override stays on its side
        pr = self.pr(findings=[{"path": "src/api.py", "line": 2, "severity": "medium", "status": "open"}])
        att, warn = compute(pr, overrides=[{"path": "src/api.py", "tier": "skim", "reason": "x"}])
        at2 = next(r for r in att["ranges"] if r["path"] == "src/api.py" and r["side"] == "new" and r["from"] <= 2 <= r["to"])
        self.assertIn(at2["tier"], ("review", "deep"))   # the finding's line stays on the reading list
        self.assertTrue(any("open finding sits" in w for w in warn))

    def test_rerun_green_is_not_failing(self):
        from cockpit.attention import _ci_passed
        ks = C.latest_checks([{"name": "unit", "conclusion": "FAILURE", "completedAt": "2026-10-01T10:00:00Z"},
                              {"name": "unit", "conclusion": "SUCCESS", "completedAt": "2026-10-01T11:00:00Z"},
                              {"name": "label", "conclusion": "CANCELLED", "completedAt": "2026-10-01T10:00:00Z"}])
        self.assertEqual(len(ks), 2)
        self.assertTrue(_ci_passed({"checks": ks}))

    def test_defaults_and_guards(self):
        from cockpit.attention import compute
        att, warn = compute(self.pr())
        t = self.tiers(att)
        self.assertEqual(t["src/api.py"], {("review", "code"), ("skip", "old side of a rewrite")})   # `return x` is on the new side
        self.assertEqual(t["tests/test_api.py"], {("skip", "tests, additive")})   # CI ran them green
        self.assertEqual(t["tests/test_old.py"], {("review", "test weakened")})   # the assertion was dropped
        self.assertEqual(t["package-lock.json"], {("skip", "generated")})
        ev = next(r["evidence"] for r in att["ranges"] if r["path"] == "tests/test_api.py")
        self.assertIn("1 check(s) ran and passed", ev)
        self.assertIn("assert status() == 500", next(r["evidence"] for r in att["ranges"] if r["path"] == "tests/test_old.py"))
        self.assertEqual(att["summary"]["total"], sum(att["summary"][t] for t in ("deep", "review", "skim", "skip")))

    def test_more_lines_skip_but_deleted_checks_stay(self):
        from cockpit.attention import compute
        diff = """diff --git a/src/svc.py b/src/svc.py
--- a/src/svc.py
+++ b/src/svc.py
@@ -1,6 +1,7 @@
-import os
+import os, sys
+from a import b
 def run(user):
-    if not user.allowed:
-        raise Denied()
-    total = price(user)
+    log("run")
+    total = price(user, sys.argv)
     return total
"""
        files = [{"path": p, "hunks": h} for p, h in C.parse_diff(diff).items()]
        att, _ = compute({"key": "o/r#3", "files": files, "findings": [], "checks": []})
        tier = {(r["side"], n): r["tier"] for r in att["ranges"] for n in range(r["from"], r["to"] + 1)}
        self.assertEqual((tier[("new", 1)], tier[("new", 2)], tier[("old", 1)]), ("skip", "skip", "skip"))   # imports
        self.assertIn(tier[("old", 3)], ("review", "deep"))   # the deleted permission check has no new version
        self.assertIn(tier[("old", 4)], ("review", "deep"))
        self.assertEqual(tier[("old", 5)], "skip")            # `total = price(user)` lives on, rewritten
        self.assertIn(tier[("new", 5)], ("review", "deep"))
        tests = """diff --git a/tests/test_y.py b/tests/test_y.py
--- a/tests/test_y.py
+++ b/tests/test_y.py
@@ -1,1 +1,2 @@
 def test_a():
+    assert a()
"""
        files = [{"path": p, "hunks": h, "role": "test"} for p, h in C.parse_diff(tests).items()]
        pr = {"key": "o/r#4", "files": files, "findings": [], "checks": [{"name": "ci", "state": "SUCCESS"}]}
        self.assertEqual(compute(pr)[0]["ranges"][0]["tier"], "skip")
        self.assertEqual(compute(pr, additive_tests="skim")[0]["ranges"][0]["tier"], "skim")   # the config keeps them on skim
        pr["checks"] = []
        self.assertEqual(compute(pr)[0]["ranges"][0]["tier"], "skim")   # no green CI, no skip
        pr["checks"] = [{"name": "unit", "state": "SKIPPED"}, {"name": "lint", "state": "NEUTRAL"}, {"name": "e2e", "state": "CANCELLED"}]
        self.assertEqual(compute(pr)[0]["ranges"][0]["tier"], "skim")   # nothing actually ran
        code = """diff --git a/src/k.py b/src/k.py
--- a/src/k.py
+++ b/src/k.py
@@ -1,2 +1,6 @@
 def f():
+    return \"\"\"new value\"\"\"
 x = 1
+#if FEATURE
+#define LIMIT 3
+    \"\"\"A docstring.\"\"\"
"""
        files = [{"path": p, "hunks": h} for p, h in C.parse_diff(code).items()]
        tier = {r_n: r["tier"] for r in compute({"key": "o/r#5", "files": files, "findings": [], "checks": []})[0]["ranges"]
                for r_n in range(r["from"], r["to"] + 1)}
        self.assertIn(tier[2], ("review", "deep"))   # a string-valued return is code, triple quotes or not
        self.assertIn(tier[4], ("review", "deep"))   # #if and #define decide what compiles
        self.assertIn(tier[5], ("review", "deep"))

    def test_edited_tests_and_failing_ci_are_read(self):
        from cockpit.attention import compute
        diff = """diff --git a/tests/test_x.py b/tests/test_x.py
--- a/tests/test_x.py
+++ b/tests/test_x.py
@@ -1,2 +1,2 @@
 def test_total():
-    assert total() == 10
+    assert total() == 12
"""
        files = [{"path": p, "hunks": h, "role": "test"} for p, h in C.parse_diff(diff).items()]
        att, _ = compute({"key": "o/r#2", "files": files, "findings": [], "checks": [{"name": "ci", "state": "SUCCESS"}]})
        self.assertEqual({("review" if r["tier"] == "deep" else r["tier"], r["reason"]) for r in att["ranges"]}, {("review", "tests changed")})
        att, _ = compute(self.pr(checks=[{"name": "ci", "state": "FAILURE"}]))
        self.assertEqual(self.tiers(att)["tests/test_api.py"], {("review", "tests, CI failing")})

    def test_high_finding_span_and_left_side(self):
        from cockpit.attention import compute
        pr = self.pr(findings=[{"path": "tests/test_api.py", "line": 1, "end_line": 1, "severity": "high", "status": "open"},
                               {"path": "src/api.py", "line": 2, "side": "LEFT", "severity": "high", "status": "open"}])
        att, _ = compute(pr, overrides=[{"path": "tests/test_api.py", "tier": "skip", "reason": "x"}])
        self.assertEqual(self.tiers(att)["tests/test_api.py"], {("review", "open high finding")})   # padded span reaches the changed lines

    def test_high_finding_and_override_and_preference(self):
        from cockpit.attention import compute
        pr = self.pr(findings=[{"path": "tests/test_api.py", "line": 2, "severity": "high", "status": "open"}])
        att, warn = compute(pr, overrides=[{"path": "src/api.py", "from": 2, "to": 3, "tier": "skim", "reason": "logging only"},
                                           {"path": "tests/test_api.py", "tier": "skip"}])
        t = self.tiers(att)
        self.assertIn(("skim", "logging only"), t["src/api.py"])
        self.assertIn(("review", "open high finding"), t["tests/test_api.py"])   # an override can't hide a high finding
        self.assertTrue(any("needs a reason" in w for w in warn))
        att2, _ = compute(self.pr(), rules=[{"action": "attention", "reason": "tests,-additive".replace(",-", ", "), "tier": "review"}])
        self.assertEqual(self.tiers(att2)["tests/test_api.py"], {("review", "tests, additive")})

    def test_must_read_follows_layers(self):
        from cockpit.attention import compute
        pr = self.pr(layers=[{"id": "t", "ranges": [{"path": "tests/test_old.py", "from": 1, "to": 2}]},
                             {"id": "a", "ranges": [{"path": "src/api.py", "from": 1, "to": 3}]}])
        att, _ = compute(pr)
        first = next(b for b in att["blocks"] if b["id"] == att["must_read"][0])
        self.assertEqual(first["path"], "tests/test_old.py")


    def test_blocks_stop_at_layer_boundaries(self):
        from cockpit.attention import compute
        att, _ = compute(self.pr())
        b = max((b for b in att["blocks"] if b["tier"] in ("review", "deep") and b["side"] == "new"), key=lambda b: b["lines"])
        assert b["lines"] >= 2, b
        mid = b["from"] + 1
        pr = self.pr(layers=[{"id": "x", "ranges": [{"path": b["path"], "from": b["from"], "to": mid - 1}]},
                             {"id": "y", "ranges": [{"path": b["path"], "from": mid, "to": b["to"]}]}])
        att, _ = compute(pr)
        mine = sorted((x["layer"], x["from"], x["to"]) for x in att["blocks"] if x["path"] == b["path"] and x["side"] == "new" and b["from"] <= x["from"] <= b["to"] and not x.get("zoom_of"))
        self.assertEqual([m[0] for m in mine], [0, 1])   # one changed range, two layers: two blocks, two units
        self.assertLess(mine[0][2], mine[1][1])
        att, _ = compute(pr, overrides=[{"path": b["path"], "from": b["from"], "to": b["to"], "tier": "deep", "reason": "the core change"}])
        later = next(x for x in att["blocks"] if x["path"] == b["path"] and x["side"] == "new" and x["layer"] == 1 and not x.get("zoom_of"))
        self.assertIn("deep (agent)", later["why"])   # a signal range cut at the boundary still counts in the later block

class StoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self._sessions = C.SESSIONS
        C.SESSIONS = self.tmp / "sessions"
        cfg = load_config()
        shutil.copytree(ROOT / "fixtures" / "demo-memory", self.tmp / "mem")
        cfg["memory"] = {"amr": str(self.tmp / "mem/amr"), "okf": str(self.tmp / "mem/okf"), "auto_commit": False}
        self.cfg = cfg
        fx = json.loads((ROOT / "fixtures" / "demo-prs.json").read_text())
        _, self.sdir = C.build(fx["prs"], cfg, demo=True, session="st", reviewer_login="x")

    def tearDown(self):
        C.SESSIONS = self._sessions
        shutil.rmtree(self.tmp)

    def data(self):
        return json.loads((self.sdir / "review-data.json").read_text())

    def test_demo_story_enriches_without_warnings(self):
        from cockpit.enrich import enrich
        res = enrich(self.sdir, json.loads((ROOT / "fixtures" / "demo-enrich.json").read_text()))
        self.assertEqual(res["warnings"], [])
        d = self.data()
        self.assertEqual([b["kind"] for b in d["story"]], ["diagram", "flow", "journey", "stories", "callout", "question"])
        self.assertEqual(d["story"][0]["weight"], "lead")
        pr = {p["key"]: p for p in d["prs"]}["qodo-ai/shop-demo#101"]
        self.assertEqual({f["id"]: f.get("stance") for f in pr["findings"]}["q-101-2"], "disagree")

    def test_enrich_keeps_door_when_only_deploy_is_sent(self):
        from cockpit.enrich import enrich
        enrich(self.sdir, {"door": {"verdict": "one-way", "why": "drops a column"}, "deploy": [{"step": "Migrate", "prs": ["qodo-ai/shop-demo#101"]}]})
        enrich(self.sdir, {"deploy": [{"step": "Flip the flag", "prs": []}]})
        d = self.data()
        self.assertEqual(d["door"]["verdict"], "one-way"); self.assertEqual([x["step"] for x in d["deploy"]], ["Flip the flag"])

    def test_enrich_twice_does_not_duplicate_knowledge(self):
        from cockpit.enrich import enrich
        k = {"knowledge": [{"type": "RiskArea", "title": "Stream lag bounds staleness", "body": "b", "paths": ["src/cache/**"],
                            "pr": "qodo-ai/shop-demo#101"}]}
        first = enrich(self.sdir, k)["candidates"]
        self.assertEqual(first, ["risk-areas/stream-lag-bounds-staleness.md"])
        self.assertEqual(enrich(self.sdir, k)["candidates"], [])
        self.assertEqual([c["path"] for c in self.data()["okf"]["candidates"]], first)

    def test_enrich_twice_does_not_duplicate_agent_findings(self):
        from cockpit.enrich import enrich
        k = {"prs": {"qodo-ai/shop-demo#101": {"findings": [{"title": "t", "path": "src/cache/price_cache.py", "line": 20}]}}}
        enrich(self.sdir, k); enrich(self.sdir, k)
        pr = {p["key"]: p for p in self.data()["prs"]}["qodo-ai/shop-demo#101"]
        self.assertEqual(sum(f["source"] == "agent" for f in pr["findings"]), 1)

    def test_brief_and_views_validation(self):
        from cockpit.story import normalize
        prs = {p["key"]: p for p in self.data()["prs"]}
        beats, warn = normalize([
            {"kind": "brief", "title": "t", "lede": "l", "paragraphs": ["w " * 70],
             "contributions": [{"pr": "qodo-ai/shop-demo#101", "adds": "x"}, {"pr": "#5"}]},
            {"kind": "views", "title": "t", "lede": "l", "views": [{"label": "Architecture", "question": "q", "mermaid": "flowchart LR\nA-->B"}]},
            {"kind": "views", "title": "t", "lede": "l", "views": [
                {"label": "Architecture", "question": "q", "mermaid": "flowchart LR\nA-->B"},
                {"label": "Execution", "shape": {"form": "calltree", "text": "a"}}]},
        ], where="session", prs=prs, sdir=self.sdir)
        text = "\n".join(warn)
        self.assertIn("label the brief's paragraphs Why, What and How (missing: Why, What, How)", text)   # the overview's switch
        ok, w2 = normalize([{"kind": "brief", "title": "t", "lede": "l", "paragraphs": [
            {"label": "Why", "text": "a"}, {"label": "What", "text": "b"}, {"label": "How", "text": "c"}]}], where="session", prs=prs, sdir=self.sdir)
        self.assertFalse([x for x in w2 if "Why, What and How" in x])
        for frag in ("paragraph 1 has 70 words", "contribution pr '#5'", "views needs 2-4 lenses",
                     "lens v2 needs a label and the question"):
            self.assertIn(frag, text)
        self.assertEqual([v["id"] for v in beats[2]["views"]], ["v1", "v2"])

    def test_notice_validation(self):
        from cockpit.story import normalize
        prs = {p["key"]: p for p in self.data()["prs"]}
        _, warn = normalize([
            {"id": "n", "kind": "notice", "title": "t", "lede": "l", "items": [
                {"title": "a", "text": "b", "tone": "scary", "beat": "nope"},
                {"title": "x " * 12, "text": "y", "tone": "risk", "beat": "d"}] + [{"title": "c", "text": "d"}] * 2},
            {"id": "d", "kind": "callout", "title": "t", "lede": "l", "text": "x"}], where="session", prs=prs, sdir=self.sdir)
        text = "\n".join(warn)
        for frag in ("notice holds 1-3 items", "tone must be", "unknown beat 'nope'", "item 2 is too long"):
            self.assertIn(frag, text)

    def test_opening_skimmed_code_becomes_attention_rule(self):
        with (self.sdir / "events.jsonl").open("a") as fh:
            for _ in range(3):
                fh.write(json.dumps({"type": "attention_opened", "pr": "qodo-ai/shop-demo#101",
                                     "target": {"kind": "range", "id": "x:r1", "reason": "tests, additive", "tier": "skim"}}) + "\n")
        res = {r["rule"]: r["evidence"] for r in distill(self.sdir, self.cfg)["amr"]}
        self.assertEqual(res.get("attention reason=tests,-additive tier=review"), 3)
        from cockpit.memory import parse_rule
        r = parse_rule("attention reason=tests,-additive tier=review")
        self.assertEqual((r["reason"].replace("-", " "), r["tier"]), ("tests, additive", "review"))

    def test_lens_choice_becomes_preference(self):
        with (self.sdir / "events.jsonl").open("a") as fh:
            for _ in range(2):
                fh.write(json.dumps({"type": "lens", "pr": "session", "target": {"kind": "beat", "id": "session:s2"}, "lens": "Data flow"}) + "\n")
        res = {r["rule"]: r["evidence"] for r in distill(self.sdir, self.cfg)["amr"]}
        self.assertEqual(res.get("prefer-lens name=data-flow"), 2)

    def test_export_is_one_self_contained_file(self):
        from cockpit.enrich import enrich
        from cockpit.export import export
        enrich(self.sdir, json.loads((ROOT / "fixtures" / "demo-enrich.json").read_text()))
        (self.sdir / "media").mkdir()
        (self.sdir / "media" / "101-after.png").write_bytes(b"\x89PNG")
        html = export(self.sdir, style="cockpit").read_text()
        self.assertIn("window.__COCKPIT__ = ", html)
        self.assertNotIn('href="app.css"', html)
        self.assertNotIn('src="app.js"', html)
        self.assertIn("data:image/png;base64,", html)
        payload = html.split("window.__COCKPIT__ = ", 1)[1].split(";</script>", 1)[0]
        self.assertNotIn("</script", payload)
        data = json.loads(payload.replace("<\\/", "</"))
        self.assertEqual(len(data["data"]["prs"]), 3)

    def test_layers_validate_and_report_coverage(self):
        from cockpit.layers import normalize as layers
        pr = {p["key"]: p for p in self.data()["prs"]}["qodo-ai/shop-demo#101"]
        ls, cov, warn = layers([
            {"id": "cache", "title": "The cache applies changes", "summary": "s",
             "ranges": [{"path": "src/cache/price_cache.py", "from": 1, "to": 25}]},
            {"id": "checkout", "title": "Checkout reads through it", "summary": "s", "depends_on": ["cache", "later"],
             "ranges": [{"path": "src/payments/checkout.py", "from": 9, "to": 9}, {"path": "nope.py", "from": 1, "to": 2}]}], pr)
        text = "\n".join(warn)
        self.assertIn("depends_on 'later' is not an earlier layer", text)
        self.assertIn("nope.py is not in the changed files", text)
        self.assertIn("are in no layer: test_price_cache.py (13)", text)
        self.assertEqual([u["path"] for u in cov["uncovered"]], ["tests/test_price_cache.py"])   # deletions inside covered ranges count
        self.assertGreater(cov["covered"], 0)

    def test_ask_agents_have_no_access_of_their_own(self):
        from unittest import mock
        from cockpit import ask as A
        with mock.patch.object(A.shutil, "which", return_value=None), self.assertRaises(A.AskError):
            A.pick("auto")
        with self.assertRaises(A.AskError):
            A.pick("cluade")   # a typo is reported, not treated as auto
        self.assertEqual(A._calls('{"calls": [null, "x", {"tool": "session ls", "args": "{}"}]}'), [{"tool": "session ls", "args": "{}"}])
        self.assertEqual(A._calls('{"calls": "session ls"}'), [])
        seen = []
        def fake(argv, **kw):
            seen.append((argv, kw.get("cwd")))
            if argv[1] == "exec":
                Path(argv[argv.index("-o") + 1]).write_text('{"answer": "ok", "cites": [], "covered": true, "code": [], "calls": []}')
                return mock.Mock(returncode=0, stdout="", stderr="")
            return mock.Mock(returncode=0, stdout='{"result": "{\\"answer\\": \\"ok\\", \\"calls\\": []}"}', stderr="")
        for agent in ("claude", "codex"):
            with mock.patch.object(A, "_CATALOG", {}), mock.patch.object(A.shutil, "which", side_effect=lambda n: f"/bin/{n}"), \
                 mock.patch.object(A.subprocess, "run", side_effect=fake), mock.patch.object(A.subprocess, "Popen", popen_from(fake)):
                A.ask("why?", self.sdir, agent)
        (claude, cwd1), (codex, cwd2) = seen
        self.assertEqual(claude[claude.index("--tools") + 1], "")   # no built-in tools at all
        self.assertIn("--strict-mcp-config", claude)
        for f in ("shell_tool", "apps", "browser_use", "computer_use"):
            self.assertIn(f, codex[codex.index("--disable"):])
        self.assertIn("--ignore-user-config", codex)
        self.assertEqual(codex[codex.index("--sandbox") + 1], "read-only")   # the explicit read-only sandbox, too
        self.assertNotEqual(Path(cwd1).resolve(), self.sdir.resolve())   # they work from an empty folder, not the session

    def test_ask_reads_only_inside_the_session(self):
        from cockpit import ask as A
        (self.sdir / "review-data.json").write_text('{"x": 1}\nsecond line')
        outside = self.sdir.parent / "outside.txt"; outside.write_text("secret")
        cat = {"codebase grep": {"description": "grep", "params": ["path_glob", "pattern", "repo"], "required": ["repo", "pattern"]}}
        rd = lambda tool, args: A.run_read({"tool": tool, "args": args}, cat, self.sdir)
        self.assertIn('1: {"x": 1}', rd("session read", '{"path": "review-data.json"}'))
        for bad in ('{"path": "../outside.txt"}', f'{{"path": "{outside}"}}', '{"path": "/etc/hosts"}'):
            self.assertIn("refused", rd("session read", bad))
        self.assertNotIn("secret", rd("session grep", '{"pattern": "secret"}'))
        (self.sdir / "link.txt").symlink_to(outside)   # a symlink out of the session is never followed
        self.assertNotIn("secret", rd("session grep", '{"pattern": "secret"}'))
        self.assertIn("refused", rd("session read", '{"path": "link.txt"}'))
        self.assertNotIn("link.txt", rd("session ls", "{}"))
        self.assertIn("refused", rd("session grep", '{"pattern": "x", "path": "../outside.txt"}'))   # not "no matches"
        self.assertIn("under 200", rd("session grep", '{"pattern": "' + "a" * 201 + '"}'))
        self.assertIn("isn't a session tool or in Qodo's read catalog", rd("codebase grep; rm -rf /", "{}"))
        self.assertIn("isn't a session tool or in Qodo's read catalog", rd("rules create", "{}"))
        self.assertIn("plain values", rd("codebase grep", '{"repo": "o/r", "pattern": "x", "evil": 1}'))
        self.assertIn("missing pattern", rd("codebase grep", '{"repo": "o/r"}'))
        self.assertIn("args must be a JSON object", A.run_read({"tool": "session ls", "args": 5}, cat, self.sdir))   # not a crash
        from unittest import mock
        with mock.patch.object(A, "qodo_bin", return_value=None):
            self.assertIn("isn't available now", rd("codebase grep", '{"repo": "o/r", "pattern": "x"}'))   # not a TypeError
        for bad in ("[]", "5", '{"result": ["x"]}'):
            with mock.patch.object(A, "_run", return_value=mock.Mock(stdout=bad)), mock.patch.object(A.shutil, "which", return_value="claude"):
                try:
                    self.assertIsInstance(A._turn("claude", "q", self.sdir, 5), str)
                except A.AskError:
                    pass   # a clean error, never an AttributeError
        self.assertIn("1: {", A.run_read({"tool": "session read", "args": {"path": "review-data.json"}}, cat, self.sdir))

    def test_ask_catalog_keeps_only_read_tools(self):
        import json as _j
        from unittest import mock
        from cockpit import ask as A
        tools = [{"group": "codebase", "leaf": "grep", "access": "read", "parameters": {"properties": {"pattern": {}}, "required": ["pattern"]}},
                 {"group": "rules", "leaf": "create", "access": "write", "mutating": True},
                 {"group": "rules", "leaf": "sync", "access": "read", "mutating": True},
                 {"group": "pr", "leaf": "comment", "access": "write"}]
        out = mock.Mock(stdout=_j.dumps({"tools": tools}) + "\ntrace line")
        with mock.patch.object(A, "_CATALOG", None), mock.patch.object(A, "_MISSED", [None]), mock.patch.object(A, "qodo_bin", return_value="qodo"), \
             mock.patch.object(A.subprocess, "run", return_value=out):
            cat = A.catalog()
        self.assertEqual(list(cat), ["codebase grep"])   # mutating or non-read tools never enter the catalog
        for t in ("rules create", "rules sync", "pr comment"):
            self.assertIn("isn't a session tool or in Qodo's read catalog", A.run_read({"tool": t, "args": "{}"}, cat, self.sdir))
        with mock.patch.object(A, "_CATALOG", None), mock.patch.object(A, "_MISSED", [None]), mock.patch.object(A, "qodo_bin", return_value="qodo"):
            with mock.patch.object(A.subprocess, "run", side_effect=OSError):
                self.assertEqual(A.catalog(), {})   # Qodo is down
            with mock.patch.object(A.subprocess, "run", return_value=out), mock.patch.object(A, "RETRY_SECONDS", 0):
                self.assertEqual(list(A.catalog()), ["codebase grep"])   # and the outage isn't cached once it's back

    def test_ask_one_question_at_a_time_and_rounds(self):
        import json as _j
        from unittest import mock
        from cockpit import ask as A
        self.assertTrue(A._ONE.acquire(blocking=False))
        try:
            with mock.patch.object(A.shutil, "which", side_effect=lambda n: f"/bin/{n}"), self.assertRaises(A.Busy):
                A.ask("why?", self.sdir, "codex")
        finally:
            A._ONE.release()
        cat = {"codebase grep": {"description": "grep", "params": ["pattern", "repo"], "required": ["repo", "pattern"]}}
        runs, inputs = [], []
        def fake(argv, **kw):
            runs.append(argv); inputs.append(kw.get("input") or "")
            if argv[1] == "read":
                return mock.Mock(returncode=0, stdout='{"matches": [{"path": "a.py", "line": 3}]}', stderr="")
            first = sum(1 for r in runs if r[1] == "exec") == 1
            Path(argv[argv.index("-o") + 1]).write_text(_j.dumps({"answer": "" if first else "In a.py.", "cites": [], "covered": True, "code": [],
                "calls": [{"tool": "codebase grep", "args": '{"repo": "o/r", "pattern": "x"}'}] if first else []}))
            return mock.Mock(returncode=0, stdout="", stderr="")
        with mock.patch.object(A, "_CATALOG", cat), mock.patch.object(A.shutil, "which", side_effect=lambda n: f"/bin/{n}"), \
             mock.patch.object(A.subprocess, "run", side_effect=fake), mock.patch.object(A.subprocess, "Popen", popen_from(fake)):
            out = A.ask("where?", self.sdir, "codex")
        self.assertEqual([r for r in runs if r[1] == "read"], [["/bin/qodo", "read", "codebase", "grep", "--args", '{"repo": "o/r", "pattern": "x"}', "--json"]])
        self.assertIn('"path": "a.py"', [i for r, i in zip(runs, inputs) if r[1] == "exec"][1])   # the result reached the agent
        self.assertEqual(_j.loads(out["answer"])["answer"], "In a.py.")
        self.assertFalse(A._has_answer('{"answer": "", "calls": [{"tool": "session ls", "args": "{}"}]}'))
        self.assertTrue(A._has_answer('{"answer": "In a.py.", "calls": []}'))
        A._NOW["cancelled"] = True   # a cancel between rounds ends the question and frees the lock
        with mock.patch.object(A, "_CATALOG", cat), mock.patch.object(A.shutil, "which", side_effect=lambda n: f"/bin/{n}"), \
             mock.patch.object(A.subprocess, "Popen", popen_from(fake)):
            orig = A._run
            def cancelling(*a, **k):
                self.assertFalse(A.cancel("someone-else"))   # another page's cancel leaves this question alone
                A.cancel("q1"); return orig(*a, **k)
            with mock.patch.object(A, "_run", side_effect=cancelling), self.assertRaises(A.AskError):
                A.ask("where?", self.sdir, "codex", qid="q1")
        self.assertTrue(A._ONE.acquire(blocking=False)); A._ONE.release()
        with mock.patch.object(A.shutil, "which", return_value="/bin/qodo"), \
             mock.patch.object(A.subprocess, "run", return_value=mock.Mock(returncode=0, stdout='{"tools": [null, 3, {"group": "g"}]}', stderr="")), \
             mock.patch.object(A, "_CATALOG", None):
            self.assertEqual(A.catalog(), {})   # an odd catalog is no catalog, never a crash

    def test_reviewers_from_signals(self):
        from unittest import mock
        from cockpit import reviewers as R
        data = {"reviewer": "me", "prs": [{"key": "o/r#1", "repo": "o/r", "number": 1, "author": "alice", "base": "main", "title": "t",
                                         "files": [{"path": "svc/api/a.py", "additions": 30}, {"path": "svc/api/b.py", "additions": 5}]}]}
        def api(args):
            path = args[1] if args[0] == "api" else args[2]
            if "CODEOWNERS" in path:
                return None
            if path.startswith("repos/o/r/commits?path="):
                return [{"sha": "s1", "author": {"login": "bob"}}, {"sha": "s2", "author": {"login": "alice"}}, {"sha": "s3", "author": {"login": "dependabot[bot]"}}]
            if path.endswith("/pulls") and "/commits/" in path:
                return [{"number": 7, "user": {"login": "frank"}}] if "s1" in path else [{"number": 1}]   # its own PR is skipped
            if path.startswith("repos/o/r/pulls/7/reviews"):
                return [{"user": {"login": "carol"}, "state": "APPROVED"}, {"user": {"login": "carol"}, "state": "APPROVED"},   # twice on one PR: one credit
                        {"user": {"login": "me"}, "state": "APPROVED"}, {"user": {"login": "erin"}, "state": "COMMENTED", "body": ""},
                        {"user": {"login": "frank"}, "state": "COMMENTED", "body": "replying to my own reviewers " * 3},   # #7's author
                        {"user": {"login": "qodo-merge[bot]"}, "state": "COMMENTED", "body": "x" * 100}]
            if path.startswith("repos/o/r/pulls/7/comments"):
                return [{"user": {"login": "erin"}, "body": "this breaks retries"}]   # an inline-only review
            if path == "repos/o/r/pulls/1":
                return {"requested_reviewers": [{"login": "dave"}]}
            return []
        import json as _j
        run = lambda argv, **kw: mock.Mock(returncode=0, stdout=_j.dumps(api(argv[1:])) if api(argv[1:]) is not None else "", stderr="")
        with mock.patch.object(R.subprocess, "run", side_effect=run), mock.patch.object(R.shutil, "which", return_value=None), \
             mock.patch.object(R, "TOP", 5):   # room for the weak ones too
            res = R.suggest(data)
        names = [r["login"] for r in res["suggested"]]
        self.assertEqual(names[0], "carol")   # an approval on a PR touching these paths counts most
        self.assertEqual([r["weak"] for r in res["suggested"]], sorted(r["weak"] for r in res["suggested"]))   # strong evidence ranks first
        self.assertNotIn("me", names); self.assertNotIn("alice", names)   # never the reviewer or the author
        self.assertFalse(any("bot" in n for n in names))
        self.assertNotIn("reviewed 1 recent PR here in depth", next((r["evidence"] for r in res["suggested"] if r["login"] == "frank"), []))   # not for their own PR
        bob = next(r for r in res["suggested"] if r["login"] == "bob")
        self.assertTrue(bob["weak"])   # commits alone are weak evidence
        self.assertIn("approved 1 recent PR on these paths", next(r for r in res["suggested"] if r["login"] == "carol")["evidence"])
        self.assertIn("reviewed 1 recent PR here in depth", next(r for r in res["suggested"] if r["login"] == "erin")["evidence"])
        two = {"prs": data["prs"] + [{**data["prs"][0], "key": f"o/r{k}#1", "repo": f"o/r{k}"} for k in (2, 3)]}
        with mock.patch.object(R.subprocess, "run", side_effect=run), mock.patch.object(R.shutil, "which", return_value=None):
            self.assertLessEqual(R.suggest(two, max_calls=2)["calls"], 2)   # more repos than calls still stays under the limit
        with mock.patch.object(R.subprocess, "run", side_effect=run), mock.patch.object(R.shutil, "which", return_value=None):
            small = R.suggest(data, max_calls=2)
        self.assertLessEqual(small["calls"], 2)   # the call budget holds
        self.assertIn("dave", [r["login"] for r in small["suggested"]])   # the requested reviewer is fetched before history
        pair = {"prs": [data["prs"][0], {**data["prs"][0], "key": "o/r#2", "number": 2, "files": [{"path": "web/ui/x.ts", "additions": 3}]}]}
        with mock.patch.object(R.subprocess, "run", side_effect=run), mock.patch.object(R.shutil, "which", return_value=None):
            got = {r["login"]: r["prs"] for r in R.suggest(pair)["suggested"]}
        self.assertEqual(got["carol"], ["o/r#1"])   # her approval came from svc/api, which only #1 changed
        b0 = R.basis(pair); pair["prs"][1]["files"].append({"path": "web/ui/y.ts"})
        self.assertNotEqual(b0, R.basis(pair))   # a refresh can tell the suggestion is out of date
        failing = lambda argv, **kw: mock.Mock(returncode=1, stdout="", stderr="HTTP 502")
        with mock.patch.object(R.subprocess, "run", side_effect=failing), mock.patch.object(R.shutil, "which", return_value=None):
            self.assertGreater(R.suggest(data)["failed_calls"], 0)   # a failed lookup is counted, not taken for no evidence
        data["reviewer_login"], data["reviewer"] = "carol", "Carol C."   # excluded by login even when the display name differs
        with mock.patch.object(R.subprocess, "run", side_effect=run), mock.patch.object(R.shutil, "which", return_value=None):
            self.assertNotIn("carol", [r["login"] for r in R.suggest(data)["suggested"]])

    def test_reviewers_latest_verdict_and_configured_qodo(self):
        from unittest import mock
        from cockpit import reviewers as R
        b = mock.Mock(); b.api.side_effect = lambda path: [{"user": {"login": "gus"}, "state": "APPROVED"},
                                                           {"user": {"login": "gus"}, "state": "CHANGES_REQUESTED", "body": ""}] if "/reviews" in path else []
        self.assertEqual(R._reviews("o/r", 5, b), {"gus": "reviewed"})   # a later request for changes replaces the approval
        import base64
        co = base64.b64encode(b"docs/ @hal\ndocs/generated/\n").decode()
        b2 = mock.Mock(); b2.api.side_effect = lambda path: {"content": co} if "CODEOWNERS" in path and "ref=release" in path else None
        own = R._owners("o/r", "release", [{"path": "docs/a.md"}, {"path": "docs/generated/b.md"}], b2)
        self.assertEqual(own, {"hal": ["docs/a.md"]})   # a later rule with no owners leaves its files unowned
        self.assertEqual(R._owners("o/r", "main", [{"path": "docs/a.md"}], b2), {})   # each base branch's own CODEOWNERS
        empty = base64.b64encode(b"").decode()
        b3 = mock.Mock(); b3.api.side_effect = lambda path: {"content": empty} if ".github/CODEOWNERS" in path else {"content": co}
        self.assertEqual(R._owners("o/r", "release", [{"path": "docs/a.md"}], b3), {})   # an empty first CODEOWNERS wins, as on GitHub
        one = {"prs": [{"key": "o/r#1", "repo": "o/r", "number": 1, "author": "x", "files": []}]}
        with mock.patch.object(R.subprocess, "run", return_value=mock.Mock(returncode=1, stdout="", stderr="404")), mock.patch.object(R.shutil, "which", return_value=None):
            res = R.suggest(one, {"reviewers": {"priors": {"o/r": ["Ivy", "ivy"]}}})
        self.assertEqual([r["login"] for r in res["suggested"]], ["Ivy"])   # one person, however it's spelled
        with mock.patch.object(R.subprocess, "run", return_value=mock.Mock(returncode=1, stdout="", stderr="404")), mock.patch.object(R.shutil, "which", return_value=None):
            res = R.suggest(one, {"qodo_bot_logins": ["PRAgentSvc"], "reviewers": {"priors": {"o/r": ["pragentsvc", "Ivy"]}}})
        self.assertEqual([r["login"] for r in res["suggested"]], ["Ivy"])   # a service account that publishes reviews is never suggested
        with mock.patch.object(R.subprocess, "run", return_value=mock.Mock(returncode=1, stdout="", stderr="404")), mock.patch.object(R.shutil, "which", return_value=None):
            res = R.suggest(one, {"reviewers": {"exclude": "pragentsvc", "priors": {"o/r": ["pragentsvc", "Ivy"]}}})
        self.assertEqual([r["login"] for r in res["suggested"]], ["Ivy"])   # one exclusion as a string works too
        with mock.patch.object(R.subprocess, "run", return_value=mock.Mock(returncode=1, stdout="", stderr="404")), mock.patch.object(R.shutil, "which", return_value=None):
            self.assertEqual([r["login"] for r in R.suggest(one, {"reviewers": {"priors": {"o/r": "ivy"}}})["suggested"]], ["ivy"])   # a string is one login, not letters
        why = {}
        with mock.patch.object(R.subprocess, "run", return_value=mock.Mock(stdout='{"results": {"bad": 1}}')):
            self.assertEqual(R._similar("o/r", "t", R.Budget(5), why, "qodo"), []); self.assertIn("o/r", why)   # a bad shape is a missing signal
        with mock.patch.object(R.shutil, "which", side_effect=lambda c: "/opt/q/bin/qodo-cli" if c == "qodo-cli" else None):
            self.assertEqual(R.qodo_cmd({"qodo_findings": {"command": "qodo-cli"}}), "/opt/q/bin/qodo-cli")   # the configured name, not just qodo
            self.assertIsNone(R.qodo_cmd({}))

    def test_reviewers_codeowners_matching(self):
        from cockpit.reviewers import _owns
        for pat, path, want in [("docs/*", "docs/a.md", True), ("docs/*", "docs/build-app/troubleshooting.md", False),
                                ("/docs/", "docs/x/y.md", True), ("apps/", "src/apps/a.js", True), ("*.js", "a/b/c.js", True),
                                ("/build/logs/", "x/build/logs/a", False), ("**/logs", "x/y/logs/a", True), ("src/*.py", "src/x/a.py", False)]:
            self.assertEqual(_owns(pat, path), want, (pat, path))   # GitHub's rules, not fnmatch's

    def test_rollback_sensitive_files_and_plan(self):
        from cockpit.rollback import check, normalize, sensitive, uncovered
        prs = [{"key": "o/r#1", "files": [{"path": "infra/main.tf"}, {"path": "db/migrations/0042_add.py"}, {"path": "Dockerfile"},
                                          {"path": "cookbooks/web/recipes/default.rb"}, {"path": "site/app.pp"}, {"path": ".github/workflows/ci.yml"},
                                          {"path": "src/app.py"}, {"path": "README.md"}]}]
        self.assertEqual([f["path"] for f in sensitive([{"key": "k", "files": [{"path": "config.json"}, {"path": "package.json"}]}])], ["config.json"])
        self.assertEqual(len(sensitive([{"key": "k", "files": [{"path": "infra/main.tf.json"}, {"path": "prod.tfvars.json"}]}])), 2)   # Terraform's JSON forms
        self.assertEqual([f["kind"] for f in sensitive([{"key": "k", "files": [{"path": "azure-pipelines.yml"}, {"path": "ci/azure-pipelines-release.yaml"}, {"path": "bitbucket-pipelines.yml"}]}])], ["pipeline"] * 3)
        self.assertIn("no rollback plan", check(None, sensitive([{"key": "k", "files": [{"path": "config.json"}]}]), "low")[0])   # a root config counts
        from cockpit.rollback import covers
        self.assertFalse(covers("config/*.yaml", "config/prod/secrets.yaml"))   # * stays in one directory
        self.assertTrue(covers("config/**", "config/prod/secrets.yaml")); self.assertTrue(covers("infra/", "infra/a/b.tf"))
        self.assertIn("needs verify", " ".join(normalize({"steps": [{"text": "Revert"}]}, set())[1]))   # no way to tell it worked
        bad, w2 = normalize({"steps": [{"text": ["revert"], "covers": ["infra/*.tf"]}]}, set())
        self.assertEqual(bad["steps"], []); self.assertIn("needs text", w2[0])   # a list isn't an instruction, so it can't cover anything
        self.assertIn("needs what", " ".join(normalize({"steps": [{"text": "x"}], "one_way": [{"why": "lost"}]}, set())[1]))   # dropped, but said
        files = sensitive(prs)
        self.assertEqual([f["kind"] for f in files], ["terraform", "migration", "docker", "chef", "puppet", "pipeline"])   # not app code or docs
        self.assertIn("no rollback plan", check(None, files, "low")[0])
        self.assertIn("High and there's no rollback plan", check(None, [], "high")[0])
        self.assertEqual(check(None, [], "medium"), [])
        plan, w = normalize({"steps": [{"text": "Revert", "prs": ["o/r#1", "o/r#9"], "covers": ["infra/*.tf", "db/migrations/*"]}, {"nope": 1}],
                             "one_way": [{"what": "rewritten rows", "why": "no backup"}]}, {"o/r#1"})
        self.assertEqual(plan["steps"][0]["prs"], ["o/r#1"])
        self.assertTrue(any("unknown prs" in x for x in w) and any("needs text" in x for x in w))
        self.assertEqual([f["path"] for f in uncovered(plan, files)], ["Dockerfile", "cookbooks/web/recipes/default.rb", "site/app.pp", ".github/workflows/ci.yml"])
        self.assertIn("doesn't cover 4", check(plan, files, "high")[0])
        self.assertIn("needs steps", normalize({"before": [{"text": "backup"}]}, set())[1][0])
        prep = normalize({"before": [{"text": "back up", "covers": ["infra/*.tf"]}], "steps": [{"text": "revert"}]}, set())[0]
        self.assertIn("infra/main.tf", [f["path"] for f in uncovered(prep, files)])   # preparing isn't undoing
        odd, w = normalize({"steps": [{"text": "x", "prs": 12, "covers": "a"}], "one_way": "nope"}, set())   # never a crash
        self.assertEqual(odd["steps"][0]["prs"], []); self.assertTrue(any("are lists" in x for x in w))
        many = [{"key": "o/r#2", "files": [{"path": f"db/migrations/{i}.sql"} for i in range(80)]}]
        self.assertEqual(len(sensitive(many)), 80)   # every file is checked, not the first 60
        self.assertEqual(sensitive([{"key": "k", "files": [{"path": "clusters/saas/prod/qodo-apps-values.yaml"}]}])[0]["kind"], "deploy")

    def test_mermaid_semicolon_in_a_label_is_caught(self):
        from cockpit.story import mermaid_traps
        self.assertTrue(mermaid_traps("sequenceDiagram\n  A->>B: publish comments; approval disabled"))
        self.assertTrue(mermaid_traps("flowchart LR\n  A[read; then write]-->B"))
        self.assertTrue(mermaid_traps("flowchart LR\n  A-->|yes; no|B"))
        self.assertEqual(mermaid_traps('flowchart LR\n  A-->B;\n  B["x; y"]-->C'), [])   # a trailing ';' and quoted labels are fine
        self.assertEqual(mermaid_traps("graph LR; A-->B; B-->C"), [])   # ';' between statements
        self.assertEqual(mermaid_traps("flowchart LR\n  A[one #59; two]-->B"), [])   # Mermaid's own entity code
        self.assertEqual(mermaid_traps(["not", "text"]), [])   # malformed input warns elsewhere, never crashes here

    def test_plain_layer_keeps_ordinary_words(self):
        from cockpit.story import refs_in, missing_flow
        self.assertEqual(refs_in("Bytes are UTF-8 and hashed with SHA-256 in Node.js", {"o/api", "api"}), [])
        self.assertEqual(refs_in("the api answers", {"o/api", "api"}), [])   # a repo named like a word
        self.assertEqual(refs_in("it breaks in Auth.js", set()), ["Auth.js"])   # only known products are exempt
        self.assertEqual(refs_in("see shared-gateway and PLA-74", {"example-org/shared-gateway", "shared-gateway"}), ["PLA-74", "shared-gateway"])
        self.assertTrue(missing_flow([]))   # an empty story hasn't decided either

    def test_risk_edges_from_review(self):
        from cockpit.risk import assess, normalize_factors
        f, w = normalize_factors({"radius": {"level": "large", "why": "w", "ev": [{"path": ["a.py"]}, {"path": "a.py"}]},
                                  "damage": {"level": "low", "why": "w"}, "complexity": {"level": "low", "why": "w"}}, {"a.py"})
        self.assertEqual(f["radius"]["ev"], [{"path": "a.py"}])   # a list-valued path is dropped with a warning, not a crash
        self.assertTrue(any("without a text path" in x for x in w))
        fx = lambda r, d, c: {"radius": {"level": r, "why": "w"}, "damage": {"level": d, "why": "w"}, "complexity": {"level": c, "why": "w"}}
        low = {"component": "small", "factors": fx("small", "low", "low")}
        part = {"component": "part", "factors": {k: v for k, v in fx("medium", "medium", "low").items() if k != "complexity"}}
        r = assess({"impact": [low, part], "prs": []})
        self.assertEqual(r["level"], "unknown")
        self.assertEqual(r["range"], ["medium", "high"])   # the partly known scenario is at least Medium
        self.assertEqual(r["deciding"], 1)   # the scenario that could be worst decides, not the known Low one
        known = {"impact": [{"component": "x", "factors": fx("small", "low", "low")}]}
        cases = [({"qodo_source": None}, True), ({"qodo_source": "cli", "qodo_review": {"status": "started", "commit": "h"}, "head_sha": "h"}, True),
                 ({"qodo_source": "cli", "qodo_review": {"status": "completed", "commit": "old"}, "head_sha": "h"}, True),
                 ({"qodo_source": "cli", "qodo_review": {"status": "completed", "commit": "h"}, "head_sha": "h"}, False)]
        for pr, blocked in cases:
            a = assess({**known, "prs": [{"key": "o/r#1", "findings": [], **pr}]})["approval"]
            self.assertEqual(a["result"] == "human review", blocked, pr)

    def test_flow_beat_needs_what_each_hop_carries(self):
        from cockpit.story import normalize
        prs = {p["key"]: p for p in self.data()["prs"]}
        hop = {"from": "A", "to": "B", "call": "POST /x", "carries": "`id`, `change`", "prs": ["qodo-ai/shop-demo#101"]}
        ok, warn = normalize([{"kind": "flow", "title": "How it works", "lede": "l", "answers": [{"q": "What replaces clone?", "a": "Reads on demand."}],
                               "hops": [hop, hop, hop]}], where="session", prs=prs, sdir=self.sdir)
        self.assertEqual([b["kind"] for b in ok], ["flow"])
        self.assertEqual(warn, [])
        _, warn = normalize([{"kind": "flow", "title": "t", "lede": "l", "answers": [{"q": "q"}] * 4,
                              "hops": [{"from": "A", "to": "B", "prs": ["#9"]}]}], where="session", prs=prs, sdir=self.sdir)
        text = "\n".join(warn)
        for frag in ("3-14 hops", "hop 1 needs from, to and carries", "hop 1 has bad PR keys ['#9']", "at most 3 answers", "answer 1 needs q and a"):
            self.assertIn(frag, text)
        deep = {"kind": "flow", "title": "t", "lede": "l", "hops": [hop] * 3,
                "differs": {"usual": "a Git host", "this": "Perforce", "rows": [{"aspect": "Code", "usual": "a clone", "this": "served"}, {"aspect": "Diff", "usual": "API", "this": "p4"}]},
                "decisions": [{"decision": "Serve remotely", "instead": "a checkout", "why": "no Git to fall back to"}, {"decision": "No fallback", "why": "a failure stays one"}],
                "contracts": [{"contract": "Shared adapter", "change": "diff caps", "affects": "all", "prs": ["qodo-ai/shop-demo#101"]}]}
        _, warn = normalize([deep], where="session", prs=prs, sdir=self.sdir)
        self.assertEqual(warn, [])
        bad = dict(deep, differs={"usual": "x", "rows": [{"aspect": "a"}]}, decisions=[{"decision": "d"}] * 5, contracts=[{"contract": "c", "prs": ["#9"]}])
        _, warn = normalize([bad], where="session", prs=prs, sdir=self.sdir)
        text = "\n".join(warn)
        for frag in ("differs needs usual, this and 2-8 rows", "differs row 1 needs aspect, usual and this", "2-4 key decisions",
                     "decision 1 needs decision and why", "contract 1 needs contract, change and affects", "contract 1 has bad PR keys ['#9']"):
            self.assertIn(frag, text)
        skipped, warn = normalize([{"kind": "flow", "skip": "a copy edit: nothing moves across parts"}], where="session", prs=prs, sdir=self.sdir)
        self.assertEqual(warn, [])   # a visible decision, not a missing beat
        self.assertEqual(skipped[0]["skip"], "a copy edit: nothing moves across parts")
        from cockpit.story import missing_flow
        self.assertEqual(missing_flow(skipped), [])
        self.assertIn("no flow beat", missing_flow([{"kind": "brief"}])[0])
        _, warn = normalize([{"kind": "flow", "title": "t", "lede": "l", "answers": [{"q": "q", "a": "It sits behind #5343 in src/a/b.py."}], "hops": [hop] * 3}],
                            where="session", prs=prs, sdir=self.sdir)
        self.assertIn("answer 1 mixes in references (#5343, src/a/b.py", "\n".join(warn))

    def test_normalize_warns_and_drops(self):
        from cockpit.story import normalize
        prs = {p["key"]: p for p in self.data()["prs"]}
        k = "qodo-ai/shop-demo#101"
        beats, warn = normalize([
            {"kind": "poem", "title": "x", "lede": "y"},
            {"kind": "code", "title": "t", "lede": "l", "path": "nope.py", "from": 3, "to": 1},
            {"kind": "media", "title": "t", "lede": "l", "src": "../../etc/passwd"},
            {"kind": "media", "title": "t", "lede": "l", "src": "101-after.png"},
            {"kind": "journey", "title": "t", "lede": "l", "steps": [{"text": "a", "prs": ["o/r#9", "#9"], "status": "meh"}]},
            {"kind": "shape", "title": "t", "lede": "l", "form": "tree", "diff": True, "text": "+a\nb\n c",
             "notes": [{"line": 9, "text": "x"}]},
            {"kind": "code", "title": "t", "lede": "l", "path": "src/cache/price_cache.py", "from": 1, "to": 30},
            {"kind": "diagram", "title": "t", "lede": " ".join(["w"] * 40), "mermaid": "flowchart LR\n A-->B",
             "refs": [{"path": "src/cache/price_cache.py", "line": 3}, {"finding": "nope"}]},
        ], where=k, prs=prs, sdir=self.sdir)
        self.assertEqual([b["kind"] for b in beats], ["code", "media", "media", "journey", "shape", "code", "diagram"])
        self.assertEqual(beats[0]["weight"], "lead")
        text = "\n".join(warn)
        for frag in ("unknown kind 'poem'", "code path nope.py", "integer from <= to", "inside the session's media/",
                     "media/101-after.png does not exist", "bad PR keys ['#9']", "journey status",
                     "lede has 40 words", "ref finding nope", "shape form should be one of",
                     "every line starts with '+', '-' or ' '", "note line 9 is outside the shape", "code excerpt has 30 lines"):
            self.assertIn(frag, text)
        (self.sdir / "media").mkdir()
        (self.sdir / "media" / "101-after.png").write_bytes(b"png")
        beats, warn = normalize([{"kind": "media", "title": "t", "lede": "l", "src": "101-after.png"}], where=k, prs=prs, sdir=self.sdir)
        self.assertEqual((warn, beats[0]["type"]), ([], "image"))

    def test_beat_marks_and_reading_become_story_preferences(self):
        d = self.data()
        d["prs"][0]["story"] = [{"id": f"b{i}", "kind": "callout"} for i in range(5)]
        (self.sdir / "review-data.json").write_text(json.dumps(d))
        t = lambda kind, form, i: {"kind": "beat", "id": f"{d['prs'][0]['key']}:b{i}", "beat_kind": kind, "form": form}
        evs = [{"type": "mark", "pr": d["prs"][0]["key"], "emoji": "👍", "target": t("diagram", "sequenceDiagram", 1)},
               {"type": "mark", "pr": d["prs"][0]["key"], "emoji": "👎", "target": t("table", "", 2)},
               {"type": "beat_seen", "pr": d["prs"][0]["key"], "target": {"kind": "beat", "id": "x:b0"}}]
        with (self.sdir / "events.jsonl").open("a") as fh:
            fh.writelines(json.dumps(e) + "\n" for e in evs)
        rules = {r["rule"] for r in distill(self.sdir, self.cfg)["amr"]}
        self.assertIn("prefer-beat kind=diagram form=sequenceDiagram", rules)
        self.assertIn("avoid-beat kind=table", rules)
        self.assertIn("story-length max=3", rules)
        self.assertIn("[[preferences/story]]", (self.tmp / "mem/amr/MEMORY.md").read_text())

    def test_media_route_serves_only_session_media(self):
        import threading, urllib.request, urllib.error
        from http.server import ThreadingHTTPServer
        from cockpit.server import Handler
        (self.sdir / "media").mkdir()
        (self.sdir / "media" / "a.png").write_bytes(b"\x89PNG")
        Handler.sdir, Handler.cfg = self.sdir, {**self.cfg, "emoji": EMOJI}
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{httpd.server_address[1]}/media/"
        try:
            with urllib.request.urlopen(base + "a.png") as r:
                self.assertEqual((r.status, r.headers["Content-Type"], r.read()), (200, "image/png", b"\x89PNG"))
            for bad in ("..%2Freview-data.json", "%2E%2E/review-data.json", "nope.png"):
                with self.assertRaises(urllib.error.HTTPError):
                    urllib.request.urlopen(base + bad)
        finally:
            httpd.shutdown(); httpd.server_close()


class ContextTests(unittest.TestCase):
    def pr(self, n, head, base, body="", title="t"):
        return {"key": f"o/r#{n}", "repo": "o/r", "number": n, "head": head, "base": base, "body": body,
                "title": title, "url": f"https://github.com/o/r/pull/{n}", "files": []}

    def test_branching_stack_gives_one_path_per_leaf(self):
        prs = [self.pr(1, "a", "main"), self.pr(2, "b", "a"), self.pr(3, "c", "b"), self.pr(4, "d", "b"), self.pr(5, "x", "main")]
        self.assertEqual(C.stacks(prs), [["o/r#1", "o/r#2", "o/r#3"], ["o/r#1", "o/r#2", "o/r#4"]])

    def test_every_file_past_100_and_patches_when_the_diff_is_refused(self):
        from unittest import mock
        files = [{"filename": f"f{i}.py", "additions": 1, "deletions": 0, "patch": "@@ -0,0 +1 @@\n+x = %d" % i} for i in range(105)]
        def gh_json(args):
            if args[:2] == ["pr", "view"]:
                return {"number": 9, "title": "t", "url": "u", "files": [{"path": f["filename"]} for f in files[:100]]}
            if args[0] == "api" and "/files" in args[1]:
                return files
            return []
        def gh(args):
            raise RuntimeError("diff too large")   # GitHub refuses the whole diff
        with mock.patch.object(C, "gh_json", side_effect=gh_json), mock.patch.object(C, "gh", side_effect=gh), \
             mock.patch.object(C, "prior_bases", return_value=[]):
            p = C.fetch_pr("o/r", 9)
        self.assertEqual(len(p["files"]), 105)   # gh pr view lists 100
        self.assertEqual(p["files"][104]["hunks"][0]["lines"], [["+", None, 1, "x = 104"]])   # from the file's own patch
        # an added "++ x" and a removed "-- y" inside a hunk are lines, not file headers
        h = C.parse_diff("diff --git a/a.c b/a.c\n--- a/a.c\n+++ b/a.c\n@@ -1,1 +1,1 @@\n--- y\n+++ x\n")["a.c"][0]["lines"]
        self.assertEqual(h, [["-", 1, None, "-- y"], ["+", None, 1, "++ x"]])
        # the file list fails: the whole diff still names every file
        diff = "".join(f"diff --git a/g{i}.py b/g{i}.py\n--- a/g{i}.py\n+++ b/g{i}.py\n@@ -0,0 +1 @@\n+y\n" for i in range(105))
        def gh_json2(args):
            if args[:2] == ["pr", "view"]:
                return {"number": 9, "title": "t", "url": "u", "changedFiles": 105, "files": [{"path": f"g{i}.py"} for i in range(100)]}
            if args[0] == "api" and "/files" in args[1]:
                raise RuntimeError("rate limited")
            return []
        with mock.patch.object(C, "gh_json", side_effect=gh_json2), mock.patch.object(C, "gh", return_value=diff), \
             mock.patch.object(C, "prior_bases", return_value=[]):
            p = C.fetch_pr("o/r", 9)
        self.assertEqual((len(p["files"]), p.get("files_missing")), (105, None))
        # everything gave out (GitHub's 3000-file cap): the PR says how many are missing
        def gh_json3(args):
            return {"number": 9, "title": "t", "url": "u", "changedFiles": 3005, "files": []} if args[:2] == ["pr", "view"] else files if "/files" in str(args) else []
        with mock.patch.object(C, "gh_json", side_effect=gh_json3), mock.patch.object(C, "gh", side_effect=gh), \
             mock.patch.object(C, "prior_bases", return_value=[]):
            p = C.fetch_pr("o/r", 9)
        self.assertEqual(p["files_missing"], 3005 - 105)

    def test_retargeted_pr_keeps_its_place_in_the_stack(self):
        prs = [self.pr(5, "scanner-bots", "main"), dict(self.pr(6, "more-bots", "main"), prior_bases=["scanner-bots"]), self.pr(7, "look", "main")]
        self.assertEqual(C.stacks(prs), [["o/r#5", "o/r#6"]])   # #6 moved to main when #5 merged

    def test_same_number_mentions_in_two_repos_stay_apart(self):
        a = self.pr(1, "a", "main", "Depends on gateway #813")
        b = dict(self.pr(2, "b", "main", "Follows #813"), repo="o/other", key="o/other#2")
        refs = sorted(m["same_repo_guess"] for m in C.context([a, b])["mentions"])
        self.assertEqual(refs, ["o/other#813", "o/r#813"])

    def test_stacks_links_tickets_and_missing_members(self):
        a = self.pr(1, "feat-a", "main", "Part of https://linear.app/x/issue/PLT-12/foo and spec https://www.notion.so/Spec-1.\n"
                                          "![b](https://img.shields.io/badge/x) see https://github.com/o/r/pull/1")
        b = self.pr(2, "feat-b", "feat-a", "Follows PLT-12. Design: https://www.figma.com/file/abc", title="PLT-13 approvals")
        ctx = C.context([b, a], {"o/r": [{"number": 3, "headRefName": "feat-c", "baseRefName": "feat-b", "url": "u3", "title": "c"},
                                         {"number": 4, "headRefName": "x", "baseRefName": "main", "url": "u4", "title": "d"}]})
        self.assertEqual(ctx["stacks"], [["o/r#1", "o/r#2"]])
        self.assertEqual({s["url"]: s["kind"] for s in ctx["sources"]},
                         {"https://linear.app/x/issue/PLT-12/foo": "ticket", "https://www.notion.so/Spec-1": "doc",
                          "https://www.figma.com/file/abc": "design"})
        self.assertEqual({t["key"]: sorted(t["prs"]) for t in ctx["tickets"]}, {"PLT-12": ["o/r#1", "o/r#2"], "PLT-13": ["o/r#2"]})
        self.assertEqual([m["key"] for m in ctx["missing_stack"]], ["o/r#3"])


class StyleTests(unittest.TestCase):
    """Review styles: the behavior diff check, the view, rendering, export and the server routes."""
    P1, P2 = "qodo-ai/shop-demo#101", "qodo-ai/shop-demo#102"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self._sessions = C.SESSIONS
        C.SESSIONS = self.tmp / "sessions"
        cfg = load_config()
        shutil.copytree(ROOT / "fixtures" / "demo-memory", self.tmp / "mem")
        cfg["memory"] = {"amr": str(self.tmp / "mem/amr"), "okf": str(self.tmp / "mem/okf"), "auto_commit": False}
        fx = json.loads((ROOT / "fixtures" / "demo-prs.json").read_text())
        _, self.sdir = C.build(fx["prs"], cfg, demo=True, session="sty", reviewer_login="x")
        from cockpit.enrich import enrich
        self.demo = json.loads((ROOT / "fixtures" / "demo-enrich.json").read_text())
        self.res = enrich(self.sdir, self.demo)

    def tearDown(self):
        C.SESSIONS = self._sessions
        shutil.rmtree(self.tmp)

    def data(self):
        return json.loads((self.sdir / "review-data.json").read_text())

    def test_every_style_page_parses(self):
        """A stray // or a broken template literal leaves a page blank; node catches it before a reader does."""
        import re, subprocess
        node = shutil.which("node")
        if not node:
            self.skipTest("node not installed")
        from cockpit.styles import names, render
        for st in names():
            if st == "cockpit":
                continue
            html = render(st, self.sdir)
            for j, code in enumerate(re.findall(r"<script>(.*?)</script>", html, re.S)):   # inline code, not the JSON data blocks
                f = Path(tempfile.mkdtemp()) / f"{st}-{j}.js"
                f.write_text(code)
                r = subprocess.run([node, "--check", str(f)], capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, f"{st} script {j}: {r.stderr[:400]}")

    def test_package_walkthrough_pages_need_their_files(self):
        """Execution walkthrough and Finding review appear only when the session holds builder.json or triage/."""
        from cockpit.styles import render
        from cockpit.walkthrough import check_files
        self.assertNotIn('id="wt-data"', render("package", self.sdir))
        self.assertNotIn("{{WALKTHROUGH}}", render("package", self.sdir))
        (self.sdir / "builder.json").write_text(json.dumps({"files": [{"pr": self.P1, "path": "src/cache/price_cache.py", "purpose": "Caches prices.", "methods": []}], "flows": []}))
        (self.sdir / "triage").mkdir()
        (self.sdir / "triage" / "findings-101.json").write_text(json.dumps({"review_session": {}, "findings": [{"id": "a", "attribution_status": "implemented"}]}))
        html = render("package", self.sdir)
        self.assertIn('id="wt-data"', html)
        self.assertIn("BLOCKS.builder = ", html)
        b, tri, warn = check_files(self.sdir, self.data())
        self.assertEqual(b["files"][0]["uid"], "bwf-qodo-ai-shop-demo-101-src-cache-price-cache-py")
        self.assertEqual(tri[0]["counts"]["open"], 0)
        self.assertIn("no flows: Flow mode will be empty", warn)
        (self.sdir / "builder.json").write_text(json.dumps({"files": "nope"}))
        self.assertTrue(any("needs `files`" in w for w in check_files(self.sdir, self.data())[2]))

    def line(self, **kw):
        return {"files": [{"pr": self.P1, "path": "src/cache/price_cache.py", "headline": "h",
                           "hunks": [{"title": "t", "lines": [{"k": "+", "kind": "behavior", "text": "x", **kw}]}]}]}

    def test_demo_behavior_checks_clean_and_is_stored(self):
        from cockpit.behavior import check
        self.assertEqual(self.res["warnings"], [])
        bh, errs, warns = check(self.data()["behavior"], self.data())
        self.assertEqual((errs, warns), ([], []))
        cv = bh["coverage"]
        self.assertGreater(cv["cited"], 0.6 * cv["important_lines"])

    def test_behavior_lines_must_cite_changed_lines(self):
        from cockpit.behavior import check
        d = self.data()
        _, errs, _ = check(self.line(), d)
        self.assertIn("needs ev", errs[0])
        _, errs, _ = check(self.line(ev=[{"side": "new", "from": 3, "to": 4}]), d)   # lines 3-4 are unchanged context
        self.assertIn("touches no changed line", errs[0])
        _, errs, _ = check(self.line(ev=[{"side": "old", "from": 9, "to": 12}], finding="nope"), d)
        self.assertEqual(errs, ["behavior src/cache/price_cache.py hunk 0 line 0: unknown finding nope"])
        _, errs, _ = check({"files": [{"pr": self.P1, "path": "src/payments/discounts.py", "hunks": []}]}, d)
        self.assertIn("is not changed in", errs[0])
        _, errs, _ = check(self.line(ev=[{"side": "right", "from": 9, "to": 12}]), d)
        self.assertIn("side must be new or old", errs[0])

    def test_enrich_reports_behavior_errors_as_warnings(self):
        from cockpit.enrich import enrich
        res = enrich(self.sdir, {"behavior": self.line(ev=[{"side": "new", "from": 3, "to": 3}])})
        self.assertTrue(any("touches no changed line" in w for w in res["warnings"]))
        self.assertTrue(any("cites" in w and "read-tier" in w for w in res["warnings"]))
        self.assertTrue(any("behavior not saved" in w for w in res["warnings"]))
        self.assertEqual(self.data()["behavior"], self.demo["behavior"])   # the last valid sketch stays

    def test_media_drops_non_http_links(self):
        from cockpit.view import _media
        d = {"story": [{"kind": "media", "src": s, "title": s} for s in
                       ("javascript:alert(1)", "data:text/html,x", 'https://x.test/a.png" onerror="x')], "prs": []}
        self.assertEqual([m["src"] for m in _media(d, self.sdir, False)], ['https://x.test/a.png" onerror="x'])   # pages esc() it

    def test_view_resolves_evidence_and_gaps(self):
        from cockpit.view import view_data
        v = view_data(self.sdir)
        f = next(x for x in v["behavior"]["files"] if x["path"] == "src/cache/price_cache.py")
        ev = f["hunks"][0]["lines"][1]["ev"][0]
        self.assertIn(["+", None, 23, "        cents = fetch_price(sku)"], ev["lines"])
        cov = {(c["pr"], c["path"]): c for c in v["behavior"]["coverage"]["files"]}
        self.assertTrue(cov[(self.P1, "src/cache/price_cache.py")]["gaps"])   # uncited lines are listed
        self.assertEqual([p["key"] for p in v["prs"]], [self.P1, self.P2, "qodo-ai/shop-demo#103"])
        self.assertTrue(all(p["code"] for p in v["prs"][:2]))

    def test_test_names_cover_each_and_count_past_the_cap(self):
        from cockpit import view as V
        lines = [["+", None, i + 1, f"def test_{i}():"] for i in range(45)] + [["+", None, 50, "it.each(cases)('handles %s', (c) => {"],
                                                                             ["+", None, 51, "test.concurrent('runs alone', async () => {"]]
        p = {"files": [{"path": "tests/test_big.py", "role": "test", "hunks": [{"lines": lines}]}]}
        ts = V._tests(p)
        self.assertEqual(len(ts), 47)
        self.assertIn("handles %s", [t["name"] for t in ts])
        self.assertIn("runs alone", [t["name"] for t in ts])
        self.assertEqual(V._test_counts(ts), {"tests/test_big.py": 47})   # the view caps names, not the count

    def test_view_names_added_test_cases_and_missing_files(self):
        from cockpit.view import _pr_view
        p = {"key": "o/r#1", "repo": "o/r", "number": 1, "title": "t", "files_missing": 2, "files": [
            {"path": "tests/test_a.py", "role": "test", "hunks": [{"lines": [["+", None, 3, "def test_one_thing():"], [" ", 4, 4, "def test_old():"],
                                                                         ["+", None, 9, "    async def test_two(x):", {"spans": []}]]}]},
            {"path": "web/a.spec.ts", "hunks": [{"lines": [["+", None, 1, "it('renders the list', () => {"]]}]},
            {"path": "src/a.py", "hunks": [{"lines": [["+", None, 1, "def test_not_a_test_file():"]]}]}]}
        v = _pr_view(p)
        self.assertEqual([t["name"] for t in v["tests"]], ["test_one_thing", "test_two", "renders the list"])   # added only, test files only
        self.assertEqual(v["files_missing"], 2)

    def test_styles_render_with_session_inlined(self):
        import re
        from cockpit.styles import as_document, render
        for style in ("focus", "guided", "behavior", "console", "onepage", "decisions"):
            frag = render(style, self.sdir)
            self.assertTrue(frag.startswith("<title>"))
            tag = re.search(r'<script type="application/json" class="case-data"[^>]*>(.*?)</script>', frag, re.S).group(1)
            self.assertNotIn("<", tag)                       # every '<' escaped: data can't close the tag
            self.assertEqual(json.loads(tag)["session"], "sty")
            host = json.loads(re.search(r'id="cockpit-host">(.*?)</script>', frag, re.S).group(1))
            self.assertEqual((host["mode"], host["style"]), ("snapshot", style))
            self.assertNotIn("{{", frag)
            self.assertTrue(as_document(frag).startswith("<!doctype html>"))

    def test_stories_beat_is_checked(self):
        from cockpit.story import normalize
        prs = {p["key"]: p for p in self.data()["prs"]}
        good = {"kind": "stories", "lede": "l", "items": [{"for": "user", "as": "shopper", "want": "a code", "prs": [self.P2],
                                                            "status": "partial", "source": {"kind": "qodo", "title": "t"}}]}
        _, w = normalize([good], where="session", prs=prs, sdir=self.sdir)
        self.assertEqual(w, [])
        bad = {"kind": "stories", "lede": "l", "items": [{"for": "robot", "want": "x", "prs": ["nope"], "status": "done", "source": {}}]}
        _, w = normalize([bad], where="session", prs=prs, sdir=self.sdir)
        self.assertEqual(len(w), 5)   # for, as, status, PR key, source
        many = [{"kind": "callout", "lede": "l", "tone": "note", "text": "t"} for _ in range(8)] + [good]
        _, w = normalize(many, where="session", prs=prs, sdir=self.sdir)
        self.assertFalse(any("stops being a story" in x for x in w))   # stories don't count toward the budget

    def test_demo_has_stories_and_qodo_in_view(self):
        from cockpit.view import view_data
        v = view_data(self.sdir)
        st = next(b for b in v["story"] if b["kind"] == "stories")
        self.assertEqual({it["for"] for it in st["items"]}, {"user", "operator", "developer"})
        self.assertIn("qodo", v["prs"][0])
        # the Overview's tools row tells "Qodo found nothing" from "Qodo didn't run" by this
        self.assertIn("qodo_source", v["prs"][0])

    def test_style_names_are_checked(self):
        from cockpit.styles import missing_content, require
        self.assertEqual(require(None), "package")
        self.assertRaisesRegex(ValueError, "unknown style", require, "fancy")
        self.assertRaisesRegex(ValueError, "planned", require, "living")
        d = self.data(); d.pop("behavior")
        self.assertIn("no behavior diff", missing_content("behavior", d))
        self.assertIsNone(missing_content("guided", d))

    def test_export_per_style(self):
        from cockpit.export import export
        out = export(self.sdir, style="behavior")
        self.assertEqual(out.name, "101-102-103-review-behavior.html")
        self.assertIn("Behavior Diff", out.read_text())
        frag = export(self.sdir, style="guided", fragment=True, title="Checkout Review")
        self.assertTrue(frag.read_text().startswith("<title>Checkout Review</title>"))
        self.assertEqual(export(self.sdir, style="cockpit").name, "101-102-103-review.html")   # the full app
        self.assertEqual(export(self.sdir).name, "101-102-103-review-package.html")           # the default style

    def test_style_switcher_opens_or_asks(self):
        import re
        from cockpit.export import export
        from cockpit.styles import menu
        d = self.data()
        served = {s["id"]: s for s in menu(self.sdir, d, "serve")}
        self.assertEqual((served["guided"]["url"], served["cockpit"]["url"]), ("/s/guided", "/index.html"))   # served: the server renders any style
        alone = {s["id"]: s for s in menu(self.sdir, d, "snapshot")}
        self.assertIsNone(alone["guided"]["url"])
        self.assertIn("in the Guided Review style", alone["guided"]["ask"])   # a lone snapshot gives the ask
        d.pop("behavior")
        self.assertIn("/review-prs write the behavior diff", {s["id"]: s for s in menu(self.sdir, d, "serve")}["behavior"]["ask"])   # content first
        more = []
        out = export(self.sdir, title="Checkout Review", with_styles=True, written=more)
        self.assertEqual(sorted(f.name for f in more), ["101-102-103-review-behavior.html", "101-102-103-review-cockpit.html", "101-102-103-review-console.html", "101-102-103-review-decisions.html", "101-102-103-review-focus.html", "101-102-103-review-guided.html", "101-102-103-review-onepage.html", "101-102-103-review-risk.html", "101-102-103-review-verdict.html"])
        host = json.loads(re.search(r'<script type="application/json" id="cockpit-host">(.*?)</script>', out.read_text()).group(1))
        self.assertEqual({s["id"]: s["url"] for s in host["styles"]}["guided"], "101-102-103-review-guided.html")   # siblings open from the switcher
        self.assertTrue(all(f.read_text().startswith("<!doctype html>") for f in more))   # full pages, so a host can serve them as files
        app = next(f for f in more if f.name.endswith("-cockpit.html")).read_text()
        self.assertIn('"url": "101-102-103-review-focus.html"', app)   # the full app links back to the styles exported with it

    def test_artifact_style_pages_link_only_to_files_that_exist(self):
        import re
        from cockpit.export import export
        more = []
        frag = export(self.sdir, title="Checkout Review", fragment=True, with_styles=True, written=more)
        published = {f.name for f in more}   # what a host serves next to the fragment; the fragment itself has no file name
        self.assertIn("101-102-103-review-risk.html", published)   # a full copy of the main style, for the way back
        for f in [frag] + more:
            urls = re.findall(r'"url": "([^"/][^"]*\.html)"', f.read_text())
            self.assertTrue(urls, f.name)
            self.assertFalse(set(urls) - published, f"{f.name} links to unpublished pages")
        for taken in ("101-102-103-review-risk.html", "101-102-103-review-focus.html"):   # --out takes the main copy's name, or another style's
            more = []
            frag = export(self.sdir, out=self.sdir / "share" / taken, fragment=True, with_styles=True, written=more)
            published = {f.name for f in more}
            self.assertNotIn(frag.name, published)
            for f in [frag] + more:
                urls = re.findall(r'"url": "([^"/][^"]*\.html)"', f.read_text())
                self.assertTrue(urls, f.name)
                self.assertFalse(set(urls) - published, f"{taken}: {f.name} links to unpublished pages")

    def test_session_data_is_swapped_in_whole(self):
        from cockpit.util import write_json
        p = self.sdir / "review-data.json"
        write_json(p, {"a": 1})
        self.assertEqual(json.loads(p.read_text()), {"a": 1})
        self.assertEqual([x.name for x in self.sdir.iterdir() if x.name.endswith(".tmp")], [])   # no temp file left behind

    def test_refresh_from_the_page_runs_in_the_background(self):
        import threading, time, urllib.request
        from http.server import ThreadingHTTPServer
        from unittest import mock
        from cockpit import server as srv
        from cockpit.view import view_data
        self.assertTrue(view_data(self.sdir)["reviewed_at"])                      # the freshness line has a time
        srv.Handler.sdir, srv.Handler.cfg, srv.Handler.style = self.sdir, {**load_config(), "emoji": EMOJI}, "focus"
        srv.Handler._refreshing.clear()
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), srv.Handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{httpd.server_port}"
        post = lambda: json.loads(urllib.request.urlopen(urllib.request.Request(base + "/api/refresh", data=b"{}", headers={"Content-Type": "application/json"}, method="POST")).read())
        get = lambda: json.loads(urllib.request.urlopen(base + "/api/refresh").read())
        try:
            self.assertEqual(get()["state"], "idle")
            self.assertIn("error", post())                                         # the demo has nothing to re-read
            data = json.loads((self.sdir / "review-data.json").read_text()); data["demo"] = False
            (self.sdir / "review-data.json").write_text(json.dumps(data))
            gate, calls = threading.Event(), []
            def slow(sdir, cfg):
                calls.append(1); gate.wait(5); return {"warnings": ["w"]}
            with mock.patch("cockpit.collect.refresh", side_effect=slow):
                states = []
                clicks = [threading.Thread(target=lambda: states.append(post()["state"])) for _ in range(6)]
                [t.start() for t in clicks]; [t.join() for t in clicks]
                self.assertEqual(states, ["running"] * 6)
                time.sleep(0.1)
                self.assertEqual(len(calls), 1)                                    # six clicks at once, one collector
                gate.set()
                for _ in range(50):
                    if get()["state"] != "running":
                        break
                    time.sleep(0.05)
            self.assertEqual((get()["state"], get()["warnings"]), ("done", ["w"]))
            with mock.patch("cockpit.collect.refresh", side_effect=RuntimeError("gh down")):
                post()
                for _ in range(50):
                    if get()["state"] != "running":
                        break
                    time.sleep(0.05)
            self.assertEqual((get()["state"], get()["error"]), ("error", "gh down"))
        finally:
            httpd.shutdown(); srv.Handler._refreshing.clear()

    def test_reveal_opens_only_the_session_folder(self):
        import subprocess, tempfile, threading, urllib.error, urllib.request
        from http.server import ThreadingHTTPServer
        from pathlib import Path
        from unittest import mock
        from cockpit import server as srv
        srv.Handler.sdir, srv.Handler.cfg, srv.Handler.style = self.sdir, {**load_config(), "emoji": EMOJI}, "package"
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), srv.Handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{httpd.server_port}/api/reveal"
        req = lambda **h: urllib.request.Request(url, data=b'{"path": "/etc"}', headers={"Content-Type": "application/json", **h}, method="POST")
        done = lambda code, err="": subprocess.CompletedProcess([], code, "", err)
        try:
            with mock.patch("subprocess.run", return_value=done(0)) as run:
                self.assertTrue(json.loads(urllib.request.urlopen(req()).read())["ok"])
            self.assertEqual(run.call_args[0][0][-1], str(self.sdir))              # the body's path is ignored
            from cockpit import appstate, util as U2
            named = lambda t: urllib.request.Request(url, data=json.dumps({"target": t}).encode(), headers={"Content-Type": "application/json"}, method="POST")
            with mock.patch("subprocess.run", return_value=done(0)) as run:
                urllib.request.urlopen(named("sessions"))
            self.assertEqual(run.call_args[0][0][-1], str(U2.SESSIONS))           # the work package folder
            with tempfile.TemporaryDirectory() as d, mock.patch.object(appstate, "path", lambda: Path(d) / "app-state.json"), mock.patch("sys.platform", "darwin"):
                with mock.patch("subprocess.run", return_value=done(0)) as run:
                    urllib.request.urlopen(named("app-state"))
                self.assertEqual(run.call_args[0][0], ["open", d])                 # no file yet: its folder
                (Path(d) / "app-state.json").write_text("{}")
                with mock.patch("subprocess.run", return_value=done(0)) as run:
                    urllib.request.urlopen(named("app-state"))
                self.assertEqual(run.call_args[0][0], ["open", "-R", str(Path(d) / "app-state.json")])   # the file, selected
            with mock.patch("subprocess.run") as run:
                self.assertEqual(json.loads(urllib.request.urlopen(named("/etc")).read()), {"error": "unknown folder"})
            self.assertFalse(run.called)                                           # never a path from the request
            with mock.patch("subprocess.run", return_value=done(4, "no handler")), mock.patch("sys.platform", "linux"):
                self.assertEqual(json.loads(urllib.request.urlopen(req()).read()), {"error": "no handler"})
            with mock.patch("subprocess.run") as run, self.assertRaises(urllib.error.HTTPError) as e:
                urllib.request.urlopen(req(Host="rebound.example:80", Origin="http://rebound.example"))
            self.assertEqual((e.exception.code, run.called), (403, False))     # a rebound name never launches anything
        finally:
            httpd.shutdown()

    def test_live_state_counts_unresolved_threads(self):
        from unittest import mock
        from cockpit import collect as CL
        pr = {"key": "o/r#1", "repo": "o/r", "number": 1, "head_sha": "abc", "collected_at": "2026-01-01T00:00:00Z"}
        view = {"headRefOid": "abc", "state": "OPEN", "mergeStateStatus": "CLEAN", "reviewDecision": "REVIEW_REQUIRED", "isDraft": False, "comments": [], "reviews": []}
        with mock.patch.object(CL, "gh_json", return_value=view), mock.patch.object(CL.threads, "fetch", return_value={1: {"resolved": False}, 2: {"resolved": True}, 3: {"resolved": False}}):
            got = CL.live_state([pr])["o/r#1"]
        self.assertEqual((got["unresolved"], got["unresolved_ids"], got["review_decision"]), (2, [1, 3], "REVIEW_REQUIRED"))
        with mock.patch.object(CL, "gh_json", return_value=view), mock.patch.object(CL.threads, "fetch", side_effect=RuntimeError("no gh")):
            self.assertIsNone(CL.live_state([pr])["o/r#1"]["unresolved"])                  # unknown, not zero

    def test_manage_work_packages(self):
        import shutil, subprocess, tempfile, threading, urllib.error, urllib.request
        from http.server import ThreadingHTTPServer
        from pathlib import Path
        from unittest import mock
        from cockpit import server as srv, util as U2
        with tempfile.TemporaryDirectory() as t:
            home, base = Path(t), Path(t) / "sessions"
            for n in ("pkg-a", "pkg-b"):
                (base / n).mkdir(parents=True); shutil.copy(self.sdir / "review-data.json", base / n / "review-data.json")
            srv.Handler.sdir, srv.Handler.cfg, srv.Handler.style = base / "pkg-a", {**load_config(), "emoji": EMOJI}, "package"
            httpd = ThreadingHTTPServer(("127.0.0.1", 0), srv.Handler)
            threading.Thread(target=httpd.serve_forever, daemon=True).start()
            post = lambda path, body: json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{httpd.server_port}{path}", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")).read())
            try:
                with mock.patch.object(srv, "SESSIONS", base), mock.patch.object(U2, "HOME", home), mock.patch("sys.platform", "linux"):
                    one = next(x for x in srv.list_sessions() if x["id"] == "pkg-b")
                    self.assertEqual((one["named"], one["repos"] >= 1, isinstance(one["stacks"], int)), (False, True, True))
                    got = next(x for x in post("/api/session-rename", {"session": "pkg-b", "name": "  My package "})["sessions"] if x["id"] == "pkg-b")
                    self.assertEqual((got["title"], got["named"]), ("My package", True))
                    self.assertFalse(next(x for x in post("/api/session-rename", {"session": "pkg-b", "name": ""})["sessions"] if x["id"] == "pkg-b")["named"])   # "" gives back its own name
                    with self.assertRaises(urllib.error.HTTPError) as e:
                        post("/api/session-delete", {"session": "pkg-a"})
                    self.assertEqual(e.exception.code, 409)                               # the package open here stays
                    with self.assertRaises(urllib.error.HTTPError) as e:
                        post("/api/session-delete", {"session": "../pkg-b"})
                    self.assertEqual(e.exception.code, 404)                               # a name, never a path
                    j = post("/api/session-delete", {"session": "pkg-b"})
                    self.assertTrue((home / "trash" / "pkg-b" / "review-data.json").is_file())   # moved, not erased
                    self.assertEqual([x["id"] for x in j["sessions"]], ["pkg-a"])
                    with mock.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, "", "")) as run:
                        post("/api/reveal", {"target": "session", "session": "pkg-a"})
                    self.assertEqual(run.call_args[0][0][-1], str(base / "pkg-a"))
                    with mock.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 1, "", "")), mock.patch("sys.platform", "darwin"):
                        self.assertEqual(post("/api/reveal", {"target": "sessions"}), {"error": "open exited with 1"})   # a silent failure still answers
            finally:
                httpd.shutdown()

    def test_app_state_shared_by_every_session(self):
        import tempfile, threading, urllib.error, urllib.request
        from http.server import ThreadingHTTPServer
        from pathlib import Path
        from unittest import mock
        from cockpit import appstate, server as srv
        srv.Handler.sdir, srv.Handler.cfg, srv.Handler.style = self.sdir, {**load_config(), "emoji": EMOJI}, "package"
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), srv.Handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{httpd.server_port}"
        post = lambda body: urllib.request.urlopen(urllib.request.Request(base + "/api/app-state", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST"))
        with tempfile.TemporaryDirectory() as d, mock.patch.object(appstate, "path", lambda: Path(d) / "app-state.json"):
            try:
                self.assertEqual(json.loads(urllib.request.urlopen(base + "/api/app-state").read())["state"], {})
                mine = [{"id": "my-1", "name": "Mine", "pages": [{"id": "a", "label": "A", "icon": "ovw", "widgets": ["verdict"]}]}]
                post({"set": {"cockpit:theme": "light", "cockpit:my-layouts": mine}})
                post({"set": {"cockpit:theme": None}})                                  # null removes a setting
                self.assertEqual(appstate.load(), {"cockpit:my-layouts": mine})
                self.assertIn('"cockpit:my-layouts"', urllib.request.urlopen(base + "/").read().decode())   # the page arrives with them
                with self.assertRaises(urllib.error.HTTPError) as e:
                    post({"set": {"focus:some-session": {}}})                          # a review's own state stays in the browser
                self.assertEqual(e.exception.code, 400)
                with mock.patch.object(appstate, "MAX_BYTES", 10), self.assertRaises(ValueError):
                    appstate.update({"cockpit:theme": "dark"})
            finally:
                httpd.shutdown()

    def test_server_routes(self):
        import threading
        import urllib.request
        from http.server import ThreadingHTTPServer
        from cockpit import server as srv
        srv.Handler.sdir, srv.Handler.cfg, srv.Handler.style = self.sdir, {**load_config(), "emoji": EMOJI}, "behavior"
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), srv.Handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{httpd.server_port}"
        try:
            home = urllib.request.urlopen(base + "/").read().decode()
            self.assertIn('"mode": "serve"', home)
            self.assertTrue(json.loads(urllib.request.urlopen(base + "/api/health").read())["ok"])   # the page's server check
            ico = urllib.request.urlopen(base + "/favicon.ico")
            self.assertEqual((ico.status, ico.headers["Content-Type"]), (200, "image/svg+xml"))   # the Qodo icon
            self.assertLess(home.index('rel="icon"'), home.index("</head>"))                       # in the head, where browsers read it
            self.assertIn("Behavior Diff", home)
            self.assertIn("Guided Review", urllib.request.urlopen(base + "/s/guided").read().decode())
            self.assertIn("Review Cockpit", urllib.request.urlopen(base + "/s/cockpit").read().decode())   # redirect to the app
            styles = json.loads(urllib.request.urlopen(base + "/api/styles").read())
            self.assertEqual([s["id"] for s in styles["styles"]], ["cockpit", "focus", "risk", "package", "verdict", "guided", "behavior", "console", "onepage", "decisions"])
            with self.assertRaises(urllib.error.HTTPError) as cm:
                urllib.request.urlopen(base + "/s/living")
            self.assertEqual(cm.exception.code, 404)
        finally:
            httpd.shutdown(); httpd.server_close()

    def test_cli_style_flag(self):
        from cockpit.__main__ import main
        with self.assertRaises(SystemExit):
            main(["serve", "--style", "fancy"])



class MemoryOffTests(unittest.TestCase):
    """Memory is optional: with `memory.enabled: false` nothing is read from or written to memory."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self._sessions = C.SESSIONS
        C.SESSIONS = self.tmp / "sessions"
        cfg = load_config()
        cfg["memory"] = {"enabled": False, "amr": str(self.tmp / "mem/amr"), "okf": str(self.tmp / "mem/okf"), "auto_commit": False}
        fx = json.loads((ROOT / "fixtures" / "demo-prs.json").read_text())
        _, self.sdir = C.build(fx["prs"], cfg, demo=True, session="off", reviewer_login="x")

    def tearDown(self):
        C.SESSIONS = self._sessions
        shutil.rmtree(self.tmp)

    def test_nothing_touches_memory(self):
        from cockpit.enrich import enrich
        from cockpit.util import session_config
        self.assertFalse((self.tmp / "mem").exists())
        cfg = session_config(self.sdir)
        self.assertFalse(cfg["memory"]["enabled"])
        res = enrich(self.sdir, {"knowledge": [{"type": "Fact", "title": "t", "body": "b", "paths": ["src/**"]}]})
        self.assertTrue(any("memory is off" in w for w in res["warnings"]))
        self.assertEqual(res["candidates"], [])
        with self.assertRaises(RuntimeError):
            distill(self.sdir, cfg)
        self.assertEqual(dream(cfg), {"skipped": "memory is off (config memory.enabled)"})
        self.assertFalse((self.tmp / "mem").exists())

    def test_demo_keeps_memory_off(self):
        from unittest import mock
        from cockpit.util import session_config
        cfg = load_config(); cfg["memory"] = {**cfg["memory"], "enabled": False}
        with mock.patch.object(C, "load_config", return_value=cfg):
            _, sdir = C.collect_demo()
        self.assertFalse(session_config(sdir)["memory"]["enabled"])
        self.assertFalse((sdir / "memory").exists())

    def test_local_config_overlays_and_memory_paths_expand(self):
        from cockpit.util import _merge, mem_path
        cfg = _merge(load_config(), {"memory": {"amr": "~/cockpit-mem/amr"}})
        self.assertEqual(cfg["memory"]["okf"], load_config()["memory"]["okf"])   # siblings kept
        self.assertEqual(mem_path(cfg, "amr"), Path.home() / "cockpit-mem/amr")


class ScannerTests(unittest.TestCase):
    """Security scanners' PR comments become findings (formats copied from real Snyk and Upwind comments)."""
    SNYK_SVG = "https://res.cloudinary.com/snyk/image/upload/r-d/scm-platform/snyk-pull-requests/severity-{}.svg"

    def pr(self, comments, checks=()):
        files = [{"path": "requirements.txt", "hunks": [{"lines": [["+", None, 3, "gitpython==3.1.53"]]}]}]
        return {"key": "o/r#1", "files": files, "checks": list(checks), "_raw_comments": comments}

    def collect(self, pr):
        from cockpit.adapters import scanners
        return scanners.collect(pr, load_config())

    def test_bot_logins_are_literal_except_star(self):
        from cockpit.adapters.scanners import _bot
        self.assertTrue(_bot("snyk-io[bot]", ["snyk-io[bot]"]))
        self.assertTrue(_bot("upwind-code-eu[bot]", ["upwind-code-*[bot]"]))
        self.assertFalse(_bot("snyk-iob", ["snyk-io[bot]"]))

    def test_snyk_inline_and_summary(self):
        inline = {"id": 1, "author": "snyk-io[bot]", "path": "app/api.py", "line": 27, "url": "u1",
                  "body": f'### <sub><img src="{self.SNYK_SVG.format("high")}" width="20"/></sub>&nbsp; Command Injection\n\n'
                          "Unsanitized input from `an HTTP header` flows into `subprocess`.\n\n<h6>\nLine 27 | "
                          '<a href="https://cwe.mitre.org/data/definitions/78.html">CWE-78</a> | <a href="x">Priority score 608</a> | x</h6>'}
        summary = {"id": 2, "author": "snyk-io[bot]", "url": "u2", "body":
                   "### :no_entry: **Snyk checks have failed. 2 issues have been found so far.**\n\n"
                   "| Status | Scan Engine | C | H | M | L | Total (2) |\n|---|---|---|---|---|---|---|\n"
                   "| :no_entry: | Open Source Security| 0 | 0 | 1 | 0 | [ 1 issues](https://app.snyk.io/org/o/pr-checks/1) |\n"
                   "| :white_check_mark: | Licenses| 0 | 0 | 0 | 0 | [ 0 issues](https://app.snyk.io/org/o/pr-checks/1/license) |\n"
                   "| :no_entry: | Code Security| 0 | 1 | 0 | 0 | [ 1 issues](https://app.snyk.io/org/o/p/1) |\n"}
        fs = self.collect(self.pr([summary, inline]))
        by = {f["scanner"]["kind"]: f for f in fs}
        self.assertEqual(set(by), {"sast", "sca"})   # Code Security is listed inline, not again as a count
        self.assertEqual((by["sast"]["title"], by["sast"]["severity"], by["sast"]["scanner"]["rule"], by["sast"]["line"]),
                         ("Command Injection", "high", "CWE-78", 27))
        self.assertEqual(by["sca"]["severity"], "medium")
        self.assertIn("app.snyk.io", by["sca"]["url"])
        fixed = self.collect(self.pr([inline], checks=[{"name": "code/snyk (Org)", "state": "success"}]))
        self.assertEqual(fixed[0]["status"], "resolved")   # Snyk Code passes now: the old comment is history
        self.assertEqual(fixed[0]["id"], by["sast"]["id"])   # same issue, same id

    def test_upwind_code_iac_and_secrets(self):
        head = '## <img src="x" alt="Upwind"> Upwind {} Scan - ⛔ Blocked\n\n> **2 newly introduced** · **1 resolved**\n\n'
        block = "<details>\n<summary>{} <b>{} · 1 finding</b></summary>\n\n{}\n\n</details>\n"
        sca = head.format("Code") + block.format("🔴", "Critical", "| CVE | Package | Version | Fix |\n|---|---|---|---|\n| CVE-1 | `gitpython` | `3.1.53` | `3.1.59` |") \
            + block.format("🔶", "High", "| CVE | Package | Version | Fix |\n|---|---|---|---|\n| CVE-2 | `gitpython` | `3.1.53` | `3.1.58` |\n| CVE-2 | `gitpython` | `3.1.53` | — |") \
            + block.format("✅", "Resolved", "| CVE | Package | Version | Fix |\n|---|---|---|---|\n| CVE-9 | `old` | `1.0` | `1.1` |") \
            + "[View full analysis in Upwind Console](https://console.upwind.io/x)\n" \
            + block.format("", "Scan history (2 scans)", "| Commit | Scanned at | New | Resolved | Net |\n|---|---|---|---|---|\n| a | b | 1 | 0 | 1 |")
        iac = head.format("IaC") + block.format("🟢", "Low", "| Rule | Resource | File |\n|---|---|---|\n| CPU not limited | `api` (Deployment) | `charts/api.yaml` |\n| CPU not limited | `job` (Job) | `charts/job.yaml` |")
        sec = "<!-- upwind-shiftleft-secrets -->\n" + head.format("Secrets") + block.format("🔶", "PII", "| File | Line | Type | Value |\n|---|---|---|---|\n| [`README.md`](https://github.com/o/r/blob/s/README.md#L26) | 26 | Email | `••••@github.com` |")
        fs = self.collect(self.pr([{"id": i, "author": "upwind-code-us[bot]", "url": "u", "body": b} for i, b in enumerate((sca, iac, sec))]))
        dep = next(f for f in fs if f["title"].startswith("gitpython"))
        self.assertEqual((dep["severity"], dep["path"], dep["line"]), ("high", "requirements.txt", 3))   # worst CVE; the bumped line
        self.assertIn("CVE-1, CVE-2.", dep["body"]); self.assertIn("Upgrade to 3.1.59", dep["body"])
        self.assertEqual(next(f for f in fs if f["title"].startswith("old"))["status"], "resolved")
        cpu = next(f for f in fs if f["scanner"]["kind"] == "iac")
        self.assertEqual((cpu["title"], cpu["severity"], cpu["path"]), ("CPU not limited (2 places)", "low", "charts/api.yaml"))
        email = next(f for f in fs if f["scanner"]["kind"] == "secret")
        self.assertEqual((email["path"], email["line"], email["severity"]), ("README.md", 26, "medium"))
        self.assertFalse(any("history" in f["title"].lower() for f in fs))

    def snyk_summary(self, open_source_medium, updated):
        row = (":no_entry:", 1) if open_source_medium else (":white_check_mark:", 0)
        return {"id": updated, "author": "snyk-io[bot]", "url": "u", "updated": updated, "body":
                "### **Snyk checks have run.**\n\n| Status | Scan Engine | C | H | M | L | Total |\n|---|---|---|---|---|---|---|\n"
                f"| {row[0]} | Open Source Security| 0 | 0 | {row[1]} | 0 | [ x](https://app.snyk.io/org/o/pr-checks/1) |\n"}

    def upwind_iac(self, blocks, updated):
        body = '## <img alt="Upwind"> Upwind IaC Scan - ⛔ Blocked\n\n' + "".join(
            f"<details>\n<summary>{lab} · 1 finding</summary>\n\n| Rule | Resource | File |\n|---|---|---|\n{rows}\n\n</details>\n"
            for lab, rows in blocks)
        return {"id": updated, "author": "upwind-code-us[bot]", "url": "u", "updated": updated, "body": body}

    def test_latest_scan_wins(self):
        old, new = self.snyk_summary(True, "2026-10-01T00:00:00Z"), self.snyk_summary(False, "2026-10-02T00:00:00Z")
        self.assertEqual(self.collect(self.pr([old, new])), [])   # the failed row was replaced by a passing scan
        row = "| CPU not limited | `api` | `charts/api.yaml` |"
        seen = [self.upwind_iac([("Low", row)], "2026-10-01T00:00:00Z"), self.upwind_iac([("Resolved", row)], "2026-10-02T00:00:00Z")]
        self.assertEqual([f.get("status") for f in self.collect(self.pr(seen))], ["resolved"])

    def test_clean_scans_are_reported(self):
        from cockpit.adapters.scanners import scans
        up = {"id": 9, "author": "upwind-code-us[bot]", "url": "u9", "updated": "2026-10-03T00:00:00Z", "body":
              '## <img alt="Upwind"> Upwind Code Scan - ✅ Passed\n\n> **0 newly introduced vulnerabilities** · **0 resolved** · **7 total** in this PR'}
        pr = self.pr([self.snyk_summary(False, "2026-10-02T00:00:00Z"), self.snyk_summary(True, "2026-10-01T00:00:00Z"), up])
        got = {s["name"]: s for s in scans(pr, load_config(), self.collect(pr))}
        self.assertEqual(got["Snyk"]["status"], "passed")   # the latest summary, not the older failure
        self.assertEqual(got["Upwind"]["text"], "Code passed, 0 new of 7")
        self.assertNotIn("CodeQL", got)   # a scanner that never ran is not listed
        failed = self.pr([self.snyk_summary(True, "t")])
        self.assertEqual(scans(failed, load_config(), self.collect(failed))[0]["status"], "failed")

    def sonar_gate(self, failed, updated, project=None):
        icon = lambda st: f"![](https://sonarsource.github.io/sonarcloud-github-static-resources/v2/common/{st}-16px.png '')"
        for_ = f" for '{project}'" if project else ""
        dash = f"https://sonarcloud.io/dashboard?id={project or 'o_r'}&pullRequest=7"
        body = (f"## [![Quality Gate](https://sonarsource.github.io/x/qg-{'failed' if failed else 'passed'}-20px.png 'Q')]({dash}) "
                f"**Quality Gate {'failed' if failed else 'passed'}{for_}**  \n")
        body += (f"Failed conditions  \n{icon('failed')} [38.0% Coverage on New Code](https://sonarcloud.io/m?id=o_r) (required ≥ 40%)  \n"
                 f"{icon('failed')} [E Security Rating on New Code](https://sonarcloud.io/i?id=o_r) (required ≥ A)  \n" if failed else
                 f"Issues  \n{icon('passed')} [3 New issues](https://sonarcloud.io/i?id=o_r)  \n")
        body += f"\n[See analysis details on SonarQube Cloud]({dash})"
        return {"id": updated, "author": "sonarqubecloud[bot]", "url": "u", "updated": updated, "body": body}

    def test_sonar_gate_conditions_and_latest_per_project(self):
        pr = self.pr([self.sonar_gate(True, "2026-10-02T00:00:00Z"), self.sonar_gate(False, "2026-10-01T00:00:00Z")])
        [gate] = self.collect(pr)   # the latest comment only: the older pass is history
        self.assertEqual((gate["severity"], gate["category"]), ("high", "security"))   # a Security Rating failed
        self.assertIn("[38.0% Coverage on New Code](https://sonarcloud.io/m?id=o_r) (required ≥ 40%)", gate["body"])
        self.assertEqual(gate["url"], "https://sonarcloud.io/dashboard?id=o_r&pullRequest=7")   # the dashboard, not the badge
        self.assertEqual(self.collect(self.pr([self.sonar_gate(False, "b"), self.sonar_gate(True, "a")]))[0]["severity"], "low")   # fixed since
        mono = self.pr([self.sonar_gate(True, "b", "api"), self.sonar_gate(True, "a", "web")])
        self.assertEqual(sorted(f["title"].split(":")[0] for f in self.collect(mono)),
                         ["SonarQube quality gate failed (api)", "SonarQube quality gate failed (web)"])

    def test_sonar_annotations_give_lines_and_match_code_scanning(self):
        ann = {"check": "SonarCloud Code Analysis", "app": "sonarqubecloud", "url": "run", "path": "app/x.py", "line": 12,
               "level": "failure", "title": "Make sure this regex is safe.",
               "message": "\nSee more on https://sonarcloud.io/project/issues?id=o_r&issues=AZk1&open=AZk1&pullRequest=7"}
        cs = {"id": 5, "author": "github-advanced-security[bot]", "path": "app/x.py", "line": 12, "url": "c", "updated": "t",
              "body": "## SonarCloud / Regex should be safe\n\n<!--SONAR_ISSUE_KEY:AZk1-->Make sure this regex is safe.\n\n"
                      "[Show more details](https://github.com/o/r/security/code-scanning/9)"}
        pr = {**self.pr([self.sonar_gate(False, "t"), cs]), "_annotations": [ann]}
        fs = self.collect(pr)
        self.assertEqual([(f["source"], f["path"], f["line"], f["severity"]) for f in fs], [("sonar", "app/x.py", 12, "high")])   # once
        from cockpit.adapters.scanners import scans
        self.assertEqual({s["name"]: s["text"] for s in scans(pr, load_config(), fs)}["SonarQube"], "quality gate passed · 1 open")
        semgrep = {**cs, "body": "## Semgrep OSS / python.lang.security.audit.eval\n\nDetected eval.\n\n"
                                 "[Show more details](https://github.com/o/r/security/code-scanning/10)"}
        f = self.collect(self.pr([semgrep]))[0]
        self.assertEqual((f["source"], f["scanner"]["name"], f["title"]), ("code_scanning", "Semgrep OSS", "python.lang.security.audit.eval"))

    def test_ai_reviewers_codex_and_copilot(self):
        codex = {"id": 1, "author": "chatgpt-codex-connector[bot]", "path": "a.toml", "line": 19, "url": "u", "body":
                 "**<sub><sub>![P1 Badge](https://img.shields.io/badge/P1-orange?style=flat)</sub></sub>  Update the prompt contract assertions**"
                 "\n\nThe test still requires the previous phrases.\n\nUseful? React with 👍 / 👎"}
        pic = lambda lvl: f'<picture><img src="x.png" alt="{lvl} severity" width="62"></picture>'
        overview = {"id": 2, "author": "copilot-pull-request-reviewer[bot]", "created": "t", "body":
                    "<!-- ccr-overview-v2 -->\n## Copilot review overview\n\n### 🟡 Changes recommended\n\n<details open>\n"
                    f"<summary><strong>Open (1)</strong></summary>\n\n- {pic('High')} [Key outlives expiry](#discussion_r10) · New\n</details>\n"
                    f"<details>\n<summary><strong>Resolved (1)</strong></summary>\n\n- {pic('Low')} [Missing decision record](#discussion_r11)\n</details>"}
        inl = [{"id": 10, "author": "Copilot", "path": "gw.py", "line": 263, "url": "c10", "body": "The relative duration can extend access."},
               {"id": 11, "author": "Copilot", "path": "req.txt", "line": 7, "url": "c11", "body": "No decision entry."}]
        fs = {f["source"] + str(f["line"]): f for f in self.collect(self.pr([codex, overview] + inl))}
        self.assertEqual((fs["codex19"]["severity"], fs["codex19"]["title"]), ("high", "Update the prompt contract assertions"))
        self.assertNotIn("Useful?", fs["codex19"]["body"])
        self.assertEqual((fs["copilot263"]["severity"], fs["copilot263"]["title"], fs["copilot263"].get("status")), ("high", "Key outlives expiry", None))
        self.assertEqual(fs["copilot7"]["status"], "resolved")   # listed under Resolved in the latest overview
        from cockpit.adapters.scanners import scans
        got = {s["name"]: s for s in scans(self.pr([codex, overview] + inl), load_config(), list(fs.values()))}
        self.assertEqual((got["Copilot"]["status"], got["Copilot"]["text"]), ("failed", "changes recommended · 1 open"))

    def test_gitguardian_and_socket(self):
        row = ("| [3799](https://dashboard.gitguardian.com/workspace/2/incidents/3799?occurrence={o}) | Triggered | Generic Password "
               "| {sha} | src/a.spec.ts | [View secret](https://github.com/o/r/commit/{sha}#diff-1fR95) |")
        gg = {"id": 1, "author": "gitguardian[bot]", "url": "g", "updated": "t", "body":
              "#### ⚠️ GitGuardian has uncovered 2 secrets following the scan of your pull request.\n\n"
              "| GitGuardian id | GitGuardian status | Secret | Commit | Filename | |\n| - | - | - | - | - | - |\n"
              + row.format(o=1, sha="aaa") + "\n" + row.format(o=2, sha="bbb") + "\n"}
        [f] = self.collect(self.pr([gg]))   # two occurrences of one incident
        self.assertEqual((f["severity"], f["path"], f["line"], f["scanner"]["kind"]), ("high", "src/a.spec.ts", 95, "secret"))
        sock = {"id": 2, "author": "socket-security[bot]", "url": "s", "updated": "t", "body":
                "> [!WARNING]\n> **Review the following alerts detected in dependencies.**\n\n<table><tbody>\n<tr>\n<td valign=\"top\">Warn</td>\n"
                '<td align="center"><a href="https://socket.dev/dashboard/org/o/diff-scan/1/alert/QUh"><img src="s.svg" title="High" alt="High"></a></td>\n'
                "<td><details open><summary><strong>Obfuscated code</strong>:  golang <code>github.com/modern-go/reflect2</code> is 90.0% likely obfuscated</summary>\n"
                '<p><strong>From:</strong> <a href="https://github.com/o/r/pull/1/files#diff-3">go.mod</a> → <code>golang/github.com/gruntwork-io/terragrunt@v0.54.11</code> → '
                "<code>golang/github.com/modern-go/reflect2@v1.0.2</code></p></details></td>\n</tr>\n</tbody></table>"}
        pr = self.pr([sock])
        pr["files"] = [{"path": "go.mod", "hunks": [{"lines": [["+", None, 4, "\tgithub.com/x/y v1"], ["+", None, 9, "\tgithub.com/gruntwork-io/terragrunt v0.54.11"]]}]}]
        [s] = self.collect(pr)
        self.assertEqual((s["severity"], s["path"], s["line"]), ("high", "go.mod", 9))   # the direct dependency that pulls it in
        self.assertEqual(s["title"], "Obfuscated code: github.com/modern-go/reflect2")

    def test_check_annotations_by_name(self):
        cfg = load_config()
        anns = [{"check": "Codacy Static Code Analysis", "app": "codacy-production", "url": "run", "path": "a.mjs", "line": 35, "level": "failure",
                 "title": "a.mjs#L35", "message": "The application dynamically constructs file or path information."},
                {"check": "Codacy Static Code Analysis", "app": "codacy-production", "path": ".github/workflows/x.yml", "line": 1, "level": "warning",
                 "title": "Node 16 is deprecated", "message": ""},
                {"check": "lint", "app": "github-actions", "path": "b.py", "line": 2, "level": "failure", "title": "E501", "message": ""}]
        from cockpit.adapters import scanners
        fs = scanners.collect({**self.pr([]), "_annotations": anns}, cfg)
        self.assertEqual([(f["source"], f["scanner"]["name"], f["title"], f["severity"]) for f in fs],
                         [("codacy", "Codacy", "The application dynamically constructs file or path information.", "medium")])
        from cockpit.adapters import annotation_checks
        self.assertIn("codacy-production", annotation_checks(cfg))   # collect fetches these runs' annotations

    def test_more_bots_edge_cases(self):
        from cockpit.adapters.scanners import scans
        cfg = load_config()
        badge = "**<sub><sub>![P2 Badge](https://img.shields.io/badge/P2-yellow?style=flat)</sub></sub>  Close the file**\n\nIt leaks."
        two = [{"id": i, "author": "chatgpt-codex-connector[bot]", "path": "a.py", "line": ln, "body": badge} for i, ln in ((1, 3), (2, 40))]
        self.assertEqual(sorted(f["line"] for f in self.collect(self.pr(two))), [3, 40])   # one title on two lines stays two findings
        row = lambda action, pkg, frm: (f'<tr>\n<td valign="top">{action}</td>\n<td><img title="High"></td>\n<td><details><summary><strong>Install scripts</strong>: '
                                        f"npm <code>{pkg}</code> runs a script</summary>\n<p><strong>From:</strong> <a href=\"f\">package.json</a> → <code>{frm}</code></p></details></td>\n</tr>\n")
        sock = {"id": 3, "author": "socket-security[bot]", "url": "s", "updated": "t", "body": "**Review the following alerts detected in dependencies.**\n<table><tbody>\n"
                + row("Warn", "@acme/core@2.0.0", "npm/@acme/cli@1.4.0") + row("Warn", "@acme/core@2.0.0", "npm/left-pad@1.0.0")
                + row("Ignore", "evil@1.0.0", "npm/evil@1.0.0") + "</tbody></table>"}
        pr = self.pr([sock])
        pr["files"] = [{"path": "package.json", "hunks": [{"lines": [["+", None, 5, '"left-pad": "1.0.0",'], ["+", None, 6, '"@acme/cli": "^1.4.0",'],
                                                                      ["+", None, 7, '"evil": "1.0.0"']]}]}]
        fs = self.collect(pr)
        warn = sorted(f["line"] for f in fs if not f.get("status"))
        self.assertEqual(warn, [5, 6])   # same alert text from two direct dependencies; the scoped one is found by its scope
        self.assertEqual([f["status"] for f in fs if f.get("status")], ["dismissed"])   # Ignore is not open
        self.assertEqual({s["name"]: s["open"] for s in scans(pr, cfg, fs)}["Socket"], 2)
        from cockpit.adapters.scanners import _line_with
        pr["files"][0]["hunks"][0]["lines"].insert(0, ["+", None, 4, '"my-left-pad": "2.0.0",'])
        self.assertEqual(_line_with(pr, "package.json", ["left-pad"]), 5)   # a whole name, not a substring of another
        gg = {"id": 4, "author": "gitguardian[bot]", "url": "g", "updated": "t", "body":
              "#### ⚠️ GitGuardian has uncovered 1 secret following the scan of your pull request.\n\n| GitGuardian id | GitGuardian status | Secret | Commit | Filename | |\n"
              "| - | - | - | - | - | - |\n| [9](https://dashboard.gitguardian.com/w/2/incidents/9) | Resolved | Password | aaa | a.py | [View secret](https://github.com/o/r/commit/aaa#diff-1fR3) |\n"}
        [s] = scans(self.pr([gg]), cfg, self.collect(self.pr([gg])))
        self.assertEqual((s["status"], s["open"]), ("passed", 0))   # every incident is resolved
        cfg["scanners"]["security_lint"] = {**cfg["scanners"]["snyk"], "parser": "snyk", "name": "Lint"}
        cfg["scanners"]["snyk"]["enabled"] = False
        from cockpit.adapters import scanners
        snyk = self.pr([self.snyk_summary(True, "t")])
        got = {s["name"]: s for s in scans(snyk, cfg, scanners.collect(snyk, cfg))}
        self.assertEqual(got["Lint"]["open"], 1)   # a key that names another parser counts its findings

    def test_worst_severity_and_reliable_locations(self):
        rows = [("Low", "| Run as non-root | `a` | `charts/a.yaml` |"), ("Critical", "| Run as non-root | `b` | `charts/b.yaml` |")]
        pr = self.pr([self.upwind_iac(rows, "t")])
        pr["files"] = [{"path": "README.md", "hunks": [{"lines": [["+", None, 1, "We use gitpython for git."]]}]},
                       {"path": "charts/b.yaml", "hunks": [{"lines": [[" ", 1, 1, "kind: Job"], ["+", None, 2, "image: x"]]}]},
                       {"path": "requirements.txt", "hunks": [{"lines": [["+", None, 7, "gitpython==3.1.53"]]}]}]
        iac = self.collect(pr)[0]
        self.assertEqual((iac["severity"], iac["path"], iac["line"]), ("high", "charts/b.yaml", 2))   # worst row; the changed file
        from cockpit.adapters.scanners import _manifest_at
        self.assertEqual(_manifest_at(pr, "gitpython"), ("requirements.txt", 7))   # the declaration, not the README
        self.assertEqual(_manifest_at(pr, "git"), (None, None))   # no substring matches
        snyk = self.collect({**pr, "_raw_comments": [self.snyk_summary(True, "t")]})[0]
        self.assertEqual((snyk["path"], snyk["line"]), ("requirements.txt", 7))   # a dependency count sits on the manifest

    def test_other_bots_and_disabled_scanners_are_ignored(self):
        cfg = load_config()
        cfg["scanners"]["upwind"]["enabled"] = False
        from cockpit.adapters import scanners
        body = '## <img alt="Upwind"> Upwind Scan - ❌ Scan Failed\n\n> The security scan could not be completed.'
        self.assertEqual(scanners.collect(self.pr([{"id": 1, "author": "upwind-code-us[bot]", "body": body}]), cfg), [])
        self.assertEqual(self.collect(self.pr([{"id": 1, "author": "someone", "body": body}])), [])
        failed = self.collect(self.pr([{"id": 1, "author": "upwind-code-us[bot]", "body": body}]))
        self.assertEqual([(f["title"], f["scanner"]["kind"]) for f in failed], [("Upwind scan failed", "gate")])



class RecipeTests(unittest.TestCase):
    """Your own styles: a recipe Focus draws, saved in the data home, and the requests a served page sends."""
    def setUp(self):
        import tempfile
        from unittest import mock
        from cockpit import recipes as R
        self.tmp = Path(tempfile.mkdtemp())
        self.patches = [mock.patch.object(R, "DIR", self.tmp), mock.patch.object(R, "REQUESTS", self.tmp / "requests")]
        for x in self.patches:
            x.start()
        self.R = R

    def tearDown(self):
        for x in self.patches:
            x.stop()

    def test_validate_keeps_what_focus_can_draw(self):
        clean, notes = self.R.validate({"name": "Risk first", "accent": "neon", "tabs": [
            {"label": "Merge", "blocks": ["brief", "starts", "nope", "brief"]}, {"label": "", "blocks": ["findings"]}, {"blocks": []}]})
        self.assertEqual(clean["id"], "risk-first")
        self.assertEqual([t["blocks"] for t in clean["tabs"]], [["brief", "starts"], ["findings"]])
        self.assertEqual(clean["tabs"][1]["label"], "Quality")   # a tab without a label takes its first block's
        self.assertEqual((clean["accent"], clean["density"], clean["brief"], clean["layout"]), ("purple", "calm", "line", "tabs"))
        self.assertTrue(any("nope" in n for n in notes) and any("once" in n for n in notes))
        page, _ = self.R.validate({"name": "All of it", "layout": "page", "tabs": [{"blocks": ["brief"]}, {"blocks": ["walk", "review"]}]})
        self.assertEqual(page["tabs"], [{"label": "All of it", "blocks": ["brief", "walk", "review"]}])   # one page: one tab, in order
        for bad in ({}, {"name": "x"}, {"name": "x", "tabs": [{"blocks": ["nope"]}]}, "text"):
            self.assertRaises(ValueError, self.R.validate, bad)

    def test_a_request_is_answered_by_a_saved_recipe(self):
        req = self.R.add_request("risk first, no stories", {"name": "Focus", "tabs": [{"blocks": ["brief"]}]}, "s1")
        self.assertEqual((req["id"], req["status"], req["base"]["tabs"][0]["blocks"]), ("r1", "open", ["brief"]))
        self.assertEqual(self.R.add_request("again")["id"], "r2")
        self.assertRaises(ValueError, self.R.add_request, "  ")
        self.R.save({"name": "Risk first", "tabs": [{"label": "Risks", "blocks": ["starts", "findings"]}]}, request="r1")
        self.assertEqual([r["id"] for r in self.R.load_all()], ["risk-first"])
        self.assertEqual(self.R.load_all()[0]["request"], "r1")   # the open page finds its answer by this
        self.assertEqual([r["id"] for r in self.R.requests(open_only=True)], ["r2"])
        (self.tmp / "broken.json").write_text("{")
        self.assertEqual(len(self.R.load_all()), 1)   # a broken file is skipped, not fatal

    def test_the_wrong_shape_is_refused_not_a_crash(self):
        for bad in ({"name": "x", "tabs": 5}, {"name": "x", "tabs": [{"blocks": [["brief"]]}]}, {"name": "x", "tabs": [{"blocks": "brief"}]}):
            self.assertRaises(ValueError, self.R.validate, bad)
        self.assertRaises(ValueError, self.R.save, None)
        (self.tmp / "hand-edited.json").write_text(json.dumps({"name": "x", "tabs": 5}))
        self.assertEqual(self.R.load_all(), [])   # skipped, so every review page still renders
        self.assertEqual(self.R.validate({"name": "Focus", "tabs": [{"blocks": ["brief"]}]})[0]["id"], "focus-style")   # the built-in keeps its id

    def test_answering_a_request_never_overwrites_a_saved_style(self):
        mine, _ = self.R.save({"name": "Risk first", "tabs": [{"blocks": ["starts"]}]})
        theirs, notes = self.R.save({"name": "Risk first", "tabs": [{"blocks": ["findings"]}]}, request="r9")
        self.assertEqual((mine["id"], theirs["id"]), ("risk-first", "risk-first-2"))
        self.assertTrue(any("--replace" in n for n in notes))
        again, _ = self.R.save({"name": "Risk first", "tabs": [{"blocks": ["walk"]}]}, replace=True)
        self.assertEqual(again["id"], "risk-first")   # the page's edit, or --replace, keeps the id
        self.assertEqual({r["id"]: r["tabs"][0]["blocks"] for r in self.R.load_all()}, {"risk-first": ["walk"], "risk-first-2": ["findings"]})

    def test_requests_sent_together_get_their_own_ids(self):
        import threading
        out = []
        ts = [threading.Thread(target=lambda i=i: out.append(self.R.add_request(f"ask {i}")["id"])) for i in range(8)]
        [t.start() for t in ts]; [t.join() for t in ts]
        self.assertEqual(len(set(out)), 8)
        self.assertEqual(sorted(r["text"] for r in self.R.requests()), sorted(f"ask {i}" for i in range(8)))

    def test_served_page_saves_recipes_and_sends_requests(self):
        import threading, urllib.request
        from http.server import ThreadingHTTPServer
        from cockpit import server as srv
        sdir = Path(tempfile_dir := __import__("tempfile").mkdtemp())
        (sdir / "review-data.json").write_text(json.dumps({"session": "s9", "prs": [], "story": []}))
        srv.Handler.sdir, srv.Handler.cfg, srv.Handler.style = sdir, {**load_config(), "emoji": EMOJI}, "focus"
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), srv.Handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{httpd.server_port}"
        def call(path, body=None):
            req = urllib.request.Request(base + path, data=None if body is None else json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"}, method="GET" if body is None else "POST")
            try:
                return json.loads(urllib.request.urlopen(req).read())
            except urllib.error.HTTPError as e:
                return json.loads(e.read())
        try:
            self.assertIn("error", call("/api/recipes", {"recipe": {"name": "x"}}))
            ok = call("/api/recipes", {"recipe": {"name": "Calm read", "tabs": [{"blocks": ["brief", "walk"]}]}})
            self.assertEqual(ok["recipe"]["id"], "calm-read")
            r = call("/api/recipe-request", {"text": "for a PM", "base": ok["recipe"]})
            self.assertEqual(r["ask"], "/review-prs make my review style from request r1")
            got = call("/api/recipes")
            self.assertEqual(([x["id"] for x in got["recipes"]], [x["session"] for x in got["requests"]]), (["calm-read"], ["s9"]))
        finally:
            httpd.shutdown()

    def test_focus_and_python_know_the_same_blocks(self):
        import re as _re
        html = (ROOT / "app" / "styles" / "focus.html").read_text()
        js = html[html.index("const BLOCKS = {"):html.index("const ACCENTS")]
        self.assertEqual(dict(_re.findall(r'^  (\w+): \{ label: "([^"]+)"', js, _re.M)), self.R.LABELS)   # same blocks, same names
        self.assertEqual(set(_re.findall(r"(\w+): \"#", html[html.index("const ACCENTS"):html.index("const FOCUS")])), set(self.R.ACCENTS))



class RiskTests(unittest.TestCase):
    """Explainable Risk: three factors per failure scenario, two fixed tables, Unknown explicit, findings kept out."""
    def data(self, rows, **pr):
        p = {"key": "o/r#1", "repo": "o/r", "files": [{"path": "src/auth/guard.py", "role": "source", "hunks": []}], "findings": [], "qodo_source": "cli"}
        p.update(pr)
        return {"prs": [p], "impact": rows}

    def row(self, r=None, d=None, c=None, name="Guard"):
        fx = {k: {"level": v, "why": "because"} for k, v in (("radius", r), ("damage", d), ("complexity", c)) if v}
        return {"component": name, "prs": ["o/r#1"], **({"factors": fx} if fx else {})}

    def test_the_two_tables_and_their_rules(self):
        from cockpit.risk import combine
        self.assertEqual(combine("large", "high", "low"), {"impact": "high", "risk": "high", "rules": ["er-v1.T1.large-high", "er-v1.T2.high-low"]})   # auth rule in a shared helper
        self.assertEqual(combine("small", "medium", "high")["risk"], "high")    # new scheduling algorithm
        self.assertEqual(combine("large", "low", "low")["risk"], "medium")      # shared CSS tweak: reach alone stays Medium

    def test_more_of_any_factor_never_lowers_risk(self):
        from cockpit.risk import combine, SCALES, LEVELS
        R, L = SCALES["radius"], LEVELS
        for a in range(3):
            for b in range(3):
                for c in range(3):
                    base = L.index(combine(R[a], L[b], L[c])["risk"])
                    for up in ((min(a + 1, 2), b, c), (a, min(b + 1, 2), c), (a, b, min(c + 1, 2))):
                        self.assertGreaterEqual(L.index(combine(R[up[0]], L[up[1]], L[up[2]])["risk"]), base)

    def test_unknown_is_a_range_never_low(self):
        from cockpit.risk import assess
        r = assess(self.data([self.row()]))   # nothing assessed
        self.assertEqual((r["level"], r["range"], r["source"]), ("unknown", ["low", "high"], "none"))
        r = assess(self.data([self.row("large", "high")]))   # complexity unknown, but large x high is High whatever it is
        self.assertEqual(r["level"], "high")
        r = assess(self.data([self.row("small", "low")]))   # small x low: Low or Medium depending on complexity
        self.assertEqual((r["level"], r["range"]), ("unknown", ["low", "medium"]))

    def test_merge_risk_is_the_riskiest_scenario_and_findings_never_move_it(self):
        from cockpit.risk import assess
        rows = [self.row("small", "low", "low", "A"), self.row("medium", "high", "low", "B")]
        quiet = assess(self.data(rows))
        noisy = assess(self.data(rows, findings=[{"severity": "high", "status": "open"}] + [{"severity": "medium", "status": "resolved"}] * 50))
        self.assertEqual((quiet["level"], quiet["deciding"]), ("high", 1))
        self.assertEqual(noisy["level"], quiet["level"])   # 50 fixed findings and an open high: same Risk
        self.assertEqual(noisy["approval"]["result"], "human review")
        self.assertIn("1 open high-severity finding.", noisy["approval"]["reasons"])

    def test_approval_needs_risk_within_the_limit_findings_and_a_review(self):
        from cockpit.risk import assess
        ok = assess(self.data([self.row("small", "low", "low")]))
        self.assertEqual(ok["approval"]["result"], "approve")
        self.assertEqual(assess(self.data([self.row("small", "low", "low")], qodo_source="none"))["approval"]["result"], "human review")

    def test_factors_are_checked_and_evidence_must_be_changed_code(self):
        from cockpit.risk import normalize_factors
        fx, warn = normalize_factors({"radius": {"level": "huge", "why": "x"}, "damage": {"level": "high", "why": "money", "ev": [{"path": "src/auth/guard.py"}, {"path": "nope.py"}]},
                                      "criticality": "low"}, {"src/auth/guard.py"})
        self.assertEqual(fx["radius"]["level"], "unknown")
        self.assertEqual(fx["damage"]["ev"], [{"path": "src/auth/guard.py"}])
        self.assertEqual(fx["complexity"]["level"], "unknown")
        self.assertTrue(any("radius" in w for w in warn) and any("nope.py" in w for w in warn))

    def test_the_report_names_each_scenario_and_how_it_was_decided(self):
        from cockpit.risk import report
        rows = [{**self.row("large", "high", "low", "Guard"), "fails": "a member writes rules for hidden repos", "gaps": ["no test for new write routes"]}]
        md = report({**self.data(rows), "title": "Repo access"})
        self.assertIn("Merge Risk: High", md); self.assertIn("er-v1.T1.large-high", md); self.assertIn("To lower it: close the gap — no test for new write routes", md)


class CriticalityTests(unittest.TestCase):
    """The criticality map: declared beats discovered, an unconfirmed Low is undeclared, and only the team protects."""
    def data(self, paths, repo="d/infra", **extra):
        p = {"key": f"{repo}#1", "repo": repo, "head_sha": "abc1234def", "qodo_source": "cli", "findings": [],
             "files": [{"path": x, "role": "config", "additions": 3, "deletions": 1, "hunks": []} for x in paths]}
        return {"prs": [p], **extra}

    def test_the_narrowest_declared_entry_wins_and_whole_repo_is_just_globstar(self):
        from cockpit.criticality import resolve
        cfg = {"criticality": {"map": [{"repo": "d/infra", "paths": ["**"], "level": "medium", "reason": "infra"},
                                       {"repo": "d/infra", "paths": ["applications/datarails-prod-*/**"], "level": "high", "reason": "prod"}]}}
        f = {x["path"]: x for x in resolve(self.data(["applications/datarails-prod-eu/values.yaml", "applications/base/datarails-dev/v.yaml"]), cfg)["files"]}
        self.assertEqual(f["applications/datarails-prod-eu/values.yaml"]["level"], "high")
        self.assertEqual(f["applications/base/datarails-dev/v.yaml"]["level"], "medium")
        self.assertEqual({x["source"] for x in f.values()}, {"declared"})

    def test_a_suggested_low_is_undeclared_and_a_suggestion_never_protects(self):
        from cockpit.criticality import normalize_map, resolve
        disc, warn = normalize_map([{"repo": "d/infra", "paths": ["**"], "level": "low", "reason": "dev only", "approve": "never"}], "discovered")
        self.assertIsNone(disc[0]["approve"]); self.assertTrue(any("only the team's map" in w for w in warn))
        f = resolve(self.data(["a.yaml"], criticality=disc), {})["files"][0]
        self.assertEqual((f["level"], f["suggested"], f["protected"]), ("undeclared", "low", False))

    def test_protected_paths_stop_approval_even_in_a_mixed_pr(self):
        from cockpit.criticality import resolve
        from cockpit.risk import assess
        cfg = {"criticality": {"map": [{"repo": "*", "paths": ["applications/datarails-prod-*/**", "applications/datarails-demo*/**"], "approve": "never", "reason": "prod clusters"}]}}
        rows = [{"component": "values", "prs": ["d/infra#1"], "factors": {k: {"level": v, "why": "x"} for k, v in (("radius", "small"), ("damage", "low"), ("complexity", "low"))}}]
        mixed = self.data(["applications/datarails-prod-us/values.yaml", "applications/base/datarails-test/v.yaml"], impact=rows)
        r = assess(mixed, resolve(mixed, cfg))
        self.assertEqual(r["approval"]["result"], "human review")
        self.assertTrue(r["approval"]["blocked_by_path"])
        self.assertTrue(any("protected paths" in x and "mixed PR" in x and "doesn't read it yet" in x for x in r["approval"]["reasons"]))
        self.assertEqual(r["approval"]["heads"], {"d/infra#1": "abc1234"})   # a new commit voids it
        safe = self.data(["applications/base/datarails-test/v.yaml"], impact=rows)
        self.assertEqual(assess(safe, resolve(safe, cfg))["approval"]["result"], "approve")

    def test_codeowners_protects_only_when_opted_in_and_never_through_a_catch_all(self):
        from cockpit.criticality import resolve
        owned = {"d/infra": {"prod/a.yaml": ["/prod/"], "src/x.py": ["*"]}}
        d = self.data(["prod/a.yaml", "src/x.py"], reviewers={"owned": owned})
        self.assertFalse(any(f["protected"] for f in resolve(d, {})["files"]))
        f = {x["path"]: x for x in resolve(d, {"criticality": {"codeowners": "protect"}})["files"]}
        self.assertTrue(f["prod/a.yaml"]["protected"]); self.assertFalse(f["src/x.py"]["protected"])

    def test_the_reviews_own_low_reads_as_a_suggestion_in_merge_risk(self):
        from cockpit.risk import assess
        row = {"component": "c", "prs": ["d/infra#1"], "factors": {"radius": {"level": "small", "why": "x"}, "criticality": "low"}}
        s = assess(self.data(["a.yaml"], impact=[row]))["scenarios"][0]
        self.assertEqual((s["criticality"], s["criticality_from"].get("suggested")), ("undeclared", "low"))


    def test_the_gate_fails_closed(self):
        from cockpit.criticality import resolve
        from cockpit.risk import assess
        rows = [{"component": "v", "prs": ["d/infra#1"], "factors": {k: {"level": v, "why": "x"} for k, v in (("radius", "small"), ("damage", "low"), ("complexity", "low"))}}]
        cfg = {"criticality": {"map": [{"repo": "*", "paths": ["/prod/**"], "approve": "never", "reason": "prod"}]}}
        d = self.data(["prod/values.yaml"], impact=rows)
        self.assertEqual(assess(d, resolve(d, cfg))["approval"]["result"], "human review")   # a leading slash is the root, as in CODEOWNERS
        d = self.data(["dev/values.yaml"], impact=rows); d["prs"][0]["files_missing"] = 2
        r = assess(d, resolve(d, cfg))["approval"]
        self.assertEqual(r["result"], "human review"); self.assertTrue(any("weren't collected" in x for x in r["reasons"]))
        r = assess(self.data(["dev/values.yaml"], impact=rows), {"error": "ValueError: bad map", "files": []})["approval"]
        self.assertEqual(r["result"], "human review")   # a map that can't be read never lets a package through
        self.assertEqual(resolve(self.data(["a"]), {"criticality": {"map": [{"paths": 123, "level": "high", "reason": "x"}]}})["declared"], [])


    def test_map_paths_read_like_codeowners(self):
        from cockpit.criticality import resolve
        cfg = {"criticality": {"map": [{"repo": "*", "paths": ["payments"], "approve": "never", "reason": "money"},
                                       {"repo": "*", "paths": ["svc/**"], "level": "medium", "reason": "svc"},
                                       {"repo": "*", "paths": ["svc/*"], "level": "high", "reason": "svc top"}]}}
        f = {x["path"]: x for x in resolve(self.data(["payments/x.py", "svc/a.py", "svc/deep/b.py"]), cfg)["files"]}
        self.assertTrue(f["payments/x.py"]["protected"])   # a bare folder covers what's below it
        self.assertEqual((f["svc/a.py"]["level"], f["svc/deep/b.py"]["level"]), ("high", "medium"))   # svc/* is narrower than svc/**

    def test_moving_a_file_out_of_a_protected_folder_is_still_protected(self):
        from cockpit.criticality import resolve
        d = self.data(["dev/values.yaml"]); d["prs"][0]["files"][0]["previous"] = "prod/values.yaml"
        cfg = {"criticality": {"map": [{"repo": "*", "paths": ["prod/**"], "approve": "never", "reason": "prod"}]}}
        self.assertTrue(resolve(d, cfg)["files"][0]["protected"])

    def test_codeowners_not_looked_up_fails_closed(self):
        from cockpit.criticality import resolve
        from cockpit.risk import assess
        rows = [{"component": "v", "prs": ["d/infra#1"], "factors": {k: {"level": v, "why": "x"} for k, v in (("radius", "small"), ("damage", "low"), ("complexity", "low"))}}]
        cfg = {"criticality": {"codeowners": "protect"}}
        for rv in (None, {"owned": {}, "stale": True}):
            d = self.data(["a.yaml"], impact=rows, **({"reviewers": rv} if rv else {}))
            r = assess(d, resolve(d, cfg))["approval"]
            self.assertEqual(r["result"], "human review"); self.assertTrue(any("wasn't looked up" in x for x in r["reasons"]))


class RoutesTests(unittest.TestCase):
    def test_routes_need_two_options_a_source_and_what_to_prove(self):
        from cockpit.routes import normalize
        r, warn = normalize({"chosen": "b", "options": [{"id": "a", "name": "Serve", "source": "documented"},
                                                        {"id": "g", "name": "git-p4", "source": "inferred"}]}, set())
        self.assertEqual(r["chosen"], "a")   # an unknown choice falls back, with a warning
        self.assertTrue(any("ref.url" in w for w in warn) and any("prove" in w for w in warn) and any("routes.chosen" in w for w in warn))
        self.assertEqual(normalize({"skip": "a one-line fix"}, set())[0], {"skip": "a one-line fix"})
        self.assertTrue(any("at least two" in w for w in normalize({"options": [{"name": "x"}]}, set())[1]))

    def test_the_chosen_route_is_never_cut(self):
        from cockpit.routes import normalize
        opts = [{"id": f"r{i}", "name": f"R{i}", "source": "inferred", "prove": "x"} for i in range(6)]
        r, warn = normalize({"chosen": "r5", "options": opts}, set())
        self.assertIn("r5", [o["id"] for o in r["options"]]); self.assertEqual(len(r["options"]), 4)

    def test_sizes_count_what_came_from_the_base_apart(self):
        from cockpit.routes import sizes
        p = {"files": [{"path": "a.py", "role": "source", "additions": 100}, {"path": "t/test_a.py", "role": "test", "additions": 40}],
             "attention": {"ranges": [{"path": "a.py", "lines": 70, "reason": "merged from main by 1234"}]}}
        self.assertEqual(sizes(p), {"production": 30, "test": 40, "docs": 0, "config": 0, "generated": 0, "from_base": 70})


class SystemTests(unittest.TestCase):
    """The contracts first (Shlomo's contract map): refs checked against the diff, the rest derived."""
    def data(self):
        f = {"path": "api/models.py", "role": "source", "additions": 3, "deletions": 0,
             "hunks": [{"lines": [[" ", 9, 9, "class A:"], ["+", None, 10, "    roots: list"], ["+", None, 11, "    pin: int"], ["+", None, 12, ""]]}]}
        g = {"path": "client/use.py", "role": "source", "additions": 1, "deletions": 0, "hunks": [{"lines": [["+", None, 5, "x = A().roots"]]}]}
        return {"session": "s", "prs": [{"key": "o/api#1", "repo": "o/api", "number": 1, "base": "main", "files": [f], "findings": []},
                                         {"key": "o/cli#2", "repo": "o/cli", "number": 2, "base": "main", "files": [g], "findings": []}]}

    def raw(self, **c):
        con = {"id": "roots", "name": "`A.roots`", "kind": "type", "change": "added", "from": "api", "to": ["cli"], "prs": ["o/api#1"], "risk": "high",
               "defined": [{"pr": "o/api#1", "path": "api/models.py", "from": 10, "to": 11}], "used": [{"pr": "o/cli#2", "path": "client/use.py", "from": 5, "to": 5}], **c}
        return {"summary": "x", "components": [{"id": "api", "name": "API"}, {"id": "cli", "name": "Client"}], "contracts": [con],
                "flows": [{"title": "f", "steps": [{"text": "a", "contract": "roots"}, {"text": "b", "contract": "nope"}]}]}

    def test_refs_are_checked_and_resolved_against_the_diff(self):
        from cockpit.system import normalize, resolve
        d = self.data()
        sysd, warn = normalize(self.raw(defined=[{"pr": "o/api#1", "path": "api/other.py", "from": 1, "to": 2}]), d, fetch=False)
        self.assertTrue(any("isn't in o/api#1's diff" in w for w in warn) and any("unknown contract nope" in w for w in warn))
        sysd, _ = normalize(self.raw(), d, fetch=False)
        y = resolve({**d, "system": sysd})
        c = y["contracts"][0]
        self.assertTrue(c["defined"][0]["changed"]); self.assertEqual(c["defined"][0]["at"], 11)
        self.assertEqual(c["touched_by"], ["o/api#1", "o/cli#2"]); self.assertEqual(c["tier"], 1)   # high, but additive and two-way
        brk, _ = normalize(self.raw(compat="breaking"), d, fetch=False)
        self.assertEqual(resolve({**d, "system": brk})["contracts"][0]["tier"], 0)   # high and breaking: read first
        self.assertEqual(y["components"][0]["risk"], "high")
        self.assertEqual([m["pr"] for m in y["merge"]], ["o/api#1", "o/cli#2"])   # the user waits on the owner
        self.assertEqual(y["merge"][1]["because"], {"o/api#1": ["roots"]})
        self.assertEqual(y["headline"], "Review 1 contract")   # a small change: no line count to beat

    def test_contract_ids_carry_no_spaces(self):
        from cockpit.system import normalize
        sysd, _ = normalize(self.raw(id="snapshot info"), self.data(), fetch=False)
        self.assertEqual(sysd["contracts"][0]["id"], "snapshot-info"); self.assertEqual(sysd["flows"][0]["steps"][0].get("contract"), None)

    def test_a_claimed_change_without_a_changed_line_is_unproven(self):
        from cockpit.system import normalize, resolve
        d = self.data()
        sysd, _ = normalize(self.raw(defined=[{"pr": "o/api#1", "path": "api/models.py", "from": 9, "to": 9}], used=[]), d, fetch=False)
        y = resolve({**d, "system": sysd})
        self.assertTrue(y["contracts"][0]["unproven"]); self.assertEqual(y["counts"]["unproven"], 1)


class ImpactTests(unittest.TestCase):
    """Blast radius and validation: what the diff says about tests, and the rows the page draws."""
    def pr(self):
        src = {"path": "src/shop/cart.py", "role": "source", "hunks": [{"lines": [["+", None, 1, "def add_item(cart, sku):"], ["+", None, 2, "    return cart"]]}]}
        other = {"path": "src/shop/tax.py", "role": "source", "hunks": [{"lines": [["+", None, 1, "def tax_rate(region):"]]}]}
        test = {"path": "tests/test_shop.py", "role": "test", "hunks": [{"lines": [["+", None, 1, "def test_add():"], ["+", None, 2, "    assert add_item({}, 'a')"]]}]}
        ranges = [{"path": "src/shop/cart.py", "tier": "deep", "lines": 2, "reason": "code"}, {"path": "src/shop/tax.py", "tier": "review", "lines": 1, "reason": "code"},
                  {"path": "tests/test_old.py", "tier": "review", "lines": 3, "reason": "test weakened"}]
        return {"key": "o/r#1", "files": [src, other, test], "attention": {"ranges": ranges}, "findings": []}

    def test_evidence_counts_tests_and_finds_code_no_test_calls(self):
        from cockpit.impact import evidence
        ev = evidence(self.pr())
        self.assertEqual(ev["tests_added"], 1)
        self.assertEqual(ev["weakened"], ["tests/test_old.py"])
        self.assertEqual([u["path"] for u in ev["untested"]], ["src/shop/tax.py"])   # cart.py: the test calls add_item
        self.assertEqual(ev["untested"][0]["names"], ["tax_rate"])   # what the Quality tab says no test calls

    def test_weakened_tests_say_what_they_lost_line_by_line(self):
        from cockpit.impact import evidence
        old = {"path": "tests/test_old.py", "role": "test", "hunks": [{"lines": [
            [" ", 9, 9, "def test_total():"], ["-", 10, None, "    assert total([]) == 0"], ["-", 11, None, "    assert total([2]) == 2"],
            ["+", None, 10, "    assert total([2]) >= 0"], ["+", None, 12, "@pytest.mark.skip(reason='flaky')"]]}]}
        pr = self.pr(); pr["files"].append(old)
        w = evidence(pr)["weakened_detail"]
        self.assertEqual([(x["path"], x["net"], x["asserts_added"]) for x in w], [("tests/test_old.py", 2, 1)])   # 2 removed - 1 added + 1 skip
        self.assertEqual([(x["side"], x["line"]) for x in w[0]["removed"]], [("old", 10), ("old", 11)])
        self.assertEqual(w[0]["disabled"], [{"side": "new", "line": 12, "text": "@pytest.mark.skip(reason='flaky')"}])

    def test_quality_explains_weakened_and_untested_files_and_warns_on_the_rest(self):
        from cockpit.impact import normalize_quality
        pr = self.pr(); pr["files"].append({"path": "tests/test_old.py", "role": "test", "hunks": []})
        q, warn = normalize_quality({"summary": "Cart is tested; tax isn't.", "tests": [
            {"path": "src/shop/tax.py", "verdict": "concern", "why": "tax_rate has no test"},
            {"path": "nope.py", "verdict": "fine", "why": "x"}, {"path": "src/shop/cart.py", "verdict": "meh", "why": "y"}]}, pr)
        self.assertEqual([(t["path"], t["verdict"]) for t in q["tests"]], [("src/shop/tax.py", "concern"), ("src/shop/cart.py", "concern")])
        self.assertTrue(any("nope.py is not a changed file" in x for x in warn))
        self.assertTrue(any("verdict must be fine|concern" in x for x in warn))
        self.assertTrue(any("cart.py is neither" in x for x in warn))
        self.assertTrue(any("no word on tests/test_old.py" in x for x in warn))   # weakened, left unexplained

    def test_quality_keeps_one_entry_per_file_the_last_one(self):
        from cockpit.impact import normalize_quality
        q, warn = normalize_quality({"tests": [{"path": "src/shop/tax.py", "verdict": "concern", "why": "no test"},
                                               {"path": "src/shop/tax.py", "verdict": "fine", "why": "covered by e2e"}]}, self.pr())
        self.assertEqual([(t["verdict"], t["why"]) for t in q["tests"]], [("fine", "covered by e2e")])   # the correction wins
        self.assertTrue(any("more than once" in x for x in warn))

    def test_a_blank_or_structured_why_is_no_explanation(self):
        from cockpit.impact import normalize_quality
        q, warn = normalize_quality({"tests": [{"path": "src/shop/tax.py", "verdict": "fine", "why": "   "},
                                               {"path": "src/shop/cart.py", "verdict": "fine", "why": {"text": "x"}}]}, self.pr())
        self.assertEqual(q["tests"], [])
        self.assertEqual(sum("needs a path and a why" in x for x in warn), 2)
        self.assertTrue(any("no word on src/shop/tax.py" in x for x in warn))   # still named as unexplained

    def test_covered_by_must_be_text_or_it_warns(self):
        from cockpit.impact import normalize_quality
        q, warn = normalize_quality({"tests": [{"path": "src/shop/tax.py", "verdict": "fine", "why": "e2e", "covered_by": ["tests/e2e/tax.py"]}]}, self.pr())
        self.assertNotIn("covered_by", q["tests"][0])
        self.assertTrue(any("covered_by must be text" in x for x in warn))

    def test_missing_quality_still_names_the_unexplained_files(self):
        from cockpit.impact import unexplained
        self.assertTrue(any("no word on src/shop/tax.py" in x for x in unexplained(self.pr(), None)))
        self.assertEqual(unexplained(self.pr(), {"tests": [{"path": "src/shop/tax.py"}, {"path": "tests/test_old.py"}]}), [])

    def test_test_counts_and_coverage_come_from_checks_and_bot_comments(self):
        from cockpit.impact import coverage, test_results
        runs = [{"name": "Page Tests", "output": {"title": "1 fail, 2 skipped, 3\u2009053 pass in 54m 35s"}, "html_url": "u"},
                {"name": "Unit Tests", "output": {"title": "All 7\u2008040 tests pass in 1m 43s"}},
                {"name": "build", "output": {"title": "Build passed"}}, {"name": "lint", "output": {"title": None}},
                {"name": "codecov/patch", "output": {"title": "85.71% of diff hit (target 80.00%)"}}]
        self.assertEqual([(r["name"], r["passed"], r["failed"], r["skipped"]) for r in test_results(runs)],
                         [("Page Tests", 3053, 1, 2), ("Unit Tests", 7040, 0, 0)])   # GitHub groups thousands with odd spaces
        cov = coverage(runs, [{"author": "codecov[bot]", "body": "Patch coverage is `92.30%` with 2 lines missing. Project coverage is 71.2%.", "url": "c"},
                              {"author": "someone", "body": "coverage is 99%"}])
        self.assertEqual([(c["name"], c["percent"]) for c in cov], [("codecov/patch", 85.71), ("codecov", 92.3)])
        self.assertIn("project 71.2%", cov[1]["text"])

    def test_a_test_counts_by_its_name_or_its_code_never_a_mention_in_its_path(self):
        from cockpit.impact import evidence
        src = lambda path, line: {"path": path, "role": "source", "hunks": [{"lines": [["+", None, 1, line]]}]}
        test = lambda path, line: {"path": path, "role": "test", "hunks": [{"lines": [["+", None, 1, line]]}]}
        rng = lambda *ps: {"ranges": [{"path": x, "tier": "review", "lines": 1, "reason": "code"} for x in ps]}
        pr = {"files": [src("cockpit/view.py", "x = 1"), src("src/shop.py", "y = 2"), src("src/run.py", "def run(job):"),
                        test("tests/test_view.py", "assert True"), test("tests/test_shop_admin.py", "assert True"), test("tests/test_jobs.py", "run(j)")],
              "attention": rng("cockpit/view.py", "src/shop.py", "src/run.py")}
        self.assertEqual([u["path"] for u in evidence(pr)["untested"]], ["src/shop.py"])   # view: test_view.py; run: a test calls run()

    def test_decisions_cite_changed_lines_and_quote_the_plan(self):
        from cockpit.decisions import normalize
        f = {"path": "src/a.py", "hunks": [{"lines": [[" ", 1, 1, "x = 1"], ["+", None, 2, "y = fetch()"], ["+", None, 3, "z = 0"]]}]}
        pr = {"key": "o/r#1", "files": [f], "findings": [{"id": "q1"}]}
        ok, warn = normalize([{"text": "Falls back to the DB", "status": "unplanned", "source": "notes", "effects": ["volume", "made-up"],
                               "ev": [{"path": "src/a.py", "from": 2, "to": 3}], "finding": "q1"},
                              {"text": "Stream feeds the cache", "status": "missing", "plan": "driven by the stream", "source": "pr"},
                              {"text": "Lock per SKU", "status": "planned", "plan": "incremental", "source": "ticket", "ev": [{"path": "src/a.py", "from": 3}]}], pr, resolve=True)
        self.assertEqual(warn, [])
        self.assertEqual([d["status"] for d in ok], ["unplanned", "missing", "planned"])
        self.assertEqual((ok[0]["effects"], ok[0]["finding"], len(ok[0]["ev"][0]["lines"])), (["volume"], "q1", 2))
        bad, warn = normalize([{"text": "No code", "status": "unplanned", "source": "pr"},                                  # needs ev
                               {"text": "Touches context only", "status": "unplanned", "ev": [{"path": "src/a.py", "from": 1}]},
                               {"text": "Changed, no plan quoted", "status": "changed", "ev": [{"path": "src/a.py", "from": 2}]},
                               {"text": "x", "status": "maybe"}, {"text": "Inferred", "status": "unplanned", "source": "guess",
                               "ev": [{"path": "src/a.py", "from": 2}]}], pr)
        self.assertEqual([d["text"] for d in bad], ["Inferred"]); self.assertEqual(bad[0]["source"], "inferred")
        self.assertEqual(len(warn), 5)
        self.assertTrue(any("touches no changed line" in w for w in warn))
        got, warn = normalize([{"text": "Starts on context", "status": "unplanned", "source": "pr", "ev": [{"path": "src/a.py", "from": 1, "to": 3}]},
                               {"id": "d1", "text": "Same id", "status": "unplanned", "source": "pr", "ev": [{"path": "src/a.py", "from": 2}]},
                               {"text": "Bad ev", "status": "unplanned", "source": "pr", "ev": [None, "x"]}], pr)
        self.assertEqual([(d["text"], d["ev"][0]["at"]) for d in got], [("Starts on context", 2)])   # the answer pins to the changed line
        self.assertTrue(any("used by another decision" in w for w in warn)); self.assertTrue(any("each ev is" in w for w in warn))

    def test_notices_stay_open_until_accepted_fixed_or_stale(self):
        from cockpit.decisions import normalize_notices
        prs = {"o/r#1": {"decisions": [{"id": "d1"}]}}
        got, warn = normalize_notices([{"text": "Unlike Gerrit, a re-run fails", "kind": "pattern", "response": "knew", "pr": "o/r#1", "decision": "d1"},
                                       {"text": "Same fix in another PR", "kind": "duplicate", "response": "dismissed", "state": "maybe", "pr": "o/r#9"},
                                       {"text": "Linked to nothing", "pr": "o/r#1", "decision": "d9"}, {"kind": "risk"}], prs)
        self.assertEqual([(n["kind"], n["response"], n["state"], n["pr"], n["decision"]) for n in got],
                         [("pattern", "knew", "open", "o/r#1", "d1"), ("duplicate", "dismissed", "open", None, ""), ("other", "none", "open", "o/r#1", "")])
        self.assertEqual(len(warn), 4)   # bad state, unknown pr, unknown decision, no text
        got, warn = normalize_notices([{"text": "A list for a PR", "pr": ["o/r#1"], "kind": {"x": 1}}, {"text": "Fine", "pr": "o/r#1"}], prs)
        self.assertEqual([(n["text"], n["pr"], n["kind"]) for n in got], [("A list for a PR", None, "other"), ("Fine", "o/r#1", "other")])
        self.assertTrue(any("must be a string" in w for w in warn))

    def test_notes_cli_output_and_failures_never_stop_a_review(self):
        import subprocess
        import cockpit.notes as N
        outs = iter(['trace x\n{\n  "repo_ref": "123"\n}\n', '{"lookupStatus": "no_pr_notes"}', '{"error": "MT-FORBIDDEN"}'])
        orig = subprocess.run
        subprocess.run = lambda argv, **kw: subprocess.CompletedProcess(argv, 0, next(outs), "")
        try:
            self.assertEqual(N._read("qodo", "resolve-repository", []), ({"repo_ref": "123"}, None))   # pretty-printed JSON after a trace line
            self.assertEqual(N._read("qodo", "for-pr", [])[0]["lookupStatus"], "no_pr_notes")
            self.assertEqual(N._read("qodo", "for-pr", []), (None, "for-pr: MT-FORBIDDEN"))   # an error as a plain string
        finally:
            subprocess.run = orig
        orig_for, orig_cmd = N.for_pr, N._cmd
        N._cmd = lambda cfg: None
        N.for_pr = lambda pr, cfg, cache: (_ for _ in ()).throw(AttributeError("x"))
        try:
            prs = [{"repo": "o/r", "number": 1}]
            N.collect(prs, {})
            self.assertEqual(prs[0]["notes"]["status"], "unavailable")
        finally:
            N.for_pr, N._cmd = orig_for, orig_cmd

    def test_notes_reader_resolves_the_repo_and_follows_pages(self):
        import cockpit.notes as N
        calls = []
        pages = {"for-pr": [{"result_is_page": True, "text": '{"lookupStatus":"ready","prContext":{"id":"n1","publishedRevision":2,"document":',
                             "next_read_cursor": "c2"},
                            {"result_is_page": True, "text": '{"contentMarkdown":"## Intent\\nCache","commitShaAtUpdate":"abc","validationChecks":[{"name":"unit","result":"passed"}]}},'
                             '"developmentTrack":{"id":"t1","document":{"title":"Prices","contentMarkdown":"## Goal"}},"validationApplicability":[true]}', "next_read_cursor": None}]}
        def fake(cmd, leaf, args):
            calls.append(leaf)
            if leaf == "resolve-repository":
                return {"repo_ref": "123"}, None
            parts = pages[leaf]; text = "".join(x["text"] for x in parts)
            return json.loads(text), None
        orig_read, orig_cmd = N._read, N._cmd
        N._cmd = lambda cfg: "qodo"
        try:
            N._read = fake
            got = N.for_pr({"repo": "o/r", "number": 1, "head_sha": "abc"}, {}, {})
            self.assertEqual((got["status"], got["pr"]["head_matches"], got["track"]["title"], got["pr"]["validation"][0]["applies"]), ("ready", True, "Prices", True))
            N._read = lambda cmd, leaf, args: ({"repo_ref": "123"}, None) if leaf == "resolve-repository" else ({"lookupStatus": "no_pr_notes"}, None)
            self.assertEqual(N.for_pr({"repo": "o/r", "number": 2, "head_sha": "x"}, {}, {})["why"], "no PR Review Notes are bound to this PR")
            N._read = lambda cmd, leaf, args: (None, "resolve-repository: MT-NOT-FOUND")
            self.assertIn("not registered", N.for_pr({"repo": "o/r", "number": 3}, {}, {})["why"])
        finally:
            N._read, N._cmd = orig_read, orig_cmd
        N._cmd = lambda cfg: None
        try:
            self.assertEqual(N.for_pr({"repo": "o/r", "number": 1}, {}, {})["status"], "unavailable")
        finally:
            N._cmd = orig_cmd

    def test_merge_danger_door_domains_and_deploy(self):
        from cockpit.impact import domains, door_guess, normalize, normalize_deploy, normalize_door
        f = lambda path, role="source": {"path": path, "role": role}
        pr = {"files": [f("db/migrations/0042_add_col.py"), f("api/routes/rules.py"), f("web/Button.tsx"), f("config/flags.yaml"),
                        f("svc/rules.py"), f("tests/test_rules.py", "test"), f("README.md", "docs")]}
        self.assertEqual(door_guess(pr)["verdict"], "one-way"); self.assertIn("a migration", door_guess(pr)["why"])
        self.assertEqual(door_guess({"files": [f("svc/rules.py")]})["verdict"], "two-way")
        self.assertEqual(door_guess({"files": [f("infra/main.tf")]})["verdict"], "one-way")   # terraform outside a terraform/ folder
        self.assertEqual(door_guess({"files": [f("tests/fixtures/seed.sql", "test"), f("docs/migrations/howto.md", "docs")]})["verdict"], "two-way")
        self.assertEqual({k: v for k, v in domains({"files": [f("api/schema.graphql"), f("app/app.js"), f("app/main.py"), f("infra/main.tf")]}).items()},
                         {"contract": ["api/schema.graphql"], "frontend": ["app/app.js"], "backend": ["app/main.py"], "config": ["infra/main.tf"]})
        self.assertEqual({k: len(v) for k, v in domains(pr).items()}, {"db": 1, "contract": 1, "frontend": 1, "config": 1, "backend": 1})   # tests, docs left out
        prs = {"o/r#1": {}}
        steps, warn = normalize_deploy([{"step": "Migrate", "prs": ["o/r#1", "o/r#9"], "why": "first", "verify": "the column exists"}, {"prs": []}], prs)
        self.assertEqual(steps, [{"step": "Migrate", "prs": ["o/r#1"], "why": "first", "verify": "the column exists"}]); self.assertEqual(len(warn), 2)
        self.assertEqual(normalize_deploy([{"step": "Ship", "prs": [1, "#1"]}], prs)[0][0]["prs"], ["o/r#1", "o/r#1"])   # a bare number, when one PR has it
        steps, warn = normalize_deploy([{"step": "Ship", "prs": [{"key": "o/r#1"}, ["o/r#1"], True]}], prs)   # not a PR reference: a warning, not a crash
        self.assertEqual(steps[0]["prs"], []); self.assertEqual(len(warn), 1)
        self.assertEqual(normalize_door({"verdict": "one-way", "why": "drops a column"})[0]["verdict"], "one-way")
        self.assertIsNone(normalize_door({"verdict": "maybe"})[0])
        rows, _ = normalize([{"component": "x", "prs": ["o/r#1"], "door": "one-way", "undo": "u", "fails": "f", "notice": "n"},
                             {"component": "y", "prs": ["o/r#1"], "door": "sideways"}], prs)
        self.assertEqual([(r["door"], r["undo"], r["fails"], r["notice"]) for r in rows], [("one-way", "u", "f", "n"), ("", "", "", "")])

    def test_failure_counts_reruns_and_bad_rows(self):
        from cockpit.impact import normalize, test_results
        runs = [{"name": "unit", "id": 1, "completed_at": "2026-10-15T01:00:00Z", "output": {"title": "3 tests failed, 10 passed"}},
                {"name": "unit", "id": 2, "completed_at": "2026-10-15T02:00:00Z", "output": {"title": "13 passed"}},   # the rerun passed
                {"name": "e2e", "id": 3, "output": {"title": "2 errors, 1 fail"}}, {"name": "lint", "output": {"title": "12 failed, 3 skipped"}}]
        got = {r["name"]: (r["passed"], r["failed"], r["skipped"]) for r in test_results(runs)}
        self.assertEqual(got, {"unit": (13, 0, 0), "e2e": (0, 3, 0), "lint": (0, 12, 3)})
        rows, warn = normalize([{"component": "x", "prs": 5, "affects": ["y"], "gaps": ["z"]}], {})
        self.assertEqual(rows[0]["prs"], []); self.assertTrue(any("prs must be a list" in w for w in warn))

    def test_rows_are_checked_and_derived_rows_group_by_folder(self):
        from cockpit.impact import derived, normalize
        rows, warn = normalize([{"component": "Cart", "prs": ["o/r#1", "o/r#9"], "risk": "severe", "affects": ["checkout"]},
                                {"component": "Tax", "risk": "high", "affects": "invoices", "evidence": ["test_tax"]}, {"risk": "low"}], {"o/r#1": {}})
        self.assertEqual([(r["component"], r["risk"]) for r in rows], [("Tax", "high"), ("Cart", "medium")])   # riskiest first
        self.assertEqual(rows[1]["prs"], ["o/r#1"]); self.assertEqual(rows[0]["affects"], ["invoices"])
        text = " ".join(warn)
        for frag in ("risk must be high, medium or low", "unknown prs", "give the evidence, or the gap", "needs a component"):
            self.assertIn(frag, text)
        d = derived({"prs": [self.pr()]})
        self.assertEqual([(r["component"], r["risk"], r["gaps"]) for r in d], [("src/shop", "medium", ["no changed test calls 1 of 2"])])


if __name__ == "__main__":
    unittest.main()
