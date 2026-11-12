/* The header's package switcher (joined inside package.js at its marker): with the side menu collapsed, the package name in the header
   is a menu of the work packages on this machine, for switching only; the PR filter stays in the side menu's Workpackage box */
const navMini = () => document.body.classList.contains("nv-mini");
function ptlWp(nm) {   // the name, as a button when there's another package to switch to
  return WPKS.length > 1 ? `<button type="button" class="ptl-w ptl-wb" data-ptlwp aria-haspopup="menu" aria-expanded="false" title="Switch work package">${esc(nm)}${HICON.chev}</button>` : `<span class="ptl-w">${esc(nm)}</span>`;
}
function ptlClose() { const m = document.getElementById("ptlm"), b = document.querySelector("[data-ptlwp]"); if (m) m.hidden = true; if (b) b.setAttribute("aria-expanded", "false"); }
function ptlMenu(btn) {   // the packages, the open one marked; fixed to the page so the header doesn't clip it
  let m = document.getElementById("ptlm"); if (m && !m.hidden) return ptlClose();
  if (!m) { m = document.createElement("div"); m.id = "ptlm"; m.className = "nv-mm hmenu ptl-mm"; m.setAttribute("role", "menu"); m.setAttribute("aria-label", "Work packages"); document.body.appendChild(m); }
  m.innerHTML = `<p class="ptl-mh">Work packages</p>` + WPKS.map((s) => { const on = s.id === KIT.host.session;
    return `<button type="button" class="hopt${on ? " on" : ""}" role="menuitemradio" aria-checked="${on}"${on ? "" : ` data-ptlgo="${esc(s.id)}"`}><i class="hrad" aria-hidden="true"></i><span class="wpk-tx"><b>${esc(s.title)}</b><small>${esc(wpkMeta(s))}</small></span></button>`; }).join("");
  const r = btn.getBoundingClientRect(); m.hidden = false; m.style.top = r.bottom + 6 + "px"; m.style.left = Math.max(8, Math.min(r.left, innerWidth - m.offsetWidth - 8)) + "px";
  btn.setAttribute("aria-expanded", "true"); (m.querySelector("[data-ptlgo]") || m.querySelector("button")).focus();
}
document.addEventListener("click", (e) => { const t = e.target.closest ? e.target : null; if (!t) return;
  const b = t.closest("[data-ptlwp]"); if (b) { e.preventDefault(); return ptlMenu(b); }
  const g = t.closest("[data-ptlgo]"); if (g) { ptlClose(); return wpkGo(g.dataset.ptlgo, true); }
  if (!t.closest("#ptlm")) ptlClose(); });
document.addEventListener("keydown", (e) => { const m = document.getElementById("ptlm"); if (m && !m.hidden && e.key === "Escape") { ptlClose(); const b = document.querySelector("[data-ptlwp]"); if (b) b.focus(); } });
