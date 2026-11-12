/* Reader (cockpit/styles.py splices this file into package.js at its READER marker comment, inside package.js's scope): every widget on every page, expanded, in one full-page view — Scroll, with one widget in focus, or Stepper, the full-screen dialog — and Share › Export, its layout on paper */
const RDKEY = "cockpit:reader-mode";
const RDICON = { scroll: '<path d="M7 2h10"/><path d="M5 6h14"/><rect width="18" height="12" x="3" y="10" rx="2"/>', step: '<path d="M2 7v10"/><path d="M6 5v14"/><rect width="12" height="18" x="10" y="3" rx="2"/>' };   // a stack read down, a stack stepped across
const rdSeg = () => `<span class="pviews rd-seg" role="group" aria-label="Reader mode">${[["scroll", "Scroll"], ["step", "Steps"]].map(([k, t]) => `<button type="button" class="pv" data-rdmode="${k}" aria-pressed="${READER === k}">${svg(RDICON[k], "rd-mi")}${t}</button>`).join("")}</span>`;
const RDZKEY = "cockpit:reader-zoom", RDZ = [0.85, 1, 1.15, 1.3, 1.5];   // Reader's text sizes; the setting is a place in this list
let RDZI = Math.max(0, Math.min(RDZ.length - 1, +store.get(RDZKEY, 1) || 0));
const rdZoom = (i) => { RDZI = Math.max(0, Math.min(RDZ.length - 1, i)); store.set(RDZKEY, RDZI); document.documentElement.style.setProperty("--rdz", RDZ[RDZI]);
  document.querySelectorAll('[data-rdfs="-1"]').forEach((b) => (b.disabled = RDZI === 0)); document.querySelectorAll('[data-rdfs="1"]').forEach((b) => (b.disabled = RDZI === RDZ.length - 1)); };
document.documentElement.style.setProperty("--rdz", RDZ[RDZI]);
const RDPGKEY = "cockpit:reader-pages"; let RDPG = store.get(RDPGKEY, true) !== false;   // Scroll: a dashed boundary and the page's name between pages
const rdPgBtn = () => `<button type="button" class="wz-ic rd-pgt" data-rdpg aria-pressed="${RDPG}" aria-label="Page boundaries" title="${RDPG ? "Hide" : "Show"} page boundaries">${svg('<rect x="4" y="3" width="16" height="6" rx="1.5"/><path d="M3 12h2M8 12h3M14 12h3M19 12h2"/><rect x="4" y="15" width="16" height="6" rx="1.5"/>')}</button>`;
const rdFs = () => `<span class="rd-fs" role="group" aria-label="Text size"><button type="button" class="wz-ic" data-rdfs="-1" aria-label="Smaller text" title="Smaller text"${RDZI === 0 ? " disabled" : ""}><span class="rd-a">A</span></button><button type="button" class="wz-ic" data-rdfs="1" aria-label="Larger text" title="Larger text"${RDZI === RDZ.length - 1 ? " disabled" : ""}><span class="rd-a rd-al">A</span></button></span>`;
const RDMAG = '<svg class="rd-mag" viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>';
const GLASSES_T = GLASSES.replace('class="g24"', 'class="sico"');   // in the dialog's tile, drawn like every widget icon
function rdHead(step) {   // one header for both modes: Reader on the left, the mode switch and text size in the middle, Find and close on the right
  return `<div class="lmod-h wfm-h rd-hd"><span class="rd-hl"><span class="stile">${GLASSES_T}</span><b>Reader</b></span><span class="rd-hc">${rdSeg()}${rdFs()}${step ? "" : rdPgBtn()}</span><span class="rd-hr">`
    + `<span class="rd-find"><button type="button" class="wz-ic rd-fb" data-rdfind aria-haspopup="listbox" aria-expanded="false" aria-label="Find a widget" title="Find a widget">${RDMAG}</button><div class="rd-pop" hidden><div class="rd-ps">${RDMAG}<input type="search" class="rd-q" placeholder="Find a widget" aria-label="Find a widget" autocomplete="off" role="combobox" aria-expanded="true" aria-controls="rd-res"></div><div class="rd-res" id="rd-res" role="listbox"></div></div></span>`
    + `<button type="button" class="wz-ic" ${step ? "data-wfm-close" : "data-rdclose"} aria-label="Close Reader" title="Close (Esc)"><svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg></button></span></div>`;
}
function rdFoot(step) {   // a narrow footer, centred: first, previous, where you are, next, last
  const seq = wseq(), done = step && WFULL === WDONE, at = step ? (done ? seq.length : wpos(seq)) : RDAT, a = step ? "data-wfstep" : "data-rdstep";
  return `<div class="rd-ft"><span class="wfm-nav"><button type="button" class="wz-ic" data-rdend="first" aria-label="First widget" title="First widget"${at > 0 ? "" : " disabled"}>${svg('<path d="m11 17-5-5 5-5"/><path d="m18 17-5-5 5-5"/>')}</button><button type="button" class="wz-ic" ${a}="-1" aria-label="Previous widget" title="Previous widget (←)"${at > 0 ? "" : " disabled"}>${svg('<path d="m15 18-6-6 6-6"/>')}</button><span class="wfm-n" id="rd-n">${done ? "Done" : `${at + 1} of ${seq.length}`}</span><button type="button" class="wz-ic" ${a}="1" aria-label="Next widget" title="Next widget (→)"${(step ? done : at >= seq.length - 1) ? " disabled" : ""}>${svg('<path d="m9 18 6-6-6-6"/>')}</button><button type="button" class="wz-ic" data-rdend="last" aria-label="Last widget" title="Last widget"${at >= seq.length - 1 || done ? " disabled" : ""}>${svg('<path d="m6 17 5-5-5-5"/><path d="m13 17 5-5-5-5"/>')}</button></span></div>`;
}
const rdTitle = (w, pid) => { const B = BLOCKS[w] || {}; return `<div class="ssum rd-ht"><span class="stile">${sico(w)}</span><h2>${esc(wname(w, rdPage(pid)))}</h2>${B.sub ? `<span class="ssub">${B.sub()}</span>` : ""}</div>`; };   // Stepper: the widget's title, above its content
const rdPage = (id) => LAYOUT.pages.find((p) => p.id === id) || {};
const rdWidget = ([w, pid], i, extra = "") => { const B = BLOCKS[w], pg = rdPage(pid);   // a widget as Reader and the export show it: its title bar, then all of it
  return `<section class="rd-w" data-rdi="${i}"><div class="ssum rd-h"${extra}><span class="stile">${sico(w)}</span><h2>${esc(wname(w, pg))}</h2>${B.sub ? `<span class="ssub">${B.sub()}</span>` : ""}</div><div class="sbody">${widgetHtml(w)}</div></section>`; };
const rdSecs = () => { let s = ""; const m = {}; navItems().forEach((x) => { if (x.widgets) m[x.id] = s; else s = x.label || ""; }); return m; };   // each page's section: the divider above it in the nav
const rdBody = (seq, extra) => { const ps = [...new Set(seq.map((x) => x[1]))], sec = rdSecs();   // each page opens with a strip: its icon, section › name, and where it sits
  return seq.map((x, i) => { if (i && seq[i - 1][1] === x[1]) return rdWidget(x, i, extra(i)); const pg = rdPage(x[1]), s = sec[x[1]];
    return `<div class="rd-pg"><span class="stile">${sico(pg.icon)}</span><span class="rd-pgc">${s ? `<span>${esc(s)}</span><i aria-hidden="true">›</i>` : ""}<b>${esc(pg.label || "")}</b></span><span class="rd-pgn">Page ${ps.indexOf(x[1]) + 1} of ${ps.length}</span></div>` + rdWidget(x, i, extra(i)); }).join(""); };
const rdAfter = (root, seq) => { const seen = {};   // each widget's own setup, once: a widget with one live instance (the System map) shows on its first page only
  root.querySelectorAll(".rd-w").forEach((el) => { const [w, pid] = seq[+el.dataset.rdi], B = BLOCKS[w]; if (!B || !B.after) return;
    if (seen[w]) { el.querySelector(".sbody").innerHTML = `<p class="wempty">This widget is shown earlier, on ${esc(seen[w])}.</p>`; return; }
    seen[w] = rdPage(pid).label || "an earlier page"; B.after(el); });
  return rdMermaid(root); };
function rdMermaid(root) {   // diagrams in Reader and the PDF: the page's loader only draws the page panel
  if (!root.querySelector("[data-mermaid]")) return Promise.resolve();
  if (window.mermaid) return Promise.resolve(KIT.mermaid(root)).catch(() => {});
  loadMermaid(); return new Promise((done) => { let n = 0; const t = setInterval(() => { if (window.mermaid || ++n > 50) { clearInterval(t); done(window.mermaid ? Promise.resolve(KIT.mermaid(root)).catch(() => {}) : null); } }, 100); });
}
function rdOpen(mode) {   // from the header: start at this page's first widget
  const seq = wseq(); if (!seq.length) return toast("This review has no widgets to read yet");
  const i = seq.findIndex(([, p]) => p === S.tab); RDAT = i >= 0 ? i : 0; rdMode(mode || store.get(RDKEY, "scroll"));
}
function rdMode(mode) {   // switch between Scroll and Stepper on the same widget
  const seq = wseq(); store.set(RDKEY, mode);
  if (mode === "step") { const x = seq[RDAT] || seq[0]; rdClose(); READER = "step"; WFULL = x[0]; WFPAGE = x[1]; return wfullDraw(); }
  if (READER === "step") { RDAT = WFULL === WDONE ? seq.length - 1 : Math.max(0, wpos(seq)); WFULL = null; wfullDraw(); }
  READER = "scroll"; rdDraw(); rdFocus(RDAT, "instant");
}
function rdClose() { const m = document.getElementById("rdm"); READER = READER === "scroll" ? null : READER; if (m) { m.remove(); if (BLOCKS.system) BLOCKS.system.after(); } }
function rdDraw() {   // Scroll: every widget, one after another; it redraws with the page and keeps its place
  const seq = wseq(); let m = document.getElementById("rdm");
  if (READER !== "scroll" || !seq.length) return rdClose();
  const fresh = !m, top = m ? m.querySelector(".rd-b").scrollTop : 0, oq = m && m.querySelector(".rd-q"), find = oq && !oq.closest(".rd-pop").hidden && { v: oq.value, focus: document.activeElement === oq, at: oq.selectionStart };   // a search in progress survives the redraw
  if (!m) { m = document.createElement("div"); m.id = "rdm"; m.className = "lmod"; document.body.appendChild(m); }
  m.innerHTML = `<div class="lmod-c wfm-c" role="dialog" aria-modal="true" aria-label="Reader">${rdHead(false)}
    <div class="rd-b${RDPG ? "" : " rd-nopg"}">${rdBody(seq, (i) => ` data-rdfocus="${i}" role="button" tabindex="0" title="Focus this widget"`)}</div>${rdFoot(false)}</div>`;
  rdAfter(m, seq); m.querySelector(".rd-b").scrollTop = top;
  if (find) { rdFindOpen(m, find.v); const q = m.querySelector(".rd-q"); if (find.focus) q.setSelectionRange(find.at, find.at); else q.blur(); }   // an open Find survives the redraw
  rdFocus(RDAT, false); if (fresh) m.querySelector("[data-rdclose]").focus();
}
function rdFocus(i, scroll = true) {   // one widget in focus: marked, counted in the header, and brought to the top
  const m = document.getElementById("rdm"), n = wseq().length; if (!m) return; RDAT = Math.max(0, Math.min(n - 1, i));
  m.querySelectorAll(".rd-w").forEach((el) => el.classList.toggle("on", +el.dataset.rdi === RDAT));
  m.querySelector("#rd-n").textContent = `${RDAT + 1} of ${n}`;
  m.querySelector('[data-rdstep="-1"]').disabled = m.querySelector('[data-rdend="first"]').disabled = RDAT === 0; m.querySelector('[data-rdstep="1"]').disabled = m.querySelector('[data-rdend="last"]').disabled = RDAT === n - 1;
  if (!scroll) return;
  const b = m.querySelector(".rd-b"), el = m.querySelector(`.rd-w[data-rdi="${RDAT}"]`), head = el.previousElementSibling && el.previousElementSibling.matches(".rd-pg") && RDPG ? el.previousElementSibling : el;
  b.scrollTo({ top: head.getBoundingClientRect().top - b.getBoundingClientRect().top + b.scrollTop - 16, behavior: scroll === "instant" ? "instant" : "smooth" });   // the focus moves only by a title click or the arrows, never by scrolling
}
document.addEventListener("click", (e) => {
  const t = e.target.closest ? e.target : null; if (!t) return;
  if (t.closest("[data-reader]")) { e.preventDefault(); return rdOpen(); }
  const end = t.closest("[data-rdend]"); if (end) { e.preventDefault(); e.stopPropagation(); const n = wseq().length, to = end.dataset.rdend === "first" ? 0 : n - 1;   // the first or the last widget, in either mode
    if (READER === "scroll") return rdFocus(to); const at = WFULL === WDONE ? n : wpos(wseq()); return to !== at && wfStep(to - at); }
  const fs = t.closest("[data-rdfs]"); if (fs) { e.preventDefault(); e.stopPropagation(); rdZoom(RDZI + +fs.dataset.rdfs); return READER === "scroll" && rdFocus(RDAT, "instant"); }   // text size, in either mode
  if (t.closest("[data-rdpg]")) { e.preventDefault(); RDPG = !RDPG; store.set(RDPGKEY, RDPG); const b = document.querySelector("#rdm .rd-b"), g = t.closest("[data-rdpg]");   // page boundaries on or off
    if (b) b.classList.toggle("rd-nopg", !RDPG); g.setAttribute("aria-pressed", String(RDPG)); g.title = `${RDPG ? "Hide" : "Show"} page boundaries`; return rdFocus(RDAT, "instant"); }
  const md = t.closest("[data-rdmode]"); if (md) { e.preventDefault(); e.stopPropagation(); return md.dataset.rdmode !== READER && rdMode(md.dataset.rdmode); }
  if (READER !== "scroll") return;
  const st = t.closest("[data-rdstep]"); if (st) { e.preventDefault(); return rdFocus(RDAT + +st.dataset.rdstep); }
  const f = t.closest("[data-rdfocus]"); if (f && !t.closest("button, a, input, select, textarea, summary")) return rdFocus(+f.dataset.rdfocus);
  if (t.closest("[data-rdclose]")) { e.preventDefault(); rdClose(); }
}, true);
document.addEventListener("keydown", (e) => { if (READER !== "scroll" || WFULL || LD || (e.target.matches && e.target.matches(".rd-q"))) return;   // Find keeps its own keys
  if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); return rdClose(); }
  const f = e.target.closest && e.target.closest("[data-rdfocus]"); if (f && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); return rdFocus(+f.dataset.rdfocus); }
  if (!/^Arrow(Left|Right)$/.test(e.key) || (e.target.closest && e.target.closest("input, textarea, select, [contenteditable], [role=tab], [role=tablist], [role=radiogroup], .bv, .wtab, .cm"))) return;   // ← → move the focus; controls keep their own arrows
  e.preventDefault(); e.stopPropagation(); rdFocus(RDAT + (e.key === "ArrowRight" ? 1 : -1)); }, true);
function rdExport() {   // Share › Export: Reader's layout on paper, every widget and fold open, in the light theme; the print dialog saves it as a PDF
  const seq = wseq(); if (!seq.length) return toast("This review has no widgets to export yet");
  const R = document.documentElement, was = R.dataset.theme, old = document.getElementById("rdp"); if (old) old.remove();
  const el = document.createElement("div"), title = document.title.split(" · ")[0], day = new Date().toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" });
  el.id = "rdp"; el.className = "rdp";
  el.innerHTML = `<header class="rdp-cover"><p class="rdp-eb">Work package review</p><h1>${esc(title)}</h1><p class="muted">${pl(C.prs.length, "pull request")} · exported ${esc(day)}</p><ul>${C.prs.map((p) => `<li><b>${esc(p.key)}</b> ${esc(strip(p.title || ""))}</li>`).join("")}</ul></header>${rdBody(seq, () => "")}`;
  document.body.appendChild(el); R.dataset.theme = "light"; document.body.classList.add("rd-printing"); KIT.mermaidReset();   // diagrams redraw in the light colours
  el.querySelectorAll("details").forEach((d) => (d.open = true));
  el.querySelectorAll("textarea").forEach((x) => { const d = document.createElement("div"); d.className = "rdp-ta"; d.textContent = x.value; x.replaceWith(d); });   // typed notes as text, not editable fields
  const done = () => { el.remove(); document.body.classList.remove("rd-printing"); if (was) R.dataset.theme = was; else delete R.dataset.theme; if (BLOCKS.system) BLOCKS.system.after();
    KIT.mermaidReset(); if (window.mermaid) KIT.mermaid($("#panel")); };   // and back in the page's own theme
  addEventListener("afterprint", done, { once: true }); rdAfter(el, seq).then(() => setTimeout(() => print(), 120));   // after the widgets' setup and diagrams
}
/* Find: the glass opens every widget, page by page, with a search on top: scroll and pick, or type to narrow by name, page, what it shows and (in Scroll) its text */
function rdFind(q) {
  const words = q.toLowerCase().split(/\s+/).filter(Boolean);
  return wseq().map(([w, pid], i) => { const pg = rdPage(pid), name = wname(w, pg);
    if (!words.length) return { i, w, name, page: pg.label || "", snip: "", score: 1 };
    const what = (WIDGETS[w] || [])[1] || "", el = document.querySelector(`#rdm .rd-w[data-rdi="${i}"] .sbody`), text = el ? el.textContent.replace(/\s+/g, " ") : "";
    const hay = (where) => words.every((x) => where.toLowerCase().includes(x)), score = hay(name) ? 3 : hay(`${name} ${pg.label || ""}`) ? 2 : hay(`${name} ${pg.label || ""} ${what}`) ? 1 : hay(text) ? 0.5 : 0;
    let snip = ""; if (score === 0.5) { const k = text.toLowerCase().indexOf(words[0]); snip = (k > 40 ? "…" : "") + text.slice(Math.max(0, k - 40), k + 60).trim() + "…"; }
    return { i, w, name, page: pg.label || "", snip, score }; }).filter((x) => x.score).sort((a, b) => b.score - a.score || a.i - b.i);
}
function rdFindDraw(inp) {   // the list: every widget under its page's name, or the matches, best first
  const box = inp.closest(".rd-pop").querySelector(".rd-res"), all = !inp.value.trim(), hits = rdFind(inp.value), cur = READER === "scroll" ? RDAT : wpos(wseq());
  RDFI = all ? Math.max(0, hits.findIndex((h) => h.i === cur)) : 0;   // the open list starts on the widget you're on
  box.innerHTML = hits.length ? hits.map((h, k) => (all && (k === 0 || hits[k - 1].page !== h.page) ? `<p class="rd-rg">${esc(h.page)}</p>` : "")
    + `<button type="button" class="rd-r${k === RDFI ? " on" : ""}${h.i === cur ? " cur" : ""}" role="option" id="rd-opt-${k}" aria-selected="${k === RDFI}" data-rdgo="${h.i}"><span class="stile">${sico(h.w)}</span><span class="rd-rt"><b>${esc(h.name)}</b>${all ? "" : `<small>${esc(h.page)}${h.snip ? ` · ${esc(h.snip)}` : ""}</small>`}</span></button>`).join("") : `<p class="rd-none">No widget matches</p>`;
  if (hits.length) { inp.setAttribute("aria-activedescendant", `rd-opt-${RDFI}`); const on = box.querySelector(".rd-r.on"); if (on) on.scrollIntoView({ block: "nearest" }); } else inp.removeAttribute("aria-activedescendant");
}
let RDFI = 0;   // the highlighted row
function rdFindOpen(root, v = "") { const pop = root.querySelector(".rd-pop"), b = root.querySelector("[data-rdfind]"), q = pop.querySelector(".rd-q");
  pop.hidden = false; b.setAttribute("aria-expanded", "true"); q.value = v; rdFindDraw(q); q.focus(); }
function rdFindClose(focusButton) { document.querySelectorAll(".rd-pop:not([hidden])").forEach((pop) => { pop.hidden = true; const f = pop.closest(".rd-find"), b = f.querySelector("[data-rdfind]"); b.setAttribute("aria-expanded", "false"); f.querySelector(".rd-q").removeAttribute("aria-activedescendant"); if (focusButton) b.focus(); }); }
function rdGo(i) {   // to a widget, in either mode
  rdFindClose(false);
  if (READER === "scroll") rdFocus(i);
  else { const n = wseq().length, at = WFULL === WDONE ? n : wpos(wseq()); if (i !== at) wfStep(i - at); }
  const to = document.querySelector(READER === "scroll" ? `#rdm .rd-w[data-rdi="${i}"] [data-rdfocus]` : "#wfm .rd-ht") || document.querySelector(".wfm-c [data-rdfind]");   // keyboard focus lands on the widget you picked, never the hidden search
  if (to) { if (!to.hasAttribute("tabindex")) to.tabIndex = -1; to.focus({ preventScroll: true }); }
}
document.addEventListener("input", (e) => { if (e.target.matches && e.target.matches(".rd-q")) rdFindDraw(e.target); });
document.addEventListener("keydown", (e) => { const q = e.target.matches && e.target.matches(".rd-q") ? e.target : null; if (!q) return;
  const opts = [...q.closest(".rd-pop").querySelectorAll(".rd-r")];
  if (e.key === "Escape") { e.preventDefault(); return q.value ? (q.value = "", rdFindDraw(q)) : rdFindClose(true); }   // clears the search, then closes the list; never Reader
  if ((e.key === "ArrowDown" || e.key === "ArrowUp") && opts.length) { e.preventDefault(); RDFI = (RDFI + (e.key === "ArrowDown" ? 1 : -1) + opts.length) % opts.length;
    opts.forEach((o, k) => { o.classList.toggle("on", k === RDFI); o.setAttribute("aria-selected", String(k === RDFI)); }); q.setAttribute("aria-activedescendant", opts[RDFI].id); opts[RDFI].scrollIntoView({ block: "nearest" }); return; }
  if (e.key === "Enter" && opts.length) { e.preventDefault(); rdGo(+opts[RDFI].dataset.rdgo); } });
document.addEventListener("click", (e) => { const t = e.target.closest ? e.target : null; if (!t) return;
  const g = t.closest("[data-rdgo]"); if (g) { e.preventDefault(); e.stopPropagation(); return rdGo(+g.dataset.rdgo); }
  const fb = t.closest("[data-rdfind]"); if (fb) { e.preventDefault(); e.stopPropagation(); const pop = fb.parentNode.querySelector(".rd-pop"); return pop.hidden ? rdFindOpen(fb.closest(".lmod-c")) : rdFindClose(true); }
  if (!t.closest(".rd-find")) rdFindClose(false); }, true);
