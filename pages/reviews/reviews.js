/* PAGE: Reviews (sidebar item "Reviews")
   Filters, review KPIs, severity donut and radar.
   Script for this page. */
function rev() {
  const f = st.rv,
    m = f.repo * f.team * f.range,
    n = (x) => Math.round(x * m),
    t = tab("r", "Summary");
  const b =
    t === "Summary"
      ? `<div class="g4">${kpi("MERGED PULL REQUESTS", n(29))}${kpi("ACTIVE USERS", f.team === 1 ? 2 : 1)}${kpi("MEDIAN TIME TO LAST COMMIT", (31.8 * (f.range === 1 ? 1 : 1.4)).toFixed(1) + " min")}${kpi("REVIEWER TIME SAVED", (23.4 * m).toFixed(1) + " h")}</div><div class="g3"><div class="box"><h2>Agent review comments</h2><div class="row" style="justify-content:space-around"><div class="kpi"><small>POSTED</small><strong>${n(250)}</strong></div><div class="kpi"><small>ACCEPTANCE RATE</small><strong>56.8%</strong></div></div></div><div class="box"><h2>Comments by severity</h2><div class="row">${donut(
          [
            ["Minor", 45, "var(--ok)"],
            ["Major", 35, "var(--acc)"],
            ["Critical", 20, "var(--bad)"],
          ],
          "250",
        )}${leg([
          ["Minor", 45, "var(--ok)"],
          ["Major", 35, "var(--acc)"],
          ["Critical", 20, "var(--bad)"],
        ])}</div></div><div class="box"><h2>Severity distribution</h2>${radar()}</div></div><div class="box"><h2>Average comments per pull request</h2><div class="row" style="justify-content:space-around"><div class="kpi"><small>BY AGENT</small><strong>10.9</strong></div><div class="kpi"><small>BY HUMAN REVIEWERS</small><strong>1</strong></div></div></div>`
      : t === "Quality Metrics"
        ? `<div class="g2"><div class="box"><h2>Acceptance rate by week</h2>${line(rn(12, 45, 65))}</div><div class="box"><h2>Comments by category</h2>${hb(
            [
              ["Hallucinated API", 40],
              ["Missing test", 28],
              ["Edge case", 19],
              ["Style", 9],
            ],
          )}</div></div>`
        : `<div class="g2"><div class="box"><h2>Time to last commit, by week</h2>${bars(rn(12, 20, 45))}</div><div class="box"><h2>Reviewer time saved, by week</h2>${line(rn(12, 10, 30), 120, "var(--ok)")}</div></div>`;
  const sel = (k, a) =>
    `<select data-f="${k}" aria-label="${k}">${a.map(([l, v]) => `<option value="${v}"${f[k] == v ? " selected" : ""}>${l}</option>`).join("")}</select>`;
  return (
    head("Reviews", "How the agent's patches fare in review.") +
    tabs("r", ["Summary", "Quality Metrics", "Time Metrics"]) +
    `<div class="row" style="margin-bottom:12px">Repository ${sel("repo", [
      ["All", 1],
      ["acme/shop", 0.5],
      ["acme/api", 0.3],
    ])} Team ${sel("team", [
      ["All", 1],
      ["Platform", 0.6],
    ])} Range ${sel("range", [
      ["Last 30 days", 1],
      ["Last 7 days", 0.3],
      ["Last 90 days", 2.5],
    ])}</div>` +
    b
  );
}
