/* PAGE: Analytics (sidebar item "Analytics")
   Heatmap, 30-day chart and the four tabs (Cost, Token, Productivity, Workflow Intelligence).
   Script for this page. */
function ana() {
  const t = tab("an", "Cost Analytics"),
    M = [
      ["opus-class", 1.6],
      ["sonnet-class", 2.5],
      ["haiku-class", 0.35],
    ],
    W = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  const b = {
    "Cost Analytics": `<div class="g21"><div class="box"><h2>Daily cost trend</h2>${line(rn(30, 60, 240))}</div><div class="box"><h2>Cost by model</h2>${hb(M.map(([n, v]) => [n, v, "$" + (v * 1000).toFixed(0)]))}</div></div><div class="box"><h2>Cost by weekday</h2>${hb(W.map((d) => [d, rn(1, 200, 900)[0], ""]))}</div>`,
    "Token Analytics": `<div class="g2"><div class="box"><h2>Tokens by stage</h2>${hb([
      ["Locate", 38, "38%"],
      ["Patch", 31, "31%"],
      ["Verify", 19, "19%"],
      ["Index", 12, "12%"],
    ])}</div><div class="box"><h2>Cache hit rate</h2>${line(rn(20, 80, 98))}</div></div>`,
    "Productivity Analytics": `<div class="g2"><div class="box"><h2>Resolve rate by week</h2>${line(rn(12, 60, 80))}</div><div class="box"><h2>Average diff size</h2>${bars(rn(12, 9, 22))}</div></div>`,
    "Workflow Intelligence": `<div class="g2"><div class="box"><h2>Repair attempts needed</h2>${hb([
      ["0 retries", 78, "78%"],
      ["1 retry", 14, "14%"],
      ["2 retries", 5, "5%"],
      ["3 retries (blocked)", 3, "3%"],
    ])}</div><div class="box"><h2>Rejection reasons</h2>${hb([
      ["Hallucinated call", 41],
      ["Unresolved import", 23],
      ["Syntax error", 12],
      ["Regression found", 9],
    ])}</div></div>`,
  }[t];
  return (
    head("Analytics", "Real-time monitoring and analytics for agent sessions.") +
    `<div class="g4">${kpi("TOTAL SESSIONS", "1.3k", "3 active")}${kpi("TOTAL AGENTS", "1.8k")}${kpi("TOTAL TOKENS", "6.1B", "95% cache hit rate")}${kpi("TOTAL EVENTS", "74.1k", "~56 per session")}</div><div class="g21"><div class="box"><h2>Event activity, last 52 weeks</h2>${heat()}</div><div class="box"><h2>Last 30 days</h2>${bars(rn(30, 2, 18))}<p class="mut" style="margin:6px 0 0">Peak day 10.2k events</p></div></div>` +
    tabs("an", [
      "Cost Analytics",
      "Token Analytics",
      "Productivity Analytics",
      "Workflow Intelligence",
    ]) +
    b
  );
}
