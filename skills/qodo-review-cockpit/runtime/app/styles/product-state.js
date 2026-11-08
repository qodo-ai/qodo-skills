/* Product-only hydration of the existing durable local event contract. No provider operations. */
const PRODUCT_STATE = (() => {
  function hydrate(data, stored = null, mode = 'snapshot') {
    // Exported events seed a new reader. Existing snapshot readers own their local edits.
    const savedSnapshot = mode !== 'serve' && stored && Object.keys(stored).length > 0;
    stored = stored || {};
    const keys = new Set((data.prs || []).map((p) => p.key)), notes = new Map(), marks = new Map();
    if (savedSnapshot) return {...stored,
      notes:(stored.notes || []).filter((n) => keys.has(n.anchor?.pr)),
      verdict:Object.fromEntries(Object.entries(stored.verdict || {}).filter(([key]) => keys.has(key))),
      marks:(stored.marks || []).filter((m) => keys.has(m.pr))};
    let state = {};
    for (const event of data.events || []) {
      if (event.session && event.session !== data.session) continue;
      if (event.type === 'package_state' && event.target?.id === data.session) { state = event.state || {}; continue; }
      if (!keys.has(event.pr)) continue;
      if (event.type === 'note' && event.note_id) notes.set(event.note_id, {...notes.get(event.note_id),...event});
      if (event.type === 'mark') marks.set(JSON.stringify([event.pr,event.target,event.emoji]),event);
      if (event.type === 'finding_verdict') marks.set(JSON.stringify([event.pr,event.id || event.target?.id || event.target,'finding_verdict']),event);
    }
    const byUi = new Map([...notes.values()].map((event) => [event.ui_id || 'saved:'+event.note_id,event]));
    const local = (stored.notes || []).filter((n) => keys.has(n.anchor?.pr) && !notes.has(n.sent) && !byUi.has(n.id));
    const types = { '🚫':'blocking','❓':'question','🧹':'nit','🐛':'bug' };
    for (const event of byUi.values()) {
      const id=event.note_id;
      if (event.undo) continue;
      local.push({id:event.ui_id || 'saved:'+id, sent:id, text:event.text || '', type:event.note_type || types[event.emoji] || 'note',
        anchor:{pr:event.pr,path:event.path || null,line:event.line || null,side:'new',label:event.target?.label || event.path || event.pr}});
    }
    const filterVerdict = (v) => Object.fromEntries(Object.entries(v || {}).filter(([key]) => keys.has(key)));
    return {...stored, ...state, notes:local, verdict:filterVerdict(state.verdict || stored.verdict),
      marks:[...marks.values()].filter((e) => !e.undo && (e.type !== 'finding_verdict' || ['accept','dismiss'].includes(e.verdict)))};
  }
  return {hydrate};
})();
