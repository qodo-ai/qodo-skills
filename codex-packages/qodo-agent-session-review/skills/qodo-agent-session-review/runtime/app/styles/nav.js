/* The header's package switcher (joined inside package.js at its marker): with the side menu collapsed, the package name in the header
   is a menu of the work packages on this machine, for switching only; the PR filter stays in the side menu's Workpackage box */
const navMini = () => document.body.classList.contains("nv-mini");
function navReady() { document.documentElement.classList.remove("ck-boot"); }   // after a package switch: show the page once the Workpackage box has its list
if (document.documentElement.classList.contains("ck-boot")) setTimeout(navReady, 1500);   // never hidden for long, even if the list is slow
{ const top = document.querySelector("header.top");   // the side menu's logo row matches the header's height, whenever the header changes (its buttons draw after the first render)
  if (top && window.ResizeObserver) new ResizeObserver(() => document.documentElement.style.setProperty("--hh", top.offsetHeight + "px")).observe(top); }
requestAnimationFrame(() => document.documentElement.classList.remove("ck-hold"));   // just before the first paint: by then the script has drawn the header, side menu and page
function ptlWp(nm) {   // the name, as a button when there's another package to switch to
  const open = !!(document.getElementById("ptlm") && !document.getElementById("ptlm").hidden);   // a redraw keeps an open menu's trigger marked
  return WPKS.length > 1 ? `<button type="button" class="ptl-w ptl-wb" data-ptlwp aria-haspopup="menu" aria-expanded="${open}" title="Switch work package">${esc(nm)}${HICON.chev}</button>` : `<span class="ptl-w">${esc(nm)}</span>`;
}
function ptlClose() { const m = document.getElementById("ptlm"), b = document.querySelector("[data-ptlwp]"); if (m) m.hidden = true; if (b) b.setAttribute("aria-expanded", "false"); }
function ptlMenu(btn) {   // the packages, the open one marked; fixed to the page so the header doesn't clip it
  let m = document.getElementById("ptlm"); if (m && !m.hidden) return ptlClose();
  if (!m) { m = document.createElement("div"); m.id = "ptlm"; m.className = "ptl-mm hmenu"; m.setAttribute("role", "menu"); m.setAttribute("aria-label", "Work packages"); document.body.appendChild(m); }   // its own menu: never the ⋮ menu's .nv-mm
  m.innerHTML = `<p class="ptl-mh">Work packages</p>` + WPKS.map((s) => { const on = s.id === KIT.host.session;
    return `<button type="button" class="hopt${on ? " on" : ""}" role="menuitemradio" aria-checked="${on}"${on ? "" : ` data-ptlgo="${esc(s.id)}"`}><i class="hrad" aria-hidden="true"></i><span class="wpk-tx"><b>${esc(s.title)}</b><small>${esc(wpkMeta(s))}</small></span></button>`; }).join("");
  const r = btn.getBoundingClientRect(); m.hidden = false; m.style.top = r.bottom + 6 + "px"; m.style.left = Math.max(8, Math.min(r.left, innerWidth - m.offsetWidth - 8)) + "px";
  btn.setAttribute("aria-expanded", "true"); (m.querySelector("[data-ptlgo]") || m.querySelector("button")).focus();
}
document.addEventListener("click", (e) => { const t = e.target.closest ? e.target : null; if (!t) return;
  const b = t.closest("[data-ptlwp]"); if (b) { e.preventDefault(); return ptlMenu(b); }
  const g = t.closest("[data-ptlgo]"); if (g) { ptlClose(); return wpkGo(g.dataset.ptlgo); }
  if (!t.closest("#ptlm")) ptlClose(); });
document.addEventListener("keydown", (e) => { const m = document.getElementById("ptlm"); if (!m || m.hidden) return;
  if (e.key === "Escape") { ptlClose(); const b = document.querySelector("[data-ptlwp]"); if (b) b.focus(); return; }
  if (!m.contains(document.activeElement)) return;   // focus has moved elsewhere: its keys are its own
  const items = [...m.querySelectorAll(".hopt")], i = items.indexOf(document.activeElement);   // a menu: arrows, Home and End move between the packages
  const to = { ArrowDown: (i + 1) % items.length, ArrowUp: (i - 1 + items.length) % items.length, Home: 0, End: items.length - 1 }[e.key];
  if (to !== undefined && items.length) { e.preventDefault(); items[to].focus(); } });
