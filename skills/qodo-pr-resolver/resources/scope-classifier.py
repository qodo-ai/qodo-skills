#!/usr/bin/env python3
r"""Classify Qodo review findings by their location relative to git diffs.

Used by the qodo-pr-resolver skill (Step 3c) to separate findings into:
  - "current"      : the finding sits on code changed in the CURRENT review round
  - "carried_over" : inside the overall PR diff, but not the current round (an earlier round)
  - "outside_pr"   : not inside the PR diff at all (likely stale / mislocated)
  - "unknown"      : the finding carries no usable line number

The approach is ported from pr-agent (codium-proxy): parse unified-diff hunk
headers `@@ -a,b +c,d @@`, take the NEW-file line ranges, and test whether each
finding's line falls inside them. Pure stdlib, deterministic, no network.

Granularity is hunk-level: a finding counts as "in scope" if its line falls
inside any changed hunk of the new file. Pass `git diff --unified=0 ...` to keep
the ranges tight around the actual edits (recommended); a wider context just
makes membership more lenient.

Usage:
  python3 scope-classifier.py \
    --pr-diff      pr.diff \       # unified diff of the whole PR (merge-base..HEAD)
    --current-diff current.diff \  # unified diff of the current round (base_round..HEAD)
    --findings     findings.json   # JSON: [{"file": "...", "line": N}, ...]

  Omit --current-diff for a single-round PR: every in-PR finding is "current".

Findings JSON accepts per item: {"file": str, "line": int}
  or {"file": str, "start_line": int, "end_line": int}. Any extra keys (title,
  etc.) are echoed back untouched with an added "scope" field.

Output (stdout): the findings array, each item with an added "scope" field.
"""

import argparse
import json
import re
import sys

HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
DIFFGIT_RE = re.compile(r"^diff --git a/.* b/(.+)$")


def parse_new_side_ranges(diff_text):
    """Parse a unified diff into {file_path: [(start, end), ...]} of changed
    NEW-file line ranges. Keyed by the new-file path. Deletion-only hunks
    (new-side size 0) and deleted files (+++ /dev/null) contribute nothing."""
    ranges = {}
    current_file = None
    prev_minus_header = False  # True right after a "--- " line (so "+++ " is a header, not added content)
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            m = DIFFGIT_RE.match(line)
            current_file = m.group(1) if m else None
            if current_file is not None:
                ranges.setdefault(current_file, [])
            prev_minus_header = False
            continue
        if line.startswith("--- "):
            prev_minus_header = True
            continue
        if line.startswith("+++ ") and prev_minus_header:
            prev_minus_header = False
            path = line[4:].strip()
            if path == "/dev/null":
                current_file = None  # file deleted: no new-side lines
            else:
                current_file = path[2:] if path.startswith(("a/", "b/")) else path
                ranges.setdefault(current_file, [])
            continue
        prev_minus_header = False
        if line.startswith("@@") and current_file is not None:
            m = HUNK_RE.match(line)
            if not m:
                continue
            start_new = int(m.group(3))
            size_new = int(m.group(4)) if m.group(4) is not None else 1
            if size_new > 0:
                ranges[current_file].append((start_new, start_new + size_new - 1))
    return ranges


def _norm(path):
    return path[2:] if path.startswith("./") else path


def overlaps(start, end, rngs):
    return any(not (end < s or start > e) for (s, e) in rngs)


def classify(finding, pr_ranges, cur_ranges, single_round):
    f = _norm(str(finding.get("file", "")))
    raw_start = finding.get("start_line", finding.get("line"))
    if raw_start is None:
        return "unknown"
    start = int(raw_start)
    end = int(finding.get("end_line", finding.get("line", start)))
    if end < start:
        start, end = end, start
    pr = pr_ranges.get(f, [])
    if single_round:
        return "current" if overlaps(start, end, pr) else "outside_pr"
    if overlaps(start, end, cur_ranges.get(f, [])):
        return "current"
    if overlaps(start, end, pr):
        return "carried_over"
    return "outside_pr"


def _read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def main():
    ap = argparse.ArgumentParser(description="Classify findings by git-diff scope.")
    ap.add_argument("--pr-diff", required=True, help="Unified diff of the whole PR (merge-base..HEAD).")
    ap.add_argument("--current-diff", help="Unified diff of the current round (base_round..HEAD). Omit for single-round.")
    ap.add_argument("--findings", required=True, help="JSON array of findings ({file, line} / {file, start_line, end_line}).")
    args = ap.parse_args()

    pr_ranges = parse_new_side_ranges(_read(args.pr_diff))
    single_round = args.current_diff is None
    cur_ranges = {} if single_round else parse_new_side_ranges(_read(args.current_diff))

    findings = json.loads(_read(args.findings))
    if not isinstance(findings, list):
        print("findings JSON must be an array", file=sys.stderr)
        return 2

    out = [dict(fnd, scope=classify(fnd, pr_ranges, cur_ranges, single_round)) for fnd in findings]
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
