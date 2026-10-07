/* PAGE: Kanban Board (sidebar item "Kanban Board")
   The five columns (Queued, Running, In review, Done, Blocked) and their cards.
   Script for this page. */
function kan() {
  const C = [
    ["Queued", [["Rename utils.parse_date callers", "acme/etl"]]],
    ["Running", S.filter((s) => s.s === "run").map((s) => [s.title, s.repo])],
    ["In review", S.filter((s) => s.s === "ok" && s.open).map((s) => [s.title, s.repo])],
    ["Done", S.filter((s) => s.s === "ok" && !s.open).map((s) => [s.title, s.repo])],
    ["Blocked", S.filter((s) => s.s === "bad").map((s) => [s.title, s.repo])],
  ];
  return (
    head("Kanban Board", "Every task by stage.") +
    `<div class="kan">${C.map(([n, c]) => `<div><h2>${n} <span class="mut">${c.length}</span></h2>${c.map(([t, r]) => `<div class="kc">${esc(t)}<br><span class="mut">${r}</span></div>`).join("") || '<p class="mut">Nothing here.</p>'}</div>`).join("")}</div>`
  );
}
