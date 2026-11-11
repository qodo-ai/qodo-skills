"""GitHub review threads: which findings have one, and replying to or resolving them from the cockpit.

A Qodo (or scanner) finding that GitHub shows as an inline comment links to its thread's first comment
(`.../pull/12#discussion_r<id>`). A note on that finding is posted as a reply in the thread, not as a line
in a new review, and can resolve the thread. Findings without a thread (summary-only items, issue comments)
keep going into the review body.
"""
from __future__ import annotations

import json
import re

from .util import gh

DISCUSSION = re.compile(r"#discussion_r(\d+)$")

_QUERY = """query($o:String!,$r:String!,$n:Int!,$after:String){repository(owner:$o,name:$r){pullRequest(number:$n){
reviewThreads(first:100,after:$after){pageInfo{hasNextPage endCursor}
nodes{id isResolved isOutdated viewerCanResolve viewerCanUnresolve viewerCanReply comments(first:1){nodes{databaseId}}}}}}}"""


def comment_id(f: dict) -> int | None:
    """The thread's first comment id, from the finding's link (or the old thread's link once outdated)."""
    for k in ("url", "thread_url"):
        m = DISCUSSION.search(f.get(k) or "")
        if m:
            return int(m.group(1))
    m = re.fullmatch(r"gh\d*:[^:]+:(\d+)", str(f.get("inline_comment_id") or ""))   # Qodo CLI: gh1:<thread node>:<comment>
    return int(m.group(1)) if m else None


def fetch(repo: str, number: int) -> dict[int, dict]:
    """{first comment id: thread state} for every review thread on the PR. Raises RuntimeError if gh fails."""
    owner, name = repo.split("/", 1)
    out, after = {}, None
    for _ in range(30):   # 3000 threads; GitHub's own pages are 100
        args = ["api", "graphql", "-f", f"query={_QUERY}", "-f", f"o={owner}", "-f", f"r={name}", "-F", f"n={number}"]   # -f: always a string
        if after:
            args += ["-f", f"after={after}"]
        res = json.loads(gh(args))
        if res.get("errors"):
            raise RuntimeError("; ".join(e.get("message", "") for e in res["errors"])[:300])
        page = (((res.get("data") or {}).get("repository") or {}).get("pullRequest") or {}).get("reviewThreads") or {}
        for t in page.get("nodes") or []:
            first = ((t.get("comments") or {}).get("nodes") or [{}])[0].get("databaseId")
            if first:
                out[int(first)] = {"id": t["id"], "resolved": bool(t.get("isResolved")), "outdated": bool(t.get("isOutdated")),
                                   "can_reply": bool(t.get("viewerCanReply")), "can_resolve": bool(t.get("viewerCanResolve"))}
        info = page.get("pageInfo") or {}
        if not info.get("hasNextPage"):
            break
        after = info.get("endCursor")
    return out


def attach(findings: list[dict], threads: dict[int, dict]) -> None:
    """Give each finding that has a review thread its state, as `thread` (shown in the app, used at publish)."""
    for f in findings:
        cid = comment_id(f)
        if cid and cid in threads:
            f["thread"] = {"comment_id": cid, **threads[cid]}
        else:
            f.pop("thread", None)


def reply(repo: str, number: int, cid: int, body: str) -> dict:
    return json.loads(gh(["api", f"repos/{repo}/pulls/{number}/comments/{cid}/replies", "--method", "POST", "--input", "-"],
                         input_text=json.dumps({"body": body})))


def resolve(thread_id: str) -> None:
    res = json.loads(gh(["api", "graphql", "-f", "query=mutation($t:ID!){resolveReviewThread(input:{threadId:$t}){thread{isResolved}}}",
                         "-f", f"t={thread_id}"]))
    if res.get("errors"):
        raise RuntimeError("; ".join(e.get("message", "") for e in res["errors"])[:300])
