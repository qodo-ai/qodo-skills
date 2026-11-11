function checksSummary(pr) {
  const ks = pr.checks || [];
  if (!ks.length) return "";
  const ok = ks.filter((k) => /SUCC|PASS/i.test(k.state));
  const rest = ks.filter((k) => !ok.includes(k));
  const all = ks.map((k) => `${k.name}: ${k.state}`).join("\n");
  return `<span class="pill ${rest.some((k) => /FAIL|ERR/i.test(k.state)) ? "fail" : "ok"}" title="${esc(all)}">${ok.length}/${ks.length} checks passed</span>` +
    rest.map((k) => `<span class="pill ${/FAIL|ERR/i.test(k.state) ? "fail" : ""}">${esc(k.name)}: ${esc(String(k.state).toLowerCase())}</span>`).join("");
}
