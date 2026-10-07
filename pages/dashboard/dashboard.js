/* PAGE: Dashboard (sidebar item "Dashboard")
   Task box, headline stats, agent health, charts, recent sessions, patch-acceptance numbers.
   Script for this page. */
function dash() {
  const h = [
    ["working", 3, "var(--acc)"],
    ["idle", 2, "var(--muted)"],
    ["completed", 18, "var(--ok)"],
    ["error", 1, "var(--bad)"],
  ];
  return (
    head(
      "Dashboard",
      "Delegate a coding task to the agent, then review the diff and the evidence.",
    ) +
    `
<div class="box task" style="margin-bottom:12px"><textarea id="ti" aria-label="Describe a coding task" placeholder="Describe a bug to fix or a small feature to add"></textarea><div class="row"><button class="chip">acme/shop</button><button class="chip">main</button><button class="chip">Python 3.12</button><button class="btn pri r" data-a="run">Run agent</button></div></div>
<div class="g4">${kpi("SESSIONS", "1.3k", "3 active")}${kpi("AGENTS", "1.8k", "4 per session")}${kpi("TOKENS", "6.1B", "95% cache hit rate")}${kpi("COST", "$4,450", "3 models")}</div>
<div class="g21"><div class="box"><h2>Activity, last 52 weeks</h2>${heat()}</div><div class="box"><h2>Agent health</h2><div class="hb">${h.map((x) => `<i style="flex:${x[1]};background:${x[2]}"></i>`).join("")}</div><div class="legend" style="flex-direction:column;gap:4px">${h.map((x) => `<span><i style="background:${x[2]}"></i>${x[0]} · ${x[1]}</span>`).join("")}</div></div></div>
<div class="g21"><div class="box"><h2>Tasks resolved, last 30 days</h2>${bars(rn(30, 4, 20))}</div><div class="box"><h2>Outcomes</h2><div class="row">${donut(
      [
        ["a", 78, "var(--ok)"],
        ["b", 14, "var(--acc)"],
        ["c", 8, "var(--bad)"],
      ],
      "92%",
    )}${leg([
      ["Resolved first try", 78, "var(--ok)"],
      ["Fixed after guard rejection", 14, "var(--acc)"],
      ["Stopped and reported", 8, "var(--bad)"],
    ])}</div></div></div>
<div class="g3">${kpi("PATCH SUGGESTIONS", "74,418", "last 28 days")}${kpi("PATCHES ACCEPTED", "9,409", '<div class="bar"><i style="width:13%"></i></div>13% acceptance rate')}${kpi("AGENT CONTRIBUTION", "99%", "of code changes were agent-initiated")}</div>
<div class="g2"><div class="box"><h2>Lines of code changed</h2><div class="kpi"><strong>1.8m</strong><em>added and deleted, last 28 days · avg 8.5k deleted per day</em></div></div><div class="box"><h2>Lines added and deleted</h2>${line(rn(28, 3, 20))}</div></div>
<div class="box"><h2>Recent sessions</h2>${filt()}${sessRows(fl())}</div><p class="note">Sample data throughout. Numbers illustrate what the dashboard will report.</p>`
  );
}
