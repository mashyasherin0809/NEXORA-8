/* PAGE: Workflows (sidebar item "Workflows")
   Pipeline funnel and stage rules.
   Script for this page. */
function wf() {
  const F = [
    ["Index", 100],
    ["Locate", 98],
    ["Patch", 96],
    ["Guard", 91],
    ["Verify", 84],
    ["Delivered", 78],
  ];
  return (
    head("Workflows", "Where tasks drop out of the pipeline.") +
    `<div class="g21"><div class="box"><h2>Pipeline funnel</h2>${hb(F.map(([n, v]) => [n, v, v + "% of tasks"]))}</div><div class="box"><h2>Stage rules</h2><div class="li"><span>Edit before guard</span><b class="dn">not allowed</b></div><div class="li"><span>Report before verify</span><b class="dn">not allowed</b></div><div class="li"><span>Max repair attempts</span><b>${st.cfg.tries}</b></div><div class="li"><span>Diff size limit</span><b>${st.cfg.diff} lines</b></div></div></div>`
  );
}
