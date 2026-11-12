/* Welcome (joined inside package.js at its marker): the welcome page on the first open, its tour, and its Settings switch.
   Its state is one app setting, saved with the others in app-state.json: cockpit:welcome = { hide, last } (last: the review it was shown for) */
const WCKEY = "cockpit:welcome";
const wcGen = () => `${KIT.host.session || C.title}@${C.reviewed_at || ""}`;   // a review the skill regenerates gets a new collection time
const wcState = () => store.get(WCKEY, null) || {};
function wcAuto() { const W = store.get(WCKEY, null); if (!W || (!W.hide && W.last !== wcGen())) wcOpen(); }   // the first open ever, or a regenerated review while it's switched on
const wcSave = (hide) => store.set(WCKEY, { hide, last: wcGen() });
const WCART = `<svg class="wc-art" viewBox="0 0 320 240" aria-hidden="true"><rect class="wa-win" x="18" y="22" width="284" height="196" rx="14"/><rect class="wa-nav" x="18" y="22" width="76" height="196" rx="14"/><rect class="wa-nav" x="80" y="22" width="14" height="196"/>
  <rect class="wa-lbl" x="30" y="40" width="26" height="4" rx="2"/><rect class="wa-it on" x="28" y="50" width="56" height="12" rx="4"/><rect class="wa-it" x="34" y="68" width="40" height="5" rx="2.5"/><rect class="wa-lbl" x="30" y="86" width="22" height="4" rx="2"/><rect class="wa-it" x="34" y="96" width="44" height="5" rx="2.5"/><rect class="wa-it" x="34" y="108" width="36" height="5" rx="2.5"/><rect class="wa-it" x="34" y="120" width="42" height="5" rx="2.5"/><rect class="wa-lbl" x="30" y="138" width="30" height="4" rx="2"/><rect class="wa-it" x="34" y="148" width="38" height="5" rx="2.5"/>
  <g class="wa-diff"><rect class="wa-dh" x="106" y="40" width="182" height="14" rx="5"/>${[["c",70],["d",96],["d",80],["a",104],["a",118],["a",86],["c",60],["d",74],["a",110],["a",92]].map(([k, w], i) => `<g class="wa-l ${k}"><rect x="106" y="${58 + i * 14}" width="182" height="12" rx="3"/><rect class="m" x="110" y="${62 + i * 14}" width="4" height="4" rx="1"/><rect class="t" x="120" y="${61.5 + i * 14}" width="${w}" height="5" rx="2.5"/></g>`).join("")}<rect class="wa-scan" x="106" y="58" width="182" height="12" rx="3"/></g>
  <g class="wa-card wa-c1"><rect x="106" y="40" width="182" height="58" rx="9"/><circle class="wa-ok" cx="126" cy="69" r="10"/><path class="wa-tick" d="m121 69 3.5 3.5 6.5-7"/><rect class="wa-tx" x="144" y="58" width="78" height="7" rx="3.5"/><rect class="wa-tx2" x="144" y="72" width="112" height="5" rx="2.5"/></g>
  <g class="wa-card wa-c2"><rect x="106" y="108" width="88" height="94" rx="9"/><rect class="wa-bar b1" x="120" y="162" width="12" height="28" rx="3"/><rect class="wa-bar b2" x="138" y="146" width="12" height="44" rx="3"/><rect class="wa-bar b3" x="156" y="130" width="12" height="60" rx="3"/><rect class="wa-bar b4" x="174" y="152" width="12" height="38" rx="3"/><rect class="wa-tx2" x="118" y="120" width="40" height="5" rx="2.5"/></g>
  <g class="wa-card wa-c3"><rect x="202" y="108" width="86" height="94" rx="9"/><path class="wa-rad" d="M245 126 271 146 262 178 228 178 219 146Z"/><path class="wa-rad2" d="M245 140 259 150 254 168 236 168 231 150Z"/></g>
  <g class="wa-badge"><circle cx="276" cy="204" r="24"/><g class="wa-gl"><circle cx="267" cy="207" r="5"/><circle cx="285" cy="207" r="5"/><path d="M272 207a4 4 0 0 1 8 0M262 205l3-7M290 205l-3-7"/></g></g></svg>`;
function wcOpen() {   // the welcome page: what this is, this package in numbers, and the two ways in
  let m = document.getElementById("wcm"); if (!m) { m = document.createElement("div"); m.id = "wcm"; m.className = "lmod wcm"; document.body.appendChild(m); }
  const repos = new Set(C.prs.map((p) => p.repo)).size, feat = (ic, t, d) => `<li><span class="wc-fi">${sico(ic)}</span><span><b>${t}</b>${d}</span></li>`;
  m.innerHTML = `<div class="lmod-c wc-c" role="dialog" aria-modal="true" aria-labelledby="wc-t"><div class="wc-hero">${WCART}<p class="wc-pk"><span>${esc(C.title)}</span>${pl(C.prs.length, "PR")} · ${pl(repos, "repo")} · ${pl(wseq().length, "widget")}</p></div>
    <div class="wc-b"><button type="button" class="wz-ic wc-x" data-wc-close aria-label="Close" title="Close">✕</button><p class="wc-k">${(document.querySelector(".snav-top .qlogo") || { outerHTML: "Qodo" }).outerHTML}</p><h2 id="wc-t">Agent Session Review</h2>
      <p class="wc-lead">A personalised review that helps you quickly understand what your agent sessions built, and the work package behind it: the collection of PRs that makes up your feature.</p>
      <ul class="wc-f">${feat("ovw", "Pages and widgets", "The verdict, requirements, risk, code and findings, each a widget on a page")}${feat("walk", "Reader", "Every widget in one view: scroll through them or step one at a time")}${feat("plan", "Personal", "Innovative ways to review agent code quickly, arranged the way you review")}</ul>
      <div class="wc-a"><button type="button" class="btn pri" data-wc-tour>Start the tour</button><button type="button" class="btn" data-wc-build>Help me build a layout</button></div>
      <label class="wc-ck"><input type="checkbox" data-wc-hide checked><span>Don't show again</span></label><p class="wc-note">You can manage this in Settings at any time.</p></div></div>`;
  m.querySelector("[data-wc-tour]").focus();
}
function wcClose(then) { const m = document.getElementById("wcm"); if (!m) return; const ck = m.querySelector("[data-wc-hide]"); wcSave(!ck || ck.checked); m.remove(); if (then) then(); }
const WCT = [   // the tour: what each part is for, pointed at on the page
  { at: () => document.querySelector(".snav-menu"), t: "Pages and review widgets", p: "The side menu lists this review's pages, grouped under dividers. Each page holds review widgets: the verdict, requirements, agent decisions, Merge Risk, the code map, walkthroughs and findings. Fold them, open them full screen, or rename them." },
  { at: () => document.querySelector(".snav-wp"), t: "The work package", p: "A work package is the set of PRs that makes up one feature. This box switches between the packages on this machine; the arrow on the open one filters its PRs, and every widget follows the filter." },
  { at: () => document.querySelector("#panel .rpart, #panel .sec"), t: "Where to start", p: "Start on Overview. The Verdict says whether the package meets your merge thresholds, and Package contents lists every PR with its merge, findings and CI state." },
  { at: () => [document.querySelector("[data-reader]"), document.querySelector("[data-vw]")], t: "Reader and view options", p: "Reader opens every widget in one view: scroll through them, or step one at a time with ← and →. Preferences sets how this page's widgets open: expanded, headless, accordion, manual or as tabs." },
  { at: () => document.querySelector("[data-nvmore]"), t: "Make the layout yours", p: "The ⋮ menu at the foot of the side menu: Customize adds, removes and reorders pages, widgets and dividers; Templates has ready-made layouts, and My layouts keeps your own for every review." },
  { at: () => document.querySelector(".rfw"), t: "Your data stays local", p: "This app runs on your machine. It fetches the review data through the Qodo toolbox and keeps it in a local folder; notes and marks never leave it. Refresh, top right, reads the PRs again. Hover it for the details: when the data was fetched, a folder icon that opens where it lives, and any evidence limits." }];
let WCI = -1;   // the tour's step; -1: not running
function wcTour(i) {
  let o = document.getElementById("wct"); WCI = i;
  if (i < 0 || i >= WCT.length) { if (o) o.remove(); WCI = -1; removeEventListener("resize", wcPlace); if (i >= WCT.length) toast("Tour complete"); return; }
  if (!o) { o = document.createElement("div"); o.id = "wct"; o.innerHTML = `<div class="wct-spot"></div><div class="wct-pop" role="dialog" aria-modal="true" aria-label="Tour"></div>`; document.body.appendChild(o); addEventListener("resize", wcPlace); }
  const s = WCT[i], last = i === WCT.length - 1;
  o.querySelector(".wct-pop").innerHTML = `<div class="wct-top"><span class="wct-n">${i + 1} of ${WCT.length}</span><span class="wct-dots">${WCT.map((_, k) => `<i${k === i ? ' class="on"' : ""}></i>`).join("")}</span></div><h3>${s.t}</h3><p>${s.p}</p>
    <div class="wct-a"><button type="button" class="wct-skip" data-wct="end">Skip the tour</button><span>${i ? `<button type="button" class="btn sm" data-wct="back">Back</button>` : ""}<button type="button" class="btn pri sm" data-wct="next">${last ? "Done" : "Next"}</button></span></div>`;
  wcPlace(); o.querySelector('[data-wct="next"]').focus();
}
function wcPlace() {   // the spotlight around the step's part of the page, and the card beside it, kept on screen
  const o = document.getElementById("wct"); if (!o || WCI < 0) return;
  const els = [].concat(WCT[WCI].at()).filter(Boolean), spot = o.querySelector(".wct-spot"), pop = o.querySelector(".wct-pop"), W = innerWidth, H = innerHeight, pw = pop.offsetWidth, ph = pop.offsetHeight;
  if (!els.length) { spot.style.cssText = `left:${W / 2}px;top:${H / 2}px;width:0;height:0`; Object.assign(pop.style, { left: (W - pw) / 2 + "px", top: (H - ph) / 2 + "px" }); return; }
  els[0].scrollIntoView({ block: "nearest" });
  const rs = els.map((e) => e.getBoundingClientRect()), pad = 6, r = { l: Math.min(...rs.map((x) => x.left)) - pad, t: Math.min(...rs.map((x) => x.top)) - pad, r: Math.max(...rs.map((x) => x.right)) + pad, b: Math.max(...rs.map((x) => x.bottom)) + pad };
  r.t = Math.max(r.t, 4); r.b = Math.min(r.b, H - 4);
  spot.style.cssText = `left:${r.l}px;top:${r.t}px;width:${r.r - r.l}px;height:${r.b - r.t}px`;
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(v, hi));
  let left, top;
  if (r.r + 16 + pw <= W - 16 && r.b - r.t > ph) { left = r.r + 16; top = r.t + 8; }   // tall parts (the menu): beside them
  else { left = (r.l + r.r) / 2 - pw / 2; top = r.b + 14 + ph <= H - 16 ? r.b + 14 : r.t - ph - 14; }   // otherwise below, or above when it doesn't fit
  Object.assign(pop.style, { left: clamp(left, 16, W - pw - 16) + "px", top: clamp(top, 16, H - ph - 16) + "px" });
}
const wcSetRow = () => `<p class="smod-k smod-k2">Welcome page</p><div class="smod-r wc-row"><button class="hsrow htg" role="switch" aria-checked="${!wcState().hide}" data-wcset><span><b>Show the welcome page</b><em>Opens when the skill regenerates a review for a feature, with the tour and the layout wizard. Off is the welcome page's Don't show again</em></span><i class="hsw" aria-hidden="true"></i></button><button type="button" class="btn sm wc-now" data-wc-open>Open the welcome page now</button></div>`;   // the switch and the button in one card
document.addEventListener("click", (e) => { const t = e.target.closest ? e.target : null; if (!t) return;
  if (t.closest("[data-wc-tour]")) return wcClose(() => { if (TABS[0] && S.tab !== TABS[0][0]) go(TABS[0][0]); setTimeout(() => wcTour(0), 250); });   // the tour starts on the first page
  if (t.closest("[data-wc-build]")) return wcClose(() => lDialog({ kind: "tpl", first: true, ...(store.get("cockpit:layout-template:2", null) || { who: "other", depth: "thorough", type: "full" }), kind: "tpl" }));
  if (t.closest("[data-wc-close]") || t.id === "wcm") return wcClose();
  const st = t.closest("[data-wct]"); if (st) { const a = st.dataset.wct; return wcTour(a === "next" ? WCI + 1 : a === "back" ? WCI - 1 : -1); }
  if (t.closest("[data-wcset]")) { const hide = !wcState().hide; store.set(WCKEY, { ...wcState(), hide, last: wcGen() }); return t.closest("[data-wcset]").setAttribute("aria-checked", String(!hide)); }
  if (t.closest("[data-wc-open]")) { setOpen(false); return wcOpen(); }
  if (t.closest("[data-wc-back]")) { lDialog(null); return wcOpen(); }   // the layout wizard's way back
}, true);
document.addEventListener("keydown", (e) => {
  if (WCI >= 0 && e.key === "Escape") { e.stopPropagation(); return wcTour(-1); }
  if (WCI >= 0 && (e.key === "ArrowRight" || e.key === "ArrowLeft")) { e.preventDefault(); e.stopPropagation(); return wcTour(Math.max(0, WCI + (e.key === "ArrowRight" ? 1 : -1))); }
  if (e.key === "Escape" && document.getElementById("wcm")) { e.stopPropagation(); wcClose(); } }, true);
