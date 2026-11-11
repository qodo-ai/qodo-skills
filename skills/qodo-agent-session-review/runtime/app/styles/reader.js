/* Reader (joined after package.js into one script): every widget on every page, expanded, in one full-page view — Scroll, with one widget in focus, or Stepper, the full-screen dialog — and Share › Export, its layout on paper */
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
const GLASSES_T = GLASSES.replace('class="g24"', 'class="sico"');   // in the dialog's tile, drawn like every widget icon
function rdHead(step) {   // one header for both modes: Reader on the left, the mode switch and text size in the middle, the steps and close on the right
  const seq = wseq(), done = step && WFULL === WDONE, at = step ? (done ? seq.length : wpos(seq)) : RDAT, a = step ? "data-wfstep" : "data-rdstep";
  return `<div class="lmod-h wfm-h rd-hd"><span class="rd-hl"><span class="stile">${GLASSES_T}</span><b>Reader</b></span><span class="rd-hc">${rdSeg()}${rdFs()}${step ? "" : rdPgBtn()}</span><span class="rd-hr"><span class="wfm-nav"><button type="button" class="wz-ic" data-rdend="first" aria-label="First widget" title="First widget"${at > 0 ? "" : " disabled"}>${svg('<path d="m11 17-5-5 5-5"/><path d="m18 17-5-5 5-5"/>')}</button><button type="button" class="wz-ic" ${a}="-1" aria-label="Previous widget" title="Previous widget (←)"${at > 0 ? "" : " disabled"}>${svg('<path d="m15 18-6-6 6-6"/>')}</button><span class="wfm-n" id="rd-n">${done ? "Done" : `${at + 1} of ${seq.length}`}</span><button type="button" class="wz-ic" ${a}="1" aria-label="Next widget" title="Next widget (→)"${(step ? done : at >= seq.length - 1) ? " disabled" : ""}>${svg('<path d="m9 18 6-6-6-6"/>')}</button><button type="button" class="wz-ic" data-rdend="last" aria-label="Last widget" title="Last widget"${at >= seq.length - 1 || done ? " disabled" : ""}>${svg('<path d="m6 17 5-5-5-5"/><path d="m13 17 5-5-5-5"/>')}</button></span>`
    + `<button type="button" class="wz-ic" ${step ? "data-wfm-close" : "data-rdclose"} aria-label="Close Reader" title="Close (Esc)"><svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg></button></span></div>`;
}
const rdTitle = (w, pid) => { const B = BLOCKS[w] || {}; return `<div class="ssum rd-ht"><span class="stile">${sico(w)}</span><h2>${esc(wname(w, rdPage(pid)))}</h2>${B.sub ? `<span class="ssub">${B.sub()}</span>` : ""}</div>`; };   // Stepper: the widget's title, above its content
const rdPage = (id) => LAYOUT.pages.find((p) => p.id === id) || {};
const rdWidget = ([w, pid], i, extra = "") => { const B = BLOCKS[w], pg = rdPage(pid);   // a widget as Reader and the export show it: its title bar, then all of it
  return `<section class="rd-w" data-rdi="${i}"><div class="ssum rd-h"${extra}><span class="stile">${sico(w)}</span><h2>${esc(wname(w, pg))}</h2>${B.sub ? `<span class="ssub">${B.sub()}</span>` : ""}</div><div class="sbody">${widgetHtml(w)}</div></section>`; };
const rdBody = (seq, extra) => seq.map((x, i) => (i === 0 || seq[i - 1][1] !== x[1] ? `<p class="rd-pg">${esc(rdPage(x[1]).label || "")}</p>` : "") + rdWidget(x, i, extra(i))).join("");   // each page's name above its first widget
const rdAfter = (root, seq) => root.querySelectorAll(".rd-w").forEach((el) => { const B = BLOCKS[seq[+el.dataset.rdi][0]]; if (B && B.after) B.after(el); });
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
  const fresh = !m, top = m ? m.querySelector(".rd-b").scrollTop : 0;
  if (!m) { m = document.createElement("div"); m.id = "rdm"; m.className = "lmod"; document.body.appendChild(m); }
  m.innerHTML = `<div class="lmod-c wfm-c" role="dialog" aria-modal="true" aria-label="Reader">${rdHead(false)}
    <div class="rd-b${RDPG ? "" : " rd-nopg"}">${rdBody(seq, (i) => ` data-rdfocus="${i}" role="button" tabindex="0" title="Focus this widget"`)}</div></div>`;
  rdAfter(m, seq); m.querySelector(".rd-b").scrollTop = top;
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
document.addEventListener("keydown", (e) => { if (READER !== "scroll" || WFULL || LD) return;
  if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); return rdClose(); }
  const f = e.target.closest && e.target.closest("[data-rdfocus]"); if (f && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); return rdFocus(+f.dataset.rdfocus); }
  if (!/^Arrow(Left|Right)$/.test(e.key) || (e.target.closest && e.target.closest("input, textarea, select, [contenteditable], [role=tab], [role=tablist], [role=radiogroup], .bv, .wtab, .cm"))) return;   // ← → move the focus; controls keep their own arrows
  e.preventDefault(); e.stopPropagation(); rdFocus(RDAT + (e.key === "ArrowRight" ? 1 : -1)); }, true);
function rdExport() {   // Share › Export: Reader's layout on paper, every widget and fold open, in the light theme; the print dialog saves it as a PDF
  const seq = wseq(); if (!seq.length) return toast("This review has no widgets to export yet");
  const R = document.documentElement, was = R.dataset.theme, old = document.getElementById("rdp"); if (old) old.remove();
  const el = document.createElement("div"), title = document.title.split(" · ")[0], day = new Date().toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" });
  el.id = "rdp"; el.className = "rdp";
  el.innerHTML = `<header class="rdp-cover"><p class="rd-pg">Work package review</p><h1>${esc(title)}</h1><p class="muted">${pl(C.prs.length, "pull request")} · exported ${esc(day)}</p><ul>${C.prs.map((p) => `<li><b>${esc(p.key)}</b> ${esc(strip(p.title || ""))}</li>`).join("")}</ul></header>${rdBody(seq, () => "")}`;
  document.body.appendChild(el); rdAfter(el, seq); el.querySelectorAll("details").forEach((d) => (d.open = true));
  R.dataset.theme = "light"; document.body.classList.add("rd-printing");
  const done = () => { el.remove(); document.body.classList.remove("rd-printing"); if (was) R.dataset.theme = was; else delete R.dataset.theme; if (BLOCKS.system) BLOCKS.system.after(); };
  addEventListener("afterprint", done, { once: true }); setTimeout(() => print(), 120);   // after the layout settles
}
