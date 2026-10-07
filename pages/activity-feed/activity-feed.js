/* PAGE: Activity Feed (sidebar item "Activity Feed")
   The list of events.
   Script for this page. */
function act() {
  const E = [
    ["✓", "Session #32 passed every gate", "2h ago"],
    ["✕", "Guard rejected a call to utils.paginate_query (does not exist)", "yesterday"],
    ["✓", "Session #31 ready for review", "yesterday"],
    ["!", "Session #30 blocked after 3 repair attempts", "2 days ago"],
    ["↻", "Baseline test run recorded for acme/etl", "2 days ago"],
    ["⚑", "Symbol index rebuilt: 1,486 functions", "3 days ago"],
  ];
  return (
    head("Activity Feed", "Everything the agent did, newest first.") +
    `<div class="box">${E.map((e) => `<div class="li"><span><b>${e[0]}</b> ${esc(e[1])}</span><span class="mut">${e[2]}</span></div>`).join("")}</div>`
  );
}
