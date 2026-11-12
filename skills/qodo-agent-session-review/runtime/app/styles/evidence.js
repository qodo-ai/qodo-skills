/* Evidence limits (joined inside package.js at its marker): what the managed reads couldn't confirm, as a line in the refresh details, in full in a dialog */
const EVL = KIT.host.limits || null;   // product mode only; see evidence_limits() in cockpit/styles.py
const evListGap = (p) => p.recorded && !p.files_list_complete && !p.sections.some((s) => s.name === "files" && !s.complete);   // an unconfirmed file list, unless the files section already reports it
const evGaps = (p) => p.sections.filter((s) => !s.complete).length + (evListGap(p) ? 1 : 0) + (p.files_missing ? 1 : 0) + p.files_open.length + p.files_unrecorded + p.overlaps.length + (p.qodo_error ? 1 : 0);
const evState = (p) => (!p.recorded ? ["none", "Not recorded"] : evGaps(p) ? ["warn", pl(evGaps(p), "gap")] : ["ok", "Complete"]);   // a PR: [tone, label]
function evSummary() {   // the package: [tone, headline, a line under it]
  const ps = EVL.prs, none = ps.filter((p) => !p.recorded).length, gaps = ps.filter((p) => p.recorded && evGaps(p)).length;
  if (none === ps.length) return ["none", "Not recorded for this package", "It was collected before reads recorded whether they were complete, so none can be confirmed."];
  if (gaps || none) return ["warn", `Gaps on ${gaps + none} of ${pl(ps.length, "PR")}`, "Some reads couldn't be confirmed complete. Unread evidence never counts as a clean review."];
  return ["ok", "Every read complete", "Each PR's sections and patches were read in full."];
}
function evTip() {   // the refresh details' section: the state, and a way to the full list
  if (!EVL || !EVL.prs.length) return ""; const [t, h] = evSummary();
  return `<button type="button" class="ev-tip" data-ev-open aria-haspopup="dialog"><span class="ev-k">Evidence limits</span><span class="ev-s"><i class="ev-dot ${t}"></i>${esc(h)}</span><span class="ev-more">See the details</span></button>`;
}
function authTip() {   // Session auth: this browser holds access until the server restarts; Copy link signs in another browser
  if (!KIT.host.access_url) return "";
  return `<div class="ev-tip ft-auth"><span class="ev-k">Session auth</span><span class="ev-s">This browser is signed in until the server restarts</span><button type="button" class="ft-copy" data-copy-access title="Paste it into any browser on this machine">Copy link</button></div>`;
}
function evPr(p) {   // one PR in the dialog: folded unless it has gaps
  const [tone, st] = evState(p), secs = p.sections.filter((s) => !s.complete), sure = p.files - p.files_open.length - p.files_unrecorded;
  const body = !p.recorded ? `<p class="muted">No completeness was recorded for this PR, so none of its reads can be confirmed complete.</p>` : [
    secs.length && `<p class="ev-l">Sections not read in full</p><ul>${secs.map((s) => `<li><b>${esc(s.name)}</b><span class="muted">${esc(s.status || "unknown")}</span></li>`).join("")}</ul>`,
    evListGap(p) && `<p class="ev-l">Changed-file list</p><p>Not confirmed complete, so some changed files may be missing.</p>`,
    p.files_missing && `<p class="ev-l">Missing changed files</p><p>${pl(p.files_missing, "changed file")} the PR reports ${p.files_missing === 1 ? "isn't" : "aren't"} in the review.</p>`,
    (p.files_open.length || p.files_unrecorded) && `<p class="ev-l">Patches confirmed complete: ${sure} of ${p.files}</p>${p.files_open.length ? `<ul>${p.files_open.map((f) => `<li><code>${esc(f)}</code></li>`).join("")}</ul>` : ""}${p.files_unrecorded ? `<p class="muted">${pl(p.files_unrecorded, "file")} with no completeness recorded.</p>` : ""}`,
    p.overlaps.length && `<p class="ev-l">Reading overlapping work</p><ul>${p.overlaps.map((w) => `<li>${esc(w)}</li>`).join("")}</ul>`,
    p.qodo_error && `<p class="ev-l">Qodo findings</p><p>${esc(p.qodo_error)}</p>`].filter(Boolean).join("") || `<p class="muted">Every section and patch was read in full.</p>`;
  return `<details class="ev-pr"${tone === "warn" ? " open" : ""}><summary><i class="ev-dot ${tone}"></i><b>${esc(p.key)}</b><span class="ev-t">${esc(strip(p.title))}</span><span class="ev-st ${tone}">${esc(st)}</span><span class="ev-cv" aria-hidden="true"></span></summary><div class="ev-b">${body}</div></details>`;
}
function evCommits() {   // the PRs' read commits, by repo, and any new commits since; a dialog like the evidence limits
  let m = document.getElementById("evm"); if (!m) { m = document.createElement("div"); m.id = "evm"; m.className = "lmod"; document.body.appendChild(m); }
  const row = (p) => { const v = LIVE[p.key] || {};
    return `<li><a href="${esc(p.url || "#")}${p.url ? "/commits" : ""}" target="_blank" rel="noopener"><b>#${esc(String(p.key).split("#").pop())}</b><span class="ev-t">${esc(strip(p.title || ""))}</span></a><code>${esc(String(p.head_sha || "").slice(0, 7))}</code>${v.moved ? `<span class="ev-st warn">${v.new_commits > 0 ? pl(v.new_commits, "new commit") : "new commits"}</span>` : ""}</li>`; };
  const repos = [...new Set(C.prs.map((p) => p.repo))].map((r) => `<div class="ev-repo"><p class="ev-l">${GHICON}${esc(r)}</p><ul class="ev-cm">${C.prs.filter((p) => p.repo === r).map(row).join("")}</ul></div>`).join("");
  m.innerHTML = `<div class="lmod-c evm-c" role="dialog" aria-modal="true" aria-label="PR commits"><div class="lmod-h"><b>PR commits</b><button type="button" class="wz-ic" data-ev-close aria-label="Close" title="Close (Esc)">✕</button></div>
    <p class="lmod-p">The commit each PR was read at. A PR with new commits since then needs a refresh to show them.</p>${repos}</div>`;
  m.querySelector("[data-ev-close]").focus();
}
function evOpen() {   // the full list, in a dialog like the others
  if (!EVL) return; let m = document.getElementById("evm"); const [t, h, sub] = evSummary();
  if (!m) { m = document.createElement("div"); m.id = "evm"; m.className = "lmod"; document.body.appendChild(m); }
  m.innerHTML = `<div class="lmod-c evm-c" role="dialog" aria-modal="true" aria-label="Evidence limits"><div class="lmod-h"><b>Evidence limits</b><button type="button" class="wz-ic" data-ev-close aria-label="Close" title="Close (Esc)">✕</button></div>
    <div class="ev-sum"><i class="ev-dot ${t}"></i><div><b>${esc(h)}</b><p class="muted">${esc(sub)}</p></div></div>
    <p class="lmod-p">This review reads each PR through Qodo's managed tools, a page at a time and within a limit of calls and time, and records whether each part was read in full.</p>
    ${EVL.prs.map(evPr).join("")}<p class="muted ev-foot">Diagrams and fonts load from their public CDNs.</p></div>`;
  m.querySelector("[data-ev-close]").focus();
}
document.addEventListener("click", (e) => { const t = e.target.closest ? e.target : null; if (!t) return;
  if (t.closest("[data-ev-open]")) { e.preventDefault(); return evOpen(); }
  if (t.closest("[data-commits-open]")) { e.preventDefault(); return evCommits(); }
  if (t.closest("[data-copy-access]")) { e.preventDefault(); const u = KIT.host.access_url;   // paste it into any browser on this machine
    return (navigator.clipboard ? navigator.clipboard.writeText(u) : Promise.reject()).then(() => toast("Access link copied: open it in any browser on this machine"), () => toast("Couldn't copy the access link")); }
  const m = document.getElementById("evm"); if (m && (t.id === "evm" || t.closest("[data-ev-close]"))) m.remove(); });
document.addEventListener("keydown", (e) => { const m = document.getElementById("evm"); if (m && e.key === "Escape") { e.stopPropagation(); m.remove(); } }, true);
