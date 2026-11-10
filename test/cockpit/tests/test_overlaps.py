"""Other work on the same code: spans, closeness, and each source with GitHub and the disk mocked."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cockpit import overlaps as O
from cockpit.collect import parse_diff

OURS = """diff --git a/svc/crud.py b/svc/crud.py
--- a/svc/crud.py
+++ b/svc/crud.py
@@ -425,6 +425,8 @@ def update_enforcement(rule_id):
     rule = get(rule_id)
-    rule.state = state
+    if rule.muted:
+        return refuse()
+    rule.state = state
     save(rule)
"""
THEIRS_NEAR = """diff --git a/svc/crud.py b/svc/crud.py
--- a/svc/crud.py
+++ b/svc/crud.py
@@ -430,4 +430,5 @@ def update_enforcement(rule_id):
     save(rule)
+    audit(rule)
     return rule
"""
THEIRS_FUNC = """diff --git a/svc/crud.py b/svc/crud.py
--- a/svc/crud.py
+++ b/svc/crud.py
@@ -470,3 +470,4 @@ def update_enforcement(rule_id):
     log(rule)
+    metric(rule)
"""
THEIRS_FAR = """diff --git a/svc/crud.py b/svc/crud.py
--- a/svc/crud.py
+++ b/svc/crud.py
@@ -900,3 +900,4 @@ def other():
     x = 1
+    y = 2
"""


def pr(key="o/r#2", diff=OURS, **kw):
    files = [{"path": p, "hunks": h, "role": "source"} for p, h in parse_diff(diff).items()]
    return {"key": key, "repo": "o/r", "number": int(key.split("#")[1]), "files": files, "base": "main", "head_sha": "h2", **kw}


class OverlapTests(unittest.TestCase):
    def test_spans_and_closeness(self):
        ours = O.spans(parse_diff(OURS)["svc/crud.py"])
        self.assertEqual(ours[0]["func"], "def update_enforcement(rule_id):")
        self.assertEqual(ours[0]["old"], [426, 426])
        self.assertEqual(O.closeness(ours, O.spans(parse_diff(THEIRS_NEAR)["svc/crud.py"]), 5)[0], "lines")
        self.assertEqual(O.closeness(ours, O.spans(parse_diff(THEIRS_FUNC)["svc/crud.py"]), 5)[0], "function")
        self.assertEqual(O.closeness(ours, O.spans(parse_diff(THEIRS_FAR)["svc/crud.py"]), 5)[0], "file")
        self.assertEqual(O.closeness(ours, O.spans(parse_diff(THEIRS_NEAR)["svc/crud.py"]), 0)[0], "function")   # drift beyond tolerance

    def test_noise_files_are_never_compared(self):
        p = pr(diff=OURS.replace("svc/crud.py", "uv.lock"))
        self.assertEqual(O._ours(p, 25), {})

    def test_open_prs_reads_diffs_only_for_shared_paths(self):
        page = {"data": {"repository": {"pullRequests": {"pageInfo": {"hasNextPage": False}, "nodes": [
            {"number": 7, "title": "audit", "url": "u7", "isDraft": False, "updatedAt": "t", "headRefName": "a", "baseRefName": "main",
             "author": {"login": "x"}, "files": {"nodes": [{"path": "svc/crud.py"}]}},
            {"number": 8, "title": "other", "url": "u8", "isDraft": True, "updatedAt": "t", "headRefName": "b", "baseRefName": "main",
             "author": {"login": "y"}, "files": {"nodes": [{"path": "README.md"}]}},
            {"number": 2, "title": "me", "url": "u2", "isDraft": False, "updatedAt": "t", "headRefName": "c", "baseRefName": "main",
             "author": {"login": "z"}, "files": {"nodes": [{"path": "svc/crud.py"}]}}]}}}}
        calls = []
        def gh(args, input_text=None):
            calls.append(args)
            return json.dumps(page) if args[1] == "graphql" else THEIRS_NEAR
        with mock.patch.object(O, "gh", side_effect=gh):
            hits = O.open_prs([pr()], O.conf({}), [])
        self.assertEqual([(h["key"], h["closeness"], h["state"]) for h in hits], [("o/r#7", "lines", "open")])
        self.assertEqual(sum(1 for a in calls if a[:2] == ["pr", "diff"]), 1)   # #8 shares no path, #2 is this review

    def test_merged_since_merge_base(self):
        def gh_json(args):
            u = args[1]
            if "compare" in u:
                return {"sha": "mb", "at": "2026-10-01T00:00:00Z"}
            if u.startswith("repos/o/r/commits?"):
                return [{"sha": "c1" * 20, "commit": {"message": "x", "committer": {"date": "2026-10-07T00:00:00Z"}}}, {"sha": "mb"}]
            if u.endswith("/pulls"):
                return [{"number": 6, "title": "open branch holding the commit", "merged_at": None},
                        {"number": 5, "title": "muted rules", "html_url": "u5", "user": {"login": "m"}, "merged_at": "2026-10-07T00:00:00Z", "base": {"ref": "main"}}]
            return {"files": [{"filename": "svc/crud.py", "patch": THEIRS_NEAR.split("+++ b/svc/crud.py\n", 1)[1]}]}
        def gh(args, input_text=None):   # the base gained c1 (and an old-dated c3) since the merge-base
            return ("c1" * 20) + "\n" + ("c3" * 20) + "\n"
        def gh_json2(args):
            if "total_commits" in args:
                return 2
            if args[1].startswith("repos/o/r/commits?"):
                self.assertIn("--paginate", args)
                return [{"sha": "c1" * 20, "commit": {"message": "x", "committer": {"date": "2026-10-07T00:00:00Z"}}},
                        {"sha": "c2" * 20, "commit": {"message": "not on the base since", "committer": {"date": "2026-10-08T00:00:00Z"}}}, {"sha": "mb"}]
            return gh_json(args)
        with mock.patch.object(O, "gh_json", side_effect=gh_json2), mock.patch.object(O, "gh", side_effect=gh):
            hits = O.merged([pr()], O.conf({}), [])
            self.assertEqual([(h["key"], h["state"], h["closeness"]) for h in hits], [("o/r#5", "merged", "lines")])   # c2 isn't in the ancestry
            self.assertEqual(O.merged([pr(state="MERGED")], O.conf({}), []), [])   # a merged PR has nothing merged under it

    def test_other_sessions_and_the_reading_plan(self):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "s1").mkdir()
        (tmp / "s1" / "review-data.json").write_text(json.dumps({"prs": [pr("o/r#9", THEIRS_FUNC, title="other package")]}))
        with mock.patch.object(O, "SESSIONS", tmp), mock.patch.object(O, "gh", return_value="OPEN"):
            hits, warn = O.external([p := pr()], {"overlaps": {"sources": {"open_prs": False, "merged": False}}}, session="now")
        self.assertEqual([(h["source"], h["key"], h["closeness"]) for h in hits], [("session", "o/r#9", "function")])
        self.assertEqual(p["overlap_spans"], [{"path": "svc/crud.py", "side": "new", "from": 426, "to": 428, "who": "o/r#9"}])
        from cockpit.attention import compute
        att, _ = compute(p)
        self.assertTrue(any("other work changes these lines" in (b.get("why") or []) for b in att["blocks"]))

    def test_agent_sessions_are_off_by_default_and_wired(self):
        called = []
        with mock.patch.dict(O.AGENT_SOURCES, {"checkpoints": lambda prs, o, w: called.append("cp") or [], "tracks": lambda prs, o, w: called.append("tr") or []}):
            O.external([pr()], {"overlaps": {"sources": {"open_prs": False, "merged": False, "sessions": False}}})
            self.assertEqual(called, [])
            O.external([pr()], {"overlaps": {"sources": {"open_prs": False, "merged": False, "sessions": False, "agent_sessions": True}}})
            self.assertEqual(called, ["cp", "tr"])

    def test_checkpoints_skip_this_prs_own_work_and_other_repos(self):
        tmp = Path(tempfile.mkdtemp())
        d = tmp / ".qodo" / "review-checkpoints" / "a" / "b"; d.mkdir(parents=True)
        import time
        (d / "1.json").write_text(json.dumps({"diff": THEIRS_NEAR, "baseSha": "base1", "submittedAt": time.time() * 1000}))
        (d / "2.json").write_text(json.dumps({"diff": OURS, "baseSha": "base1", "submittedAt": time.time() * 1000}))   # this PR, before it was one
        with mock.patch.object(O.Path, "home", return_value=tmp), mock.patch.object(O, "gh", return_value="sha"):
            hits = O._checkpoints([pr()], O.conf({}), [])
        self.assertEqual([(h["source"], h["agent_source"], h["closeness"]) for h in hits], [("agent", "checkpoints", "lines")])
        with mock.patch.object(O.Path, "home", return_value=tmp), mock.patch.object(O, "gh", side_effect=RuntimeError("404")):
            self.assertEqual(O._checkpoints([pr()], O.conf({}), []), [])   # base commit not in this repo

    def test_large_prs_are_read_past_their_first_page_of_files(self):
        page = {"data": {"repository": {"pullRequests": {"pageInfo": {"hasNextPage": False}, "nodes": [
            {"number": 7, "title": "big", "url": "u7", "isDraft": False, "updatedAt": "t", "headRefName": "a", "baseRefName": "main",
             "author": {"login": "x"}, "files": {"totalCount": 101, "nodes": [{"path": "other.py"}]}}]}}}}
        def gh(args, input_text=None):
            if args[1] == "graphql":
                return json.dumps(page)
            if "/files" in args[1]:
                return "other.py\nsvc/crud.py\n"
            return THEIRS_NEAR
        with mock.patch.object(O, "gh", side_effect=gh):
            hits = O.open_prs([pr()], O.conf({}), [])
        self.assertEqual([h["key"] for h in hits], ["o/r#7"])

    def test_paths_with_spaces_and_reserved_characters(self):
        spaced = OURS.replace("svc/crud.py", "svc/my crud&#1.py")
        page = {"data": {"repository": {"pullRequests": {"pageInfo": {"hasNextPage": False}, "nodes": [
            {"number": 7, "title": "big", "url": "u7", "isDraft": False, "updatedAt": "t", "headRefName": "a", "baseRefName": "main",
             "author": {"login": "x"}, "files": {"totalCount": 101, "nodes": [{"path": "other.py"}]}}]}}}}
        def gh(args, input_text=None):
            if args[1] == "graphql":
                return json.dumps(page)
            if "/files" in args[1]:
                return "other.py\nsvc/my crud&#1.py\n"
            return THEIRS_NEAR.replace("svc/crud.py", "svc/my crud&#1.py")
        with mock.patch.object(O, "gh", side_effect=gh):
            self.assertEqual([h["key"] for h in O.open_prs([pr(diff=spaced)], O.conf({}), [])], ["o/r#7"])   # a spaced path still matches
        urls = []
        def gh_json(args):
            urls.append(args[1])
            return {"sha": "mb", "at": "2026-10-01T00:00:00Z"} if "compare" in args[1] else []
        with mock.patch.object(O, "gh_json", side_effect=gh_json), mock.patch.object(O, "gh", return_value=""):
            O.merged([pr(diff=spaced)], O.conf({}), [])
        q = next(u for u in urls if u.startswith("repos/o/r/commits?"))
        self.assertIn("path=svc%2Fmy+crud%26%231.py", q)   # & and # encoded, not cutting the query

    def test_other_base_branches_match_by_function_at_most(self):
        p = pr()
        same = O._hit(p, "open_pr", {"base": "main"}, "svc/crud.py", O.spans(parse_diff(OURS)["svc/crud.py"]), O.spans(parse_diff(THEIRS_NEAR)["svc/crud.py"]), 5)
        other = O._hit(p, "open_pr", {"base": "release-1"}, "svc/crud.py", O.spans(parse_diff(OURS)["svc/crud.py"]), O.spans(parse_diff(THEIRS_NEAR)["svc/crud.py"]), 5)
        self.assertEqual((same["closeness"], other["closeness"]), ("lines", "function"))

    def test_sessions_without_a_live_list_ask_github(self):
        tmp = Path(tempfile.mkdtemp())
        for sid, n in (("s1", 9), ("s2", 10)):
            (tmp / sid).mkdir()
            (tmp / sid / "review-data.json").write_text(json.dumps({"prs": [pr(f"o/r#{n}", THEIRS_FUNC)]}))
        state = {"9": "OPEN\n", "10": "MERGED\n"}
        with mock.patch.object(O, "SESSIONS", tmp), mock.patch.object(O, "gh", side_effect=lambda a, input_text=None: state[a[2]]):
            hits = O.sessions([pr()], O.conf({}), [], "now")
        self.assertEqual([h["key"] for h in hits], ["o/r#9"])   # #10 merged since; a snapshot isn't proof
        with mock.patch.object(O, "SESSIONS", tmp), mock.patch.object(O, "gh", side_effect=RuntimeError("offline")):
            self.assertEqual(O.sessions([pr()], O.conf({}), [], "now"), [])   # unknown is not open

    def test_deletions_reach_the_plan_on_the_old_side(self):
        dele = """diff --git a/svc/crud.py b/svc/crud.py
--- a/svc/crud.py
+++ b/svc/crud.py
@@ -425,4 +425,3 @@ def update_enforcement(rule_id):
     rule = get(rule_id)
-    rule.state = state
     save(rule)
"""
        tmp = Path(tempfile.mkdtemp()); (tmp / "s1").mkdir()
        (tmp / "s1" / "review-data.json").write_text(json.dumps({"prs": [pr("o/r#9", THEIRS_NEAR)]}))
        p = pr(diff=dele)
        with mock.patch.object(O, "SESSIONS", tmp), mock.patch.object(O, "gh", return_value="OPEN"):
            O.external([p], {"overlaps": {"sources": {"open_prs": False, "merged": False}}}, session="now")
        self.assertEqual(p["overlap_spans"], [{"path": "svc/crud.py", "side": "old", "from": 426, "to": 426, "who": "o/r#9"}])

    def test_distinct_tracks_stay_apart(self):
        a = {"for": "o/r#2", "source": "agent", "key": None, "track_id": "t1", "path": "svc/crud.py", "closeness": "file", "ours": None, "ours_new": None}
        with mock.patch.dict(O.AGENT_SOURCES, {"tracks": lambda prs, o, w: [a, {**a, "track_id": "t2"}, {**a}]}):
            hits, _ = O.external([pr()], {"overlaps": {"sources": {"open_prs": False, "merged": False, "sessions": False, "agent_sessions": True},
                                                       "agent_sources": ["tracks"]}})
        self.assertEqual(sorted(h["track_id"] for h in hits), ["t1", "t2"])

    def test_tracks_resolve_the_repo_id_and_read_every_page(self):
        import cockpit.notes as N
        calls = []
        pages = [{"items": [], "nextCursor": "c1"},   # a page of records we can't read: empty, with a cursor
                 {"items": [{"id": "t9", "document": {"title": "Cache rework", "contentMarkdown": "Touches `svc/crud.py` and the jobs"}},
                            {"id": "own", "document": {"title": "This PR's plan", "contentMarkdown": "svc/crud.py"}}], "nextCursor": None}]
        def fake(cmd, leaf, args):
            calls.append((leaf, args))
            return ({"repo_ref": "123"}, None) if leaf == "resolve-repository" else (pages[len([c for c in calls if c[0] == "find-tracks"]) - 1], None)
        p = {**pr(), "notes": {"track": {"id": "own"}}}
        with mock.patch.object(N, "_cmd", lambda cfg: "qodo"), mock.patch.object(N, "_read", fake):
            hits = O._tracks([p], {"max_paths": 25, "tolerance": 5}, [])
        finds = [a for leaf, a in calls if leaf == "find-tracks"]
        self.assertEqual(finds[0][finds[0].index("--repo-ref") + 1], "123")   # the registry id, not owner/repo
        self.assertEqual(finds[1][finds[1].index("--after") + 1], "c1")       # the empty page's cursor is followed
        self.assertEqual([(h["track_id"], h["title"], h["closeness"]) for h in hits], [("t9", "Cache rework", "file")])

    def test_tracks_match_whole_paths_per_pr_and_say_when_they_stop(self):
        import cockpit.notes as N
        tracks = [{"id": "mine", "document": {"title": "#2's plan", "contentMarkdown": "We change svc/crud.py"}},
                  {"id": "near", "document": {"title": "Look-alike", "contentMarkdown": "Only docs/svc/crud.py and svc/crud.py.bak"}}]
        read = lambda cmd, leaf, args: ({"repo_ref": "1"}, None) if leaf == "resolve-repository" else ({"items": tracks, "nextCursor": None}, None)
        p2, p3 = {**pr(), "notes": {"track": {"id": "mine"}}}, pr("o/r#3")
        with mock.patch.object(N, "_cmd", lambda cfg: "qodo"), mock.patch.object(N, "_read", read):
            hits = O._tracks([p2, p3], {"max_paths": 25, "tolerance": 5}, [])
        self.assertEqual([(h["for"], h["track_id"]) for h in hits], [("o/r#3", "mine")])   # #2's own track is other work for #3; look-alikes aren't
        endless = lambda cmd, leaf, args: ({"repo_ref": "1"}, None) if leaf == "resolve-repository" else ({"items": [], "nextCursor": "again"}, None)
        warn = []
        with mock.patch.object(N, "_cmd", lambda cfg: "qodo"), mock.patch.object(N, "_read", endless), mock.patch.object(O, "TRACKS_PAGES", 3):
            O._tracks([pr()], {"max_paths": 25, "tolerance": 5}, warn)
        self.assertTrue(any("stopped after 3 pages" in w for w in warn))

    def test_a_failing_source_only_warns(self):
        with mock.patch.object(O, "open_prs", side_effect=ValueError("boom")):
            hits, warn = O.external([pr()], {"overlaps": {"sources": {"merged": False, "sessions": False}}})
        self.assertEqual(hits, [])
        self.assertTrue(warn and "open_prs failed" in warn[0])


if __name__ == "__main__":
    unittest.main()
