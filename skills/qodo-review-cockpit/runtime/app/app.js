/* Review Cockpit front end. Vanilla JS; all state is derived from the server's event log. */
"use strict";

const S = {
  data: null, mem: { rules: [], bullets: [], concepts: [] }, events: [], n: 0,
  view: "overview", panel: {}, ignorePrefs: false, showCollapsed: {}, drawerPr: "all",
  composerOpen: false, panelStart: Date.now(), flash: null, openBeats: new Set(), lens: {}, semantic: true, openMoves: new Set(), filesMode: {}, live: {}, openLedger: new Set(),
};
const PANELS = [
  ["story", "Story"], ["summary", "Summary"], ["diagram", "Diagram"], ["findings", "Findings"], ["files", "Code"], ["knowledge", "Knowledge"],
];
const SEV_ORDER = { critical: -1, high: 0, medium: 1, low: 2 };
const $ = (sel, el = document) => el.querySelector(sel);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const md = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/`([^`]+)`/g, "<code>$1</code>").split(/\n{2,}/).map((p) => `<p>${p.replace(/\n/g, "<br>")}</p>`).join("");
const mdi = (s) => esc(s).replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
const enc = (o) => esc(JSON.stringify(o));
const dec = (s) => JSON.parse(s);

/* ---------------- server I/O ---------------- */
// A shared snapshot (python3 -m cockpit export) embeds everything in window.__COCKPIT__ and has no
// server: reads come from the embedded data; marks and notes stay in this browser tab only.
const SNAPSHOT = window.__COCKPIT__ || null;
function snapshotApi(path, body) {
  const X = SNAPSHOT;
  if (body === undefined) {
    if (path === "/api/data") return structuredClone(X.data);
    if (path === "/api/memory") return structuredClone(X.memory);
    if (path.startsWith("/api/events")) { const since = Number(path.split("since=")[1] || 0); return { events: X.events.slice(since), n: X.events.length }; }
  }
  if (path === "/api/event") { (Array.isArray(body) ? body : [body]).forEach((e) => X.events.push({ ts: new Date().toISOString(), source: "snapshot", ...e })); return { ok: true }; }
  throw new Error("This is a shared snapshot: publishing, knowledge and memory work in the live cockpit only.");
}
async function api(path, body) {
  if (SNAPSHOT) return snapshotApi(path, body);
  const opt = body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
  const sid = S.data && (S.data._dir || S.data.session);
  if (sid) opt.headers = { ...(opt.headers || {}), "X-Cockpit-Session": sid };   // stay on the package this tab opened, by its folder name
  const r = await fetch(path, opt);
  const j = await r.json();
  if (!r.ok || j.error) throw new Error(j.error || r.statusText);
  return j;
}
async function record(ev) {
  try { await api("/api/event", ev); await poll(true); }
  catch (e) { toast("Not saved: " + e.message); }
}
async function poll(force) {
  try {
    const j = await api(`/api/events?since=${S.n}`);
    if (j.events.length || force) {
      const fromAgent = S.n > 0 && j.events.some((e) => e.source === "agent");
      S.events.push(...j.events); S.n = j.n;
      if (fromAgent) toast("New note from your coding agent");
      render();
    }
  } catch (_) { /* server stopped; keep page usable */ }
}

/* ---------------- derived state ---------------- */
const tkey = (t, pr) => `${pr}|${t.kind}|${t.id}`;
function marks() {
  const m = new Map();
  for (const e of S.events) {
    if (e.type !== "mark") continue;
    const k = tkey(e.target, e.pr);
    if (!m.has(k)) m.set(k, new Set());
    e.undo ? m.get(k).delete(e.emoji) : m.get(k).add(e.emoji);
  }
  return m;
}
function verdicts(pr) {
  const v = {};
  for (const e of S.events) if (e.type === "finding_verdict" && e.pr === pr) v[e.target.id] = e.verdict;
  return v;
}
function notes() {
  const m = new Map();
  for (const e of S.events) {
    if (e.type !== "note") continue;
    const id = e.note_id || `gh-${e.github_id}`;
    if (e.undo) { m.delete(id); continue; }
    m.set(id, { ...(m.get(id) || {}), ...e, note_id: id });
  }
  const pub = new Set(S.events.filter((e) => e.type === "published").flatMap((e) => e.note_ids || []));
  for (const n of m.values()) if (pub.has(n.note_id)) n.posted = true;
  return [...m.values()];
}
function prefsIgnored() {
  for (let i = S.events.length - 1; i >= 0; i--) if (S.events[i].type === "pref_toggle") return !!S.events[i].ignore;
  return false;
}

/* ---------------- preferences (AMR rules) ---------------- */
function globRe(g) {
  let out = "", i = 0;
  while (i < g.length) {
    if (g.startsWith("**/", i)) { out += "(?:.*/)?"; i += 3; }
    else if (g.startsWith("**", i)) { out += ".*"; i += 2; }
    else if (g[i] === "*") { out += "[^/]*"; i++; }
    else if (g[i] === "?") { out += "[^/]"; i++; }
    else { out += g[i].replace(/[.+^${}()|[\]\\]/g, "\\$&"); i++; }
  }
  return new RegExp("^" + out + "$");
}
const rules = () => (prefsIgnored() ? [] : S.mem.rules || []);
function collapseRule(f) {
  if (["critical", "high"].includes(f.severity)) return null; // guardrail: never hide critical/high severity
  return rules().find((r) => r.action === "collapse" && (!r.category || r.category === f.category) && (!r.path || (f.path && globRe(r.path).test(f.path))));
}
function priority(f) {
  return rules().some((r) => r.action === "prioritize" && r.category === f.category) ? 0 : 1;
}
function panelOrder() {
  const r = rules();
  const first = r.find((x) => x.action === "open-first")?.panel;
  const score = (p) => (p === first ? -10 : 0) + (r.some((x) => x.action === "boost" && x.panel === p) ? -1 : 0) + (r.some((x) => x.action === "demote" && x.panel === p) ? 5 : 0);
  return PANELS.map((p, i) => [...p, score(p[0]) + i * 0.01]).sort((a, b) => a[2] - b[2]);
}

/* ---------------- shared widgets ---------------- */
function markbar(target, pr, { compact = false, note = true, label = "" } = {}) {
  const on = marks().get(tkey(target, pr)) || new Set();
  const btns = Object.entries(S.data.emoji).map(([em, m]) =>
    `<button class="mk" data-act="mark" data-t="${enc(target)}" data-pr="${esc(pr)}" data-em="${em}" aria-pressed="${on.has(em)}" title="${esc(m.label)}">${em}</button>`).join("");
  const nb = note ? `<button class="mk note" data-act="compose" data-t="${enc({ ...target, label })}" data-pr="${esc(pr)}" title="Add a note">💬 Note</button>` : "";
  return `<span class="markbar${compact ? " compact" : ""}">${btns}${nb}</span>`;
}
// One quiet pill for passing checks; only failing / pending / skipped ones get named.
function checksSummary(pr) {
  const ks = pr.checks || [];
  if (pr.product && !pr.product_evidence?.ci_complete) {
    const reported = ks.map((k) => `<span class="pill">${esc(k.name)}: ${esc(String(k.state || k.conclusion || 'unknown').toLowerCase())} (reported)</span>`).join('');
    return '<span class="pill">CI: Unknown (coverage incomplete)</span>' + reported;
  }
  if (!ks.length) return "";
  const ok = ks.filter((k) => /SUCC|PASS/i.test(k.state));
  const rest = ks.filter((k) => !ok.includes(k));
  const all = ks.map((k) => `${k.name}: ${k.state}`).join("\n");
  return `<span class="pill ${rest.some((k) => /FAIL|ERR/i.test(k.state)) ? "fail" : "ok"}" title="${esc(all)}">${ok.length}/${ks.length} checks passed</span>` +
    rest.map((k) => `<span class="pill ${/FAIL|ERR/i.test(k.state) ? "fail" : ""}">${esc(k.name)}: ${esc(String(k.state).toLowerCase())}</span>`).join("");
}
// A local finding: what the author's own `qodo review` found before the PR. Its status is as that review left it.
function localPill(f) {
  if (f.status === 'detected_after_merge') return `<span class="pill" title="No fix was verified">detected after merge</span>`;
  const l = f.local;
  if (l?.origin === 'managed') return `<span class="pill" title="Qodo records this finding from local_skill before the PR. This origin does not establish a completed PR review.">before the PR</span>`;
  if (!l && f.review_source && f.review_source !== 'git_pr') return `<span class="pill">${esc(f.review_source === 'unknown' ? 'review origin unknown' : 'review source: '+f.review_source)}</span>`;
  if (!l) return "";
  const when = l.at ? ` on ${esc(String(l.at).slice(0, 10))}` : "";
  if (f.source !== "qodo-local") return `<span class="pill" title="The author's local review${when} found this too, and left it ${esc(l.status || "open")}${l.reason ? ": " + esc(l.reason) : ""}">also found before the PR</span>`;
  const open = (f.status || "open") === "open";
  return `<span class="pill" title="Found by the author's local qodo review${when}, before the PR.${open ? " Open at that review; a fix or dismissal since then isn't shown yet." : ""}${f.status === "dismissed" && l.reason ? ` The author dismissed it: ${esc(l.reason)}.` : ""}${l.line ? ` At line ${esc(l.line)} then; the code has moved since.` : ""}">found before the PR${l.line ? ` · line ${esc(l.line)} then` : ""}</span>`;
}
function sevPill(s, guessed) { return `<span class="pill ${esc(s)}"${guessed ? ' title="Qodo grouped this by type, not severity; the level is a guess"' : ""}>${esc(s)}${guessed ? "?" : ""}</span>`; }
function prByKey(k) { return S.data.prs.find((p) => p.key === k); }
function prSeverity(pr) {
  const f = pr.findings || [];
  return f.some((x) => ["critical", "high"].includes(x.severity)) ? "high" : f.some((x) => x.severity === "medium") ? "medium" : "low";
}
function conceptByPath(p) { return (S.mem.concepts || []).find((c) => c.path === p); }

/* ---------------- top bar ---------------- */
function renderTabs() {
  const t = [`<button class="tab" role="tab" data-act="view" data-v="overview" aria-selected="${S.view === "overview"}">Overview</button>`];
  const many = S.data.prs.length > 5;   // with many PRs the number alone fits; the title is on hover
  for (const pr of S.data.prs) {
    t.push(`<button class="tab" role="tab" data-act="view" data-v="${esc(pr.key)}" aria-selected="${S.view === pr.key}" title="${esc(pr.title)}"><i class="dot ${prSeverity(pr)}"></i>#${pr.number}${many ? "" : ` <span class="muted">${esc(pr.repo.split("/")[1])}</span>`}</button>`);
  }
  $("#tabs").innerHTML = t.join("");
  if (!SNAPSHOT) $("#session").textContent = (S.data.demo ? "demo · " : "") + S.data.session;
  $("#note-count").textContent = notes().length;
}

/* ---------------- overview ---------------- */
function renderPrefsBox() {
  const r = S.mem.rules || [];
  const ign = prefsIgnored();
  if (!r.length) return "";
  return `<div class="prefs"><div class="row" style="justify-content:space-between"><b>Applied preferences from memory/amr</b>
    <label class="chk"><input type="checkbox" id="ignore-prefs" ${ign ? "checked" : ""}> Ignore for this session</label></div>
    <ul>${r.map((x) => `<li>${mdi(x.text)} <span class="muted mono" style="font-size:12px">· ${esc(x.rule)} · evidence ${x.evidence}</span></li>`).join("")}</ul>
    <span class="muted" style="font-size:12px">High-severity findings are never collapsed by a preference.</span></div>`;
}
function renderOverview() {
  const cards = S.data.prs.map((pr) => {
    const f = pr.findings || [];
    const c = (s) => f.filter((x) => (x.severity === s || (s === "high" && x.severity === "critical"))).length;
    const checks = checksSummary(pr);
    return `<div class="card markable"><div class="hd"><button class="btn ghost" data-act="view" data-v="${esc(pr.key)}" style="text-align:left;padding:0;border:0"><h2>#${pr.number} ${esc(pr.title)}</h2></button></div>
      <div class="bd"><div class="row muted">${esc(pr.author)} · <span class="mono">${esc(pr.head)}</span> → <span class="mono">${esc(pr.base)}</span></div>
      <div class="row"><span class="stat add">+${pr.additions}</span><span class="stat del">−${pr.deletions}</span><span class="muted">${pr.files.length} files</span></div>
      <div class="row">${c("high") ? `<span class="pill high">${c("high")} high/critical</span>` : ""}${c("medium") ? `<span class="pill medium">${c("medium")} medium</span>` : ""}${c("low") ? `<span class="pill low">${c("low")} low</span>` : ""}${(pr.concepts || []).length ? `<span class="pill okf">${pr.concepts.length} known facts</span>` : ""}</div>
      <div class="row">${checks}</div>${markbar({ kind: "pr", id: pr.key }, pr.key, { compact: true, label: `PR #${pr.number}` })}</div></div>`;
  }).join("");
  const drafts = (S.mem.concepts || []).filter((c) => c.status === "draft").length;
  return `${liveNotes(S.data.prs.map((p) => p.key))}${sessionBudget()}${sessionStory()}${contextBox()}${renderPrefsBox()}
    <h3 class="section-h">The pull requests</h3>
    <div class="grid-prs">${cards}</div>
    <div class="card markable"><div class="hd"><h2>How these PRs connect</h2>${markbar({ kind: "panel", id: "overview-map" }, "session", { compact: true, label: "Overview map" })}</div>
      <div class="bd"><p class="muted" style="margin:0">Files touched by more than one PR, and known facts (OKF) each PR touches. Hover to trace, click to open.</p>
      <div class="svgwrap">${crossMap()}</div>
      ${drafts ? `<div class="row"><span class="pill okf">${drafts} knowledge draft${drafts > 1 ? "s" : ""} awaiting confirmation</span><span class="muted">Open a PR's Knowledge tab to confirm or reject.</span></div>` : ""}</div></div>`;
}
function crossMap() {
  const prs = S.data.prs;
  const shared = S.data.overlaps.files || [];
  const cset = new Map();
  prs.forEach((p) => (p.concepts || []).forEach((c) => { if (!cset.has(c)) cset.set(c, []); cset.get(c).push(p.key); }));
  const concepts = [...cset.entries()];
  if (!shared.length && !concepts.length) return `<p class="empty">No shared files or known facts between these PRs.</p>`;
  const rowH = 46, W = 900;
  const H = Math.max(prs.length, shared.length, concepts.length) * rowH + 30;
  const y = (i, n) => 20 + i * rowH + ((H - 30) - n * rowH) / 2;
  const pos = {};
  let out = `<svg viewBox="0 0 ${W} ${H}" style="min-width:680px" role="img" aria-label="PRs, shared files and known facts">`;
  out += `<text x="20" y="14" font-size="11" fill="currentColor" opacity=".6">PULL REQUESTS</text><text x="340" y="14" font-size="11" opacity=".6">SHARED FILES</text><text x="650" y="14" font-size="11" opacity=".6">KNOWN FACTS (OKF)</text>`;
  prs.forEach((p, i) => (pos["pr:" + p.key] = [20, y(i, prs.length), 230]));
  shared.forEach((f, i) => (pos["f:" + f.path] = [340, y(i, shared.length), 240]));
  concepts.forEach(([c], i) => (pos["c:" + c] = [650, y(i, concepts.length), 230]));
  const edge = (a, b, cls) => { const [x1, y1, w1] = pos[a], [x2, y2] = pos[b]; return `<path class="edge" data-a="${esc(a)}" data-b="${esc(b)}" d="M${x1 + w1} ${y1 + 16} C ${x1 + w1 + 50} ${y1 + 16}, ${x2 - 50} ${y2 + 16}, ${x2} ${y2 + 16}"/>`; };
  shared.forEach((f) => f.prs.forEach((k) => (out += edge("pr:" + k, "f:" + f.path))));
  concepts.forEach(([c, ks]) => ks.forEach((k) => (out += edge("pr:" + k, "c:" + c))));
  const node = (id, label, sub, fill, act) => { const [x, yy, w] = pos[id]; return `<g class="node" data-node="${esc(id)}" data-act="${act.act}" data-v="${esc(act.v)}" ${act.extra || ""} tabindex="0"><rect x="${x}" y="${yy}" width="${w}" height="32" rx="7" fill="${fill}"/><text x="${x + 10}" y="${yy + 14}" font-size="12" font-weight="600">${esc(label.length > 32 ? "…" + label.slice(-31) : label)}</text><text x="${x + 10}" y="${yy + 27}" font-size="10.5" opacity=".7">${esc(sub)}</text></g>`; };
  prs.forEach((p) => (out += node("pr:" + p.key, `#${p.number} ${p.title}`.slice(0, 34), `${p.files.length} files · ${(p.findings || []).length} findings`, "var(--surface)", { act: "view", v: p.key })));
  shared.forEach((f) => (out += node("f:" + f.path, f.path, `${f.prs.length} PRs touch this`, "var(--med-soft)", { act: "gofile", v: f.path, extra: `data-pr="${esc(f.prs[0])}"` })));
  concepts.forEach(([c]) => { const k = conceptByPath(c); out += node("c:" + c, k?.title || c, `${k?.type || "concept"} · ${k?.tier || ""}`, "var(--okf-soft)", { act: "goknow", v: cset.get(c)[0] }); });
  return out + "</svg>";
}

/* ---------------- PR view ---------------- */
function renderPR(pr) {
  const order = panelOrder();
  const active = S.panel[pr.key] || order[0][0];
  S.panel[pr.key] = active;
  const nFind = (pr.findings || []).length, nKnow = (pr.concepts || []).length + draftsFor(pr).length;
  const tabs = order.map(([id, label]) => `<button class="ptab" role="tab" data-act="panel" data-v="${id}" aria-selected="${active === id}">${label}${id === "findings" ? `<span class="count">${nFind}</span>` : id === "knowledge" && nKnow ? `<span class="count">${nKnow}</span>` : ""}</button>`).join("");
  const checks = checksSummary(pr);
  return `${liveNotes([pr.key])}<div class="card"><div class="hd"><div style="display:grid;gap:4px;min-width:0">
      <h1>${esc(pr.title)} <a href="${esc(pr.url)}" target="_blank" rel="noopener" class="muted" style="font-size:14px">#${pr.number} ↗</a></h1>
      <div class="row muted">${esc(pr.repo)} · ${esc(pr.author)} · <span class="mono">${esc(pr.head)} → ${esc(pr.base)}</span> · <span class="stat add">+${pr.additions}</span><span class="stat del">−${pr.deletions}</span> ${(pr.labels || []).map((l) => `<span class="pill">${esc(l)}</span>`).join("")}</div>
      <div class="row">${checks}</div></div><div class="hd-tools">${markbar({ kind: "pr", id: pr.key }, pr.key, { compact: true, label: `PR #${pr.number}` })}</div></div>
    <div class="ptabs" role="tablist">${tabs}</div>
    <div class="bd">${renderPanel(pr, active)}</div></div>`;
}
function renderPanel(pr, p) {
  if (p === "story") return panelStory(pr);
  if (p === "summary") return panelSummary(pr);
  if (p === "diagram") return panelDiagram(pr);
  if (p === "findings") return panelFindings(pr);
  if (p === "files") return panelFiles(pr);
  return panelKnowledge(pr);
}
function panelSummary(pr) {
  const prNotes = notes().filter((n) => n.pr === pr.key && n.target?.kind === "pr");
  const q = pr.qodo || {};
  const qodo = q.headline || q.description ? `<details ${pr.summary ? "" : "open"}><summary class="muted">Qodo summary${q.labels?.length ? " · " + esc(q.labels.join(" · ")) : ""}</summary><div class="prose">${q.headline ? `<p><b>${mdi(q.headline)}</b></p>` : ""}${md(q.description || "")}${q.assessment ? md(q.assessment) : ""}${q.url ? `<p><a href="${esc(q.url)}" target="_blank" rel="noopener">on GitHub ↗</a></p>` : ""}</div></details>` : "";
  return `<div class="prose">${pr.summary ? md(pr.summary) : `<p class="muted">No summary yet. The skill adds one during enrichment.</p>`}</div>
    ${qodo}
    ${pr.risk ? `<div class="prose"><h3>Risk</h3>${md(pr.risk)}</div>` : ""}
    <details><summary class="muted">PR description</summary><div class="prose">${md(pr.body || "(empty)")}</div></details>
    <div><h3>PR-level notes</h3>${prNotes.map(noteView).join("") || `<p class="empty">None yet. Use 💬 Note on the PR header.</p>`}</div>`;
}
function panelDiagram(pr) {
  const diag = (pr.diagrams || []).map((d) => `<div class="markable" style="display:grid;gap:6px"><div class="row" style="justify-content:space-between"><h2>${esc(d.title)}</h2>${markbar({ kind: "diagram", id: `${pr.key}:${d.id}` }, pr.key, { compact: true, label: d.title })}</div>
      <div class="mermaid-box" data-mermaid="${esc(d.mermaid)}"><pre>${esc(d.mermaid)}</pre></div></div>`).join("");
  return `<div style="display:grid;gap:6px"><h2>Change map</h2><p class="muted" style="margin:0">Box width shows lines changed; color shows the most severe finding. Click a file to open its diff.</p><div class="svgwrap">${fileMap(pr)}</div></div>${diag || `<p class="empty">No flow diagrams for this PR. The skill generates them for behavioral changes.</p>`}`;
}
function fileMap(pr) {
  const groups = {};
  pr.files.forEach((f) => { const d = f.path.includes("/") ? f.path.slice(0, f.path.lastIndexOf("/")) : "."; (groups[d] ||= []).push(f); });
  const W = 860, rowH = 56; let yy = 10, out = "";
  const sevOf = (f) => { const s = (pr.findings || []).filter((x) => x.path === f.path).map((x) => x.severity); return s.includes("high") ? "high" : s.includes("medium") ? "medium" : s.length ? "low" : null; };
  const maxCh = Math.max(...pr.files.map((f) => f.additions + f.deletions), 1);
  for (const [dir, files] of Object.entries(groups)) {
    out += `<text x="10" y="${yy + 22}" font-size="12" font-family="var(--f-mono)" opacity=".75">${esc(dir)}/</text>`;
    let x = 190;
    for (const f of files) {
      const w = Math.max(110, Math.round(((f.additions + f.deletions) / maxCh) * 300));
      const s = sevOf(f); const fill = s ? `var(--${s === "medium" ? "med" : s}-soft)` : "var(--sunk)";
      const n = (pr.findings || []).filter((x) => x.path === f.path).length;
      out += `<g class="node" data-act="gofile" data-v="${esc(f.path)}" data-pr="${esc(pr.key)}" tabindex="0"><rect x="${x}" y="${yy}" width="${w}" height="40" rx="6" fill="${fill}"/><text x="${x + 8}" y="${yy + 17}" font-size="12" font-weight="600">${esc(f.path.split("/").pop())}</text><text x="${x + 8}" y="${yy + 32}" font-size="11" opacity=".75">+${f.additions} −${f.deletions}${n ? ` · ${n} finding${n > 1 ? "s" : ""}` : ""}</text></g>`;
      x += w + 10;
    }
    yy += rowH;
  }
  return `<svg viewBox="0 0 ${W} ${yy}" style="min-width:640px" role="img" aria-label="Changed files by directory">${out}</svg>`;
}
function findingView(f, pr, v) {
  const rule = collapseRule(f);
  const show = S.showCollapsed[pr.key];
  const collapsed = rule && !show;
  const original = pr.product && (f.current_anchor === false || (f.local?.origin === "managed" && !f.local.current_anchor)) ? f.source_location || f.local?.source_location || {path:f.path,line:f.line,side:f.side,git_sha:f.git_sha || f.local?.commit} : null;
  const where = original ? `<span class="pill">Original source: ${esc(original.path || "path unknown")}${original.line ? ":" + esc(original.line) : ""} · ${esc(original.side || "side unknown")} · ${esc(original.git_sha ? original.git_sha.slice(0, 7) : "revision unknown")}</span>` : f.path ? `<button class="btn ghost small mono" data-act="gofile" data-v="${esc(f.path)}" data-line="${f.line || ""}" data-pr="${esc(pr.key)}">${esc(f.path)}${f.line ? ":" + f.line : ""}</button>` : "";
  return `<div class="finding sev-${esc(f.severity)} markable ${collapsed ? "collapsed" : ""} ${v === "dismiss" ? "dismissed" : ""}">
    <div class="row" style="justify-content:space-between"><div class="row">${sevPill(f.severity, f.severity_guessed)}<span class="pill">${esc(f.category)}</span><span class="pill">${esc(f.source)}</span>${f.qodo_type ? `<span class="pill">${esc(f.qodo_type)}</span>` : ""}${f.thread?.resolved ? `<span class="pill" title="This finding's thread is resolved on GitHub">resolved on GitHub</span>` : ""}${localPill(f)}${where}</div>
      <div class="row"><button class="btn small ${v === "accept" ? "amr" : ""}" data-act="verdict" data-id="${esc(f.id)}" data-pr="${esc(pr.key)}" data-v="accept" aria-pressed="${v === "accept"}">✓ Accept</button>
      <button class="btn small ${v === "dismiss" ? "danger" : ""}" data-act="verdict" data-id="${esc(f.id)}" data-pr="${esc(pr.key)}" data-v="dismiss" aria-pressed="${v === "dismiss"}">✕ Dismiss</button></div></div>
    <div class="ttl">${mdi(f.title)}</div>
    ${rule ? `<div class="pref-why">${collapsed ? "Collapsed" : "Would be collapsed"} by your preference: “${mdi(rule.text)}”</div>` : ""}
    ${f.body ? `<div class="fbody">${mdi(f.body)}</div>` : ""}
    ${f.rule ? `<div class="muted" style="font-size:12px">Rule ${esc(f.rule.id)}: ${esc(f.rule.title)}</div>` : ""}
    ${f.status && f.status !== "open" ? `<div class="muted" style="font-size:12px">${esc(f.status)}${f.status_why ? ": " + esc(f.status_why) : ""}</div>` : ""}
    ${(f.replies || []).length ? `<div class="replies">${f.replies.map((r) => `<div class="reply ${r.bot ? "bot" : ""}"><b>${esc(r.author || "")}</b> ${mdi(r.body.replace(/_🤖[^_]*_/g, "").trim().slice(0, 400))}</div>`).join("")}</div>` : ""}
    <div class="row">${markbar({ kind: "finding", id: f.id }, pr.key, { compact: true, label: f.title.slice(0, 60) })}${f.url ? `<a href="${esc(f.url)}" target="_blank" rel="noopener" style="font-size:12px">on GitHub ↗</a>` : ""}${f.qodo_url ? `<a href="${esc(f.qodo_url)}" target="_blank" rel="noopener" style="font-size:12px">in Qodo ↗</a>` : ""}</div>
    ${notes().filter((n) => n.pr === pr.key && n.target?.kind === "finding" && n.target.id === f.id).map(noteView).join("")}</div>`;
}
function sortedFindings(pr) {
  return [...(pr.findings || [])].sort((a, b) => priority(a) - priority(b) || SEV_ORDER[a.severity] - SEV_ORDER[b.severity]);
}
function panelFindings(pr) {
  const v = verdicts(pr.key);
  const list = sortedFindings(pr);
  if (!list.length && !(pr.outdated || []).length) return `<p class="empty">No findings from Qodo or the agent for this PR.</p>`;
  const nColl = list.filter((f) => collapseRule(f)).length;
  const done = list.filter((f) => v[f.id]).length;
  return `${pr.qodo?.omitted ? `<div class="pref-why">Qodo: ${esc(pr.qodo.omitted)}</div>` : ""}<div class="row" style="justify-content:space-between"><span class="muted">${done}/${list.length} triaged · sorted by your priorities, then severity</span>
    ${nColl ? `<button class="btn small amr" data-act="showcoll" data-pr="${esc(pr.key)}">${S.showCollapsed[pr.key] ? "Collapse" : "Expand"} ${nColl} collapsed by preference</button>` : ""}</div>
    ${list.map((f) => findingView(f, pr, v[f.id])).join("")}
    ${(pr.outdated || []).length ? `<details class="outdated"><summary class="muted">${pr.outdated.length} not open in this review${pr.outdated.some((f) => f.status === 'detected_after_merge') ? '; includes post-merge detections with no fix verified' : ''}</summary>${pr.outdated.map((f) => findingView(f, pr, v[f.id])).join("")}</details>` : ""}`;
}
// ---- diff rendering, semantic by default: moves fold into one row, formatting-only edits read as
// context, and the tokens that really changed inside an edited line are highlighted.
function codeHtml(k, t, m, semantic) {
  const mark = k === " " ? " " : k;
  if (!semantic || !m || !m.spans || !m.spans.length) return esc(mark + t);
  let out = esc(mark), at = 0;
  for (const [a, b] of m.spans) { out += esc(t.slice(at, a)) + `<mark class="tok">${esc(t.slice(a, b))}</mark>`; at = b; }
  return out + esc(t.slice(at));
}
function diffRows(pr, f, lines, opts = {}) {
  const semantic = S.semantic, ns = opts.notes ? notes() : [], ff = opts.findings ? (pr.findings || []).filter((x) => x.path === f.path) : [];
  const rows = [];
  for (const l of lines) {
    if (l.hh) { rows.push(`<tr class="hh"><td class="ln"></td><td class="ln"></td><td class="code">${esc(l.hh)}</td></tr>`); continue; }
    const [k, o, n, t] = l, m = l[4] || {};
    if (semantic && m.ws && k === "-") continue;
    if (semantic && m.move) {
      const key = `${pr.key}:${m.move}:${k}`;
      if (!S.openMoves.has(key)) {
        if (m.first) {
          const where = k === "-" ? m.to : m.from, verb = k === "-" ? "moved to" : "moved from";
          rows.push(`<tr class="mv"><td class="ln"></td><td class="ln">${k === "-" ? "↪" : "↩"}</td><td class="code mvc"><button class="mvb" data-act="togglemove" data-v="${esc(key)}">${m.run} lines ${verb} <code>${esc(where.path.split("/").pop())}:${where.line ?? ""}</code>, unchanged</button></td></tr>`);
        }
        continue;
      }
    }
    const line = n ?? o;
    const cls = (semantic && m.ws) ? "wsl" : k === "+" ? "a" : k === "-" ? "d" : "";
    const flash = S.flash && S.flash.path === f.path && S.flash.line === line ? " flash" : "";
    const lnAttrs = `data-act="compose-line" data-path="${esc(f.path)}" data-line="${n ?? ""}" data-oline="${o ?? ""}" data-pr="${esc(pr.key)}" title="Add a note on this line"`;
    rows.push(`<tr class="${cls}${m.move ? " moved" : ""}${flash}" data-line="${line}"${semantic && m.ws ? ' title="Formatting only"' : ""}><td class="ln" ${lnAttrs}>${o ?? ""}</td><td class="ln" ${lnAttrs}>${n ?? ""}</td><td class="code">${codeHtml(semantic && m.ws ? " " : k, t, m, semantic)}</td></tr>`);
    if (n != null) {
      ff.filter((x) => x.line === n).forEach((x) => rows.push(`<tr class="inline"><td colspan="3"><div class="inline-finding row">${sevPill(x.severity)}<b>${esc(x.title)}</b><button class="btn small ghost" data-act="panel" data-v="findings">see finding</button></div></td></tr>`));
      ns.filter((x) => x.pr === pr.key && x.path === f.path && Number(x.line) === n).forEach((x) => rows.push(`<tr class="inline"><td colspan="3">${noteView(x)}</td></tr>`));
    }
  }
  return rows.join("");
}
function hunkLines(f) {
  const out = [];
  f.hunks.forEach((h) => { out.push({ hh: h.header }); out.push(...h.lines); });
  return out;
}
// Lines of one file inside a range (new or old side), with a little context; deletions that sit
// inside a new-side range come along.
function rangeLines(f, r, ctx = 3) {
  const out = [];
  const lo = r.from - ctx, hi = r.to + ctx;
  for (const h of f.hunks) {
    let lastNew = null;
    for (const l of h.lines) {
      const [k, o, n] = l;
      if (n != null) lastNew = n;
      const inR = r.side === "old" ? o != null && o >= lo && o <= hi : n != null ? n >= lo && n <= hi : lastNew != null && lastNew >= lo - 1 && lastNew <= hi;
      if (inR) out.push(l);
    }
  }
  return out;
}
function semToggle() {
  return `<span class="seg" role="group" aria-label="Diff view"><button class="segb" data-act="semantic" data-v="1" aria-pressed="${S.semantic}">Semantic</button><button class="segb" data-act="semantic" data-v="0" aria-pressed="${!S.semantic}">Raw</button></span>`;
}
function semCounts(pr) {
  const s = pr.semantic || {};
  const folded = (s.moved || 0) + (s.whitespace || 0);
  return folded ? `<span class="muted" style="font-size:12.5px">${folded} moved or formatting-only lines folded</span>` : "";
}
function fileView(pr, f) {
  const fid = "file-" + btoa(unescape(encodeURIComponent(pr.key + f.path))).replace(/[^a-z0-9]/gi, "");
  const ff = (pr.findings || []).filter((x) => x.path === f.path);
  const sem = f.semantic || {};
  return `<details class="file markable" id="${fid}" data-path="${esc(f.path)}" ${f.hunks.reduce((a, h) => a + h.lines.length, 0) < 120 ? "open" : ""}>
      <summary><span class="path">${esc(f.path)}</span>${f.role && f.role !== "source" ? `<span class="pill">${esc(f.role)}</span>` : ""}<span class="stat add">+${f.additions}</span><span class="stat del">−${f.deletions}</span>${sem.moved ? `<span class="pill">${sem.moved} moved</span>` : ""}${ff.length ? `<span class="pill ${ff.some((x) => ["critical", "high"].includes(x.severity)) ? "high" : "medium"}">${ff.length} finding${ff.length > 1 ? "s" : ""}</span>` : ""}<span style="margin-left:auto" onclick="event.preventDefault()">${markbar({ kind: "file", id: `${pr.key}:${f.path}` }, pr.key, { compact: true, label: f.path })}</span></summary>
      <div class="diff"><table>${diffRows(pr, f, hunkLines(f), { notes: true, findings: true })}</table></div></details>`;
}
// The walk: the PR's layers in reading order, each showing only its own line ranges.
function walkView(pr) {
  const seen = seenBeats(), cov = pr.layer_coverage || { total: 0, covered: 0, uncovered: [] };
  const lid = (l) => `${pr.key}:layer:${l.id}`;
  const rail = pr.layers.map((l, i) => `<button class="rail-i ${seen.has(lid(l)) ? "seen" : ""}" data-act="gobeat" data-v="${esc(lid(l))}"><span class="t">${i + 1}. ${esc(l.title)}</span></button>`).join("")
    + (cov.uncovered.length ? `<button class="rail-i" data-act="gobeat" data-v="${esc(pr.key)}:layer:__rest"><span class="t muted">Not in any layer</span></button>` : "");
  const num = Object.fromEntries(pr.layers.map((l, i) => [l.id, i + 1]));
  const block = (r, caption) => {
    const f = pr.files.find((x) => x.path === r.path);
    if (!f) return "";
    return `<div class="lr"><div class="lr-cap"><button class="ref" data-act="peek" data-pr="${esc(pr.key)}" data-path="${esc(r.path)}" data-line="${r.from}" data-end="${r.to}">${esc(r.path)}</button><span class="muted"> · ${r.side === "old" ? "removed " : ""}lines ${r.from}–${r.to}</span>${caption ? `<span class="lr-note">${storyText(caption, pr)}</span>` : ""}</div>
      <div class="diff"><table>${diffRows(pr, f, rangeLines(f, r), { notes: true, findings: true })}</table></div></div>`;
  };
  const layers = pr.layers.map((l, i) => `<section class="layer" id="beat-${esc(lid(l))}" data-beat="${esc(lid(l))}" data-pr="${esc(pr.key)}">
      <div class="layer-h"><span class="layer-n">${i + 1}</span><h3 class="layer-t">${storyText(l.title, pr)}</h3>${(l.depends_on || []).map((d) => `<span class="pill">after ${num[d] || d}</span>`).join("")}</div>
      <p class="lede">${storyText(l.summary || "", pr)}</p>
      ${l.visual ? `<div class="visual">${l.visual.mermaid ? `<div class="mermaid-box" data-mermaid="${esc(mermaidSrc(l.visual.mermaid))}"><pre>${esc(l.visual.mermaid)}</pre></div>` : l.visual.shape ? shapeView(l.visual.shape, pr) : ""}</div>` : ""}
      ${l.ranges.map((r) => block(r, r.note)).join("")}
    </section>`).join("");
  const rest = cov.uncovered.length ? `<section class="layer rest" id="beat-${esc(pr.key)}:layer:__rest"><details><summary class="layer-h"><h3 class="layer-t">Not in any layer</h3><span class="muted">${cov.total - cov.covered} lines</span></summary>
      ${cov.uncovered.flatMap((u) => u.runs.map(([a, b]) => block({ path: u.path, side: u.side, from: a, to: b }, ""))).join("")}</details></section>` : "";
  return `<div class="journal"><nav class="rail" aria-label="Layers">${rail}</nav><div class="walk">${layers}${rest}</div></div>`;
}
// ---- review plan: must read (in layer order, checked off) and a ledger of what is safe to skip
function readChecks() {
  const m = new Map();
  for (const e of S.events) if (e.type === "read_check") m.set(e.target.id, !!e.done);
  return m;
}
const TIER_NAME = { deep: "Deep read", review: "Read", skim: "Skim", skip: "Skip" };
const TIER_ORDER = ["deep", "review", "skim", "skip"];
const TINY = 0.006;   // segments thinner than this merge into one "N more files" segment, so each one stays hoverable
// The budget bar: one segment per file and tier, soft lines between files, a gap between tiers.
// segs: [{tier, lines, label, why, jump?}] in reading order.
function budgetBar(sum, segs) {
  const t = sum.total || 1, w = (n) => `${(100 * n / t).toFixed(2)}%`;
  const out = [];
  for (const tier of TIER_ORDER) {
    const mine = (segs || [{ tier, lines: sum[tier] || 0, label: TIER_NAME[tier], why: "" }]).filter((x) => x.tier === tier && x.lines);
    const big = mine.filter((x) => x.lines / t >= TINY), small = mine.filter((x) => x.lines / t < TINY);
    if (small.length) big.push({ tier, lines: small.reduce((a, x) => a + x.lines, 0), label: `${small.length} more file${small.length > 1 ? "s" : ""}`,
      why: small.slice(0, 6).map((x) => `${x.label} (${x.lines})`).join(" · ") + (small.length > 6 ? " · …" : "") });
    big.forEach((x, i) => out.push(`<i class="b-${tier}${i === 0 && out.length ? " b-first" : ""}" style="width:${w(x.lines)}" data-tip="${esc(x.label)}" data-tip-sub="${esc(`${TIER_NAME[tier]} · ${x.lines} line${x.lines > 1 ? "s" : ""}`)}" data-tip-why="${esc(x.why || "")}"${x.jump ? ` data-act="planjump" data-v="${esc(x.jump)}" data-pr="${esc(x.pr || "")}" data-tip-hint="Click to open"` : ""}></i>`));
  }
  const label = TIER_ORDER.map((k) => `${sum[k] || 0} ${TIER_NAME[k].toLowerCase()}`).join(", ");
  return `<div class="budget" role="img" aria-label="${esc(label)}">${out.join("")}</div>`;
}
function legend(sum, extra) {
  return `<div class="plan-legend">${TIER_ORDER.map((k) => `<span><i class="b-${k}"></i>${TIER_NAME[k].toLowerCase()} ${(sum[k] || 0).toLocaleString()}</span>`).join("")}${extra || ""}</div>`;
}
const REASON_TEXT = { code: "changed code" };
function planSegments(pr) {
  const att = pr.attention, segs = [], at = {};
  const add = (tier, path, lines, why, jump) => {
    const k = `${tier}|${path}`;
    if (!at[k]) segs.push((at[k] = { tier, label: path.split("/").slice(-2).join("/"), path, lines: 0, why: new Set(), jump, pr: pr.key }));
    at[k].lines += lines;
    why.forEach((x) => x && at[k].why.add(x));
  };
  const blocks = Object.fromEntries((att.blocks || []).map((b) => [b.id, b]));
  for (const id of att.must_read || []) {   // reading order, deep first
    const b = blocks[id];
    if (!b) continue;
    const tier = b.tier === "deep" ? "deep" : "review";
    const fs = (pr.findings || []).filter((x) => x.status !== "dismissed" && x.path === b.path && x.line >= b.from && x.line <= b.to);
    add(tier, b.path, b.lines, tier === "deep" ? (b.why || []) : (b.reasons || [b.reason]).map((r) => REASON_TEXT[r] || r).concat(fs.length ? [`${fs.length} finding${fs.length > 1 ? "s" : ""}`] : []), `mr-${pr.key}:${b.id}`);
  }
  for (const r of att.ranges || []) if (r.tier === "skim" || r.tier === "skip") add(r.tier, r.path, r.lines, [`${r.reason} (${r.evidence})`], `lg-${pr.key}|${r.tier}|${r.reason}`);
  return segs.map((x) => ({ ...x, label: x.path, why: [...x.why].join(" · ") }));
}
function planItem(pr, b, i, checks) {
  const id = `${pr.key}:${b.id}`, isDone = !!checks.get(id);
  const f = pr.files.find((x) => x.path === b.path);
  const fs = (pr.findings || []).filter((x) => x.path === b.path && x.line && x.line >= b.from && x.line <= b.to);
  const deep = b.tier === "deep";
  const zoom = !deep && (pr.attention.blocks || []).find((z) => z.zoom_of === b.id);
  return `<div class="mr ${isDone ? "done" : ""} ${deep ? "deep" : ""}" id="mr-${esc(id)}">
      <div class="mr-h"><label class="mr-chk"><input type="checkbox" data-act="readcheck" data-pr="${esc(pr.key)}" data-v="${esc(id)}" ${isDone ? "checked" : ""}> <span class="mr-n">${i + 1}</span></label>
        <button class="ref" data-act="peek" data-pr="${esc(pr.key)}" data-path="${esc(b.path)}" data-line="${b.from}" data-end="${b.to}">${esc(b.path)}</button>
        <span class="muted">${b.side === "old" ? "removed " : ""}${b.from}–${b.to} · ${b.lines} lines</span>
        ${deep ? (b.why || []).map((w) => `<span class="pill ${/high|weakened|invariant/.test(w) ? "high" : ""}">${esc(w)}</span>`).join("")
               : b.reason !== "code" ? `<span class="pill ${b.reason === "open high finding" || b.reason === "test weakened" ? "high" : ""}">${esc(b.reason)}</span>` : ""}
        ${fs.map((x) => sevPill(x.severity)).join("")}
        ${zoom ? `<span class="muted">lines ${zoom.from}–${zoom.to} are in deep read</span>` : ""}</div>
      ${isDone || !f ? "" : `<div class="diff"><table>${diffRows(pr, f, rangeLines(f, b, 2), { notes: true, findings: true })}</table></div>`}
    </div>`;
}
function planView(pr) {
  const att = pr.attention, sum = att.summary, checks = readChecks();
  const blocks = Object.fromEntries((att.blocks || []).map((b) => [b.id, b]));
  const must = att.must_read.map((id) => blocks[id]).filter(Boolean);
  const done = must.filter((b) => checks.get(`${pr.key}:${b.id}`)).length;
  const deepN = sum.deep || 0, readN = sum.review || 0;
  const pct = (n) => Math.round(100 * n / (sum.total || 1));
  const layers = pr.layers || [];
  const deepItems = must.filter((b) => b.tier === "deep").map((b, i) => planItem(pr, b, i, checks)).join("");
  const nDeep = must.filter((b) => b.tier === "deep").length;
  let lastLayer = -2;
  const readItems = must.filter((b) => b.tier !== "deep").map((b, i) => {
    const head = b.layer !== lastLayer && b.layer != null && layers[b.layer] ? `<div class="mr-layer">${b.layer + 1}. ${storyText(layers[b.layer].title, pr)}</div>` : "";
    lastLayer = b.layer;
    return head + planItem(pr, b, nDeep + i, checks);
  }).join("");
  const groups = {};
  for (const r of att.ranges || []) if (r.tier === "skim" || r.tier === "skip") (groups[`${r.tier}|${r.reason}`] ||= { tier: r.tier, reason: r.reason, evidence: r.evidence, lines: 0, ranges: [] }).lines += r.lines, groups[`${r.tier}|${r.reason}`].ranges.push(r);
  const ledger = (tier) => Object.values(groups).filter((g) => g.tier === tier).sort((a, b) => b.lines - a.lines).map((g) => {
    const files = [...new Set(g.ranges.map((r) => r.path))];
    const key = `${pr.key}|${g.tier}|${g.reason}`;
    return `<details class="lg" id="lg-${esc(key)}" ${S.openLedger.has(key) ? "open" : ""} data-key="${esc(key)}" data-reason="${esc(g.reason)}" data-tier="${esc(g.tier)}" data-pr="${esc(pr.key)}">
      <summary><span class="pill ${g.tier === "skim" ? "low" : ""}">${esc(g.tier)}</span><b>${g.lines} lines</b> ${esc(g.reason)} <span class="muted">· ${files.length} file${files.length > 1 ? "s" : ""} · ${esc(g.evidence)}</span></summary>
      <div class="lg-b">${S.openLedger.has(key) ? files.map((path) => {
        const f = pr.files.find((x) => x.path === path);
        const rs = g.ranges.filter((r) => r.path === path);
        const span = { path, side: rs[0].side, from: Math.min(...rs.map((r) => r.from)), to: Math.max(...rs.map((r) => r.to)) };
        return f ? `<div class="lr"><div class="lr-cap"><span class="mono" style="font-size:12.5px">${esc(path)}</span></div><div class="diff"><table>${diffRows(pr, f, rangeLines(f, span, 1), { notes: true, findings: true })}</table></div></div>` : "";
      }).join("") : ""}</div></details>`;
  }).join("");
  const skim = ledger("skim"), skip = ledger("skip");
  const sec = (tier, n, note, body) => `<h3 class="plan-t" id="plan-${esc(pr.key)}-${tier}"><i class="tier-dot b-${tier}"></i>${TIER_NAME[tier]} <span class="muted">${n.toLocaleString()} lines · ${pct(n)}%</span></h3><p class="plan-note">${note}</p>${body}`;
  return `<div class="plan">
    <div class="plan-h"><div class="plan-n"><b>Deep-read ${deepN}</b>, read ${readN} of ${sum.total || 0} changed lines <span class="muted">(${pct(deepN + readN)}% needs you; hover the bar for each file and why)</span></div>${budgetBar(sum, planSegments(pr))}
      ${legend(sum, `<span class="muted">${done}/${must.length} read</span>`)}</div>
    ${deepItems ? sec("deep", deepN, "The riskiest lines, at most 5% of the change: open findings, weakened or failing tests, confirmed invariants, and what the story points at. Read these line by line.", deepItems) : ""}
    ${sec("review", readN, "The rest of the change, in the order of the walk. Read for intent and shape.", readItems || `<p class="empty">Nothing else needs a human read here.</p>`)}
    ${skim ? sec("skim", sum.skim || 0, "Look at the shape; the evidence says the details are safe. Open a group to read it.", `<div class="ledger">${skim}</div>`) : ""}
    ${skip ? sec("skip", sum.skip || 0, "Generated, moved or formatting only; nothing a human needs to read.", `<div class="ledger">${skip}</div>`) : ""}
  </div>`;
}
function sessionBudget() {
  const prs = S.data.prs.filter((p) => p.attention && p.attention.summary.total);
  if (!prs.length) return "";
  const sum = { deep: 0, review: 0, skim: 0, skip: 0, total: 0 };
  prs.forEach((p) => Object.keys(sum).forEach((k) => (sum[k] += p.attention.summary[k] || 0)));
  const segs = [];
  for (const p of prs) for (const tier of TIER_ORDER) {   // one segment per PR and tier; the why names its top files
    const fs = planSegments(p).filter((x) => x.tier === tier).sort((a, b) => b.lines - a.lines);
    if (fs.length) segs.push({ tier, lines: fs.reduce((a, x) => a + x.lines, 0), label: `#${p.number} ${p.title || ""}`.trim(), pr: p.key, jump: `plan-${p.key}-${tier}`,
      why: fs.slice(0, 3).map((x) => `${x.path.split("/").pop()} (${x.lines})${tier === "deep" && x.why ? `: ${x.why}` : ""}`).join(" · ") + (fs.length > 3 ? ` · +${fs.length - 3} files` : "") });
  }
  const need = sum.deep + sum.review, pct = (n) => Math.round(100 * n / (sum.total || 1));
  return `<div class="sbudget"><div><b>Deep-read ${sum.deep.toLocaleString()} and read ${sum.review.toLocaleString()} of ${sum.total.toLocaleString()} changed lines (${pct(need)}%)</b> <span class="muted">across ${prs.length} PR${prs.length > 1 ? "s" : ""}; the rest is tests, generated code, moves or formatting, each accounted for in its PR's Code tab.</span></div>${budgetBar(sum, segs)}${legend(sum)}</div>`;
}
// Hover tooltip for the budget bar: which file, how many lines, and why.
(() => {
  let tip;
  document.addEventListener("mouseover", (e) => {
    const el = e.target.closest && e.target.closest("[data-tip]");
    if (!el) { if (tip) tip.hidden = true; return; }
    tip ||= Object.assign(document.body.appendChild(document.createElement("div")), { className: "tip", role: "tooltip" });
    tip.innerHTML = `<b>${esc(el.dataset.tip)}</b><div class="muted">${esc(el.dataset.tipSub || "")}</div>${el.dataset.tipWhy ? `<div>${esc(el.dataset.tipWhy)}</div>` : ""}${el.dataset.tipHint ? `<div class="tip-hint">${esc(el.dataset.tipHint)}</div>` : ""}`;
    tip.hidden = false;
    const r = el.getBoundingClientRect(), tw = Math.min(360, window.innerWidth - 16);
    tip.style.maxWidth = `${tw}px`;
    tip.style.left = `${Math.max(8, Math.min(e.clientX - 20, window.innerWidth - tw - 8))}px`;
    tip.style.top = `${r.bottom + 8}px`;
  });
})();
function panelFiles(pr) {
  const hasWalk = (pr.layers || []).length > 0, hasPlan = !!(pr.attention && pr.attention.summary && pr.attention.summary.total);
  const mode = S.filesMode[pr.key] || (hasPlan ? "plan" : hasWalk ? "walk" : "files");
  const cov = pr.layer_coverage;
  const head = `<div class="files-h"><span class="seg" role="group" aria-label="Order">${hasPlan ? `<button class="segb" data-act="filesmode" data-pr="${esc(pr.key)}" data-v="plan" aria-pressed="${mode === "plan"}">Plan</button>` : ""}${hasWalk ? `<button class="segb" data-act="filesmode" data-pr="${esc(pr.key)}" data-v="walk" aria-pressed="${mode === "walk"}">Walk</button>` : ""}<button class="segb" data-act="filesmode" data-pr="${esc(pr.key)}" data-v="files" aria-pressed="${mode === "files"}">By file</button></span>${semToggle()}${semCounts(pr)}${mode === "walk" && cov && cov.total ? `<span class="muted" style="font-size:12.5px">layers cover ${cov.covered} of ${cov.total} changed lines</span>` : ""}</div>`;
  if (mode === "plan") return head + planView(pr);
  if (mode === "walk") return head + walkView(pr);
  return head + pr.files.map((f) => fileView(pr, f)).join("") + `<p class="muted" style="font-size:12px;margin:0">Click a line number to leave a note on that line. Notes marked “Post to GitHub” go into a review you publish from the Notes panel.</p>`;
}
function draftsFor(pr) {
  const fromCands = (S.data.okf.candidates || []).filter((c) => c.pr === pr.key).map((c) => c.path);
  const matched = new Set(pr.concepts || []);
  return (S.mem.concepts || []).filter((c) => c.status === "draft" && (fromCands.includes(c.path) || matched.has(c.path)));
}
function conceptView(c, pr) {
  const tierCls = c.tier === "human-reviewed" ? "amr" : c.tier === "machine-confirmed" ? "low" : "";
  return `<div class="concept ${c.status === "draft" ? "draft" : ""} markable">
    <div class="row" style="justify-content:space-between"><div class="row"><span class="pill okf">${esc(c.type)}</span><b>${esc(c.title)}</b></div>
      <div class="row"><span class="pill ${tierCls}">${esc(c.tier)}</span><span class="pill">${esc(c.status)}</span>${c.stale ? `<span class="pill high">stale</span>` : ""}</div></div>
    <div>${esc(c.description || c.body)}</div>
    <div class="meta mono">${esc(c.path)}${c.paths?.length ? " · applies to " + c.paths.map(esc).join(", ") : ""}</div>
    <div class="row">${c.status === "draft" ? `<button class="btn small amr" data-act="okf" data-op="confirm" data-path="${esc(c.path)}" data-pr="${esc(pr.key)}">✓ Confirm (marks human-reviewed)</button><button class="btn small danger" data-act="okf" data-op="reject" data-path="${esc(c.path)}" data-pr="${esc(pr.key)}">✕ Reject</button>` : `<button class="btn small" data-act="okf" data-op="reject" data-path="${esc(c.path)}" data-pr="${esc(pr.key)}">Deprecate</button>`}
      ${markbar({ kind: "concept", id: c.path }, pr.key, { compact: true, label: c.title })}</div></div>`;
}
function panelKnowledge(pr) {
  const known = (pr.concepts || []).map(conceptByPath).filter((c) => c && c.status !== "draft");
  const drafts = draftsFor(pr);
  const dirs = [...new Set(pr.files.map((f) => (f.path.includes("/") ? f.path.slice(0, f.path.lastIndexOf("/")) + "/**" : f.path)))];
  if (S.mem && S.mem.enabled === false)
    return `<p class="empty">Memory is off (<span class="mono">memory.enabled</span> in your config), so there is no knowledge to show or add.</p>`;
  return `<div style="display:grid;gap:8px"><h3>Known facts this PR touches</h3>${known.map((c) => conceptView(c, pr)).join("") || `<p class="empty">No confirmed facts match the changed paths.</p>`}</div>
    <div style="display:grid;gap:8px"><h3>Drafts awaiting your confirmation</h3>${drafts.map((c) => conceptView(c, pr)).join("") || `<p class="empty">No drafts. Propose one below, or start a note with “fact:”.</p>`}</div>
    <form class="form card" id="propose" data-pr="${esc(pr.key)}" style="padding:12px"><h3>Propose a fact about this code</h3>
      <div class="two"><select id="p-type" aria-label="Type">${["Invariant", "Risk Area", "Decision", "Review Rule", "Glossary Term", "Fact"].map((t) => `<option>${t}</option>`).join("")}</select><input type="text" id="p-title" placeholder="One-line fact, e.g. Discount math stays in integer cents" required></div>
      <textarea id="p-body" rows="3" placeholder="Details, rationale, how to check it"></textarea>
      <input type="text" id="p-paths" value="${esc(dirs.join(", "))}" aria-label="Applies to paths (comma separated globs)">
      <div class="row"><label class="chk"><input type="checkbox" id="p-confirm" checked> Confirm now (I verified this)</label><button class="btn primary" type="submit">Save to knowledge</button></div></form>`;
}

/* ---------------- notes ---------------- */
/* ---------------- story (journal) ---------------- */
// A story is a short sequence of beats; each beat is one thing to look at plus one sentence on
// what to see in it. The skill writes it during enrichment; without one we draft a plain one.
function beatForm(b) {
  if (b.kind === "diagram") return (b.mermaid || "").trim().split(/[\s\n]/)[0];
  if (b.kind === "media") return b.type || (/\.(mp4|webm|mov)$/i.test(b.src || "") ? "video" : "image");
  if (b.kind === "shape") return b.form || "";
  if (b.kind === "views") return (b.views || []).map((v) => v.label).join("+");
  if (b.kind === "before_after") return ["mermaid", "media", "code", "text"].find((k) => (b.after || {})[k]) || "";
  return "";
}
const beatTarget = (pr, b) => ({ kind: "beat", id: `${pr}:${b.id}`, beat_kind: b.kind, form: beatForm(b), label: b.title });
function avoidRule(b) {
  return rules().find((r) => r.action === "avoid-beat" && r.kind === b.kind && (!r.form || r.form === beatForm(b)));
}
function autoStory(pr) {
  const f = pr.findings || [];
  const high = f.filter((x) => ["critical", "high"].includes(x.severity));
  const q = pr.qodo || {};
  const beats = [];
  if (q.diagram) beats.push({ id: "a1", kind: "diagram", weight: "lead", title: "How the change flows", lede: q.headline || pr.title, mermaid: q.diagram.mermaid });
  beats.push({ id: "a2", kind: "stat", weight: beats.length ? "normal" : "lead", title: "Size of the change", lede: q.headline && !q.diagram ? q.headline : `${pr.files.length} files across ${new Set(pr.files.map((x) => x.path.split("/")[0])).size} top-level directories.`,
    items: [{ label: "lines added", value: `+${pr.additions}`, tone: "good" }, { label: "lines removed", value: `−${pr.deletions}`, tone: "bad" }, { label: "files", value: pr.files.length }, { label: "high/critical findings", value: high.length, tone: high.length ? "bad" : "neutral" }] });
  if (high.length) beats.push({ id: "a3", kind: "findings", title: "Decide on these first", lede: `${high.length} high-severity finding${high.length > 1 ? "s" : ""} from ${[...new Set(high.map((x) => x.source))].join(" and ")}.`, ids: high.map((x) => x.id) });
  return beats;
}
function storyText(s, pr) {
  // `path:line` or `file.py:12-14` in backticks becomes a link to the diff when it names a changed file.
  return mdi(s).replace(/<code>([\w./-]+?)(?::(\d+)(?:-(\d+))?)?<\/code>/g, (m, p, a) => {
    const owner = pr ? [pr] : S.data.prs;
    const hit = owner.map((x) => [x, x.files.find((y) => y.path === p || y.path.endsWith("/" + p))]).find(([, y]) => y);
    if (!hit) return m;
    const [opr, f] = hit;
    return `<button class="ref inline" data-act="peek" data-pr="${esc(opr.key)}" data-path="${esc(f.path)}" data-line="${a || ""}"><code>${esc(p)}${a ? ":" + a : ""}</code></button>`;
  });
}
function refChips(b, pr) {
  const chips = (b.refs || []).map((r) => {
    if (r.path) {
      const p = pr || S.data.prs.find((x) => x.files.some((f) => f.path === r.path));
      if (!p) return "";
      return `<button class="ref" data-act="peek" data-pr="${esc(p.key)}" data-path="${esc(r.path)}" data-line="${r.line || ""}" data-end="${r.end_line || ""}">${esc(r.label || r.path.split("/").pop() + (r.line ? ":" + r.line : ""))}</button>`;
    }
    if (r.finding) { const p = S.data.prs.find((x) => (x.findings || []).some((f) => f.id === r.finding)); return p ? `<button class="ref" data-act="panel-of" data-pr="${esc(p.key)}" data-v="findings">${esc(r.label || "finding")}</button>` : ""; }
    if (r.concept) { const c = conceptByPath(r.concept); return `<button class="ref okf" data-act="goknow" data-v="${esc(pr ? pr.key : S.data.prs[0].key)}">${esc(r.label || c?.title || r.concept)}</button>`; }
    if (r.beat) return `<button class="ref" data-act="gobeat" data-v="${esc(pr ? pr.key : "session")}:${esc(r.beat)}">${esc(r.label || "see beat")}</button>`;
    if (r.pr && prByKey(r.pr)) return `<button class="ref" data-act="view" data-v="${esc(r.pr)}">${esc(r.label || "#" + prByKey(r.pr).number)}</button>`;
    return "";
  }).join("");
  return chips ? `<div class="refs">${chips}</div>` : "";
}
// Diagrams use semantic classes the app styles per theme: pr<number> (one color per PR, same as the
// PR chips), new, changed, removed, focus. The skill never writes colors.
function themeClasses() {
  const css = getComputedStyle(document.documentElement), v = (n) => css.getPropertyValue(n).trim();
  const ink = v("--ink"), surface = v("--surface");
  const defs = S.data.prs.map((p, i) => `classDef pr${p.number} fill:${surface},stroke:${v("--p" + (i % 6))},stroke-width:3px,color:${ink}`);
  defs.push(`classDef new fill:${v("--add")},stroke:${v("--add-ink")},color:${ink}`,
    `classDef changed fill:${surface},stroke:${v("--focus")},stroke-width:3px,color:${ink}`,
    `classDef removed fill:${v("--sunk")},stroke:${v("--muted")},stroke-dasharray:4 3,color:${v("--muted")}`,
    `classDef focus stroke:${v("--focus")},stroke-width:3px`);
  return defs;
}
function mermaidSrc(src, highlight) {
  if (!/^(flowchart|graph|stateDiagram)/.test(src.trim())) return src;
  // our classDefs come last so they win over any colors written into the source
  const out = [src.replace(/^\s*classDef\s+(pr\d+|new|changed|removed|focus)\b.*$/gm, ""), ...themeClasses().map((d) => "  " + d)];
  if (highlight?.length) out.push(`  class ${highlight.join(",")} focus`);
  return out.join("\n");
}
function excerpt(pr, path, from, to, notes = []) {
  const f = pr.files.find((x) => x.path === path);
  if (!f) return `<p class="empty">${esc(path)} is not in this PR.</p>`;
  const rows = [];
  let last = null;
  for (const h of f.hunks) for (const l of h.lines) {
    const [k, o, n, t] = l, m = l[4] || {};
    const ln = n ?? null;
    const inRange = ln != null ? ln >= from && ln <= to : last != null && last >= from && last < to;
    if (ln != null) last = ln;
    if (!inRange || (S.semantic && m.ws && k === "-")) continue;
    rows.push(`<tr class="${S.semantic && m.ws ? "wsl" : k === "+" ? "a" : k === "-" ? "d" : ""}"><td class="ln">${n ?? ""}</td><td class="code">${codeHtml(S.semantic && m.ws ? " " : k, t, m, S.semantic)}</td></tr>`);
    notes.filter((x) => x.line === n).forEach((x) => rows.push(`<tr class="note-row"><td class="ln">◆</td><td>${storyText(x.text, pr)}</td></tr>`));
  }
  return rows.length ? `<div class="diff excerpt"><table>${rows.join("")}</table></div>` : `<p class="empty">Lines ${from}–${to} of ${esc(path)} are not in the diff.</p>`;
}
// Code shapes (call trees, component trees, file trees, pseudocode, types), optionally as a diff of the
// shape. File names that match a changed file become links to the diff; "# ..." is a quiet comment.
function shapeView(b, pr) {
  const owners = pr ? [pr] : S.data.prs;
  const linkPaths = (t) => t.replace(/[\w.-]+(?:\/[\w.-]+)*\.[a-z]{1,5}\b/gi, (m) => {
    const hit = owners.map((x) => [x, x.files.find((f) => f.path === m || f.path.endsWith("/" + m))]).find(([, f]) => f);
    return hit ? `<button class="ref inline" data-act="peek" data-pr="${esc(hit[0].key)}" data-path="${esc(hit[1].path)}" data-line=""><code>${m}</code></button>` : m;
  });
  const lines = (b.text || "").replace(/\n$/, "").split("\n");
  const rows = lines.map((raw, i) => {
    const mark = b.diff ? raw[0] || " " : " ";
    const body = b.diff ? raw.slice(1) : raw;
    const ci = body.indexOf("#");
    const code = ci >= 0 && /\s#\s/.test(body.slice(ci - 1, ci + 2)) ? body.slice(0, ci) : body;
    const cmt = code === body ? "" : body.slice(code.length);
    const note = (b.notes || []).filter((n) => n.line === i + 1).map((n) => `<div class="sh-note">◆ ${storyText(n.text, pr)}</div>`).join("");
    return `<div class="sh-l ${mark === "+" ? "add" : mark === "-" ? "del" : ""}"><span class="sh-m">${b.diff ? esc(mark) : ""}</span><span class="sh-c">${linkPaths(esc(code))}${cmt ? `<span class="sh-cmt">${linkPaths(esc(cmt))}</span>` : ""}</span></div>${note}`;
  }).join("");
  return `<div class="shape f-${esc(b.form || "")}">${b.form ? `<div class="sh-k">${esc(b.form)}${b.diff ? " · diff" : ""}</div>` : ""}<div class="sh-b">${rows}</div></div>`;
}
function mediaEl(src, type, caption) {
  const url = /^https?:/.test(src) ? src : SNAPSHOT ? (SNAPSHOT.media || {})[src] || "" : "/media/" + encodeURIComponent(src);
  const isVideo = type === "video" || /\.(mp4|webm|mov)$/i.test(src);
  return `<figure class="media">${isVideo ? `<video src="${esc(url)}" controls muted playsinline loop preload="metadata"></video>` : `<img src="${esc(url)}" alt="${esc(caption || "")}" loading="lazy">`}${caption ? `<figcaption>${esc(caption)}</figcaption>` : ""}</figure>`;
}
function sideView(s, pr) {
  if (!s) return "";
  if (s.mermaid) return `<div class="mermaid-box" data-mermaid="${esc(mermaidSrc(s.mermaid))}"><pre>${esc(s.mermaid)}</pre></div>`;
  if (s.media) return mediaEl(s.media, s.type, null);
  if (s.code) return `<pre class="snippet">${esc(s.code)}</pre>`;
  return `<p>${storyText(s.text || "", pr)}</p>`;
}
function findingMini(f, pr) {
  const v = verdicts(pr?.key || f.pr)[f.id];
  return `<div class="fmini sev-${esc(f.severity)}">${sevPill(f.severity)}<span class="t">${mdi(f.title)}</span>${f.stance ? `<span class="stance ${esc(f.stance)}" title="${esc(f.stance_why || "")}">agent: ${esc(f.stance)}</span>` : ""}${v ? `<span class="pill">${esc(v)}</span>` : ""}<button class="btn ghost small" data-act="panel-of" data-pr="${esc(f.pr)}" data-v="findings">open</button></div>`;
}
function beatVisual(b, pr, prKey = pr ? pr.key : "session") {
  switch (b.kind) {
    case "diagram": return `<div class="mermaid-box" data-mermaid="${esc(mermaidSrc(b.mermaid || "", b.highlight))}"><pre>${esc(b.mermaid || "")}</pre></div>`;
    case "media": return mediaEl(b.src || "", b.type, b.caption);
    case "before_after": return `<div class="ba"><div><div class="ba-l">${esc(b.before?.label || "Before")}</div>${sideView(b.before, pr)}</div><div><div class="ba-l after">${esc(b.after?.label || "After")}</div>${sideView(b.after, pr)}</div></div>`;
    case "code": { const cp = pr || prByKey(b.pr) || S.data.prs.find((x) => x.files.some((f) => f.path === b.path)); return cp ? `<div class="code-cap mono">${cp === pr ? "" : "#" + cp.number + " · "}${esc(b.path)} · ${b.from}–${b.to}</div>${excerpt(cp, b.path, b.from, b.to, b.notes || [])}` : ""; }
    case "shape": return shapeView(b, pr);
    case "brief": return briefView(b);
    case "notice": return noticeView(b, prKey);
    case "views": return viewsView(b, pr, prKey);
    case "journey": return journeyView(b);
    case "scope": return scopeView(b);
    case "stories": return storiesView(b);
    case "findings": {
      const all = S.data.prs.flatMap((p) => [...(p.findings || []), ...(p.outdated || [])]);
      return `<div class="fminis">${(b.ids || []).map((id) => all.find((f) => f.id === id)).filter(Boolean).map((f) => findingMini(f, pr)).join("")}</div>`;
    }
    case "question": return `<div class="ask"><div class="q">${storyText(b.ask || "", pr)}</div><div class="row">${(b.options || []).map((o) => `<button class="btn" data-act="decide" data-pr="${esc(pr ? pr.key : "session")}" data-t="${enc(beatTarget(pr ? pr.key : "session", b))}" data-v="${esc(o)}">${esc(o)}</button>`).join("")}<button class="btn ghost" data-act="compose" data-pr="${esc(pr ? pr.key : "session")}" data-t="${enc(beatTarget(pr ? pr.key : "session", b))}">💬 Answer in a note</button></div></div>`;
    case "stat": return `<div class="stats">${(b.items || []).map((x) => `<div class="stat-i ${esc(x.tone || "")}"><div class="v">${esc(x.value)}</div><div class="l">${esc(x.label)}</div></div>`).join("")}</div>`;
    case "callout": return `<div class="callout ${esc(b.tone || "note")}">${storyText(b.text || "", pr)}</div>`;
    case "table": return `<div class="tablewrap"><table class="tbl"><thead><tr>${(b.columns || []).map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead><tbody>${(b.rows || []).map((r) => `<tr>${r.map((c) => `<td>${storyText(String(c), pr)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
  }
  return "";
}
function seenBeats() { return new Set(S.events.filter((e) => e.type === "beat_seen").map((e) => e.target?.id)); }
function beatView(b, i, pr, prKey) {
  const t = beatTarget(prKey, b);
  const avoid = avoidRule(b) && !(b.kind === "findings" && (b.ids || []).some((id) => S.data.prs.some((p) => (p.findings || []).some((f) => f.id === id && ["critical", "high"].includes(f.severity)))));
  const open = S.openBeats.has(t.id);
  const decided = notes().filter((n) => n.target?.kind === "beat" && n.target.id === t.id);
  const marked = (marks().get(tkey(t, prKey)) || new Set()).size > 0;
  return `<section class="beat w-${esc(b.weight || "normal")} span-${b.width === "half" ? "half" : "full"} k-${esc(b.kind)} markable ${avoid && !open ? "quiet" : ""}" id="beat-${esc(t.id)}" data-beat="${esc(t.id)}" data-pr="${esc(prKey)}">
    <div class="beat-tools ${marked ? "on" : ""}">${markbar(t, prKey, { compact: true, label: b.title })}</div>
    <h2 class="beat-title">${storyText(b.title || "", pr)}</h2>
    ${b.lede ? `<p class="lede">${storyText(b.lede, pr)}</p>` : ""}
    ${avoid && !open ? `<button class="btn ghost small" data-act="openbeat" data-v="${esc(t.id)}">Show ${esc(b.kind)} <span class="muted">· quieted by your preference “${esc(avoid.text)}”</span></button>` : `<div class="visual">${beatVisual(b, pr, prKey)}</div>`}
    ${refChips(b, pr)}
    ${b.body ? `<details class="more"><summary>More</summary><div class="prose">${md(b.body)}</div></details>` : ""}
    ${decided.map(noteView).join("")}
  </section>`;
}
function storyView(beats, pr, prKey, { auto = false } = {}) {
  const seen = seenBeats();
  const rail = beats.map((b, i) => { const id = `${prKey}:${b.id}`; return `<button class="rail-i ${seen.has(id) ? "seen" : ""}" data-act="gobeat" data-v="${esc(id)}" title="${esc(b.title)}"><span class="t">${esc(b.title)}</span></button>`; }).join("");
  return `<div class="journal">
    <nav class="rail" aria-label="Story">${rail}<div class="rail-p muted">${beats.filter((b) => seen.has(`${prKey}:${b.id}`)).length}/${beats.length} read</div></nav>
    <div class="beats">${auto ? `<p class="auto-note muted">Drafted from the PR data. The skill writes a proper story during enrichment.</p>` : ""}${beats.map((b, i) => beatView(b, i, pr, prKey)).join("")}</div></div>`;
}

// The overview brief: a collapsed list (goal, how it works, status, what each PR adds). The title and
// lede stay visible; each part opens on click.
const BRIEF_LABELS = ["Goal", "How it works", "More detail", "Status and what's not included"];
function briefView(b) {
  const items = (b.paragraphs || []).map((t, i) => {
    const label = typeof t === "object" ? t.label : BRIEF_LABELS[i] || `Part ${i + 1}`;
    const text = typeof t === "object" ? t.text : t;
    return `<details class="bi"><summary>${esc(label)}</summary><p>${storyText(text || "", null)}</p></details>`;
  });
  const rows = (b.contributions || []).map((c) => `<div class="contrib">${prChip(c.pr)}<span>${storyText(c.adds || "", prByKey(c.pr) || null)}</span></div>`).join("");
  if (rows) items.push(`<details class="bi"><summary>What each PR adds <span class="muted">· ${(b.contributions || []).length}</span></summary><div class="contribs">${rows}</div></details>`);
  return `<div class="brief-list">${items.join("")}</div>`;
}
// The 1-3 things to notice first, ranked. Each jumps to the beat that explains it.
function noticeView(b, prKey) {
  const items = (b.items || []).map((it, i) => `<div class="ni ${esc(it.tone || "risk")}">
      <div class="ni-h"><span class="ni-n">${i + 1}</span><span class="ni-tone">${esc(it.tone || "risk")}</span></div>
      <div class="ni-t">${storyText(it.title || "", null)}</div>
      <div class="ni-x">${storyText(it.text || "", null)}</div>
      ${it.beat ? (it.pr && it.pr !== prKey
        ? `<button class="ref" data-act="gobeat-pr" data-pr="${esc(it.pr)}" data-v="${esc(it.pr)}:${esc(it.beat)}">see why in #${esc(prByKey(it.pr)?.number || "")} →</button>`
        : `<button class="ref" data-act="gobeat" data-v="${esc(prKey)}:${esc(it.beat)}">see why ↓</button>`) : ""}</div>`).join("");
  return `<div class="notice n${(b.items || []).length}">${items}</div>`;
}
// Several lenses on one system (architecture, data flow, execution...): one visual at a time.
function viewsView(b, pr, prKey) {
  const vs = b.views || [];
  const key = `${prKey}:${b.id}`;
  const cur = Math.min(S.lens[key] ?? 0, Math.max(vs.length - 1, 0));
  const v = vs[cur] || {};
  const tabs = vs.map((x, i) => `<button class="lens" role="tab" aria-selected="${i === cur}" data-act="lens" data-v="${esc(key)}" data-i="${i}" data-label="${esc(x.label)}" data-pr="${esc(prKey)}">${esc(x.label)}</button>`).join("");
  const body = v.mermaid ? `<div class="mermaid-box" data-mermaid="${esc(mermaidSrc(v.mermaid, v.highlight))}"><pre>${esc(v.mermaid)}</pre></div>` : v.shape ? shapeView({ ...v.shape, notes: v.shape.notes }, pr) : "";
  return `<div class="lenses" role="tablist">${tabs}</div><div class="lens-q">${esc(v.question || "")}</div>${v.lede ? `<p class="lens-lede">${storyText(v.lede, pr)}</p>` : ""}${body}`;
}
// Session-level kinds: they connect the PRs. Each PR gets a stable color (its index).
const prIdx = (k) => Math.max(0, S.data.prs.findIndex((p) => p.key === k));
// The owner's own prefix is noise: acme/acme-billing -> billing. Enough to tell repos apart.
const shortRepo = (r, owner) => { const pre = String(owner || "").split("-")[0].replace(/[^A-Za-z0-9]/g, ""); return pre ? r.replace(new RegExp(`^${pre}-`, "i"), "") || r : r; };
const prChip = (k) => {
  const p = prByKey(k);
  if (p) return `<button class="prchip c${prIdx(k) % 6}" data-act="view" data-v="${esc(k)}">#${p.number}</button>`;
  const m = /^([\w.-]+)\/([\w.-]+)#(\d+)$/.exec(k);   // a PR outside this session: link to GitHub
  return m ? `<a class="prchip ext" href="https://github.com/${esc(m[1])}/${esc(m[2])}/pull/${m[3]}" target="_blank" rel="noopener" title="${esc(k)} (not in this session)">${esc(shortRepo(m[2], m[1]))}#${m[3]}</a>` : `<span class="prchip none">${esc(k)}</span>`;
};
function journeyView(b) {
  const steps = (b.steps || []).map((st) => `<li class="st ${esc(st.status || "changed")}"><div class="st-h"><b>${esc(st.actor || "")}</b>${st.status && st.status !== "changed" ? `<span class="st-s">${esc(st.status)}</span>` : ""}</div><div class="st-t">${storyText(st.text || "", null)}</div>${(st.prs || []).length ? `<div class="st-p">${st.prs.map(prChip).join("")}</div>` : ""}</li>`);
  return `<ol class="journey">${steps.join(`<li class="arrow" aria-hidden="true">→</li>`)}</ol>`;
}
const STORY_SRC = { qodo: "Qodo", ticket: "Ticket", spec: "Spec", pr: "PR description", inferred: "Inferred" };
function storiesView(b) {   // who the change is for: "As a …, I want …, so that …", with status and source
  return `<div class="tablewrap"><table class="tbl"><thead><tr><th>Story</th><th>For</th><th>PRs</th><th>Status</th><th>Source</th></tr></thead><tbody>${(b.items || []).map((it) => {
    const src = it.source || {};
    return `<tr><td>As ${/^(a|an|the)\s/i.test(it.as || "") ? "" : /^[aeiou]/i.test(it.as || "") ? "an " : "a "}<b>${esc(it.as || "")}</b>, I want ${esc(it.want || "")}${it.so_that ? `, so that ${esc(it.so_that)}` : ""}.</td><td>${esc(it.for || "user")}</td><td>${(it.prs || []).map((k) => prChip(k)).join(" ")}</td><td>${esc(it.status || "delivered")}</td><td>${esc(STORY_SRC[src.kind] || "")}${src.title ? ": " + (src.url ? `<a href="${esc(src.url)}" target="_blank" rel="noopener">${esc(src.title)}</a>` : esc(src.title)) : ""}</td></tr>`;
  }).join("")}</tbody></table></div>`;
}
function scopeView(b) {
  const prs = b.prs || S.data.prs.map((p) => p.key);
  const sym = { done: "●", partial: "◐", missing: "○", none: "" };
  return `<div class="tablewrap"><table class="tbl scope"><thead><tr><th>${esc(b.item_label || "Scope")}</th>${prs.map((k) => `<th>${prChip(k)}</th>`).join("")}<th>Status</th></tr></thead><tbody>${(b.items || []).map((it) => {
    const cells = prs.map((k) => (it.by || {})[k] || "none");
    const status = it.status || (cells.includes("done") ? (cells.includes("missing") || cells.includes("partial") ? "partial" : "done") : cells.includes("partial") ? "partial" : "missing");
    return `<tr class="${esc(status)}"><td>${storyText(it.text || "", null)}${it.source ? ` <span class="muted" style="font-size:12px">· ${esc(it.source)}</span>` : ""}</td>${cells.map((c) => `<td class="cell ${esc(c)}" title="${esc(c)}">${sym[c] ?? esc(c)}</td>`).join("")}<td><span class="pill ${status === "done" ? "ok" : status === "missing" ? "fail" : "medium"}">${esc(status)}</span></td></tr>`; }).join("")}</tbody></table></div>`;
}
function sessionStory() {
  if (S.data.story?.length) return storyView(S.data.story, null, "session");
  if (S.data.prs.length < 2) return "";
  return `<p class="auto-note muted">One story across all ${S.data.prs.length} PRs appears here after the skill's enrichment step.</p>`;
}
function contextBox() {
  const c = S.data.context || {};
  const src = c.sources || [];
  const gh = (u) => (/^https:\/\/github\.com\//.test(String(u || "")) ? u : "#");
  const stacked = new Set((c.missing_stack || []).map((m) => String(m.key || "").toLowerCase()));   // a stacked PR a description also names: once
  const miss = (c.missing_stack || []).concat((c.related || []).filter((r) => r && r.key && !stacked.has(r.key.toLowerCase())).map((r) => ({ key: r.key, url: gh(r.url),
    why: [r.why, r.draft ? "draft" : "", r.title ? r.title.slice(0, 80) : ""].filter(Boolean).join(" · ") })));   // sister PRs elsewhere too
  if (!src.length && !miss.length) return "";
  return `<details class="card ctx"><summary class="hd"><h2>Context behind the story</h2><span class="muted">${src.length} source${src.length === 1 ? "" : "s"}${miss.length ? ` · ${miss.length} related PR${miss.length > 1 ? "s" : ""} not in this session` : ""}</span></summary><div class="bd">
    ${src.map((x) => `<div class="src-i"><a href="${esc(x.url || "#")}" target="_blank" rel="noopener"><b>${esc(x.title || x.url)}</b></a> <span class="pill">${esc(x.kind || "link")}</span> ${(x.prs || []).map(prChip).join("")}${x.summary ? `<div class="muted">${storyText(x.summary, null)}</div>` : ""}</div>`).join("")}
    ${miss.length ? `<div class="muted">Related but not loaded: ${miss.map((m) => `<a href="${esc(m.url)}" target="_blank" rel="noopener">${esc(m.key)}</a> <span class="muted">(${esc(m.why)})</span>`).join(", ")}</div>` : ""}</div></details>`;
}
function panelStory(pr) {
  const beats = pr.story?.length ? pr.story : autoStory(pr);
  return storyView(beats, pr, pr.key, { auto: !pr.story?.length });
}
function peek(prKey, path, line, end) {
  const pr = prByKey(prKey);
  const n = Number(line) || null;
  const from = n ? Math.max(1, n - 6) : 1, to = n ? (Number(end) || n) + 6 : 40;
  modal(`<div class="row" style="justify-content:space-between"><h2 class="mono" style="font-size:13px">${esc(path)}${n ? ":" + n : ""}</h2><span class="row"><button class="btn small" data-act="gofile-close" data-pr="${esc(prKey)}" data-v="${esc(path)}" data-line="${n || ""}">Open in Files</button><button class="btn small ghost" data-act="close-modal">Close</button></span></div>
    ${excerpt(pr, path, from, to)}`);
}
let beatObserver = null;
function watchBeats() {
  beatObserver?.disconnect();
  const timers = new Map(), seen = seenBeats(), sent = (watchBeats.sent ||= new Set());
  beatObserver = new IntersectionObserver((entries) => {
    for (const en of entries) {
      const id = en.target.dataset.beat, pr = en.target.dataset.pr;
      if (seen.has(id) || sent.has(id)) continue;
      if (en.isIntersecting) timers.set(id, setTimeout(() => { sent.add(id); api("/api/event", { type: "beat_seen", pr, target: { kind: "beat", id } }).catch(() => {}); }, 1200));
      else clearTimeout(timers.get(id));
    }
  }, { threshold: 0.6 });
  document.querySelectorAll("section.beat[data-beat], section.layer[data-beat]").forEach((el) => beatObserver.observe(el));
}

function noteView(n) {
  const src = n.source === "agent" ? "agent" : n.source === "github" ? "github" : "app";
  return `<div class="nitem ${src}"><div>${n.emoji ? esc(n.emoji) + " " : ""}${esc(n.text)}</div>
    <div class="row src"><b>${src === "agent" ? "from coding agent" : src === "github" ? "already on GitHub" : "you"}</b>${n.target?.label ? " · " + esc(n.target.label) : n.path ? ` · ${esc(n.path)}:${esc(n.line)}` : ""}${n.posted ? " · posted" : n.post ? (findingThread(n.target || {}, n.pr) ? (n.resolve ? " · will reply in its thread and resolve it" : " · will reply in its thread") : " · will post") : ""}</div></div>`;
}
function renderDrawer() {
  const all = notes().sort((a, b) => (b.ts || "").localeCompare(a.ts || ""));
  const list = S.drawerPr === "all" ? all : all.filter((n) => n.pr === S.drawerPr);
  const nMarks = [...marks().values()].reduce((a, s) => a + s.size, 0);
  const resolvedThreads = new Set(S.events.filter((e) => e.type === "thread_resolved").map((e) => e.thread_id));
  const retries = (k) => new Set(S.events.filter((e) => e.type === "published" && e.pr === k && e.resolve_pending && !resolvedThreads.has(e.thread_id)).map((e) => e.thread_id)).size;
  const postable = S.data.prs.map((p) => [p, all.filter((n) => n.pr === p.key && n.post && !n.posted).length + retries(p.key)]).filter(([, k]) => k);
  $("#drawer").innerHTML = `<h2>Notes <span class="muted" style="font-weight:400;font-size:12px">${all.length} notes · ${nMarks} marks</span></h2>
    <select id="drawer-pr" aria-label="Filter notes"><option value="all">All PRs</option>${S.data.prs.map((p) => `<option value="${esc(p.key)}" ${S.drawerPr === p.key ? "selected" : ""}>#${p.number} ${esc(p.title.slice(0, 40))}</option>`).join("")}</select>
    ${SNAPSHOT || S.data.product ? "" : postable.map(([p, k]) => `<button class="btn primary" data-act="publish" data-pr="${esc(p.key)}">Publish #${p.number} to GitHub (${k})</button>`).join("")}
    <p class="muted" style="font-size:12px;margin:0">Start a note with <code>remember:</code> to save a preference, or <code>fact:</code> to propose knowledge. Agents can add notes with <code>python3 -m cockpit note</code>.</p>
    ${list.map((n) => `<div style="display:grid;gap:4px">${noteView(n)}<div class="row">
      ${S.data.product || n.posted || n.source === "github" ? "" : `<label class="chk" style="font-size:12px"><input type="checkbox" data-act="togglepost" data-id="${esc(n.note_id)}" ${n.post ? "checked" : ""}> Post to GitHub</label>`}
      ${n.source === "github" ? "" : `<button class="btn ghost small" data-act="delnote" data-id="${esc(n.note_id)}" data-pr="${esc(n.pr)}">Delete</button>`}
      <button class="btn ghost small" data-act="gonote" data-id="${esc(n.note_id)}">Show</button></div></div>`).join("") || `<p class="empty">No notes yet.</p>`}`;
}
function findingThread(target, pr) {
  if (target.kind !== "finding") return null;
  const f = (prByKey(pr)?.findings || []).find((x) => x.id === target.id);
  if (f?.thread) return f.thread.can_reply !== false ? f.thread : null;
  // collected before thread state was read: the link still says it has one; publish checks GitHub first
  // same test as the server's threads.comment_id: either link, or the Qodo CLI's inline comment id
  const linked = [f?.url, f?.thread_url].some((u) => /#discussion_r\d+$/.test(u || "")) || /^gh\d*:[^:]+:\d+$/.test(f?.inline_comment_id || "");
  return linked ? { can_resolve: true, guessed: true } : null;
}
function composerHTML(target, pr, extra = {}) {
  const th = findingThread(target, pr);
  const where = th ? (th.resolved ? "replies in its thread on GitHub (already resolved there)" : "replies in its thread on GitHub")
    : extra.path ? (extra.line ? `inline on ${esc(extra.path)}:${esc(extra.line)}` : "deleted line: goes in the review body")
    : target.kind === "finding" ? "goes in the review body (this finding has no thread on GitHub)" : "goes in the review body";
  const resolve = th && !th.resolved && th.can_resolve ? `<label class="chk" style="font-size:12px"><input type="checkbox" id="c-resolve"> Resolve the thread</label>` : "";
  const ems = Object.entries(S.data.emoji).filter(([, m]) => m.prefix).map(([em, m]) => `<label class="chk" style="font-size:12px"><input type="radio" name="c-em" value="${em}"> ${em} ${esc(m.label)}</label>`).join("");
  return `<form class="composer" id="composer" data-t="${enc(target)}" data-pr="${esc(pr)}" data-path="${esc(extra.path || "")}" data-line="${esc(extra.line || "")}">
    <div class="row muted" style="font-size:12px">Note on ${esc(target.label || target.kind)}</div>
    <div class="row"><label class="chk" style="font-size:12px"><input type="radio" name="c-em" value="" checked> plain</label>${ems}</div>
    <textarea id="c-text" placeholder="Your comment. remember: … saves a preference; fact: … proposes knowledge" required></textarea>
    <div class="row"><label class="chk"><input type="checkbox" id="c-post" ${S.data.product ? "disabled" : ""} ${extra.post === false || S.data.product ? "" : "checked"}> Post to GitHub</label>
      <span class="hint">${where}</span>${resolve}
      <span style="flex:1"></span><button type="button" class="btn" data-act="cancel-compose">Cancel</button><button class="btn primary" type="submit">Save note</button></div></form>`;
}
function openComposer(anchor, target, pr, extra) {
  closeComposer();
  S.composerOpen = true;
  const wrap = document.createElement(anchor.tagName === "TR" ? "tr" : "div");
  wrap.id = "composer-wrap";
  if (anchor.tagName === "TR") { wrap.className = "inline"; wrap.innerHTML = `<td colspan="3">${composerHTML(target, pr, extra)}</td>`; anchor.after(wrap); }
  else { wrap.innerHTML = composerHTML(target, pr, extra); anchor.after(wrap); }
  $("#c-text").focus();
}
function closeComposer() { $("#composer-wrap")?.remove(); S.composerOpen = false; }

/* ---------------- live state: has the PR moved since this snapshot? ---------------- */
const MERGE_BLOCKERS = { DIRTY: "merge conflicts", BLOCKED: "blocked by checks or rules", BEHIND: "behind its base branch", DRAFT: "still a draft" };
function liveNotes(keys) {
  const items = [];
  for (const k of keys) {
    const l = S.live[k];
    const p = prByKey(k);
    if (!l || !p || l.error) continue;
    const bits = [];
    if (l.moved) bits.push(l.new_commits > 0 ? `${l.new_commits} new commit${l.new_commits > 1 ? "s" : ""}` : "new commits (rewritten history)");
    if ((l.approved_by || []).length) bits.push(`approved by ${l.approved_by.join(", ")}`);
    if (l.new_comments) bits.push(`${l.new_comments} new comment${l.new_comments > 1 ? "s" : ""}`);
    if (l.state && l.state !== "OPEN") bits.push(l.state.toLowerCase());
    // "blocked" while a review is still required is every PR under review: not news
    const awaiting = l.merge_state === "BLOCKED" && (l.review_decision === "REVIEW_REQUIRED" || l.review_decision === "CHANGES_REQUESTED");
    if (MERGE_BLOCKERS[l.merge_state] && !awaiting) bits.push(MERGE_BLOCKERS[l.merge_state]);
    if (bits.length) items.push({ k, p, bits, moved: l.moved });
  }
  if (!items.length) return "";
  const moved = items.some((x) => x.moved || x.bits.some((b) => b.includes("comment") || b.startsWith("approved")));
  return `<div class="livebar">${items.map((x) => `<div><b>#${x.p.number}</b> ${esc(x.bits.join(" · "))}</div>`).join("")}
    ${moved ? `<div class="muted">This review shows the snapshot from ${esc((S.data.created || "").slice(0, 16).replace("T", " "))}. To update it and keep your notes: <code>python3 -m cockpit refresh --session ${esc(S.data.session)}</code>, then reload.</div>` : ""}</div>`;
}
async function pollLive() {
  if (SNAPSHOT || S.data.demo) return;
  try { const j = await api("/api/live"); S.live = j.prs || {}; render(); } catch (_) { /* offline: keep the snapshot */ }
}

/* ---------------- render ---------------- */
function render() {
  let localNotice = document.getElementById('product-notice');
  if (S.data?.product && !localNotice) {
    localNotice = document.createElement('aside'); localNotice.id = 'product-notice';
    localNotice.style.cssText = 'position:fixed;bottom:0;left:0;right:0;z-index:99999;background:var(--surface);color:var(--ink);border-top:1px solid var(--line);padding:8px;font:12px sans-serif';
    document.body.appendChild(localNotice);
  }
  if (S.data?.product && localNotice) {
    localNotice.textContent = 'Local review and export only. Notes and accept/dismiss marks stay local; provider threads and Qodo dispositions are unchanged.';
    if (S.data.collection?.complete === false) localNotice.textContent += ` Work package incomplete: ${S.data.collection.collected_refs?.length || 0} of ${S.data.collection.requested_refs?.length || 0} requested changes retained.`;
  }
  if (S.composerOpen) { renderDrawer(); renderTabs(); return; } // don't wipe a note being typed
  const sy = window.scrollY;
  renderTabs();
  const pr = prByKey(S.view);
  $("#main").innerHTML = pr ? renderPR(pr) : renderOverview();
  renderDrawer();
  renderMermaid();
  watchBeats();
  window.scrollTo(0, sy);
  if (S.flash) {
    const row = document.querySelector("tr.flash");
    if (row) row.scrollIntoView({ block: "center" });
    S.flash.done = true;
  }
}
let mermaidReady = false;
const mermaidCache = new Map();
function renderMermaid() {
  if (!window.mermaid) return;
  if (!mermaidReady) {
    const css = getComputedStyle(document.documentElement), v = (n) => css.getPropertyValue(n).trim();
    window.mermaid.initialize({ startOnLoad: false, securityLevel: "strict", theme: "base", themeVariables: {
      fontFamily: v("--f-ui"), fontSize: "13px", background: v("--card"), primaryColor: v("--surface"), primaryTextColor: v("--ink"),
      primaryBorderColor: v("--line-strong"), lineColor: v("--muted"), secondaryColor: v("--card"), tertiaryColor: v("--card"),
      clusterBkg: v("--card"), clusterBorder: v("--line"), edgeLabelBackground: v("--card"), noteBkgColor: v("--hl"), noteTextColor: v("--ink"),
      actorBkg: v("--surface"), actorBorder: v("--line-strong"), actorTextColor: v("--ink"), signalColor: v("--muted"), signalTextColor: v("--ink"),
      labelBoxBkgColor: v("--card"), labelBoxBorderColor: v("--line"), labelTextColor: v("--ink"), loopTextColor: v("--muted") } });
    mermaidReady = true;
  }
  document.querySelectorAll("[data-mermaid]").forEach(async (el, i) => {
    const src = el.dataset.mermaid;
    if (mermaidCache.has(src)) { el.innerHTML = mermaidCache.get(src); return; }
    const id = `m${Date.now()}${i}`;
    try { const { svg } = await window.mermaid.render(id, src); mermaidCache.set(src, svg); el.innerHTML = svg; }
    catch (_) {   // mermaid leaves its "Syntax error" drawing at the end of the page: remove it, keep the source text visible
      document.querySelectorAll(`#${id}, #d${id}`).forEach((n) => n.remove());
    }
  });
}
function toast(msg) {
  const t = $("#toast"); t.textContent = msg; t.hidden = false;
  clearTimeout(toast._t); toast._t = setTimeout(() => (t.hidden = true), 2600);
}
function modal(html) { $("#modal-body").innerHTML = html; $("#modal").hidden = false; $("#modal-body button, #modal-body a")?.focus(); }
function closeModal() { $("#modal").hidden = true; }

/* ---------------- navigation + dwell ---------------- */
function leavePanel() {
  const pr = prByKey(S.view);
  const ms = Date.now() - S.panelStart;
  if (pr && ms > 1500) api("/api/event", { type: "dwell", pr: pr.key, panel: S.panel[pr.key], ms }).catch(() => {});
  S.panelStart = Date.now();
}
function go(view, panel, explicit) {
  leavePanel();
  closeComposer();
  S.view = view;
  if (panel) S.panel[view] = panel;
  if (explicit && panel) api("/api/event", { type: "view", pr: view, panel }).catch(() => {});
  render();
  window.scrollTo(0, 0);
}
function goFile(prKey, path, line) {
  S.flash = line ? { path, line: Number(line) } : null;
  S.filesMode[prKey] = "files";   // jumping to a line needs the file view
  go(prKey, "files");
  const el = [...document.querySelectorAll("details.file")].find((d) => d.dataset.path === path);
  if (el) { el.open = true; if (!line) el.scrollIntoView({ block: "start" }); }
}

/* ---------------- events ---------------- */
document.addEventListener("click", async (e) => {
  const el = e.target.closest("[data-act]");
  if (!el) { if (e.target.id === "modal") closeModal(); return; }
  const a = el.dataset.act, pr = el.dataset.pr;
  if (a === "view") return go(el.dataset.v, null, false);
  if (a === "panel") return go(S.view, el.dataset.v, true);
  if (a === "gofile") return goFile(pr, el.dataset.v, el.dataset.line);
  if (a === "goknow") return go(el.dataset.v, "knowledge", true);
  if (a === "panel-of") return go(pr, el.dataset.v, true);
  if (a === "peek") return peek(pr, el.dataset.path, el.dataset.line, el.dataset.end);
  if (a === "gofile-close") { closeModal(); return goFile(pr, el.dataset.v, el.dataset.line); }
  if (a === "gobeat-pr") {
    go(pr, "story", true);
    setTimeout(() => { const t = document.getElementById("beat-" + el.dataset.v); if (t) { t.scrollIntoView({ block: "start" }); t.classList.add("flash"); } }, 50);
    return;
  }
  if (a === "gobeat") {
    const tgt = document.getElementById("beat-" + el.dataset.v);
    if (!tgt) return;
    tgt.scrollIntoView({ behavior: "smooth", block: "start" });
    tgt.classList.remove("flash"); void tgt.offsetWidth; tgt.classList.add("flash");
    return;
  }
  if (a === "readcheck") return record({ type: "read_check", pr, target: { kind: "block", id: el.dataset.v }, done: el.checked });
  if (a === "semantic") { S.semantic = el.dataset.v === "1"; return render(); }
  if (a === "togglemove") { S.openMoves.has(el.dataset.v) ? S.openMoves.delete(el.dataset.v) : S.openMoves.add(el.dataset.v); return render(); }
  if (a === "filesmode") { S.filesMode[pr] = el.dataset.v; return render(); }
  if (a === "lens") {
    S.lens[el.dataset.v] = Number(el.dataset.i);
    api("/api/event", { type: "lens", pr: el.dataset.pr, target: { kind: "beat", id: el.dataset.v }, lens: el.dataset.label }).catch(() => {});
    return render();
  }
  if (a === "openbeat") { S.openBeats.add(el.dataset.v); return render(); }
  if (a === "decide") return record({ type: "note", pr, target: dec(el.dataset.t), text: `Decision: ${el.dataset.v}`, post: false, note_id: "n-" + Math.random().toString(16).slice(2, 10) });
  if (a === "mark") {
    const t = dec(el.dataset.t), em = el.dataset.em;
    const on = el.getAttribute("aria-pressed") === "true";
    return record({ type: "mark", pr, target: t, emoji: em, undo: on });
  }
  if (a === "verdict") {
    const cur = verdicts(pr)[el.dataset.id];
    const v = cur === el.dataset.v ? "none" : el.dataset.v;
    return record({ type: "finding_verdict", pr, target: { kind: "finding", id: el.dataset.id }, verdict: v });
  }
  if (a === "showcoll") { S.showCollapsed[pr] = !S.showCollapsed[pr]; return render(); }
  if (a === "compose") {
    const t = dec(el.dataset.t);
    const anchor = el.closest(".finding, .concept, .card > .hd, .markable, .row") || el;
    return openComposer(anchor, t, pr, { post: t.kind !== "panel" });
  }
  if (a === "compose-line") {
    const path = el.dataset.path, line = el.dataset.line || "", oline = el.dataset.oline;
    const target = { kind: "line", id: `${path}:${line || "old" + oline}`, label: `${path}:${line || oline}` };
    return openComposer(el.closest("tr"), target, pr, { path, line });
  }
  if (a === "cancel-compose") return closeComposer();
  if (a === "togglepost") {
    const n = notes().find((x) => x.note_id === el.dataset.id);
    return record({ ...strip(n), post: el.checked });
  }
  if (a === "delnote") return record({ type: "note", pr, note_id: el.dataset.id, undo: true });
  if (a === "gonote") {
    const n = notes().find((x) => x.note_id === el.dataset.id);
    if (!n) return;
    if (n.path) return goFile(n.pr, n.path, n.line);
    if (n.target?.kind === "finding") return go(n.pr, "findings", false);
    if (prByKey(n.pr)) return go(n.pr, "summary", false);
    return go("overview");
  }
  if (a === "okf") {
    try {
      const j = await api("/api/okf", { action: el.dataset.op, path: el.dataset.path, pr });
      S.mem = j.memory; toast(`Knowledge ${j.verdict === "confirm" ? "confirmed" : j.verdict}`); await poll(true);
    } catch (err) { toast(err.message); }
    return;
  }
  if (a === "publish") return publish(pr);
  if (a === "publish-real") return publish(pr, false);
  if (a === "close-modal") return closeModal();
  if (a === "planjump") {   // a bar segment: open that PR's plan, then its block, tier section or ledger group
    const id = el.dataset.v, key = el.dataset.pr;
    if (id.startsWith("lg-") && !S.openLedger.has(id.slice(3))) {   // render the group open; it counts as opening it
      const gk = id.slice(3), [, tier, reason] = gk.split("|");
      S.openLedger.add(gk);
      api("/api/event", { type: "attention_opened", pr: key, target: { kind: "range", id: gk, reason, tier } }).catch(() => {});
    }
    const away = key && (S.view !== key || S.panel[key] !== "files" || (S.filesMode[key] || "plan") !== "plan");
    if (away) { S.filesMode[key] = "plan"; go(key, "files", true); } else render();
    const tip = document.querySelector(".tip");
    if (tip) tip.hidden = true;
    const land = () => { const x = document.getElementById(id); if (x) { x.scrollIntoView({ behavior: away ? "auto" : "smooth", block: "start" }); x.classList.add("flash"); } };
    requestAnimationFrame(land);   // after the new tab has laid out (instant when the tab changed)
    return;
  }
});
function strip(n) { const { ts, ...rest } = n; return rest; }

// Opening a skim/skip group shows its code; the first open per group is recorded, so a reviewer who
// keeps opening, say, tests gets them on the reading list next time.
document.addEventListener("toggle", (e) => {
  const d = e.target;
  if (!d.matches || !d.matches("details.lg")) return;
  const key = d.dataset.key;
  if (d.open && !S.openLedger.has(key)) {
    S.openLedger.add(key);
    api("/api/event", { type: "attention_opened", pr: d.dataset.pr, target: { kind: "range", id: key, reason: d.dataset.reason, tier: d.dataset.tier } }).catch(() => {});
    render();
  } else if (!d.open && S.openLedger.has(key)) {
    S.openLedger.delete(key);
  }
}, true);
document.addEventListener("change", (e) => {
  if (e.target.id === "ignore-prefs") record({ type: "pref_toggle", ignore: e.target.checked });
  if (e.target.id === "drawer-pr") { S.drawerPr = e.target.value; renderDrawer(); }
});
document.addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = e.target;
  if (f.id === "composer") {
    const text = $("#c-text").value.trim();
    if (!text) return;
    const target = dec(f.dataset.t);
    const ev = { type: "note", pr: f.dataset.pr, target, text, emoji: (f.querySelector("input[name=c-em]:checked") || {}).value || null,
      post: $("#c-post").checked, resolve: !!$("#c-resolve")?.checked, note_id: "n-" + Math.random().toString(16).slice(2, 10), path: f.dataset.path || null, line: f.dataset.line ? Number(f.dataset.line) : null };
    closeComposer();
    await record(ev);
    const memOn = !(S.mem && S.mem.enabled === false);
    toast(!memOn ? "Note saved" : text.toLowerCase().startsWith("remember:") ? "Saved. Becomes a preference when you finish." : text.toLowerCase().startsWith("fact:") ? "Saved. Becomes a knowledge draft when you finish." : "Note saved");
  }
  if (f.id === "propose") {
    const title = $("#p-title").value.trim();
    if (!title) return;
    try {
      const j = await api("/api/okf", { action: "propose", pr: f.dataset.pr, type: $("#p-type").value, title, body: $("#p-body").value.trim(),
        paths: $("#p-paths").value.split(",").map((s) => s.trim()).filter(Boolean), confirm: $("#p-confirm").checked,
        source: prByKey(f.dataset.pr)?.url });
      S.mem = j.memory;
      const pr = prByKey(f.dataset.pr); if (pr && !pr.concepts.includes(j.path)) pr.concepts.push(j.path);
      toast("Saved to knowledge"); await poll(true);
    } catch (err) { toast(err.message); }
  }
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") { closeModal(); closeComposer(); }
  if (e.key === "Enter" && e.target.matches("g.node")) e.target.dispatchEvent(new MouseEvent("click", { bubbles: true }));
});
document.addEventListener("mouseover", (e) => {
  const n = e.target.closest("svg g.node[data-node]");
  document.querySelectorAll("svg .edge.on, svg .node.on").forEach((x) => x.classList.remove("on"));
  if (!n) return;
  const id = n.dataset.node; n.classList.add("on");
  document.querySelectorAll("svg .edge").forEach((p) => { if (p.dataset.a === id || p.dataset.b === id) { p.classList.add("on"); document.querySelector(`g.node[data-node="${CSS.escape(p.dataset.a === id ? p.dataset.b : p.dataset.a)}"]`)?.classList.add("on"); } });
});

async function publish(prKey, dry = true) {
  if (S.data.product) return toast("Local review and export only");
  try {
    const j = await api("/api/publish", { pr: prKey, dry_run: dry, ...(dry || !S.expect?.[prKey] ? {} : { expect: S.expect[prKey] }) });
    if (!j.ok && !j.results) return toast(j.error);
    if (j.dry_run) (S.expect ||= {})[prKey] = j.expect;   // what Publish may post: exactly what this preview shows
    if (j.dry_run) {
      const p = j.payload, rs = j.replies || [];
      const resolving = rs.filter((r) => r.resolve && !r.resolved && r.can_resolve).length;
      const pre = (r) => r.resolve_only ? `<pre>${esc(r.title)}\n→ resolves the thread (retry: the reply is already on GitHub)</pre>`
        : `<pre>${esc(r.title)}${r.resolve ? (r.resolved ? "\n(already resolved on GitHub)" : r.can_resolve ? "\n→ resolves the thread" : "\n(you can't resolve threads on this repo: reply only)") : ""}\n\n${esc(r.body)}</pre>`;
      const rsHtml = rs.length ? `<h3>Replies in existing threads (${rs.length})</h3>${rs.map(pre).join("")}` : "";
      const rvHtml = p ? `<h3>Review (${p.comments.length} inline, the rest in the body)</h3><pre>${esc(p.body)}</pre>${p.comments.map((c) => `<pre>${esc(c.path)}:${c.line}\n${esc(c.body)}</pre>`).join("")}` : "";
      modal(`<h2>Publish to GitHub: ${esc(prKey)}</h2><p class="muted">${j.count} note(s): ${rs.length ? `${rs.length} repl${rs.length > 1 ? "ies" : "y"} in existing threads${resolving ? `, resolving ${resolving}` : ""}` : ""}${rs.length && p ? "; " : ""}${p ? "a COMMENT review (no approve or request-changes)" : ""}.</p>
        ${j.note ? `<div class="pref-why">${esc(j.note)}</div>` : ""}${rsHtml}${rvHtml}
        <div class="row">${S.data.demo ? `<span class="muted">Demo session: publishing is disabled.</span>` : `<button class="btn primary" data-act="publish-real" data-pr="${esc(prKey)}">Publish to GitHub</button>`}<button class="btn" data-act="close-modal">Cancel</button></div>`);
    } else {
      closeModal(); await poll(true);
      const rs = j.results || [];
      toast(j.ok ? `Published ${j.count} comment(s)` : j.error);
      const KIND = { review: "Review", reply: "Reply", resolve: "Resolve" };
      const line = (r) => `<li>${r.ok ? "✓" : "✕"} ${KIND[r.kind] || "Item"}${r.kind === "review" ? "" : ": " + esc(r.title || "")}${r.ok && r.url ? ` · <a href="${esc(r.url)}" target="_blank" rel="noopener">open ↗</a>` : ""}${r.resolve ? ` · ${esc(r.resolve)}` : ""}${r.error ? `<br><span class="muted">${esc(r.error)}</span>` : ""}</li>`;
      if (rs.length) modal(`<h2>${j.ok ? "Published" : rs.some((r) => r.ok) ? "Partly published" : "Not published"}</h2>${j.ok ? "" : `<p class="muted">${esc(j.error)}</p>`}<ul>${rs.map(line).join("")}</ul><button class="btn" data-act="close-modal">Close</button>`);
    }
  } catch (err) { toast(err.message); }
}

$("#toggle-notes").addEventListener("click", (e) => {
  const lay = document.querySelector(".layout"); lay.classList.toggle("no-drawer");
  e.currentTarget.setAttribute("aria-expanded", String(!lay.classList.contains("no-drawer")));
});
$("#finish").addEventListener("click", async () => {
  leavePanel();
  modal(`<h2>Making memories…</h2><p class="muted">Turning this review into preferences and knowledge.</p>`);
  try {
    const j = await api("/api/finish", {});
    S.mem = j.memory;
    const r = j.result;
    modal(`<h2>Memories made</h2>
      <h3>Preferences (AMR)</h3>${r.amr.length ? `<ul>${r.amr.map((b) => `<li>${mdi(b.text)} <span class="muted mono" style="font-size:12px">${b.result}${b.rule ? " · " + esc(b.rule) : ""} · +${b.evidence}</span></li>`).join("")}</ul>` : `<p class="muted">No new preference signals this time.</p>`}
      <h3>Knowledge (OKF)</h3>${r.okf.length ? `<ul>${r.okf.map((p) => `<li class="mono">${esc(p)} <span class="pill">draft</span></li>`).join("")}</ul>` : `<p class="muted">No new drafts from notes. Confirmed facts were saved as you went.</p>`}
      ${r.review_log ? `<p class="muted">Review log: <span class="mono">memory/amr/${esc(r.review_log)}</span></p>` : ""}
      <p class="muted">${j.commit ? "Git: " + esc(j.commit) : "Not committed (demo session or auto_commit off)."}</p>
      <div class="row"><button class="btn primary" data-act="close-modal">Done</button></div>`);
    render();
  } catch (err) { modal(`<h2>Couldn't finish</h2><pre>${esc(err.message)}</pre><button class="btn" data-act="close-modal">Close</button>`); }
});
window.addEventListener("beforeunload", leavePanel);

(async function boot() {
  try {
    if (SNAPSHOT) {
      document.body.classList.add("snapshot");
      $("#session").textContent = "";
      $("#finish").hidden = true;
      $(".brand").insertAdjacentHTML("beforeend", `<span class="snap-pill" title="Exported ${esc(SNAPSHOT.exported_at)}. Marks and notes stay in this browser.">shared snapshot · ${esc(SNAPSHOT.exported_at.slice(0, 10))}</span>`);
    }
    S.data = await api("/api/data");
    // Outdated findings (no longer in the current diff) live apart and never count toward severity.
    for (const pr of S.data.prs) {
      const all = pr.findings || [];
      const closed = (f) => ["outdated", "dismissed", "resolved", "detected_after_merge"].includes(f.status);
      pr.outdated = all.filter(closed);
      pr.findings = all.filter((f) => !closed(f));
    }
    S.mem = await api("/api/memory");
    if (S.mem && S.mem.enabled === false) $("#finish").hidden = true;   // memory is optional
    (SNAPSHOT ? Promise.resolve({ styles: SNAPSHOT.styles || [], recipes: SNAPSHOT.recipes || [] }) : api("/api/styles")).then((j) => {   // other ways to read this session (a snapshot: those exported with it)
      // one quiet Style menu, the same as the other styles' (no row of buttons): every way to read it, then your own
      const all = (j.styles || []).filter((s) => s.url || s.id === "cockpit"), other = all.filter((s) => s.id !== "cockpit");
      if (!other.length) return;
      const local = (() => { try { const v = JSON.parse(localStorage.getItem("ck:recipes") || "[]"); return Array.isArray(v) ? v : []; } catch (_) { return []; } })();
      const byId = new Map(); local.concat(j.recipes || []).forEach((r) => { if (r && r.id && r.name) byId.set(r.id, r); });   // saved in this browser too; the data home's copy wins
      const focus = other.find((s) => s.id === "focus"), mine = focus ? [...byId.values()].sort((a, b) => a.name.localeCompare(b.name)) : [];
      const it = (s) => s.id === "cockpit" ? `<div class="sm-it" aria-current="page"><b>${esc(s.name || "Cockpit")}</b><em>this page</em>${s.what ? `<span>${esc(s.what)}</span>` : ""}</div>`
        : `<a class="sm-it" role="menuitem" href="${esc(s.url)}"><b>${esc(s.name)}</b><em>Open →</em>${s.what ? `<span>${esc(s.what)}</span>` : ""}</a>`;
      const own = focus ? `<div class="sm-h">Your own style</div><p class="sm-note">Describe how you like to review, or arrange the parts yourself. It opens in Focus.</p>`
        + `<a class="sm-create" role="menuitem" href="${esc(focus.url)}#create">＋ Create your style</a>`
        + mine.map((r) => `<a class="sm-it" role="menuitem" href="${esc(focus.url)}#style-${esc(r.id)}"><b>${esc(r.name)}</b><em>Open →</em>${r.about ? `<span>${esc(r.about)}</span>` : ""}</a>`).join("") : "";
      $(".top-actions").insertAdjacentHTML("afterbegin", `<span class="style-menu"><button class="btn ghost sm-btn" aria-haspopup="menu" aria-expanded="false" title="Other ways to read this review">Style <b>Cockpit</b> ▾</button>
        <div class="sm-menu" role="menu" aria-label="Review styles" hidden>${own}<div class="sm-h${own ? " sep" : ""}">Review in a different style</div>${(all.some((s) => s.id === "cockpit") ? all : [{ id: "cockpit", name: "Cockpit" }].concat(other)).map(it).join("")}</div></span>`);
      const btn = $(".sm-btn"), menu = $(".sm-menu");
      const close = () => { menu.hidden = true; btn.setAttribute("aria-expanded", "false"); };
      btn.addEventListener("click", (e) => { e.stopPropagation(); const open = menu.hidden; menu.hidden = !open; btn.setAttribute("aria-expanded", String(open));
        if (open) { const r = btn.getBoundingClientRect(), left = r.left + r.width / 2 < innerWidth / 2; menu.style.left = left ? "0" : ""; menu.style.right = left ? "auto" : "";
          const first = menu.querySelector("a[role=menuitem]"); if (first) first.focus(); } });
      menu.addEventListener("keydown", (e) => {   // a menu moves with the arrows, Home and End
        const items = [...menu.querySelectorAll("a[role=menuitem]")], i = items.indexOf(document.activeElement);
        const to = { ArrowDown: i + 1, ArrowUp: i - 1, Home: 0, End: items.length - 1 }[e.key];
        if (to === undefined || !items.length) return;
        e.preventDefault(); items[(to + items.length) % items.length].focus();
      });
      document.addEventListener("click", (e) => { if (!e.target.closest(".style-menu")) close(); });
      document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !menu.hidden) { close(); btn.focus(); } });
    }).catch(() => {});
    const want = /pr=(\d+)/.exec(location.hash)?.[1];   // #pr=123 opens that PR
    const hit = want && S.data.prs.find((p) => String(p.number) === want);
    if (hit) { S.view = hit.key; const pn = /panel=(\w+)/.exec(location.hash)?.[1]; if (pn) S.panel[hit.key] = pn; }
    await poll(true);
    document.title = `Review · ${S.data.prs.map((p) => "#" + p.number).join(" ")}`;
    setInterval(poll, 2500);
    pollLive(); setInterval(pollLive, 180000);
    window.addEventListener("load", renderMermaid);
  } catch (e) {
    $("#main").innerHTML = `<div class="card"><div class="bd"><h2>Can't reach the cockpit server</h2><p class="muted">Start it with <code>python3 -m cockpit serve</code>, then reload. (${esc(e.message)})</p></div></div>`;
  }
})();
