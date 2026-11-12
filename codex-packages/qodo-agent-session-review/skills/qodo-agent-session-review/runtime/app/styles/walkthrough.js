/* ---------- Execution walkthrough and Finding review: the session's builder.json and triage/ pages (cockpit/walkthrough.py) ---------- */
const CRM = (() => { try { return JSON.parse(document.getElementById("wt-data").textContent); } catch (_) { return {}; } })();
const BWF = ((CRM.builder || {}).files) || [], BWFL = ((CRM.builder || {}).flows) || [], TRI = CRM.triage || [];
const BWKEY = "crm:" + C.session;
const BW = Object.assign({ mode: "flow", hide: [], kinds: [], flat: false }, store.get(BWKEY, {}), { q: "", open: {}, dirs: true });   // flat: no nesting (flows unindented, files unfoldered); dirs: folders open by default
const bwSave = () => store.set(BWKEY, { mode: BW.mode, hide: BW.hide, kinds: BW.kinds, flat: BW.flat });
const ROLE = { source: "Source", test: "Tests", config: "Config", docs: "Docs", migration: "Migrations", generated: "Generated" };
const HIDEABLE = ["test", "config", "docs", "migration", "generated"];
const KIND = { function: "function", method: "method", class: "class", component: "component", hook: "hook", type: "type", enum: "enum", const: "const", section: "section", module: "top level" };
const CODEK = ["function", "method", "class", "component", "hook"];
const BWKG = { class: ["Class", ["class"]], method: ["Method", ["method", "function"]], module: ["Top-level code", ["module"]], component: ["Component", ["component", "hook"]],
  type: ["Type", ["type", "enum"]], const: ["Constant", ["const"]], section: ["Section", ["section"]] };   // the Exclude parts chips, in this order
const bwKind = (m) => Object.keys(BWKG).find((g) => BWKG[g][1].includes(m.kind)) || "method";
const CHG = { added: ["New", "added"], modified: ["Changed", "modified"], deleted: ["Removed", "deleted"] };
const TRIG = {
  user: ["User action", '<path d="m9 9 5 12 1.8-5.2L21 14Z"/><path d="M7.2 2.2 8 5.1"/><path d="m5.1 8-2.9-.8"/><path d="M14 4.1 12 6"/><path d="m6 12-1.9 2"/>'],
  api: ["API endpoint", '<rect width="20" height="8" x="2" y="2" rx="2"/><rect width="20" height="8" x="2" y="14" rx="2"/><path d="M6 6h.01"/><path d="M6 18h.01"/>'],
  webhook: ["Webhook", '<path d="M18 16.98h-5.99c-1.1 0-1.95.94-2.48 1.9A4 4 0 0 1 2 17c.01-.7.2-1.4.57-2"/><path d="m6 17 3.13-5.78c.53-.97.1-2.18-.5-3.1a4 4 0 1 1 6.89-4.06"/><path d="m12 6 3.13 5.73C15.66 12.7 16.9 13 18 13a4 4 0 0 1 0 8"/>'],
  cron: ["Scheduled job", '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>'],
  cli: ["Command", '<path d="m4 17 6-6-6-6"/><path d="M12 19h8"/>'],
  event: ["Event", '<path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z"/>'],
  deploy: ["Deploy", '<path d="M12 2v13"/><path d="m8 11 4 4 4-4"/><path d="M20 21H4"/>'] };
TRIG.queue = TRIG.event;
const ENDICON = '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>';
PCOUNT.triage = ["open finding", "open findings"];
const svg = (p, cls = "") => `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true">${p}</svg>`;
const KICON = {   // one icon per kind, beside its colour
  component: '<path d="M15.5 11.3a1 1 0 0 0 0 1.4l2.4 2.4a1 1 0 0 0 1.4 0l2.4-2.4a1 1 0 0 0 0-1.4l-2.4-2.4a1 1 0 0 0-1.4 0z"/><path d="M2.3 11.3a1 1 0 0 0 0 1.4l2.4 2.4a1 1 0 0 0 1.4 0l2.4-2.4a1 1 0 0 0 0-1.4L6.1 8.9a1 1 0 0 0-1.4 0z"/><path d="M8.9 17.9a1 1 0 0 0 0 1.4l2.4 2.4a1 1 0 0 0 1.4 0l2.4-2.4a1 1 0 0 0 0-1.4l-2.4-2.4a1 1 0 0 0-1.4 0z"/><path d="M8.9 4.7a1 1 0 0 0 0 1.4l2.4 2.4a1 1 0 0 0 1.4 0l2.4-2.4a1 1 0 0 0 0-1.4l-2.4-2.4a1 1 0 0 0-1.4 0z"/>',
  hook: '<path d="M12 22V8"/><path d="M5 12H2a10 10 0 0 0 20 0h-3"/><circle cx="12" cy="5" r="3"/>',
  function: '<path d="M8 19c2.5 0 3.4-1.3 3.4-3.4V9.4C11.4 7 12.6 5 15.6 5"/><path d="M8 11.5h7"/>',
  method: '<path d="M8 3H7a2 2 0 0 0-2 2v5a2 2 0 0 1-2 2 2 2 0 0 1 2 2v5a2 2 0 0 0 2 2h1"/><path d="M16 21h1a2 2 0 0 0 2-2v-5a2 2 0 0 1 2-2 2 2 0 0 1-2-2V5a2 2 0 0 0-2-2h-1"/>',
  class: '<path d="M21 8a2 2 0 0 0-1-1.7l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.7l7 4a2 2 0 0 0 2 0l7-4a2 2 0 0 0 1-1.7Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/>',
  type: '<path d="M4 7V4h16v3"/><path d="M9 20h6"/><path d="M12 4v16"/>',
  enum: '<path d="M3 6h.01"/><path d="M3 12h.01"/><path d="M3 18h.01"/><path d="M8 6h13"/><path d="M8 12h13"/><path d="M8 18h13"/>',
  const: '<path d="M4 9h16"/><path d="M4 15h16"/><path d="M10 3 8 21"/><path d="m16 3-2 18"/>',
  section: '<path d="M6 12h12"/><path d="M6 20V4"/><path d="M18 20V4"/>',
  module: '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="m10 12.5-2 2.5 2 2.5"/><path d="m14 12.5 2 2.5-2 2.5"/>' };
const kindChip = (k) => `<span class="bw-k k-${esc(k)}">${KICON[k] ? svg(KICON[k]) : ""}${esc(KIND[k] || k)}</span>`;

const bwVisible = (f) => prOn(f.pr);
const bwHit = (f, m) => { const q = BW.q.trim().toLowerCase(); return !q || [f.path, f.purpose, m ? m.qual + " " + m.purpose : ""].join(" ").toLowerCase().includes(q); };
const bwParts = (f) => f.methods.filter((m) => !BW.kinds.includes(bwKind(m)) && (bwHit(f) || bwHit(f, m)));
const bwFiles = () => BWF.filter((f) => bwVisible(f) && !BW.hide.includes(f.role) && (f.methods.length ? bwParts(f).length : !BW.kinds.length && bwHit(f)));
const bwFlows = () => BWFL.filter((fl) => S.pr === "all" || fl.steps.some((s) => prOn(s.pr)));
const mName = (m) => (m.kind === "module" ? "Top-level code" : m.qual);
const bwRef = (uid) => { for (const f of BWF) { const m = f.methods.find((x) => x.uid === uid); if (m) return [f, m]; } return null; };
const flowsOf = (m) => BWFL.flatMap((fl) => fl.steps.map((s, i) => [fl, s, i]).filter(([, s]) => s.ref === m.uid));

function bwMethodHtml(f, m) {
  const ch = CHG[m.change] || CHG.modified, fl = flowsOf(m);
  return `<details class="bw-m" data-bwk="${esc(m.uid)}" id="${esc(m.uid)}"${BW.open[m.uid] ?? EXPAND ? " open" : ""}><summary>
    ${kindChip(m.kind)}
    <span class="bw-mn"><span class="bw-nr"><code>${esc(mName(m))}</code><span class="bw-tag ${ch[1]}">${ch[0]}</span></span>${m.purpose ? `<span class="bw-mp">${md(m.purpose)}</span>` : ""}</span>
    <span class="bw-mr">${diffstat(m.add || 0, m.del || 0)}</span></summary>
    <div class="bw-mb">${(m.code || []).map((b) => codeHtml(b, { path: f.path })).join("") || `<p class="muted" style="margin:0">No changed lines kept for this ${esc(KIND[m.kind] || "part")}.</p>`}
      <div class="bw-act">${m.start ? `<span>${esc(f.path)}:${m.start}${m.end && m.end !== m.start ? "–" + m.end : ""}</span>` : ""}<button class="lnk" data-bw="changes" data-bwv="${esc(f.uid)}">Open in Changes</button>
        ${fl.map(([x, s, i]) => `<button class="lnk" data-bw="step" data-bwv="${esc(x.id + "|" + i)}">Step ${s.n} of “${esc(x.title)}”</button>`).join("")}</div></div></details>`;
}
const BARICON = {   // the bar's toggles, Lucide strokes
  tree: '<path d="M20 10a1 1 0 0 0 1-1V6a1 1 0 0 0-1-1h-2.5a1 1 0 0 1-.8-.4l-.9-1.2A1 1 0 0 0 15 3h-2a1 1 0 0 0-1 1v5a1 1 0 0 0 1 1Z"/><path d="M20 21a1 1 0 0 0 1-1v-3a1 1 0 0 0-1-1h-2.9a1 1 0 0 1-.88-.55l-.42-.85a1 1 0 0 0-.92-.6H13a1 1 0 0 0-1 1v5a1 1 0 0 0 1 1Z"/><path d="M3 5a2 2 0 0 0 2 2h3"/><path d="M3 3v13a2 2 0 0 0 2 2h3"/>',
  flow: '<circle cx="6" cy="19" r="3"/><path d="M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15"/><circle cx="18" cy="5" r="3"/>',
  nested: '<path d="M21 12h-8"/><path d="M21 6H8"/><path d="M21 18h-8"/><path d="M3 6v4c0 1.1.9 2 2 2h3"/><path d="M3 10v6c0 1.1.9 2 2 2h3"/>',
  flat: '<path d="M21 6H3"/><path d="M21 12H3"/><path d="M21 18H3"/>',
  expand: '<path d="m7 15 5 5 5-5"/><path d="m7 9 5-5 5 5"/>', collapse: '<path d="m7 20 5-5 5 5"/><path d="m7 4 5 5 5-5"/>' };
const bwAllBtn = () => svg(BARICON[bwAnyOpen() ? "collapse" : "expand"]);   // icon only; the button's label says which
function bwAnyOpen() {   // is anything open, so the toggle reads Collapse all
  if (BW.mode === "flow") return bwFlows().some((fl) => WOPEN["bf-" + sid(fl.id)] ?? EXPAND);
  return bwFiles().some((f) => BW.open[f.uid] ?? EXPAND) || (!BW.flat && BW.dirs && BWF.some((f) => f.path.includes("/")));
}
function bwDirTree(files) {   // Nested: a PR's files under their folders, a folder holding one folder merged into it
  const root = { dirs: {}, files: [] }, count = (n) => n.files.length + Object.values(n.dirs).reduce((a, c) => a + count(c), 0);
  files.forEach((f) => { const segs = f.path.split("/"); segs.pop(); let n = root; segs.forEach((x) => (n = n.dirs[x] = n.dirs[x] || { dirs: {}, files: [] })); n.files.push(f); });
  const draw = (n, path) => Object.entries(n.dirs).map(([name, c]) => { let nm = name, p = path + name + "/";
    while (!c.files.length && Object.keys(c.dirs).length === 1) { const [k, v] = Object.entries(c.dirs)[0]; nm += "/" + k; p += k + "/"; c = v; }
    const key = "dir:" + p, open = BW.open[key] ?? (BW.dirs || EXPAND);
    return `<details class="bw-dir" data-bwk="${esc(key)}"${open || BW.q.trim() ? " open" : ""}><summary>${folderIcon(nm, open)}<span class="bw-dn">${esc(nm)}/</span><span class="bw-cnt">${pl1(count(c), "file")}</span></summary>
      <div class="bw-dk">${draw(c, p)}${c.files.map(bwFileHtml).join("")}</div></details>`; }).join("");
  return `<div class="bw-fs bw-tree">${draw(root, "")}${root.files.map(bwFileHtml).join("")}</div>`;
}
function bwFileHtml(f) {
  const dir = f.path.includes("/") ? f.path.slice(0, f.path.lastIndexOf("/") + 1) : "";
  const ms = bwParts(f), open = (BW.open[f.uid] ?? EXPAND) || !!BW.q.trim();
  const word = f.methods.some((m) => CODEK.includes(m.kind)) ? "method" : "part", n = f.methods.length;
  return `<details class="bw-f" data-bwk="${esc(f.uid)}" id="${esc(f.uid)}"${open ? " open" : ""}><summary>${fileIcon(f.path)}
    <span class="bw-fn"><b>${esc(base(f.path))}</b><span class="bw-path">${esc(dir)}</span></span>
    <span class="bw-meta">${f.role !== "source" ? `<span class="bw-tag">${esc(ROLE[f.role] || f.role)}</span>` : ""}${f.status !== "modified" ? `<span class="bw-tag ${esc(f.status)}">${f.status === "added" ? "New file" : "Deleted"}</span>` : ""}<span class="bw-cnt">${ms.length < n ? `${ms.length} of ` : ""}${pl1(n, word)}</span>${diffstat(f.add, f.del)}</span>
    <p class="bw-fp">${f.purpose ? md(f.purpose) : `<span class="muted">No purpose written yet.</span>`}</p></summary>
    <div class="bw-ms">${ms.map((m) => bwMethodHtml(f, m)).join("")}</div></details>`;
}
const VICON = {   // the handoff row's icon, Lucide strokes
  click: TRIG.user[1], event: TRIG.event[1],
  api: '<circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/>',
  navigate: '<path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
  call: '<rect width="18" height="18" x="3" y="3" rx="4"/><path d="M9 17c2 0 2.8-1 2.8-2.8V10c0-2 1-3.3 3.2-3"/><path d="M9 11.2h5.7"/>',
  render: '<rect width="20" height="16" x="2" y="4" rx="2"/><path d="M2 9h20"/><path d="M6 4v5"/>',
  data: '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14a9 3 0 0 0 18 0V5"/><path d="M3 12a9 3 0 0 0 18 0"/>',
  cache: '<path d="M12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/><path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/>' };
const STATEW = {   // where a step's state change lands: [label, icon]
  local: ["Local state", '<path d="M8 21s-4-3-4-9 4-9 4-9"/><path d="M16 3s4 3 4 9-4 9-4 9"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/>'],
  app: ["App state", '<rect width="7" height="7" x="3" y="3" rx="1"/><rect width="7" height="7" x="14" y="3" rx="1"/><rect width="7" height="7" x="14" y="14" rx="1"/><rect width="7" height="7" x="3" y="14" rx="1"/>'],
  url: ["URL", '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>'],
  browser: ["Browser storage", '<path d="M22 12H2"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/><path d="M6 16h.01"/><path d="M10 16h.01"/>'],
  request: ["Request context", '<path d="M21 12a9 9 0 1 1-6.219-8.56"/><path d="M22 4 12 14.01l-3-3"/>'],
  cache: ["Cache", VICON.cache], db: ["Database", VICON.data] };
const stCode = (t, cls = "") => (String(t).includes("`") ? `<span class="${cls}">${md(String(t))}</span>` : `<code class="${cls}">${esc(t)}</code>`);   // a writer's own backticks mark the code parts
const INFOICON = '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>';
function bwState(rows) {   // each place once, then every key = value on its own line; where the key sits and why it matters wait in a tooltip
  if (!rows || !rows.length) return "";
  const groups = [];
  rows.forEach((r) => { const w = STATEW[r.where] ? r.where : "local", g = groups.find((x) => x.w === w); g ? g.rows.push(r) : groups.push({ w, rows: [r] }); });
  const row = (r) => { const parts = String(r.target).split(" → "), key = parts.pop(), from = parts.join(" → ");
    return `<div class="bf-str"><span class="bf-kv">${stCode(key, "bf-key")} = ${stCode(typeof r.value === "string" ? r.value : JSON.stringify(r.value), "bf-v")}</span>${from || r.note ? `<span class="bf-note">${from ? `<span class="bf-from">From ${stCode(from)}</span>` : ""}${r.note ? md(r.note) : ""}</span>` : ""}</div>`; };
  return `<div class="bf-st">${groups.map((g) => `<div class="bf-stg"><span class="bf-stw">${svg(STATEW[g.w][1])}${esc(STATEW[g.w][0])}</span>${g.rows.map(row).join("")}</div>`).join("")}</div>`;
}
const SRCICON ='<path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>';
const bwTok = (t) => { const m = /`([^`]+)`|\*\*([^*]+)\*\*/.exec(String(t || "")); return m ? m[1] || m[2] : ""; };   // a sentence's first code or bold part
function bwFrom(arr, i, fl) {   // the A of "A → B", and the depth of the step it comes from, which its row lines up with
  const v = arr[i].via || {}, prev = arr.slice(0, i).reverse().filter((x) => !x.boundary), d = +arr[i].depth || 0, dep = (x) => +x.depth || 0;
  const parent = d ? prev.find((x) => dep(x) === d - 1) : null, up = parent ? dep(parent) : 0;
  if (/^(rendered by|from) `/.test(v.detail || "")) { const n = bwTok(v.detail), c = prev.find((x) => x.name === n); return [n, c ? dep(c) : up]; }   // the writer named the caller
  if (v.kind === "click" || v.kind === "navigate") { const t = bwTok(v.detail) || (prev.length ? "" : bwTok((fl.trigger || {}).label)); if (t) return [t, up]; }
  const c = parent || prev[0]; return [(c || {}).name || bwTok((fl.trigger || {}).label), c ? dep(c) : 0];
}
function bwGuides(arr, i, via) {   // the tree lines in a row: one per level still open below, then an elbow into this step
  const d = +arr[i].depth || 0; if (!d) return "";
  const more = (k) => { for (let j = i + 1; j < arr.length; j++) { if (arr[j].boundary) continue; const e = +arr[j].depth || 0; if (e < k) return false; if (e === k) return true; } return false; };
  let h = ""; for (let k = 1; k < d; k++) if (more(k)) h += `<i class="bf-v" style="--k:${k}"></i>`;
  return h + `<i class="bf-v${via ? "" : more(d) ? " el" : " el end"}" style="--k:${d}"></i>`;
}
// the handoff shows its type; hovering the icon or label shows A → B and the writer's sentence
const bwVia = (v, d, a, b, g = "") => { if (!v) return "";
  const tip = (a || b ? `<span class="bf-ab"><code>${esc(a || "…")}</code><span class="bf-ar" aria-hidden="true">→</span><code>${esc(b || "…")}</code></span>` : "") + (v.detail && !/^(rendered by|from) `[^`]+`$/.test(v.detail) ? `<span class="bf-xd">${md(v.detail)}</span>` : "");   // a generated "from X" only repeats A
  const lined = g.includes(`--k:${(+d || 0) + 1}"`);   // a tree line already runs through the icon, so it draws no line of its own
  return `<li class="bf-x k-${esc(v.kind)}${lined ? " lined" : ""}" style="--d:${+d || 0}">${g}<span class="bf-xb"><span class="bf-xh"${tip ? ` tabindex="0"` : ""}><span class="bf-xi">${svg(VICON[v.kind] || VICON.call)}</span><b>${esc(v.label)}</b>${tip ? `<span class="bf-abt" role="tooltip">${tip}</span>` : ""}</span></span></li>`; };
const TECH = { tsx: ["React", "react_ts"], jsx: ["React", "react"], ts: ["TypeScript", "typescript"], js: ["JavaScript", "javascript"], mjs: ["JavaScript", "javascript"],
  py: ["Python", "python"], toml: ["TOML", "toml"], yaml: ["YAML", "yaml"], yml: ["YAML", "yaml"], json: ["JSON", "json"], sql: ["SQL", "database"], go: ["Go", "go"], rs: ["Rust", "rust"],
  java: ["Java", "java"], sh: ["Shell", "console"], css: ["CSS", "css"], scss: ["Sass", "sass"], html: ["HTML", "html"], md: ["Markdown", "markdown"], mdx: ["MDX", "mdx"] };
// one chip for what a step is and what it's written in: "React component" with the React logo; without a known language, the kind's own icon
const bwWhat = (s, k) => { let t = TECH[String(s.path || "").split(".").pop().toLowerCase()]; const kw = k ? KIND[k] || k : "";
  if (t && /^(TypeScript|JavaScript)$/.test(t[0]) && (k === "hook" || k === "component")) t = TECH.tsx;   // hooks and components are React whatever the file ends in
  if (!t) return k ? kindChip(k) : "";
  return `<span class="bf-tech" title="${esc(t[0])}${kw ? " " + esc(kw) : ""}, in ${esc(base(s.path || ""))}">${mitImg(t[1])}${esc(t[0])}${kw ? " " + esc(kw) : ""}</span>`; };
const repoOf = (s) => String((s && (s.repo || s.pr)) || "").split("#")[0];
function bwCross(arr, i) {   // a repo boundary above the first step and wherever the flow moves into another repo; it names the repo below it
  const r = repoOf(arr[i]), prev = arr.slice(0, i).reverse().find((x) => !x.boundary), p = repoOf(prev);
  return r && (!prev || r !== p) ? `<li class="bf-rx" role="separator" aria-label="${prev ? "Into" : "Starts in"} ${esc(r)}"><span class="bf-rxl">${GHICON}<b title="${esc(r)}">${esc(r.split("/").pop())}</b></span></li>` : "";
}
function bwSteps(fl) {   // each top-level step and everything under it is a subflow: a box headed by its repo, then its name (the step's "subflow")
  let h = "", open = false;
  fl.steps.forEach((s, i, arr) => { const top = !s.boundary && !(+s.depth || 0), r = top && repoOf(s);
    if (top) { h += (open ? "</ol></li>" : "") + `<li class="bf-grp"><div class="bf-gh"><span class="bf-gn">${svg(BARICON.flow)}${esc(s.subflow || s.name || "")}</span>${r ? `<span class="bf-grepo" title="${esc(r)}">${GHICON}${esc(r.split("/").pop())}</span>` : ""}</div><ol class="bf-gs">`; open = true; }
    h += bwStepHtml(s, i, arr, fl, top); });
  return h + (open ? "</ol></li>" : "");
}
function bwStepHtml(s, i, arr, fl, top = false) {
  if (s.boundary) { const prev = arr.slice(0, i).reverse().find((x) => !x.boundary), next = arr.slice(i + 1).find((x) => !x.boundary);
    return s.merged ? "" : bwVia({ kind: s.kind || "event", label: s.label || "Hands off", detail: s.boundary }, prev ? prev.depth : s.depth, prev && prev.name, (/data|cache/.test(s.kind) && bwTok(s.boundary)) || (next && next.name), bwGuides(arr, i, true)); }   // a read or write lands on its table
  const chg = s.in_diff ? (s.ref ? `<button type="button" class="bf-tag in bf-go" data-bw="goto" data-bwv="${esc(s.ref)}" title="Open in the tree">${s.change === "added" ? "New" : "Changed"}</button>`   // the chip opens the change in the tree
      : `<span class="bf-tag in">${s.change === "added" ? "New" : "Changed"}</span>`)
    : `<span class="bf-tag out"${s.file_changed ? ` title="In a file this package changes"` : ""}>Existing code</span>`;
  const hit = s.in_diff && s.ref && bwRef(s.ref);
  const ok = (hit && hit[1].kind) || s.okind;
  // a function, method or hook reads as a call: name()
  const nm = `<code>${esc(s.name || "")}${/^(function|method|hook)$/.test(ok) && !/\)$/.test(s.name || "") ? "()" : ""}</code>`;
  // folded, a step shows only its name, its kind and its repo
  const k = `st:${s.flow}:${i}`;
  const st = s.state && s.state.length ? `<span class="bf-setw"><button type="button" class="bf-setb" aria-describedby="bfst-${esc(s.flow)}-${i}">${svg(VICON.data)}State</button><span class="bf-setp bf-stp" id="bfst-${esc(s.flow)}-${i}" role="tooltip">${bwState(s.state)}</span></span>` : "";
  const [from, deep] = s.via ? bwFrom(arr, i, fl) : ["", 0], at = top ? 0 : deep;   // a subflow's first handoff starts at its box's edge, not under a caller in the box before
  return `${bwVia(s.via, at, from, s.name, bwGuides(arr, i, true))}${top ? "" : bwCross(arr, i)}<li class="bf-s ${s.in_diff ? "in" : "out"}" style="--d:${+s.depth || 0}" id="bfs-${esc(s.flow)}-${i}">${bwGuides(arr, i, false)}<details class="bf-b" data-bwk="${esc(k)}"${BW.open[k] ?? EXPAND ? " open" : ""}>
    <summary class="bf-h">${nm}${bwWhat(s, ok)}${st}<span class="bf-hr">${chg}<span class="chev" aria-hidden="true"></span></span></summary>
    ${s.what ? `<p class="bf-w">${md(s.what)}</p>` : ""}${hit ? bwStepTree(hit[0], hit[1], s, i) : ""}</details></li>`;
}
const TBICON = {   // View changes: the overview and Change summary
  file: '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="m10 13-2 2 2 2"/><path d="m14 17 2-2-2-2"/>',
  overview: '<path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/>',
  change: '<circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><path d="M13 6h3a2 2 0 0 1 2 2v7"/><path d="M11 18H8a2 2 0 0 1-2-2V9"/>' };
const KLAB = { function: "Function", method: "Method", class: "Class", component: "Component", hook: "Hook", type: "Type", enum: "Enum", const: "Constant", section: "Section", module: "Top-level code" };
function bwStepTree(f, m, s, i) {   // a changed step's Tree details, folded behind View changes: the two summaries, the changed lines, the file path
  const k = `fs:${s.flow}:${i}`, fl = flowsOf(m).filter(([x, , j]) => x.id !== s.flow || j !== i);
  const blk = (cls, icon, title, body, extra = "") => `<div class="bf-blk"><span class="bf-ti ${cls}">${svg(icon)}</span><div class="bf-bc"><h4>${esc(title)}${extra}</h4>${body}</div></div>`;
  const ln = diffstat(m.add || 0, m.del || 0);   // the lines changed sit by the change summary, else by the overview
  return `<details class="bf-tree" data-bwk="${esc(k)}"${BW.open[k] ?? EXPAND ? " open" : ""}><summary><span class="bf-tv">View changes</span></summary><div class="bf-tb">
    ${m.purpose ? blk("t-ov", TBICON.overview, `${KLAB[m.kind] || "Code"} overview`, `<p>${md(m.purpose)}</p>`, f.purpose ? "" : ln) : ""}${f.purpose ? blk("t-chg", TBICON.change, "Change summary", `<p>${md(f.purpose)}</p>`, ln) : ""}
    ${(m.code || []).map((b) => codeHtml(b, { path: f.path })).join("") || `<p class="muted" style="margin:0">No changed lines kept for this ${esc((KLAB[m.kind] || "part").toLowerCase())}.</p>`}
    <div class="bw-act">${m.start ? `<span>${esc(f.path)}:${m.start}${m.end && m.end !== m.start ? "–" + m.end : ""}</span>` : ""}
      ${fl.map(([x, t, j]) => `<button class="lnk" data-bw="step" data-bwv="${esc(x.id + "|" + j)}">Step ${t.n} of “${esc(x.title)}”</button>`).join("")}</div></div></details>`;
}
function bwSetup(fl) {   // the flow's setup, as a chip right after its title; the list waits in a tooltip
  const setup = String((fl.trigger || {}).detail || "").split(/;\s+/).filter(Boolean).map((x) => x[0].toUpperCase() + x.slice(1));
  return setup.length ? `<span class="bf-setw bf-hsetw"><button type="button" class="bf-setb" aria-describedby="bfset-${esc(fl.id)}">${svg(INFOICON)}Setup</button><span class="bf-setp" id="bfset-${esc(fl.id)}" role="tooltip"><ul>${setup.map((x) => `<li>${md(x)}</li>`).join("")}</ul></span></span>` : "";
}
function bwFlowHtml(fl) {
  const t = TRIG[(fl.trigger || {}).kind] || TRIG.event, tr = fl.trigger || {}, o = fl.outcome || {};
  // the start and the end share one layout: the kicker with its icon after it, then the line, all from the left
  const card = (cls, icon, kick, label, more) => `<div class="bf-end ${cls}"><div><span class="bf-k">${kick}${svg(icon)}</span><div class="bf-lr"><span class="bf-l">${md(label || "")}</span>${more}</div></div></div>`;
  return `<div class="bf${BW.flat ? " bf-flat" : ""}">${card("bf-start", t[1], `Starts with · ${esc(t[0])}`, tr.label, "")}
    <ol class="bf-steps">${bwSteps(fl)}</ol>
    ${card("bf-stop", ENDICON, "Ends with", o.label, "")}</div>`;
}
const KINDWHAT = { component: "A UI component: it renders markup", hook: "A React hook, named use…", function: "A standalone function", method: "A function on a class or object",
  class: "A class", type: "A type or interface", enum: "An enum", const: "A constant, often an object or a map of values", section: "A config section, such as a TOML table", module: "Code at a file's top level" };
const bwKey = (tree) => `${tree ? "" : `<span class="bf-kh">Changes</span>
  <span class="bf-kr"><span class="bf-tag in">Changed</span>Code this package changes</span><span class="bf-kr"><span class="bf-tag in">New</span>Code this package adds</span><span class="bf-kr"><span class="bf-tag out">Existing code</span>Code the flow runs through, unchanged</span>
  `}<span class="bf-kh">Kinds</span>${Object.keys(KINDWHAT).map((k) => `<span class="bf-kr bf-kk"><span class="bw-k k-${esc(k)}">${esc(KIND[k] || k)}</span>${KINDWHAT[k]}</span>`).join("")}`;   // the Key: what the chips mean, then the kinds of code
function bwHead() {
  const tree = BW.mode !== "flow", here = BWF.filter(bwVisible);
  const roles = HIDEABLE.filter((r) => here.some((f) => f.role === r));
  const parts = here.filter((f) => !BW.hide.includes(f.role)).flatMap((f) => f.methods), kinds = Object.keys(BWKG).filter((g) => parts.some((m) => bwKind(m) === g));
  const chips = (a, list, on, label, n, what) => `<div class="bw-flt"><span class="muted">${label}</span>${list.map((k) => `<button class="bw-chip" data-bw="${a}" data-bwv="${k}" aria-pressed="${on.includes(k)}" title="${on.includes(k) ? "Show" : "Hide"} ${esc(what(k))}">${esc(a === "hide" ? ROLE[k] : BWKG[k][0])}<span>${n(k)}</span></button>`).join("")}</div>`;
  // one bar in both modes: the view, the layout, expand or collapse everything, the Key; Tree adds its filter below
  return `<div class="bw-head"><div class="bw-bar"><div class="pviews" role="group" aria-label="View"><button class="pv" data-bw="mode" data-bwv="flow" aria-pressed="${!tree}">${svg(BARICON.flow)}Flow</button><button class="pv" data-bw="mode" data-bwv="tree" aria-pressed="${tree}">${svg(BARICON.tree)}Tree</button></div>
    <div class="pviews" role="group" aria-label="Layout"><button class="pv" data-bw="flat" data-bwv="0" aria-pressed="${!BW.flat}" title="${tree ? "Files under their folders" : "Steps indented by call depth"}">${svg(BARICON.nested)}Nested</button><button class="pv" data-bw="flat" data-bwv="1" aria-pressed="${BW.flat}" title="${tree ? "One list of files" : "Every step at the left edge"}">${svg(BARICON.flat)}Flat</button></div>
    <button class="btn sm bw-all" data-bw="all" aria-label="${bwAnyOpen() ? "Collapse all" : "Expand all"}" title="${bwAnyOpen() ? "Collapse all" : "Expand all"}">${bwAllBtn()}</button>
    <span class="bf-keyw"><button type="button" class="btn sm bf-keyb" aria-describedby="bf-keyp">Key</button><span class="bf-keyp" id="bf-keyp" role="tooltip">${bwKey(tree)}</span></span></div>
    ${tree ? `<input class="bw-q" type="search" placeholder="Filter files and methods" aria-label="Filter files and methods" value="${esc(BW.q)}">` : ""}
    ${tree && (roles.length || kinds.length > 1) ? `<div class="bw-flts">${roles.length ? chips("hide", roles, BW.hide, "Exclude files", (r) => here.filter((f) => f.role === r).length, (r) => ROLE[r].toLowerCase() + " files") : ""}
      ${kinds.length > 1 ? chips("kind", kinds, BW.kinds, "Exclude parts", (g) => parts.filter((m) => bwKind(m) === g).length, (g) => BWKG[g][0].toLowerCase() + " changes") : ""}</div>` : ""}
    ${tree ? `<p class="muted bw-lede">Every changed file and each method, class or section it touches, with what each one is for. Open a method for its changed lines.</p>` : ""}</div>`;
}
function sBuilder() {
  if (!CRM.builder) return [];
  let out;
  if (BW.mode === "flow") out = bwFlows().map((fl, k) => { const st = fl.steps.filter((s) => !s.boundary), n = st.filter((s) => s.in_diff).length;
    return { id: "bf-" + sid(fl.id), label: fl.title, icon: "flow", num: k + 1, after: bwSetup(fl), sub: `<span class="bf-repo">${GHICON}${pl1(new Set(st.map(repoOf).filter(Boolean)).size, "repo")}</span><span class="bf-tag ${n ? "in" : "out"}">${pl1(n, "change")}</span>`, fold: true, html: bwFlowHtml(fl) }; });
  else { const fs = bwFiles(); out = [...new Set(fs.map((f) => f.pr))].map((k) => { const p = C.prs.find((x) => x.key === k), mine = fs.filter((f) => f.pr === k);
    return { id: "bw-" + sid(k), label: `${shortPr(k)} ${strip(p ? p.title : "")}`, nav: shortPr(k), navIcon: "merge", icon: "builder",
      sub: chip(`${pl1(mine.length, "file")} · ${pl1(mine.reduce((a, f) => a + bwParts(f).length, 0), "part")}`), html: BW.flat ? `<div class="bw-fs">${mine.map(bwFileHtml).join("")}</div>` : bwDirTree(mine) }; }); }
  if (out.length === 1 && SECT[S.tab] === undefined) SECT[S.tab] = out[0].id;   // one section: open it
  return out;
}
const bwEmpty = () => !CRM.builder ? `<p class="muted">The execution walkthrough hasn't been written for this review. Ask the coding agent for one with the code-review-master skill.</p>`
  : `${bwHead()}<p class="muted">${BW.mode === "flow" ? "No flows were written for these PRs." : "Everything is hidden by the filters above."}</p>`;

/* Finding review: every PR's triaged Qodo findings as one review: summary, fix estimates, each finding with its code and an action, one prompt for the agent */
const TCLOSED = { implemented: ["Resolved", "ok"], full_implementation: ["Resolved", "ok"], dismissed: ["Dismissed", ""], outdated: ["Outdated", "warn"], detected_after_merge: ["After merge", ""] };
const TOPENL = { partial_implementation: ["Partly resolved", "warn"], not_implemented: ["Not resolved", "warn"], focus_areas_edited: ["Edited", "warn"], missing: ["Not in latest review", ""] };
const TSEVL = { action_required: "High", remediation_recommended: "Medium", informational: "Low" }, TSEVT = { High: "high", Medium: "medium", Low: "low" }, TVERD = { fix: "Fix", skip: "Skip", call: "Your call" };
const TREASONS = [["intentional", "Intentional", "the code is deliberate and correct as written"], ["false_positive", "False positive", "the finding is wrong"], ["deferred", "Deferred", "real, but out of scope for this PR"], ["rejected", "Rejected", "understood and declined"]];
const TNOTE = { resolve: ["Different approach or extra instructions", "Leave empty to follow the recommendation"], dismiss: ["Dismissal explanation", "Leave empty to use the reasoning above"], ignore: ["Note for the agent (optional)", "Why you're leaving it open"], "": ["Note", "Choose an action first"] };
const TNEWNOTE = { resolve: "Leave empty to have the agent verify and fix it", dismiss: "Required: why this finding should be dismissed" };
const TOPENST = ["pending", "partial_implementation", "not_implemented", "focus_areas_edited", "", null, undefined];
const TSKEY = "cockpit:triage", TS = store.get(TSKEY, {}) || {}, TV = { filter: "all", closed: false, all: null, open: {} };
const TOK = new Set(["P", "CODE", "B", "STRONG", "I", "EM", "BR", "UL", "OL", "LI"]);
function tSafe(h) {   // the analysis's own markup and nothing else: allowed tags rebuilt bare, every attribute dropped, anything else kept as text
  const src = document.createElement("template"); src.innerHTML = String(h || "");
  const copy = (n) => n.nodeType === 3 ? document.createTextNode(n.nodeValue) : n.nodeType !== 1 ? null
    : TOK.has(n.tagName) ? [...n.childNodes].reduce((el, c) => { const k = copy(c); if (k) el.appendChild(k); return el; }, document.createElement(n.tagName))
    : [...n.childNodes].reduce((f, c) => { const k = copy(c); if (k) f.appendChild(k); return f; }, document.createDocumentFragment());
  const out = document.createElement("div"); [...src.content.childNodes].forEach((c) => { const k = copy(c); if (k) out.appendChild(k); }); return out.innerHTML;
}
function triAll() {   // every selected PR's findings, numbered once across the package; findings Qodo raised since the triage come last
  const ts = TRI.filter((t) => prOn(t.pr) && t.targets), out = [];
  ts.forEach((t) => { const fs = t.snapshot.findings || [], st = Object.fromEntries(fs.map((f) => [f.id, f.attribution_status]));
    t.targets.forEach((x) => out.push({ ...x, pr: t.pr, prd: t, key: t.pr + "|" + x.id, add: +x.add || 0, rem: +x.rem || 0, status: x.id in st ? st[x.id] || "pending" : fs.length ? "missing" : "pending" })); });
  ts.forEach((t) => { const ids = new Set(t.targets.map((x) => x.id));
    (t.snapshot.findings || []).filter((f) => !ids.has(f.id)).forEach((f) => out.push({ isNew: TOPENST.includes(f.attribution_status), qodo: !TOPENST.includes(f.attribution_status), id: f.id, pr: t.pr, prd: t, key: t.pr + "|" + f.id, title: f.title || "", sev: TSEVL[f.action_level] || "Low", desc: f.description || "", status: f.attribution_status || "pending", badges: [],
      locs: f.file_path ? [`${f.file_path}${f.start_line ? (f.end_line && f.end_line !== f.start_line ? `, lines ${f.start_line}–${f.end_line}` : `, line ${f.start_line}`) : ""}`] : [] })); });
  return out.map((x, i) => ({ ...x, n: i + 1 }));
}
const tClosed = (x) => !!TCLOSED[x.status];
const tSt = (x) => (TS[x.key] = TS[x.key] || { action: x.isNew ? "" : ({ fix: "resolve", skip: "dismiss" })[x.verdict] || "", reason: x.reason || "intentional", note: "" });
const tShown = (x) => (TV.closed || !tClosed(x)) && (TV.filter === "all" || (TV.filter === "new" ? x.isNew : x.verdict === TV.filter && !x.isNew));
const TMAX = 2000, tWhy = (x) => tSt(x).note.trim() || (x.isNew ? "" : String(x.rec || "").replace(/^Skip\.?\s*/, "").trim());   // Qodo's dismissal explanation, and its length limit
const tLong = (x) => !tClosed(x) && tSt(x).action === "dismiss" && tWhy(x).length > TMAX;
const tSum = (xs) => [xs.reduce((a, x) => a + x.add, 0), xs.reduce((a, x) => a + x.rem, 0)];
function triPrompt(all) {   // as the per-PR triage page writes it, one section per PR
  const act = all.filter((x) => !tClosed(x) && tSt(x).action); if (!act.length) return "";
  const prs = [...new Set(act.map((x) => x.pr))].map((k) => TRI.find((t) => t.pr === k)), ind = (s) => s.split("\n").map((l) => "      " + l);
  const L = [`Use the qodo-review-resolver skill to act on Qodo's reviews of ${prs.length === 1 ? "this PR" : `these ${prs.length} PRs`}:`, ...prs.map((t) => `- ${shortPr(t.pr)}${t.sha ? ` (reviewed at ${t.sha})` : ""}: ${t.url}`), "",
    "Each finding below lists its Qodo finding id. If one is missing, run `qodo read pr-review-session findings --pr-url <its PR URL> --json` and match the finding by its title. " +
    "Resolve means fix it in code: follow my instructions where I gave them, otherwise the recommendation. Once the fix is pushed, record those findings as implemented with `qodo pr-review-session mark-implemented` as the skill describes. " +
    "Dismiss means close it in Qodo without a code change: run `qodo pr-review-session dismiss --finding-ids <ids> --reason <reason> --explanation \"<explanation>\"`, batching findings only when they share the same reason and explanation. Only open findings can be dismissed; report any that come back already closed. " +
    "Ignore means leave it open and change nothing. Commit the fixes as focused commits on each PR's branch, push, wait for CI, and report back what you did for each finding."];
  prs.forEach((t) => { const mine = act.filter((x) => x.pr === t.pr); L.push("", `## ${shortPr(t.pr)} (${t.url})`);
    [["resolve", "Resolve"], ["dismiss", "Dismiss"], ["ignore", "Ignore"]].forEach(([v, lab]) => { const g = mine.filter((x) => tSt(x).action === v); if (!g.length) return;
      const est = g.filter((x) => !x.isNew), [a, r] = tSum(est); L.push("", `${lab} (${g.length})${v === "resolve" && est.length ? `, estimated +${a} / −${r} lines` : ""}`, "");
      g.forEach((x) => { const s = tSt(x), note = s.note.trim();
        L.push(`${x.n}. ${x.isNew ? "New finding, not triaged" : `Finding #${x.n}`} (${x.sev}): ${x.title}`); if (x.id) L.push(`   Qodo finding id: ${x.id}`); (x.locs || []).forEach((l) => L.push("   " + l));
        if (v === "resolve") { if (!x.isNew) L.push(`   Estimated size: +${x.add} / −${x.rem} lines`); if (note) L.push("   My instructions:", ...ind(note)); else L.push(x.isNew ? "   Not triaged yet: read Qodo's finding, check it against the code, and fix it if it holds up. Tell me if it doesn't." : "   Recommendation: " + x.rec); }
        if (v === "dismiss") { L.push(`   Reason: ${s.reason} (${(TREASONS.find((q) => q[0] === s.reason) || [0, s.reason])[1]})`); const why = note || (x.isNew ? "" : String(x.rec || "").replace(/^Skip\.?\s*/, "").trim());
          if (why) L.push("   Explanation:", ...ind(why)); else L.push("   Explanation: none given. Ask me for one before dismissing."); }
        if (v === "ignore" && note) L.push("   Note:", ...ind(note));
        L.push(""); }); }); });
  return L.join("\n").trim();
}
function triRef(x) {   // one finding, to ask the agent about it
  const [st] = TCLOSED[x.status] || TOPENL[x.status] || [""];
  const L = [`Question about a Qodo review finding on ${shortPr(x.pr)} (${x.prd.url}).`, "", x.isNew ? `New finding, not triaged yet: ${x.title}` : x.qodo ? `Closed finding, not triaged: ${x.title}` : `Finding #${x.n}: ${x.title}`];
  if (x.id) L.push(`Qodo finding id: ${x.id}`); L.push([x.sev, ...(x.badges || []), st && `status: ${st}`].filter(Boolean).join(" · ")); (x.locs || []).forEach((l) => L.push("Location: " + l));
  if (x.isNew || x.qodo) { if (x.desc) L.push("", "Qodo's description:", x.desc); }   // Qodo's own text: no triage verdict, recommendation or size to quote
  else { L.push("", `Triage verdict: ${TVERD[x.verdict] || x.verdict}. Recommendation: ${x.rec}`, `Estimated fix size: +${x.add} / −${x.rem} lines`); if (x.impact) L.push("", "Impact:", x.impact); if (x.why) L.push("", "Why it happens:", x.why); }
  L.push("", "Read the code at the locations above, then answer my question. Don't change code or Qodo's records unless I ask.", "", "My question: ");
  return L.join("\n");
}
const triCode = (c) => { const a = c.lines[0], z = c.lines[c.lines.length - 1], rng = a ? `L${a.n}${z !== a ? "–" + z.n : ""}` : "";
  return `<figure class="tcode"><figcaption>${/^https:\/\//i.test(c.url || "") ? `<a href="${esc(c.url)}" target="_blank" rel="noopener"><b>${esc(base(c.path))}</b> <span>${rng}</span></a>` : `<b>${esc(base(c.path))}</b> <span>${rng}</span>`}<em>${esc(c.path)}</em></figcaption>
    <div class="tcode-b">${c.lines.map((l) => `<div class="tl ${esc(l.mark)}"><span class="tn">${l.n}</span><span class="tt">${esc(l.text) || "&#8203;"}</span></div>${l.note ? `<div class="tln"><span>${esc(l.note)}</span></div>` : ""}`).join("")}</div></figure>`; };
function triAct(x) {
  const s = tSt(x), [lab, ph] = TNOTE[s.action] || TNOTE[""], k = esc(x.key);
  return `<div class="tact"><div class="tact-r"><label>Action <select class="dsel" data-tact="${k}">${[["", "Choose an action"], ["resolve", "Resolve"], ["dismiss", "Dismiss"], ["ignore", "Ignore"]].map(([v, t]) => `<option value="${v}"${s.action === v ? " selected" : ""}>${t}</option>`).join("")}</select></label>
    ${s.action === "dismiss" ? `<label>Reason <select class="dsel" data-treason="${k}">${TREASONS.map(([v, t, d]) => `<option value="${v}"${s.reason === v ? " selected" : ""}>${t}: ${esc(d)}</option>`).join("")}</select></label>` : ""}</div>
    ${tLong(x) ? `<p class="tlong">The explanation is ${tWhy(x).length.toLocaleString()} characters; Qodo accepts ${TMAX.toLocaleString()}. Write a shorter one below.</p>` : ""}
    <label class="tact-n"><span>${lab}</span><textarea data-tnote="${k}" rows="3" placeholder="${esc((x.isNew && TNEWNOTE[s.action]) || ph)}">${esc(s.note)}</textarea></label></div>`;
}
const triChosen = (x) => { const s = tSt(x); return !tClosed(x) && s.action ? `<span class="tchosen ${s.action}">${{ resolve: "Resolve", dismiss: "Dismiss", ignore: "Ignore" }[s.action]}${s.note.trim() ? " · note" : ""}</span>` : ""; };
function triCard(x) {
  const c = tClosed(x), [stl, stt] = TCLOSED[x.status] || TOPENL[x.status] || [], open = TV.open[x.key] ?? TV.all ?? false;
  const meta = [`<span class="tpr">${esc(shortPr(x.pr))}</span>`, (x.locs || [])[0] ? `<span class="tloc">${esc(base(x.locs[0].split(",")[0]))}</span>` : "", `<span class="dst ${TSEVT[x.sev] || "low"}">${esc(x.sev)}</span>`,
    ...(x.badges || []).map((b) => `<span class="tbadge">${esc(b)}</span>`), x.isNew ? `<span class="dkind">New</span>` : x.verdict ? `<span class="dkind">${TVERD[x.verdict] || esc(x.verdict)}</span>` : "",
    x.isNew || x.qodo ? "" : diffnums(x.add, x.rem), stl ? `<span class="tstat ${stt}">${stl}</span>` : "", triChosen(x)].join("");
  const sec = (h, html) => (html ? `<section class="dsec"><h4>${h}</h4>${/^\s*</.test(html) ? tSafe(html) : `<p>${esc(html)}</p>`}</section>` : "");
  const body = x.isNew || x.qodo ? `<section class="dsec"><h4>Qodo's finding</h4><p class="tdesc">${esc(x.desc || "No description.")}</p></section>`
    : `<div class="tgrid">${sec("Impact", x.impact_html || x.impact)}${sec("Why it happens", x.why_html || x.why)}</div>${(x.code || []).map(triCode).join("")}
      <section class="dsec"><h4>Recommendation</h4><p>${esc(x.rec || "")}</p><p class="tsize">Estimated fix size ${diffnums(x.add, x.rem)}${x.note ? ` <span class="muted">${esc(x.note)}</span>` : ""}</p></section>`;
  return `<details class="dcard tcard${c ? " ok" : ""}" data-tk="${esc(x.key)}"${open ? " open" : ""}${tShown(x) ? "" : " hidden"}><summary><span class="dnum">${x.n}</span><span class="tsum"><span class="dtitle">${esc(x.title)}</span><span class="tmeta">${meta}</span></span>
    <button type="button" class="btn sm tref" data-tref="${esc(x.key)}" title="Copy this finding to ask the agent about it">Copy for agent</button><span class="chev" aria-hidden="true"></span></summary>
    <div class="dbody">${body}${c ? "" : triAct(x)}</div></details>`;
}
function bTriage() {
  if (!TRI.length) return `<p class="tri-none">No findings triage was built for these PRs. Ask the coding agent for one with the qodo-findings-triage skill.</p>`;
  const all = triAll(), open = all.filter((x) => !tClosed(x)), closed = all.length - open.length, quiet = TRI.filter((t) => prOn(t.pr) && !t.targets);
  const cnt = (f) => open.filter((x) => (f === "new" ? x.isNew : !x.isNew && x.verdict === f)).length;
  const fbtn = (v, t, n) => `<button class="pv" data-tfilt="${v}" aria-pressed="${TV.filter === v}">${t}<span class="dfn">${n}</span></button>`;
  const tools = `<div class="dfilts"><span class="pviews" role="group" aria-label="Filter by recommendation">${fbtn("all", "All", open.length)}${fbtn("fix", "Fix", cnt("fix"))}${fbtn("call", "Your call", cnt("call"))}${fbtn("skip", "Skip", cnt("skip"))}${cnt("new") ? fbtn("new", "New", cnt("new")) : ""}</span>
    ${closed ? `<label class="tchk"><input type="checkbox" data-tclosed${TV.closed ? " checked" : ""}> Show closed findings <span class="dfn">${closed}</span></label>` : ""}<span class="dall"><button class="btn sm" data-tall="open">Expand all</button><button class="btn sm" data-tall="close">Collapse all</button></span></div>`;
  const by = (k) => all.filter((x) => x.status && TCLOSED[x.status] && TCLOSED[x.status][0] === k).length, res = by("Resolved"), dis = by("Dismissed"), out = by("Outdated");
  const sumOpen = TV.open._sum ?? false, rows = all.filter(tShown).map((x) => `<tr${tClosed(x) ? ' class="tdim"' : ""}><td class="n">${x.n}</td><td><span class="dst ${TSEVT[x.sev] || "low"}">${esc(x.sev)}</span></td><td><b>${esc(x.title)}</b><div class="tmeta"><span class="tpr">${esc(shortPr(x.pr))}</span>${(x.badges || []).map((b) => `<span class="tbadge">${esc(b)}</span>`).join("")}</div></td>
    <td>${x.isNew || x.qodo ? "" : diffnums(x.add, x.rem)}</td><td>${x.isNew ? '<span class="dkind">New</span>' : `<span class="dkind">${TVERD[x.verdict] || ""}</span>`}</td><td data-tcell="${esc(x.key)}">${tClosed(x) ? `<span class="tstat ${(TCLOSED[x.status] || [])[1] || ""}">${(TCLOSED[x.status] || [])[0]}</span>` : triChosen(x) || '<span class="muted">—</span>'}</td></tr>`).join("");
  const summary = `<details class="dcard tblock" data-tk="_sum"${sumOpen ? " open" : ""}><summary><span class="dnum">≡</span><span class="dtitle">Finding summary</span><span class="chev" aria-hidden="true"></span></summary><div class="dbody">
    ${closed ? `<p class="muted">${closed} of ${all.length} addressed in Qodo: ${[res && `${res} resolved`, dis && `${dis} dismissed`, out && `${out} outdated`].filter(Boolean).join(", ")}.</p>` : ""}
    <div class="ttable"><table><thead><tr><th>#</th><th>Severity</th><th>Finding</th><th>Size</th><th>Recommendation</th><th>Action</th></tr></thead><tbody>${rows}</tbody></table></div></div></details>`;
  const [aa, ar] = tSum(open.filter((x) => !x.isNew)), fixes = open.filter((x) => !x.isNew && x.verdict === "fix"), [fa, fr] = tSum(fixes);
  const est = `<details class="dcard tblock" data-tk="_est"${TV.open._est ?? true ? " open" : ""}><summary><span class="dnum">±</span><span class="dtitle">Fix estimates</span><span class="chev" aria-hidden="true"></span></summary><div class="dbody"><div class="tests"><span>All open findings</span>${open.some((x) => !x.isNew) ? diffnums(aa, ar) : '<span class="muted">None open</span>'}<span class="muted">${open.some((x) => !x.isNew) ? pl1(open.filter((x) => !x.isNew).length, "finding") : ""}</span><span>Recommended findings only</span>${fixes.length ? diffnums(fa, fr) : '<span class="muted">None open</span>'}<span class="muted">${fixes.length ? pl1(fixes.length, "finding") : ""}</span></div></div></details>`;
  const promptCard = `<details class="dcard tblock" data-tk="_prompt"${TV.open._prompt ?? true ? " open" : ""}><summary><span class="dnum">&gt;_</span><span class="dtitle">Prompt for the agent</span><span class="tmeta"><span class="muted ttally">${triTally(all)}</span></span><span class="chev" aria-hidden="true"></span></summary><div class="dbody tprompt-b">${triPromptBody(all)}</div></details>`;
  const hid = TV.closed ? 0 : closed;
  return tools + summary + est + `<div class="tdiv"><span>${pl1(open.length, "open finding")}${closed ? ` · ${closed} closed${hid ? " hidden" : ""}` : ""}</span></div><div class="dlist">${all.map(triCard).join("")}</div>` + promptCard
    + (quiet.length ? `<p class="tri-none">${quiet.map((t) => `${esc(shortPr(t.pr))}: ${(t.counts || {}).reviewed === false ? "not reviewed by Qodo" : "every finding is closed"}`).join(" · ")}</p>` : "");
}
const triTally = (all) => { const open = all.filter((x) => !tClosed(x)), n = (v) => open.filter((x) => tSt(x).action === v).length, und = open.filter((x) => !tSt(x).action).length;
  return [n("resolve") && `${n("resolve")} resolve`, n("dismiss") && `${n("dismiss")} dismiss`, n("ignore") && `${n("ignore")} ignore`, und && `${und} undecided`].filter(Boolean).join(" · "); };
function triPromptBody(all) {   // the prompt, or why it can't be copied yet
  const prompt = triPrompt(all), long = all.filter(tLong);
  return `${long.length ? `<p class="tlong">Qodo accepts dismissal explanations up to ${TMAX.toLocaleString()} characters. Shorten ${long.map((x) => `#${x.n}`).join(", ")} before copying.</p>` : ""}
    ${prompt ? `<pre class="tprompt">${esc(prompt)}</pre>` : `<p class="muted">Choose an action for at least one open finding and the prompt appears here.</p>`}
    <div class="tact-b"><button class="btn pri" data-tcopy${prompt && !long.length ? "" : " disabled"}>Copy prompt</button><button class="btn" data-treset>Reset to recommendations</button></div>`;
}
function triSync(f) {   // after typing a note: the parts that depend on it, in place, so the button being pressed isn't replaced
  const all = triAll(), x = all.find((y) => y.key === f.key) || f, card = document.querySelector(`details.tcard[data-tk="${CSS.escape(f.key)}"]`);
  if (card) { const old = card.querySelector(".tmeta .tchosen"), pill = triChosen(x); if (old) old.outerHTML = pill || ""; else if (pill) card.querySelector(".tmeta").insertAdjacentHTML("beforeend", pill);
    const lg = card.querySelector(".tact .tlong"); if (lg) lg.remove(); if (tLong(x)) card.querySelector(".tact-r").insertAdjacentHTML("afterend", `<p class="tlong">The explanation is ${tWhy(x).length.toLocaleString()} characters; Qodo accepts ${TMAX.toLocaleString()}. Write a shorter one below.</p>`); }
  const cell = document.querySelector(`[data-tcell="${CSS.escape(f.key)}"]`); if (cell) cell.innerHTML = triChosen(x) || '<span class="muted">—</span>';
  const b = document.querySelector(".tprompt-b"); if (b) b.innerHTML = triPromptBody(all);
  const t = document.querySelector(".ttally"); if (t) t.textContent = triTally(all);
}
const triHeadSub = () => { const open = triAll().filter((x) => !tClosed(x)), fix = open.filter((x) => !x.isNew && x.verdict === "fix").length;
  return chip(pl1(open.length, "open finding"), "pkn") + (fix ? chip(pkDot(["warn", `${fix} to fix`]), "pkn") : ""); };
const triSave = () => store.set(TSKEY, TS);
document.addEventListener("toggle", (e) => { const d = e.target; if (d.matches && d.matches("details[data-tk]")) TV.open[d.dataset.tk] = d.open; }, true);
document.addEventListener("change", (e) => { const t = e.target; if (!t.matches) return;
  const x = (k) => triAll().find((y) => y.key === k);
  if (t.matches("[data-tact]")) { const f = x(t.dataset.tact); if (f) { tSt(f).action = t.value; triSave(); keepScroll(() => {}); } }
  else if (t.matches("[data-treason]")) { const f = x(t.dataset.treason); if (f) { tSt(f).reason = t.value; triSave(); keepScroll(() => {}); } }
  else if (t.matches("[data-tclosed]")) { TV.closed = t.checked; keepScroll(() => {}); } });
document.addEventListener("input", (e) => { const t = e.target; if (!(t.matches && t.matches("[data-tnote]"))) return;   // typing keeps its place; what depends on the note follows as you type
  const f = triAll().find((y) => y.key === t.dataset.tnote); if (f) { tSt(f).note = t.value; triSave(); triSync(f); } });
document.addEventListener("click", (e) => {
  const b = e.target.closest && e.target.closest("[data-tfilt], [data-tall], [data-tref], [data-tcopy], [data-treset]"); if (!b) return;
  const copy = (t, msg) => navigator.clipboard ? navigator.clipboard.writeText(t).then(() => toast(msg), () => toast("Couldn't copy")) : toast("Couldn't copy");
  if (b.dataset.tref !== undefined) { e.preventDefault(); e.stopPropagation(); const f = triAll().find((y) => y.key === b.dataset.tref); return f && copy(triRef(f), "Finding copied: add your question and paste it to the agent"); }
  if (b.dataset.tcopy !== undefined) return copy(triPrompt(triAll()), "Prompt copied: paste it to the coding agent");
  if (b.dataset.treset !== undefined) { triAll().forEach((x) => delete TS[x.key]); triSave(); return keepScroll(() => {}); }
  if (b.dataset.tfilt) { TV.filter = b.dataset.tfilt; return keepScroll(() => {}); }
  if (b.dataset.tall) { TV.all = b.dataset.tall === "open"; Object.keys(TV.open).filter((k) => !k.startsWith("_")).forEach((k) => delete TV.open[k]); return keepScroll(() => {}); }
}, true);
BLOCKS.builder = { label: "Execution walkthrough", what: "How the code runs: the flows from a user action or API call through the changed code (Flow), and every changed file and method with its purpose (Tree)", render: bwEmpty, prsel: true, secs: sBuilder, head: bwHead,
  after: () => { const q = document.querySelector(".bw-q"); if (q && BW.refocus) { q.focus(); q.setSelectionRange(BW.caret, BW.caret); BW.refocus = false; } } };
BLOCKS.triage = { label: "Finding review", what: "Every PR's triaged Qodo findings as one review: the summary, fix estimates, each finding with its code and an action, and one prompt for the agent", render: bTriage, prsel: true, sub: triHeadSub };
const _counts = counts;
counts = () => { PCOUNT.builder = BW.mode === "flow" ? ["flow", "flows"] : ["changed part", "changed parts"];
  return Object.assign(_counts(), { builder: BW.mode === "flow" ? bwFlows().length : bwFiles().reduce((a, f) => a + bwParts(f).length, 0), triage: TRI.filter((t) => prOn(t.pr)).reduce((a, t) => a + ((t.counts || {}).open || 0), 0) }); };

const bwFlash = (el) => { if (!el) return; el.classList.remove("bw-flash"); void el.offsetWidth; el.classList.add("bw-flash"); };
function bwGoto(uid) {   // a step in a flow, or a link, opens its method in the tree
  const f = BWF.find((x) => x.uid === uid || x.methods.some((m) => m.uid === uid)); if (!f) return;
  const m = f.methods.find((x) => x.uid === uid);
  BW.mode = "tree"; BW.q = ""; BW.hide = BW.hide.filter((r) => r !== f.role); if (m) BW.kinds = BW.kinds.filter((g) => g !== bwKind(m)); bwSave();
  BW.open[f.uid] = true; if (uid !== f.uid) BW.open[uid] = true;
  if (!prOn(f.pr)) S.pr = "all";
  SECT.builder = "bw-" + sid(f.pr); go("builder");
  const el = document.getElementById(uid); if (el) { el.scrollIntoView({ block: "center" }); bwFlash(el.querySelector("summary") || el); }
}
document.addEventListener("toggle", (e) => { const d = e.target; if (d.dataset && d.dataset.bwk) BW.open[d.dataset.bwk] = d.open;
  if (d.matches && d.matches("details.wfold, details.bw-f, details.bw-dir")) { const b = document.querySelector(".bw-all"); if (b) { const t = bwAnyOpen() ? "Collapse all" : "Expand all"; b.innerHTML = bwAllBtn(); b.title = t; b.setAttribute("aria-label", t); } } }, true);
document.addEventListener("click", (e) => { if (e.target.closest && e.target.closest("summary .bf-setb")) e.preventDefault(); });   // the State chip only shows its tooltip
document.addEventListener("input", (e) => { if (!e.target.classList || !e.target.classList.contains("bw-q")) return;
  BW.q = e.target.value; BW.caret = e.target.selectionStart ?? BW.q.length; clearTimeout(BW.t);
  BW.t = setTimeout(() => { BW.refocus = true; keepScroll(() => {}); }, 140); });   // a redraw per pause, not per key
document.addEventListener("click", (e) => {
  const b = e.target.closest && e.target.closest("[data-bw]"); if (!b) return;
  const a = b.dataset.bw, v = b.dataset.bwv;
  if (a === "mode") return keepScroll(() => { BW.mode = v; bwSave(); });
  if (a === "flat") return keepScroll(() => { BW.flat = v === "1"; bwSave(); });

  if (a === "hide") return keepScroll(() => { BW.hide = BW.hide.includes(v) ? BW.hide.filter((r) => r !== v) : BW.hide.concat(v); bwSave(); });
  if (a === "kind") return keepScroll(() => { BW.kinds = BW.kinds.includes(v) ? BW.kinds.filter((g) => g !== v) : BW.kinds.concat(v); bwSave(); });
  if (a === "all") { const on = !bwAnyOpen();   // Expand all or Collapse all, by what is open now
    if (BW.mode === "flow") { bwFlows().forEach((fl) => (WOPEN["bf-" + sid(fl.id)] = on)); if (!on) Object.keys(BW.open).forEach((k) => /^(st|fs):/.test(k) && delete BW.open[k]); }
    else { bwFiles().forEach((f) => (BW.open[f.uid] = on)); Object.keys(BW.open).forEach((k) => k.startsWith("dir:") && delete BW.open[k]); BW.dirs = on; }
    return keepScroll(() => {}); }
  if (a === "goto") { e.preventDefault(); return bwGoto(v); }   // a button in a step's summary mustn't also fold the step
  if (a === "changes") { const f = BWF.find((x) => x.uid === v); return f && go("changes", { pr: "all", file: f.pr + "|" + f.path }); }
  if (a === "step") { const j = v.lastIndexOf("|"), id = v.slice(0, j), i = v.slice(j + 1);
    const fid = "bf-" + sid(id); BW.mode = "flow"; bwSave(); WOPEN[fid] = BW.open[`st:${id}:${i}`] = true; SECT.builder = fid; go("builder");
    const el = document.getElementById(`bfs-${id}-${i}`); if (el) { el.scrollIntoView({ block: "center" }); bwFlash(el.querySelector(".bf-b")); } }
});
