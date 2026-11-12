"""Regenerate fixtures/demo-prs.json from the readable diffs below.

python3 fixtures/build_demo.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cockpit.collect import parse_diff  # noqa: E402

REPO = "qodo-ai/shop-demo"

PRS = [
 {
  "number": 101, "title": "Refresh price cache incrementally instead of full reload", "author": "maya",
  "base": "main", "head": "maya/incremental-price-cache", "labels": ["performance"],
  "body": "Full 2GB reloads every 10 min cause GC pauses that exhaust the checkout DB pool.\nThis switches to incremental refresh driven by the `price_changed` stream.",
  "summary": "Replaces the 10-minute full reload of the price cache with incremental updates from the `price_changed` stream, and caps the cache at 500k SKUs. Checkout now reads through `PriceCache.get()` instead of the raw dict.",
  "risk": "**Medium.** Cache misses now fall through to the DB on the checkout path. If the stream lags, prices can be stale for up to the consumer lag.",
  "diagrams": [{"id": "flow", "title": "Price refresh: before vs after", "mermaid":
    "sequenceDiagram\n  participant S as price_changed stream\n  participant C as PriceCache\n  participant K as Checkout\n  participant D as DB\n  S->>C: apply(sku, cents)\n  K->>C: get(sku)\n  alt hit\n    C-->>K: cents\n  else miss\n    C->>D: SELECT price_cents\n    D-->>C: cents\n    C-->>K: cents\n  end"}],
  "checks": [{"name": "unit-tests", "state": "SUCCESS"}, {"name": "lint", "state": "SUCCESS"}],
  "diff": """diff --git a/src/cache/price_cache.py b/src/cache/price_cache.py
--- a/src/cache/price_cache.py
+++ b/src/cache/price_cache.py
@@ -1,18 +1,31 @@
-import threading, time
+import threading
+from collections import OrderedDict
 from src.db import fetch_all_prices, fetch_price

+MAX_SKUS = 500_000
+
 class PriceCache:
     def __init__(self):
-        self._prices = {}
-        threading.Thread(target=self._reload_loop, daemon=True).start()
+        self._prices = OrderedDict()
+        self._lock = threading.Lock()

-    def _reload_loop(self):
-        while True:
-            self._prices = fetch_all_prices()  # ~2GB
-            time.sleep(600)
+    def apply(self, sku, cents):
+        with self._lock:
+            self._prices[sku] = cents
+            self._prices.move_to_end(sku)
+            if len(self._prices) > MAX_SKUS:
+                self._prices.popitem(last=False)

-    def get(self, sku):
-        return self._prices[sku]
+    def get(self, sku):
+        with self._lock:
+            if sku in self._prices:
+                return self._prices[sku]
+        cents = fetch_price(sku)
+        self.apply(sku, cents)
+        return cents
diff --git a/src/payments/checkout.py b/src/payments/checkout.py
--- a/src/payments/checkout.py
+++ b/src/payments/checkout.py
@@ -8,9 +8,9 @@ from src.cache.price_cache import cache
 def line_total(item):
-    unit = cache._prices[item.sku]
+    unit = cache.get(item.sku)
     return unit * item.qty

 def order_total(items):
     return sum(line_total(i) for i in items)
diff --git a/tests/test_price_cache.py b/tests/test_price_cache.py
--- a/tests/test_price_cache.py
+++ b/tests/test_price_cache.py
@@ -0,0 +1,14 @@
+from src.cache.price_cache import PriceCache, MAX_SKUS
+
+def test_apply_then_get(monkeypatch):
+    c = PriceCache()
+    c.apply("A", 1299)
+    assert c.get("A") == 1299
+
+def test_evicts_oldest(monkeypatch):
+    c = PriceCache()
+    monkeypatch.setattr("src.cache.price_cache.MAX_SKUS", 2)
+    for s in "ABC":
+        c.apply(s, 1)
+    assert "A" not in c._prices
""",
  "findings": [
    {"category": "bug", "severity": "medium", "path": "tests/test_price_cache.py", "line": 10,
     "title": "Monkeypatching MAX_SKUS has no effect: apply() reads the module constant captured at import",
     "body": "`apply()` compares against the global `MAX_SKUS` at call time, so the patch works only if the module attribute is read. It is, but the test asserts on `_prices` (private). Consider a public `__len__`."},
    {"category": "performance", "severity": "high", "path": "src/cache/price_cache.py", "line": 26,
     "title": "Cache miss calls the DB while holding no lock: thundering herd on cold start",
     "body": "On deploy, every checkout misses and calls `fetch_price` concurrently. Consider warming the cache or single-flight per SKU."},
    {"category": "naming", "severity": "low", "path": "tests/test_price_cache.py", "line": 3,
     "title": "Test name `test_apply_then_get` could be more descriptive", "body": "Suggest `test_get_returns_applied_price`."},
  ],
  "raw_comments": [
    {"id": 9001, "author": "demo-reviewer", "body": "Do we have a metric for stream consumer lag? That bounds staleness here.",
     "path": "src/cache/price_cache.py", "line": 14, "url": "https://github.com/qodo-ai/shop-demo/pull/101#discussion_r9001", "created": "2026-10-05T16:20:00Z"}
  ],
 },
 {
  "number": 102, "title": "Add discount codes at checkout", "author": "joe",
  "base": "main", "head": "joe/discount-codes", "labels": ["feature", "payments"],
  "body": "Adds `apply_discount(code, total)` and wires it into `order_total`. Supports percent and fixed-amount codes.",
  "summary": "Adds percent and fixed-amount discount codes. `order_total` now takes an optional `code` and applies it after summing line totals.",
  "risk": "**High.** Percent discounts are computed with floats on a cents total, which can produce fractional cents and break the integer-cents invariant.",
  "diagrams": [{"id": "flow", "title": "Discount decision", "mermaid":
    "flowchart TD\n  A[order_total items, code] --> B[sum line_total]\n  B --> C{code?}\n  C -- no --> R[return total]\n  C -- yes --> D{kind}\n  D -- percent --> P[total * 1 - pct/100]\n  D -- fixed --> F[max 0, total - amount]\n  P --> R\n  F --> R"}],
  "checks": [{"name": "unit-tests", "state": "SUCCESS"}, {"name": "lint", "state": "FAILURE"}],
  "diff": """diff --git a/src/payments/checkout.py b/src/payments/checkout.py
--- a/src/payments/checkout.py
+++ b/src/payments/checkout.py
@@ -1,4 +1,5 @@
 from src.cache.price_cache import cache
+from src.payments.discounts import apply_discount

@@ -12,5 +13,8 @@ def line_total(item):
     return unit * item.qty

-def order_total(items):
-    return sum(line_total(i) for i in items)
+def order_total(items, code=None):
+    total = sum(line_total(i) for i in items)
+    if code:
+        total = apply_discount(code, total)
+    return total
diff --git a/src/payments/discounts.py b/src/payments/discounts.py
--- a/src/payments/discounts.py
+++ b/src/payments/discounts.py
@@ -0,0 +1,16 @@
+from src.db import find_code
+
+def apply_discount(code, total_cents):
+    d = find_code(code)
+    if d is None:
+        return total_cents
+    if d.kind == "percent":
+        return total_cents * (1 - d.value / 100)
+    if d.kind == "fixed":
+        return max(0, total_cents - d.value)
+    return total_cents
+
+def describe(code):
+    d = find_code(code)
+    return f"{d.value}% off" if d.kind == "percent" else f"${d.value/100:.2f} off"
+
diff --git a/tests/test_discounts.py b/tests/test_discounts.py
--- a/tests/test_discounts.py
+++ b/tests/test_discounts.py
@@ -0,0 +1,9 @@
+from src.payments.discounts import apply_discount
+
+def test_percent(fake_codes):
+    fake_codes.add("TEN", "percent", 10)
+    assert apply_discount("TEN", 1000) == 900
+
+def test_fixed(fake_codes):
+    fake_codes.add("FIVE", "fixed", 500)
+    assert apply_discount("FIVE", 1000) == 500
""",
  "findings": [
    {"category": "bug", "severity": "high", "path": "src/payments/discounts.py", "line": 8,
     "title": "Percent discount returns a float; totals must be integer cents",
     "body": "`total_cents * (1 - d.value / 100)` yields e.g. `899.1`. Use integer math: `total_cents * (100 - d.value) // 100`, and decide the rounding rule."},
    {"category": "security", "severity": "high", "path": "src/payments/discounts.py", "line": 4,
     "title": "No validation that a code is active or belongs to this customer",
     "body": "`find_code` returns any code ever created. Expired or single-use codes can be replayed."},
    {"category": "bug", "severity": "medium", "path": "src/payments/discounts.py", "line": 14,
     "title": "`describe()` crashes with AttributeError when the code does not exist",
     "body": "`find_code` can return None."},
    {"category": "naming", "severity": "low", "path": "tests/test_discounts.py", "line": 3,
     "title": "Rename `test_percent` to describe the expected behaviour", "body": "e.g. `test_ten_percent_off_1000_cents_is_900`."},
    {"category": "style", "severity": "low", "path": "src/payments/discounts.py", "line": 16,
     "title": "Trailing blank line at end of file", "body": "Lint failure: W391."},
  ],
  "raw_comments": [],
 },
 {
  "number": 103, "title": "Rename ghost_text telemetry events to autocomplete_*", "author": "lior",
  "base": "main", "head": "lior/rename-ghost-text-events", "labels": ["telemetry"],
  "body": "Product calls it Autocomplete. Renames emitted event names; keeps old names as aliases for 30 days.",
  "summary": "Renames `ghost_text_shown` / `ghost_text_accepted` to `autocomplete_shown` / `autocomplete_accepted`, and emits both names during a 30-day transition.",
  "risk": "**Low** for runtime. Dashboards and saved SQL that filter on the old names keep working only while aliases are emitted.",
  "diagrams": [],
  "checks": [{"name": "unit-tests", "state": "SUCCESS"}],
  "diff": """diff --git a/src/telemetry/events.py b/src/telemetry/events.py
--- a/src/telemetry/events.py
+++ b/src/telemetry/events.py
@@ -1,6 +1,14 @@
-SHOWN = "ghost_text_shown"
-ACCEPTED = "ghost_text_accepted"
+import datetime
+
+SHOWN = "autocomplete_shown"
+ACCEPTED = "autocomplete_accepted"
+ALIASES = {SHOWN: "ghost_text_shown", ACCEPTED: "ghost_text_accepted"}
+ALIAS_UNTIL = datetime.date(2026, 11, 5)

 def emit(client, name, **props):
     client.track(name, props)
+    alias = ALIASES.get(name)
+    if alias and datetime.date.today() <= ALIAS_UNTIL:
+        client.track(alias, props)
diff --git a/tests/test_events.py b/tests/test_events.py
--- a/tests/test_events.py
+++ b/tests/test_events.py
@@ -0,0 +1,7 @@
+from src.telemetry import events
+
+def test_emits_alias(fake_client):
+    events.emit(fake_client, events.SHOWN)
+    assert fake_client.names == ["autocomplete_shown", "ghost_text_shown"]
+
+
""",
  "findings": [
    {"category": "tests", "severity": "medium", "path": "tests/test_events.py", "line": 4,
     "title": "Test depends on today's date; it will fail after 2026-11-05",
     "body": "Freeze the date or inject a clock."},
    {"category": "naming", "severity": "low", "path": "tests/test_events.py", "line": 3,
     "title": "Prefer `test_emit_sends_new_and_legacy_names`", "body": ""},
  ],
  "raw_comments": [],
 },
]


def main():
    out = {"reviewer_login": "demo-reviewer", "prs": []}
    for p in PRS:
        key = f"{REPO}#{p['number']}"
        hunks = parse_diff(p["diff"])
        files = []
        for path, hs in hunks.items():
            add = sum(1 for h in hs for l in h["lines"] if l[0] == "+")
            rem = sum(1 for h in hs for l in h["lines"] if l[0] == "-")
            files.append({"path": path, "additions": add, "deletions": rem, "hunks": hs})
        findings = []
        for i, f in enumerate(p["findings"]):
            findings.append({"id": f"q-{p['number']}-{i}", "pr": key, "source": "qodo", "url": None, **f})
        out["prs"].append({
            "key": key, "repo": REPO, "number": p["number"], "title": p["title"], "body": p["body"],
            "url": f"https://github.com/{REPO}/pull/{p['number']}", "author": p["author"], "base": p["base"],
            "head": p["head"], "head_sha": None, "labels": p["labels"],
            "additions": sum(f["additions"] for f in files), "deletions": sum(f["deletions"] for f in files),
            "files": files, "checks": p["checks"], "created": "2026-10-05T12:00:00Z",
            "summary": p["summary"], "risk": p["risk"], "diagrams": p["diagrams"], "findings": findings,
            "_raw_comments": p["raw_comments"],
        })
    Path(__file__).with_name("demo-prs.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print("wrote fixtures/demo-prs.json")


if __name__ == "__main__":
    main()
