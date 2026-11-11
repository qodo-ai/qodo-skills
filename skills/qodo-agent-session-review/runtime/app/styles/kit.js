/* Shared helpers for the review styles (app/styles/*.html). The session arrives as
   <script type="application/json" class="case-data">, the host as <script id="cockpit-host">:
   mode "serve" (notes go to the local Agent Session Review server) or "snapshot" (they stay in this browser). */
const KIT = (() => {
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  /* inline markdown: `code`, **bold**, [text](https://...) — input escaped first */
  const md = (s) => esc(s)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>")
    .replace(/\[([^\]]+)\]\((https:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  const cases = {};
  document.querySelectorAll("script.case-data").forEach((el) => { cases[el.dataset.case] = JSON.parse(el.textContent); });
  const caseIds = Object.keys(cases);
  const pick = () => { const h = (location.hash || "").slice(1); return cases[h] ? h : caseIds[0]; };
  const short = (key) => "#" + key.split("#")[1];
  const repoShort = (key) => key.split("/")[1].split("#")[0];
  const base = (p) => String(p ?? "").split("/").pop();
  const TIERS = ["deep", "review", "skim", "skip"];
  const TIER_NAME = { deep: "Deep read", review: "Read", skim: "Skim", skip: "Skip" };
  /* minutes to review: deep 8 lines/min, read 25, skim 120, skip 0 */
  const RATE = { deep: 8, review: 25, skim: 120, skip: Infinity };
  const minutes = (sum) => sum ? Math.round(TIERS.reduce((m, t) => m + (sum[t] || 0) / RATE[t], 0)) : 0;
  const totals = (c) => c.prs.reduce((a, p) => { const s = p.attention.summary || {}; TIERS.concat("total").forEach((t) => a[t] = (a[t] || 0) + (s[t] || 0)); return a; }, {});
  const allFindings = (c) => c.prs.flatMap((p) => p.findings.map((f) => ({ ...f, pr: p.key })));
  const sevRank = { critical: 0, high: 1, medium: 2, low: 3, info: 4 };
  const openFindings = (c) => allFindings(c).filter((f) => !f.status || f.status === "open").sort((a, b) => (sevRank[a.severity] ?? 5) - (sevRank[b.severity] ?? 5));
  /* a local finding: what the author's own `qodo review` found before the PR, its status as that review left it */
  const localTag = (f) => {
    if (f.status === 'detected_after_merge') return ` <span class="local" title="No fix was verified">· detected after merge</span>`;
    const l = f.local;
    if (l?.origin === 'managed') return ` <span class="local" title="${esc(`Qodo records this finding from local_skill before the PR${l.at ? ' on '+String(l.at).slice(0,10) : ''}. This origin does not establish a completed PR review.`)}">· before the PR</span>`;
    if (!l && f.review_source && f.review_source !== 'git_pr') return ` <span class="local">${esc(f.review_source === 'unknown' ? '· review origin unknown' : '· review source: '+f.review_source)}</span>`;
    if (!l) return "";
    const when = l.at ? ` on ${String(l.at).slice(0, 10)}` : "";
    if (f.source !== "qodo-local") return ` <span class="local" title="${esc(`The author's local review${when} found this too, and left it ${l.status || "open"}${l.reason ? `: ${l.reason}` : ""}`)}">· also found before the PR</span>`;
    const open = !f.status || f.status === "open";
    const t = `Found by the author's local qodo review${when}, before the PR.${open ? " Open at that review; a fix or dismissal since then isn't shown yet." : f.status === "dismissed" ? ` The author dismissed it${l.reason ? `: ${l.reason}` : ""}.` : f.status === "resolved" ? " A later local review confirmed the fix." : ""}${l.line ? ` At line ${l.line} then; the code has moved since.` : ""}`;
    return ` <span class="local" title="${esc(t)}">· before the PR${l.line ? `, line ${esc(l.line)} then` : ""}</span>`;
  };
  /* a rule, convention or style finding rather than a bug: Qodo's rule violations and skill insights, the style,
     naming and docs categories, and scanners of kind lint */
  const CONVENTION_CATS = new Set(["style", "naming", "docs", "documentation", "formatting", "convention", "conventions"]);
  const isConvention = (f) => /rule violation|skill insight|convention|^compliance(agentfile)?rule$|^skills?finding$/i.test(String(f.qodo_type || "")) || CONVENTION_CATS.has(String(f.category || "").toLowerCase())
    || (f.scanner && f.scanner.kind === "lint");
  /* what the author fixed or dismissed before the PR: the closed local findings, each with what became of it */
  const localDone = (findings) => {
    const done = (findings || []).filter((f) => f.source === "qodo-local" && f.local?.origin !== "managed" && f.status && f.status !== "open");
    if (!done.length) return "";
    const what = (f) => f.status === "resolved" ? "fixed" : f.status === "dismissed" ? "dismissed" : f.status === "detected_after_merge" ? "detected after merge; no fix verified" : f.status;
    return `<div class="local-done"><p class="muted" style="font-size:14px;margin:12px 0 4px">The author's saved local review has ${done.length} closed findings:</p><ul style="margin:0;padding-left:20px;font-size:14px">${done.map((f) =>
      `<li><b>${esc(what(f))}</b> · ${md(f.title)}${f.local && f.local.reason ? ` <span class="muted">(${esc(f.local.reason)})</span>` : ""}</li>`).join("")}</ul></div>`;
  };
  /* render code lines [[kind, old, new, text]] */
  /* light syntax colours, line by line (a diff's lines don't carry state, so a block comment colours only its own lines) */
  const LANGS = {
    c: { ext: /\.(js|jsx|mjs|cjs|ts|tsx|go|java|kt|kts|scala|rs|c|h|cc|cpp|hpp|cs|swift|php|dart)$/i, com: "//",
         kw: "abstract async await break case catch class const continue default defer delete do else enum export extends false final finally fn for from func function go if impl implements import in instanceof interface let match mod mut new nil null package private protected pub public return self static struct super switch this throw throws trait true try type typeof undefined var void where while yield" },
    py: { ext: /\.(py|pyi)$/i, com: "#", kw: "and as assert async await break class continue def del elif else except False finally for from global if import in is lambda None nonlocal not or pass raise return self True try while with yield" },
    rb: { ext: /\.(rb|rake)$/i, com: "#", kw: "begin class def do else elsif end ensure false if module nil rescue return self then true unless until when while yield" },
    sh: { ext: /(\.(sh|bash|zsh|ya?ml|toml|tf|tfvars|hcl|ini|cfg|conf|env|properties)|Dockerfile|Makefile)$/i, com: "#", kw: "if then else elif fi for in do done case esac function return export local true false null resource variable module provider data output locals" },
    sql: { ext: /\.sql$/i, com: "--", kw: "select from where join left right inner outer on group by order having insert into values update set delete create table alter add drop index primary key foreign references not null default and or as distinct limit" } };
  const langOf = (path) => Object.values(LANGS).find((l) => l.ext.test(String(path || ""))) || null;
  const hlText = (t, lang) => {
    if (!lang) return esc(t);
    const kw = lang.kws || (lang.kws = new Set(lang.kw.split(" ")));
    const com = lang.com.replace(/[/*]/g, "\\$&");
    const re = new RegExp(`(${com}.*$)|("(?:\\\\.|[^"\\\\])*"|'(?:\\\\.|[^'\\\\])*'|\`(?:\\\\.|[^\`\\\\])*\`)|(\\b\\d[\\d_.xXa-fA-F]*\\b)|([A-Za-z_$][\\w$]*)`, "g");
    let out = "", at = 0, m;
    while ((m = re.exec(t))) {
      out += esc(t.slice(at, m.index));
      const [w, c, s, n, id] = m;
      out += c ? `<span class="tk-c">${esc(c)}</span>` : s ? `<span class="tk-s">${esc(s)}</span>` : n ? `<span class="tk-n">${esc(n)}</span>`
        : kw.has(lang === LANGS.sql ? id.toLowerCase() : id) ? `<span class="tk-k">${esc(id)}</span>` : esc(w);
      at = m.index + w.length; if (c) break;
    }
    return out + esc(t.slice(at));
  };
  if (!document.getElementById("kit-hl")) {   // token colours that read on the light and dark code backgrounds
    const st = document.createElement("style"); st.id = "kit-hl";
    st.textContent = ".tk-k{color:#7c3aed}.tk-s{color:#0f7b55}.tk-c{color:#8a8f98;font-style:italic}.tk-n{color:#b45309}"
      + "@media (prefers-color-scheme: dark){:root:not([data-theme=light]) .tk-k{color:#b8a6ff}:root:not([data-theme=light]) .tk-s{color:#7dd3a8}:root:not([data-theme=light]) .tk-c{color:#8b929c}:root:not([data-theme=light]) .tk-n{color:#f0b46a}}"
      + ":root[data-theme=dark] .tk-k{color:#b8a6ff}:root[data-theme=dark] .tk-s{color:#7dd3a8}:root[data-theme=dark] .tk-c{color:#8b929c}:root[data-theme=dark] .tk-n{color:#f0b46a}";
    document.head.appendChild(st);
  }
  const codeHtml = (block, opts = {}) => {
    if (!block) return "";
    if (!block.lines.length) return '<div class="muted">No observed code in this range.</div>';
    const lang = langOf(opts.path || block.path);
    const rows = block.lines.map(([k, o, n, t]) => `<div class="cl ${k === "+" ? "add" : k === "-" ? "del" : "ctx"}${opts.hl && opts.hl.includes(n) ? " hl" : ""}"><span class="ln">${n ?? o ?? ""}</span><span class="sg">${k === " " ? "" : esc(k)}</span><span class="tx">${hlText(String(t ?? ""), lang)}</span></div>`).join("");
    return `<div class="code">${rows}${block.cut ? `<div class="cl cut"><span class="ln"></span><span class="sg"></span><span class="tx">… ${block.cut} more lines</span></div>` : ""}</div>`;
  };
  /* mermaid: render every [data-mermaid] inside root; source stays visible on failure */
  let mermaidInit = false;
  const mcache = new Map();
  const mermaidReset = () => { mermaidInit = false; mcache.clear(); };   // after a theme change, so diagrams redraw in its colors
  const mermaid = async (root = document) => {
    if (!window.mermaid) return;
    if (!mermaidInit) {
      const css = getComputedStyle(document.documentElement), v = (n, d) => css.getPropertyValue(n).trim() || d;
      window.mermaid.initialize({ startOnLoad: false, securityLevel: "strict", theme: "base", themeVariables: {
        fontFamily: v("--f-body", "sans-serif"), fontSize: "13px", background: v("--surface", "#fff"), primaryColor: v("--surface", "#fff"),
        primaryTextColor: v("--ink", "#111"), primaryBorderColor: v("--line", "#999"), lineColor: v("--muted", "#666"),
        secondaryColor: v("--surface", "#fff"), tertiaryColor: v("--surface", "#fff"), noteBkgColor: v("--hl", "#ffd"), noteTextColor: v("--ink", "#111"),
        actorBkg: v("--surface", "#fff"), actorBorder: v("--line", "#999"), actorTextColor: v("--ink", "#111"), signalColor: v("--muted", "#666"), signalTextColor: v("--ink", "#111"),
        labelBoxBkgColor: v("--surface", "#fff"), labelTextColor: v("--ink", "#111"), loopTextColor: v("--muted", "#666"), edgeLabelBackground: v("--bg", "#fff"), clusterBkg: v("--bg", "#fff"), clusterBorder: v("--line", "#999") } });
      mermaidInit = true;
    }
    const els = [...root.querySelectorAll("[data-mermaid]")];
    for (const [i, el] of els.entries()) {
      const src = el.dataset.mermaid;
      if (mcache.has(src)) { el.innerHTML = mcache.get(src); continue; }
      const id = `m${Date.now()}${i}`;
      try { const { svg } = await window.mermaid.render(id, src); mcache.set(src, svg); el.innerHTML = svg; }
      catch (_) {   // mermaid leaves its "Syntax error" drawing at the end of the page: remove it, show the source instead
        document.querySelectorAll(`#${id}, #d${id}`).forEach((n) => n.remove());
        el.classList.add("mx-bad"); el.innerHTML = `<p class="mx-note">This diagram couldn't be drawn; its source:</p><pre></pre>`; el.querySelector("pre").textContent = src;
      }
    }
    els.forEach((el) => { if (el.querySelector("svg") && !el.querySelector(".mx-open")) {
      el.classList.add("mx-ready"); el.title = "Click to explore";
      el.insertAdjacentHTML("beforeend", `<button class="mx-open" type="button" aria-label="Explore the diagram">⤢ Explore</button>`);
    } });
  };
  /* diagram explorer: the diagram full screen, zoom with the wheel or pinch (around the pointer), drag to pan */
  let mx = null;
  const exploreDiagram = (box) => {
    const svg0 = box.querySelector("svg"); if (!svg0) return;
    const vb = svg0.viewBox && svg0.viewBox.baseVal, w = (vb && vb.width) || svg0.getBoundingClientRect().width, h = (vb && vb.height) || svg0.getBoundingClientRect().height;
    const ov = document.createElement("div"); ov.className = "mx"; ov.setAttribute("role", "dialog"); ov.setAttribute("aria-modal", "true"); ov.setAttribute("aria-label", "Diagram");
    ov.innerHTML = `<div class="mx-bar"><button data-mx="out" aria-label="Zoom out">−</button><span class="mx-pct n">100%</span><button data-mx="in" aria-label="Zoom in">+</button><button data-mx="fit">Fit</button><span class="mx-hint">Scroll to zoom · drag to move</span><button data-mx="close" aria-label="Close">✕</button></div><div class="mx-stage"><div class="mx-c"></div></div>`;
    const stage = ov.querySelector(".mx-stage"), c = ov.querySelector(".mx-c"), svg = svg0.cloneNode(true);
    svg.removeAttribute("style"); svg.setAttribute("width", w); svg.setAttribute("height", h); c.appendChild(svg);
    document.body.appendChild(ov); document.body.style.overflow = "hidden";
    const st = { s: 1, x: 0, y: 0 }, pct = ov.querySelector(".mx-pct");
    const draw = () => { c.style.transform = `translate(${st.x}px,${st.y}px) scale(${st.s})`; pct.textContent = Math.round(st.s * 100) + "%"; };
    const fit = () => { const r = stage.getBoundingClientRect(); st.s = Math.min(4, Math.max(0.1, Math.min((r.width - 40) / w, (r.height - 40) / h))); st.x = (r.width - w * st.s) / 2; st.y = (r.height - h * st.s) / 2; draw(); };
    const zoom = (k, cx, cy) => { const r = stage.getBoundingClientRect(); cx = cx == null ? r.width / 2 : cx; cy = cy == null ? r.height / 2 : cy;
      const s = Math.min(8, Math.max(0.1, st.s * k)); st.x = cx - ((cx - st.x) * s) / st.s; st.y = cy - ((cy - st.y) * s) / st.s; st.s = s; draw(); };
    stage.addEventListener("wheel", (e) => { e.preventDefault(); const r = stage.getBoundingClientRect(); zoom(Math.exp(-e.deltaY * (e.ctrlKey ? 0.01 : 0.002)), e.clientX - r.left, e.clientY - r.top); }, { passive: false });
    let drag = null;
    stage.addEventListener("pointerdown", (e) => { drag = { x: e.clientX - st.x, y: e.clientY - st.y }; stage.setPointerCapture(e.pointerId); stage.classList.add("grab"); });
    stage.addEventListener("pointermove", (e) => { if (drag) { st.x = e.clientX - drag.x; st.y = e.clientY - drag.y; draw(); } });
    stage.addEventListener("pointerup", () => { drag = null; stage.classList.remove("grab"); });
    stage.addEventListener("dblclick", (e) => { const r = stage.getBoundingClientRect(); zoom(2, e.clientX - r.left, e.clientY - r.top); });
    const close = () => { ov.remove(); document.body.style.overflow = ""; mx = null; if (box.querySelector(".mx-open")) box.querySelector(".mx-open").focus(); };
    ov.addEventListener("click", (e) => { const b = e.target.closest("[data-mx]"); if (!b) return; const a = b.dataset.mx;
      if (a === "close") close(); else if (a === "fit") fit(); else zoom(a === "in" ? 1.25 : 0.8); });
    mx = { close, zoom, fit };
    fit(); ov.querySelector('[data-mx="close"]').focus();
  };
  document.addEventListener("click", (e) => { const box = e.target.closest && e.target.closest(".mx-ready"); if (box && !e.target.closest("a")) exploreDiagram(box); });
  document.addEventListener("keydown", (e) => { if (!mx) return;
    if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); mx.close(); }
    else if (e.key === "+" || e.key === "=") mx.zoom(1.25); else if (e.key === "-") mx.zoom(0.8); else if (e.key === "0") mx.fit(); }, true);
  const mermaidBox = (src) => `<div class="mbox" data-mermaid="${esc(src)}"><pre>${esc(src)}</pre></div>`;
  const store = { get(k, d) { try { const v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch (_) { return d; } },
                  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (_) {} if (APPK && APPK.has(k)) appPush(k, v); } };
  /* ---------- host: Agent Session Review server when served, nothing in a snapshot ---------- */
  let host = { mode: "snapshot", styles: [] };
  try { const el = document.getElementById("cockpit-host"); if (el) host = JSON.parse(el.textContent); } catch (_) {}
  const served = host.mode === "serve";
  if (served && host.session) {   // every API call names this page's work package, so a tab never writes into another
    const fetch0 = window.fetch.bind(window);
    window.fetch = (u, o = {}) => fetch0(u, typeof u === "string" && u.startsWith("/api/") ? { ...o, headers: { ...(o.headers || {}), "X-Cockpit-Session": host.session } } : o);
  }
  /* app settings (layout, Page views, theme, saved layouts): kept by the server for every session and port; this browser holds a copy */
  const APPK = served && host.app ? new Set(host.app.keys || []) : null, appQ = {};
  let appT = 0, appWarned = false;
  function appFlush(unload) {   // send what changed; a failed save goes back in the queue and says so once, so it isn't lost quietly
    clearTimeout(appT); const set = { ...appQ }; Object.keys(appQ).forEach((k) => delete appQ[k]); if (!Object.keys(set).length) return;
    const body = JSON.stringify({ set });
    fetch("/api/app-state", { method: "POST", headers: { "Content-Type": "application/json" }, body, keepalive: unload === true && body.length < 60000 })   // keepalive caps a body at 64 KiB
      .then(async (r) => { if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || `the server answered ${r.status}`); appWarned = false; })
      .catch((e) => { Object.keys(set).forEach((k) => { if (!(k in appQ)) appQ[k] = set[k]; });
        if (unload !== true && !appWarned) { appWarned = true; window.dispatchEvent(new CustomEvent("cockpit:app-save-failed", { detail: e.message || "no connection" })); } }); }
  function appPush(k, v) { appQ[k] = v === undefined ? null : v; clearTimeout(appT); appT = setTimeout(appFlush, 300); }
  if (APPK) { const st = host.app.state || {}, fresh = !Object.keys(st).length, up = {};
    APPK.forEach((k) => { if (Object.hasOwn(st, k)) { try { localStorage.setItem(k, JSON.stringify(st[k])); } catch (_) {} }
      else if (fresh) { const v = store.get(k, undefined); if (v !== undefined) up[k] = v; }   // only the very first time: this browser's settings become the shared ones
      else { try { localStorage.removeItem(k); } catch (_) {} } });   // after that, a setting the server doesn't have was removed: the old copy mustn't bring it back
    if (Object.keys(up).length) { Object.assign(appQ, up); appFlush(); }
    window.addEventListener("pagehide", () => appFlush(true)); }
  /* send note events to the session; resolves true when the server took them */
  const inflight = new Set();   // sends not answered yet: Publish waits for them, so its preview has every note
  const send = async (events) => {
    if (!served || !events.length) return false;
    const p = fetch("/api/event", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(events) })
      .then((r) => r.ok, () => false);
    inflight.add(p);
    try { return await p; } finally { inflight.delete(p); }
  };
  const EMOJI = { blocking: "🚫", question: "❓", nit: "🧹", bug: "🐛" };
  /* one note on one line, in Agent Session Review's event format (it publishes notes marked post) */
  const noteEvent = ({ id, ui_id, pr, path, line, side, text, type, label }) => {
    const onLine = path && line && side !== "old";
    return { type: "note", note_id: id, pr, text, emoji: EMOJI[type] || null, post: !host.product, style: host.style, ...(host.product ? {ui_id, note_type:type} : {}),
             path: onLine ? path : null, line: onLine ? line : null,
             target: onLine ? { kind: "line", id: `${path}:${line}`, label: `${path}:${line}` } : { kind: "pr", id: pr, label: label || (path ? `${path}${line ? ":" + line : ""} (before)` : pr) } };
  };
  const undoNote = (id, pr) => ({ type: "note", note_id: id, pr, undo: true });
  const styleCss = `.ck-style{position:relative;display:inline-flex}
.ck-sbtn{display:inline-flex;gap:6px;align-items:center;border:1px solid var(--line);background:transparent;color:var(--muted);border-radius:6px;padding:5px 10px;font:500 13px/1.2 inherit;cursor:pointer;white-space:nowrap;position:relative}
.ck-sbtn:hover,.ck-sbtn[aria-expanded="true"]{background:var(--sunk)}
.ck-sbtn .k{color:var(--muted);font-weight:400}
.ck-sbtn svg{flex:none;color:var(--muted)}
.ck-sbtn .dot{position:absolute;top:-3px;right:-3px;width:7px;height:7px;border-radius:50%;background:var(--line-strong, var(--muted));box-shadow:0 0 0 2px var(--surface)}
.ck-coach{position:absolute;top:calc(100% + 8px);right:0;z-index:70;display:flex;gap:8px;align-items:center;white-space:nowrap;background:var(--surface);color:var(--muted);border:1px solid var(--line);border-radius:6px;padding:6px 8px 6px 12px;font-size:13px;box-shadow:var(--shadow)}
.ck-coach::before{content:"";position:absolute;top:-5px;right:18px;width:10px;height:10px;background:inherit;transform:rotate(45deg)}
.ck-fresh{color:var(--muted);font-size:12.5px;white-space:nowrap}
.ck-fresh code{font:12px var(--f-mono, ui-monospace, monospace)}
.ck-refresh{border:1px solid var(--line);background:var(--surface);color:var(--ink);border-radius:5px;padding:1px 8px;font:500 12.5px/1.5 inherit;cursor:pointer}
.ck-refresh:hover{background:var(--sunk)} .ck-refresh[disabled]{opacity:.6;cursor:progress}
.ck-freshbar{max-width:1200px;margin:6px auto 0;padding:0 16px;text-align:right;box-sizing:border-box}
.ck-ask{text-decoration:underline dotted;cursor:help}
.ck-coach button{border:0;background:none;color:inherit;opacity:.7;cursor:pointer;font-size:15px;line-height:1;padding:0 2px}
.ck-menu{position:absolute;top:calc(100% + 6px);right:0;z-index:80;width:min(460px,calc(100vw - 24px));max-height:min(72vh,calc(100vh - 96px));overflow-y:auto;overscroll-behavior:contain;background:var(--surface);border:1px solid var(--line);border-radius:8px;box-shadow:var(--shadow);padding:6px}
.ck-menu .h{font:600 11px/1.2 inherit;letter-spacing:.08em;text-transform:uppercase;color:var(--faint);padding:8px 10px 6px}
.ck-it{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:2px 10px;width:100%;text-align:left;border:0;background:none;color:var(--ink);text-decoration:none;border-radius:6px;padding:8px 10px;cursor:pointer;font:inherit}
.ck-it:hover,.ck-it:focus-visible{background:var(--sunk)}
.ck-it b{font-weight:600;font-size:14px}
.ck-it span{grid-column:1/-1;color:var(--muted);font-size:13px;line-height:1.4}
.ck-it em{font-style:normal;font-size:12.5px;color:var(--accent);white-space:nowrap}
.ck-it[aria-current="page"] em{color:var(--muted)}
.ck-it.ask{cursor:default}
.ck-it.ask:hover{background:none}
.ck-menu .h.sep{border-top:1px solid var(--line);margin-top:6px;padding-top:12px}
.ck-note{margin:0 10px 4px;color:var(--muted);font-size:12.5px;line-height:1.4}
.ck-create{display:block;margin:8px 10px 6px;padding:7px 12px;border:1px dashed var(--line-strong, var(--line));border-radius:7px;background:none;color:var(--accent-text, var(--accent));font:600 13px/1.2 inherit;cursor:pointer;text-decoration:none}
.ck-create:hover,.ck-create:focus-visible{background:var(--sunk);border-style:solid}
.ck-req{grid-column:1/-1;display:flex;gap:8px;align-items:center;margin-top:6px;background:var(--sunk);border:1px solid var(--line);border-radius:6px;padding:6px 6px 6px 10px}
.ck-req code{flex:1;min-width:0;font:12px/1.4 var(--f-mono,monospace);background:none;padding:0;color:var(--ink);overflow-wrap:anywhere;user-select:all}
.ck-req button{flex:none;border:1px solid var(--line);background:var(--surface);border-radius:6px;padding:3px 8px;cursor:pointer;font:inherit}
.ck-req button em{font-size:12.5px}
.ck-pub{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.ck-pbtn{border:1px solid var(--accent);background:var(--accent);color:var(--bg);border-radius:6px;padding:7px 12px;font:600 13px/1.2 inherit;cursor:pointer}
.ck-pbtn:disabled{opacity:.6;cursor:wait}
.ck-dlg{width:min(720px,calc(100vw - 32px));max-height:calc(100vh - 64px);border:1px solid var(--line);border-radius:10px;background:var(--surface);color:var(--ink);box-shadow:var(--shadow);padding:20px;font-size:14px}
.ck-dlg::backdrop{background:rgba(0,0,0,.45)}
.ck-dlg h2{margin:0 0 6px;font-size:17px;text-transform:none;letter-spacing:0}.ck-dlg h3{margin:16px 0 6px;font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.ck-dlg p{margin:0 0 8px;color:var(--muted)}.ck-dlg pre{white-space:pre-wrap;word-break:break-word;background:var(--sunk);border-radius:6px;padding:10px;margin:0 0 8px;font:12.5px/1.45 ui-monospace,Menlo,monospace;color:var(--ink)}
.ck-dlg ul{padding-left:18px;margin:8px 0}.ck-dlg li{margin:4px 0}.ck-dlg a{color:var(--accent)}
.ck-dlg .ck-row{display:flex;gap:8px;justify-content:flex-end;margin-top:14px;flex-wrap:wrap}
.ck-dlg .ck-row button{border:1px solid var(--line);background:var(--surface);color:var(--ink);border-radius:6px;padding:7px 12px;font:500 13px/1.2 inherit;cursor:pointer}
.ck-dlg .ck-row button.pri{background:var(--accent);border-color:var(--accent);color:var(--bg);font-weight:600}
.ck-dlg .ck-note{background:var(--sunk);border-radius:6px;padding:8px 10px;margin:0 0 8px;color:var(--ink)}
.ck-banner{display:flex;gap:6px 10px;align-items:baseline;flex-wrap:wrap;box-sizing:border-box;margin:10px 16px 0;padding:8px 14px;background:var(--sunk);border:1px solid var(--line);border-radius:8px;font-size:13.5px;color:var(--muted)}
.ck-banner b{color:var(--ink)}.ck-banner .ck-bsub{margin-left:auto}
.ck-bdet{min-width:0}.ck-bdet>summary{cursor:pointer}.ck-bdet>summary:focus-visible{outline:2px solid var(--accent,currentColor);outline-offset:2px;border-radius:4px}.ck-bdet ul{margin:6px 0 2px;padding-left:18px;display:grid;gap:2px}
.mx-ready{position:relative;cursor:zoom-in}
.mx-bad .mx-note{margin:0 0 6px;color:var(--muted);font-size:13px}.mx-bad pre{margin:0;white-space:pre-wrap;font:12px var(--f-mono);color:var(--muted);max-height:220px;overflow:auto}
.mx-open{position:absolute;top:8px;right:8px;border:1px solid var(--line);background:var(--surface);color:var(--muted);border-radius:6px;padding:3px 9px;font:500 12.5px/1.3 inherit;cursor:pointer;opacity:.85}
.mx-ready:hover .mx-open,.mx-open:focus-visible{opacity:1;color:var(--ink)}
.mx{position:fixed;inset:0;z-index:90;display:flex;flex-direction:column;background:var(--bg);padding:env(safe-area-inset-top,0px) 0 env(safe-area-inset-bottom,0px)}
.mx-bar{display:flex;gap:8px;align-items:center;padding:10px 16px;border-bottom:1px solid var(--line);background:var(--surface)}
.mx-bar button{border:1px solid var(--line);background:var(--surface);color:var(--ink);border-radius:6px;min-width:32px;padding:4px 10px;font:500 14px/1.2 inherit;cursor:pointer}
.mx-bar button:hover{background:var(--sunk)}
.mx-bar [data-mx="close"]{margin-left:auto}
.mx-pct{min-width:44px;text-align:center;color:var(--muted);font-size:13px}
.mx-hint{color:var(--faint);font-size:13px;margin-left:8px}
.mx-stage{flex:1;overflow:hidden;position:relative;cursor:grab;touch-action:none;background:var(--surface)}
.mx-stage.grab{cursor:grabbing}
.mx-c{position:absolute;left:0;top:0;transform-origin:0 0}
@media (max-width:600px){.mx-hint{display:none}}
.ck-missing{max-width:68ch;margin:28px auto;padding:16px 20px;border:1px dashed var(--line);border-radius:12px;background:var(--surface)}`;
  (() => { const st = document.createElement("style"); st.textContent = styleCss; document.head.appendChild(st); })();
  /* the style switcher: every way to read this session, one click away. A style opens when it can (served,
     or exported alongside this page); one that needs content or an export gives the ask to copy for Claude. */
  const SEEN = "ck:styles-seen";
  /* your own styles: recipes Focus draws. Saved ones come from the data home (served or exported) and from this browser */
  const RECIPES = "ck:recipes", ACTIVE = "ck:recipe";
  const recipes = () => { const m = new Map(), local = store.get(RECIPES, []);
    (Array.isArray(local) ? local : []).concat(host.recipes || []).forEach((r) => { if (r && r.id && r.name && Array.isArray(r.tabs)) m.set(r.id, r); });
    return [...m.values()].sort((a, b) => a.name.localeCompare(b.name)); };
  const activeRecipe = () => (host.style === "focus" ? recipes().find((r) => r.id === store.get(ACTIVE, null)) || null : null);
  const focusUrl = () => (host.styles.find((s) => s.id === "focus" && s.url && !s.needs) || {}).url || null;
  const cur = () => activeRecipe() || host.styles.find((s) => s.id === host.style) || { name: host.style || "Review" };
  const others = () => host.styles.filter((s) => s.id !== host.style || activeRecipe());
  const itemHtml = (s) => {
    if (s.id === host.style && s.id === "focus" && activeRecipe()) return `<button class="ck-it" role="menuitem" data-ck-recipe="focus"><b>${esc(s.name)}</b><em>Use →</em>${s.what ? `<span>${esc(s.what)}</span>` : ""}</button>`;
    if (s.id === host.style) return `<div class="ck-it" aria-current="page"><b>${esc(s.name)}</b><em>this page</em>${s.what ? `<span>${esc(s.what)}</span>` : ""}</div>`;
    if (s.url && !s.needs) return `<a class="ck-it" role="menuitem" href="${esc(s.url)}"><b>${esc(s.name)}</b><em>Open →</em>${s.what ? `<span>${esc(s.what)}</span>` : ""}</a>`;
    return `<div class="ck-it ask"><b>${esc(s.name)}</b><span>${esc(s.what || "")}${s.needs ? ` ${esc(s.needs)}` : ""}</span>
      <span class="ck-req"><code>${esc(s.ask || "")}</code><button role="menuitem" data-ck-ask="${esc(s.ask || "")}"><em>Copy for Claude</em></button></span></div>`;
  };
  const ownHtml = () => {   // outside Focus these open in Focus
    const act = activeRecipe(), here = host.style === "focus", to = focusUrl();
    const item = (r) => act && act.id === r.id ? `<div class="ck-it" aria-current="page"><b>${esc(r.name)}</b><em>this page</em>${r.about ? `<span>${esc(r.about)}</span>` : ""}</div>`
      : here ? `<button class="ck-it" role="menuitem" data-ck-recipe="${esc(r.id)}"><b>${esc(r.name)}</b><em>Use →</em>${r.about ? `<span>${esc(r.about)}</span>` : ""}</button>`
      : to ? `<a class="ck-it" role="menuitem" href="${esc(to)}#style-${esc(r.id)}"><b>${esc(r.name)}</b><em>Open →</em>${r.about ? `<span>${esc(r.about)}</span>` : ""}</a>` : "";
    const create = here ? `<button class="ck-create" role="menuitem" data-ck="create">＋ Create your style</button>`
      : to ? `<a class="ck-create" role="menuitem" href="${esc(to)}#create">＋ Create your style</a>` : "";
    if (!here && !to) return "";
    return `<div class="h">Your own style</div><p class="ck-note">Describe how you like to review, or arrange the parts yourself. It starts from this review.</p>${create}${recipes().map(item).join("")}`;
  };
  const menuHtml = () => {   // what opens from here, then what Claude Code has to make first
    const now = host.styles.filter((s) => s.id === host.style || (s.url && !s.needs)), later = host.styles.filter((s) => !now.includes(s));
    const own = ownHtml();
    return own + `<div class="h${own ? " sep" : ""}">Review in a different style</div>${now.map(itemHtml).join("")}`
      + (later.length ? `<div class="h sep">Create this review in another style</div><p class="ck-note">Claude Code builds the Agent Session Review for this session in that style. Copy a request and paste it into Claude Code${served ? "" : " (where this review was made)"}.</p>${later.map(itemHtml).join("")}` : "");
  };
  const navHtml = () => {
    if (!others().length) return "";
    const fresh = !store.get(SEEN, false);
    const glyph = `<svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"><rect x="1" y="1" width="5" height="5" rx="1" fill="currentColor"/><rect x="8" y="1" width="5" height="5" rx="1" fill="none" stroke="currentColor" stroke-width="1.3"/><rect x="1" y="8" width="5" height="5" rx="1" fill="none" stroke="currentColor" stroke-width="1.3"/><rect x="8" y="8" width="5" height="5" rx="1" fill="none" stroke="currentColor" stroke-width="1.3"/></svg>`;
    const n = others().length;
    return `<div class="ck-style"><button class="ck-sbtn" data-ck="menu" aria-haspopup="menu" aria-expanded="false" title="${n} other way${n === 1 ? "" : "s"} to read this review">${glyph}<span class="k">Style</span> ${esc(cur().name)} <span aria-hidden="true">▾</span>${fresh ? `<i class="dot"></i>` : ""}</button>
      ${""/* no pop-up hint: it covered the header's freshness line; the dot is enough */}
      <div class="ck-menu" role="menu" aria-label="Review styles" hidden>${menuHtml()}</div></div>`;
  };
  const seen = () => { store.set(SEEN, true); document.querySelectorAll(".ck-coach, .ck-sbtn .dot").forEach((e) => e.remove()); };
  const closeMenu = () => document.querySelectorAll(".ck-menu").forEach((m) => { m.hidden = true; const b = m.parentNode.querySelector(".ck-sbtn"); if (b) b.setAttribute("aria-expanded", "false"); });
  document.addEventListener("click", (e) => {
    const t = e.target.closest && e.target.closest("[data-ck], [data-ck-ask], [data-ck-recipe], .ck-menu");
    if (!t) return closeMenu();
    if (t.dataset.ck === "seen") { e.stopPropagation(); return seen(); }
    if (t.dataset.ck === "refresh") { e.stopPropagation(); return refresh(t); }
    if (t.dataset.ck === "reload") return location.reload();
    if (t.dataset.ck === "create") { e.stopPropagation(); closeMenu(); return window.dispatchEvent(new CustomEvent("ck:create")); }
    if (t.dataset.ckRecipe) { e.stopPropagation(); closeMenu(); return window.dispatchEvent(new CustomEvent("ck:recipe", { detail: t.dataset.ckRecipe })); }
    if (t.dataset.ck === "menu") {
      e.stopPropagation(); const m = t.parentNode.querySelector(".ck-menu"), open = m.hidden;
      closeMenu(); seen(); m.hidden = !open; t.setAttribute("aria-expanded", String(open));
      // open toward the side with room: a button on the left half (a phone header wraps it there) opens rightward
      const r = t.getBoundingClientRect(), left = r.left + r.width / 2 < innerWidth / 2;
      m.style.left = left ? "0" : ""; m.style.right = left ? "auto" : "";
      if (open) { const f = m.querySelector("a, button"); if (f) f.focus(); }
      return;
    }
    if (t.dataset.ckAsk !== undefined) {
      e.stopPropagation(); const text = t.dataset.ckAsk, em = t.querySelector("em");
      const done = (msg) => { if (em) { em.textContent = msg; setTimeout(() => (em.textContent = "Copy for Claude"), 2600); } };
      try { navigator.clipboard.writeText(text).then(() => done("Copied, paste it to Claude"), () => done("Select it to copy")); } catch (_) { done("Select it to copy"); }
    }
  }, true);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && document.querySelector(".ck-menu:not([hidden])")) { closeMenu(); const b = document.querySelector(".ck-sbtn"); if (b) b.focus(); } });
  setTimeout(() => document.querySelectorAll(".ck-coach").forEach((c) => c.remove()), 12000);   // a hint, not a nag: it fades on its own and shows again next visit until used
  /* publish to GitHub from any style, with Agent Session Review's preview first: notes on a finding with its own thread
     reply there (and can resolve it), the rest form one COMMENT review per PR. A style whose notes wait to be
     sent sets KIT.beforePublish (resolving false stops the publish). */
  const publishHtml = (keys) => served && !host.product ? `<div class="ck-pub">${keys.map((k) => `<button class="ck-pbtn" data-ck-pub="${esc(k)}">Publish ${esc(k.split("/").pop())} to GitHub</button>`).join("")}</div>` : "";
  const api = async (body) => {
    if (host.product) throw new Error(host.notice || "Local review and export only");
    const r = await fetch("/api/publish", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const j = await r.json();
    if (!r.ok && !j.results) throw new Error(j.error || `HTTP ${r.status}`);
    return j;
  };
  const dialog = (html) => {
    let d = document.querySelector("dialog.ck-dlg");
    if (!d) { d = document.createElement("dialog"); d.className = "ck-dlg"; document.body.appendChild(d); }
    d.innerHTML = html;
    if (!d.open) { try { d.showModal(); } catch (_) { d.setAttribute("open", ""); } }
    return d;
  };
  const closeDialog = () => { const d = document.querySelector("dialog.ck-dlg"); if (d) { try { d.close(); } catch (_) {} d.remove(); } };
  const replyPre = (r) => r.resolve_only ? `<pre>${esc(r.title)}\n→ resolves the thread (retry: the reply is already on GitHub)</pre>`
    : `<pre>${esc(r.title)}${r.resolve ? (r.resolved ? "\n(already resolved on GitHub)" : r.can_resolve ? "\n→ resolves the thread" : "\n(you can't resolve threads on this repo: reply only)") : ""}\n\n${esc(r.body)}</pre>`;
  const KIND = { review: "Review", reply: "Reply", resolve: "Resolve" };
  const previewHtml = (pr, j) => {
    const p = j.payload, rs = j.replies || [];
    const resolving = rs.filter((r) => r.resolve && !r.resolved && r.can_resolve).length;
    return `<h2>Publish to GitHub: ${esc(pr)}</h2><p>${j.count} note${j.count === 1 ? "" : "s"}: ${[rs.length ? `${rs.length} repl${rs.length === 1 ? "y" : "ies"} in existing threads${resolving ? `, resolving ${resolving}` : ""}` : "", p ? "one COMMENT review (approve or request changes on GitHub)" : ""].filter(Boolean).join("; ")}. Nothing posts until you press Publish.</p>
      ${j.note ? `<div class="ck-note">${esc(j.note)}</div>` : ""}
      ${rs.length ? `<h3>Replies in existing threads (${rs.length})</h3>${rs.map(replyPre).join("")}` : ""}
      ${p ? `<h3>Review (${p.comments.length} inline, the rest in the body)</h3><pre>${esc(p.body)}</pre>${p.comments.map((c) => `<pre>${esc(c.path)}:${c.line}\n${esc(c.body)}</pre>`).join("")}` : ""}
      <div class="ck-row"><button data-ck-close>Cancel</button><button class="pri" data-ck-go="${esc(pr)}" data-ck-expect="${esc(JSON.stringify(j.expect || []))}">Publish to GitHub</button></div>`;
  };
  const resultHtml = (j) => `<h2>${j.ok ? "Published" : (j.results || []).some((r) => r.ok) ? "Partly published" : "Not published"}</h2>${j.ok ? "" : `<p>${esc(j.error || "")}</p>`}
    <ul>${(j.results || []).map((r) => `<li>${r.ok ? "✓" : "✕"} ${KIND[r.kind] || "Item"}${r.kind === "review" ? "" : ": " + esc(r.title || "")}${r.ok && r.url ? ` · <a href="${esc(r.url)}" target="_blank" rel="noopener">open ↗</a>` : ""}${r.resolve ? ` · ${esc(r.resolve)}` : ""}${r.error ? `<br><span style="color:var(--muted)">${esc(r.error)}</span>` : ""}</li>`).join("")}</ul>
    <div class="ck-row"><button class="pri" data-ck-close>Close</button></div>`;
  document.addEventListener("click", async (e) => {
    const t = e.target.closest && e.target.closest("[data-ck-pub],[data-ck-go],[data-ck-close]");
    if (!t) return;
    if (t.hasAttribute("data-ck-close")) return closeDialog();
    const pr = t.getAttribute("data-ck-pub") || t.getAttribute("data-ck-go"), real = t.hasAttribute("data-ck-go");
    if (host.product) return;
    t.disabled = true;
    try {
      if (!real && typeof KIT.beforePublish === "function" && (await KIT.beforePublish(pr)) === false) return;
      if (!real) await Promise.all([...inflight]);   // notes this page is still sending belong in the preview
      let expect;
      try { expect = real ? JSON.parse(t.getAttribute("data-ck-expect") || "null") : undefined; } catch (_) { expect = null; }
      const j = await api({ pr, dry_run: !real, ...(real && expect ? { expect } : {}) });
      const msg = (h, m) => `<h2>${esc(h)}</h2><p>${esc(m || "")}</p><div class="ck-row"><button class="pri" data-ck-close>Close</button></div>`;
      if (!real) dialog(j.ok ? previewHtml(pr, j) : msg("Nothing to publish", j.error));
      else if (!j.ok && !(j.results || []).length) dialog(msg(j.changed ? "Notes changed" : "Couldn't publish", j.error));
      else dialog(resultHtml(j));
    } catch (err) {
      dialog(`<h2>Couldn't publish</h2><p>${esc(err.message)}</p><div class="ck-row"><button class="pri" data-ck-close>Close</button></div>`);
    } finally { t.disabled = false; }
  });
  /* which commits this review read and when; served, a Refresh button re-collects it (notes, marks and the story stay) */
  const freshHtml = (c) => {
    const at = c && c.reviewed_at ? new Date(c.reviewed_at) : null;
    const when = at && !isNaN(at) ? at.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "";
    const shas = (c && c.prs || []).map((p) => `${(c.prs.length > 1 ? "#" + p.number + " " : "")}${String(p.head_sha || "").slice(0, 7)}`).filter((x) => x.trim());
    const act = c && c.demo ? `<span class="ck-ask" title="The demo review is fixed; there is nothing to re-read">the demo</span>`
      : served ? `<button class="ck-refresh" data-ck="refresh" title="Re-read the PRs from GitHub; your notes and marks stay">Refresh</button>`
      : `<span class="ck-ask" title="Ask Claude Code: /review-prs refresh session ${esc((c && c.session) || "")}">a snapshot</span>`;
    const at1 = shas.length === 1 ? ` at <code>${esc(shas[0])}</code>` : "";
    return `<span class="ck-fresh" title="${esc(shas.length > 1 ? "Reviewed at " + shas.join(", ") : "")}">reviewed${when ? ` ${esc(when)}` : ""}${at1} · ${act}</span>`;
  };
  const refresh = async (btn) => {
    const icon = btn.classList.contains("ck-ricon");   // an icon button spins instead of changing its text
    btn.disabled = true; if (icon) btn.classList.add("busy"); else btn.textContent = "Refreshing…";
    try {
      const r = await (await fetch("/api/refresh", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" })).json();
      if (r.error) throw new Error(r.error);
      for (let i = 0; i < 200; i++) {   // a re-collect reads every PR from GitHub: seconds to a few minutes
        await new Promise((ok) => setTimeout(ok, 3000));
        const s = await (await fetch("/api/refresh")).json();
        if (s.state === "done" && !(s.warnings || []).length) return location.reload();
        if (s.state === "done") {   // refreshed, but the review no longer fits the new diff everywhere: say so before reloading
          const n = s.warnings.length;
          return dialog(`<h2>Refreshed, with ${n} warning${n === 1 ? "" : "s"}</h2><p>The new commits don't match parts of the review. Ask Claude Code to fix them: <code>/review-prs refresh session ${esc(s.session || "")}</code></p><ul>${s.warnings.map((w) => `<li>${esc(w)}</li>`).join("")}</ul><div class="ck-row"><button class="pri" data-ck="reload">Reload</button></div>`);
        }
        if (s.state === "error") throw new Error(s.error || "refresh failed");
      }
      throw new Error("still running; reload later");
    } catch (err) { btn.disabled = false; if (icon) btn.classList.remove("busy"); else btn.textContent = "Refresh"; btn.title = `Couldn't refresh: ${err.message}`; }
  };
  /* the freshness line, for a page whose header doesn't place it itself */
  const freshBar = (after, c) => {
    if (!after || document.querySelector(".ck-fresh")) return;
    const d = document.createElement("div"); d.className = "ck-freshbar"; d.innerHTML = freshHtml(c);
    after.insertAdjacentElement("afterend", d);
  };
  /* "PR moved" banner from the server's live check, above the given element */
  const liveBanner = async (before) => {
    if (!served || !before) return;
    try {
      const j = await (await fetch("/api/live")).json();
      // news since this snapshot first, then merge blockers. "Blocked" while a review is still required is
      // every PR under review, so it only counts once the PR is approved (then checks or rules block it).
      const items = [];
      for (const [k, v] of Object.entries(j.prs || {})) {
        if (!v || v.error) continue;
        const name = `#${k.split("#").pop()}`, news = [], block = [];
        const f = {   // what happened, as flags: the summary counts these, never the display text
          commits: !!v.moved, approved: (v.approved_by || []).length > 0, comments: (v.new_comments || 0) > 0,
          closed: !!(v.state && v.state !== "OPEN"), conflicts: v.merge_state === "DIRTY", behind: v.merge_state === "BEHIND",
          blocked: v.merge_state === "BLOCKED" && v.review_decision !== "REVIEW_REQUIRED" && v.review_decision !== "CHANGES_REQUESTED" };
        if (f.commits) news.push(v.new_commits > 0 ? `${v.new_commits} new commit${v.new_commits === 1 ? "" : "s"}` : "new commits");
        if (f.approved) news.push(`approved by ${v.approved_by.join(", ")}`);
        if (f.comments) news.push(`${v.new_comments} new comment${v.new_comments === 1 ? "" : "s"}`);
        if (f.closed) news.push(v.state.toLowerCase());
        if (f.conflicts) block.push("merge conflicts");
        if (f.behind) block.push("behind its base");
        if (f.blocked) block.push("blocked by checks or rules");
        if (news.length || block.length) items.push({ name, k, f, news, text: [...news, ...block].join(", ") });
      }
      if (!items.length) return;
      items.sort((a, b) => b.news.length - a.news.length);
      const div = document.createElement("div"); div.className = "ck-banner"; div.setAttribute("role", "status");
      const hint = items.some((x) => x.news.length) && !document.querySelector(".ck-fresh .ck-refresh")   // one Refresh per page
        ? ` <button class="ck-refresh" data-ck="refresh" title="Re-read the PRs from GitHub; your notes and marks stay">Refresh</button>` : "";
      const line = (x) => `<b>${esc(x.name)}</b> ${esc(x.text)}`;
      if (items.length <= (innerWidth < 700 ? 1 : 2)) {
        div.innerHTML = items.map((x) => `<span title="${esc(x.k)}">${line(x)}</span>`).join(" · ") + hint;
      } else {   // many PRs: one line that counts what happened; the details open from it (click, tap or keyboard)
        const n = (key) => items.filter((x) => x.f[key]).length;
        const count = (pairs) => pairs.map(([key, t]) => [n(key), t]).filter(([c]) => c).map(([c, t]) => `${c} ${t}`).join(", ");
        const moved = items.filter((x) => x.news.length).length;
        const news = count([["commits", "with new commits"], ["approved", "approved"], ["comments", "with new comments"], ["closed", "closed or merged"]]);
        const blocks = count([["conflicts", "with merge conflicts"], ["behind", "behind base"], ["blocked", "blocked by checks"]]);
        const head = [moved && `<b>${moved} PR${moved === 1 ? "" : "s"}</b> changed since this review: ${esc(news)}`,
                      blocks && `${moved ? "" : `<b>${items.length} PRs</b> `}can't merge yet: ${esc(blocks)}`].filter(Boolean).join(" · ");
        div.innerHTML = `<details class="ck-bdet"><summary>${head}</summary><ul>${items.map((x) => `<li>${line(x)}</li>`).join("")}</ul></details>` + hint;
      }
      before.parentNode.insertBefore(div, before.nextSibling);
      // sit in the page's own column, not edge to edge: the widest centered block inside the header whose
      // content is narrower than the header's own content; else the header's own padding. Measured against
      // where the banner itself starts, so body padding or negative margins on the header don't shift it.
      const box = (el) => {
        const r = el.getBoundingClientRect(), cs = getComputedStyle(el);
        const l = r.left + parseFloat(cs.paddingLeft || 0), w = r.width - parseFloat(cs.paddingLeft || 0) - parseFloat(cs.paddingRight || 0);
        return { left: l, width: w, right: l + w };
      };
      const align = () => {
        div.style.marginLeft = "0px"; div.style.marginRight = "0px"; div.style.width = "";
        const start = div.getBoundingClientRect().left, host = box(before);
        let best = null;
        for (const c of before.querySelectorAll(":scope > *, :scope > * > *")) {
          const r = box(c);
          const centered = Math.abs((r.left - host.left) - (host.right - r.right)) < 48;   // a page column, not a side block
          if (centered && r.width > 240 && r.width < host.width - 1 && (!best || r.width > best.width)) best = r;
        }
        const col = best || host;
        div.style.marginLeft = `${Math.round(col.left - start)}px`;
        div.style.width = `${Math.round(col.width)}px`;
      };
      align(); addEventListener("resize", align);
    } catch (_) {}
  };
  const settle = () => Promise.all([...inflight]);   // wait for the events still on their way (Make memories reads them)
  return { settle, esc, md, cases, caseIds, pick, short, repoShort, base, TIERS, TIER_NAME, minutes, totals, allFindings, openFindings, localTag, localDone, isConvention, freshBar, codeHtml, mermaid, mermaidBox, mermaidReset, store, sevRank,
           host, served, recipes, RECIPES, ACTIVE, send, noteEvent, undoNote, navHtml, liveBanner, publishHtml, freshHtml };
})();
