/* PAGE: Change Analyzer (sidebar item "Change Analyzer")
   change-analyzer.js = page layout and report display. change-analyzer-engine.js = the checks, scoring and Markdown report.
   Script for this page. */
function reportHTML(R, s) {
  const title = s ? s.title : "pasted change",
    o = s
      ? `<div class="note">Session gates passed: ${s.gates.filter((g) => g[1] === 1).length} of ${s.gates.length}. Test results: ${s.tests.map((t) => t[0] + " " + t[2]).join("; ")}.</div>`
      : "";
  return `<div class="ban" style="color:${vc(R.verdict)}"><b>${R.verdict}</b><span>Score ${R.score}/100</span><span style="color:var(--fg)">${esc(R.summary)}</span></div>
<div class="g4">${kpi("LINES ADDED", R.add.length)}${kpi("LINES REMOVED", R.rem.length)}${kpi("FUNCTIONS TOUCHED", R.changed.length)}${kpi("COMPLEXITY CHANGE", (R.dc >= 0 ? "+" : "") + R.dc)}</div>
<div class="g21"><div class="box scroll"><h2>Findings (${R.F.length})</h2>${R.F.length ? `<table><tr><th>Severity</th><th>Rule</th><th>Details</th></tr>${R.F.map((x) => `<tr><td><span class="sv ${x.sev}">${x.sev}</span></td><td>${x.rule}</td><td>${esc(x.msg)}${x.line ? `<br><code class="mut">${esc(x.line)}</code>` : ""}</td></tr>`).join("")}</table>` : '<p class="up">No problems found.</p>'}</div>
<div class="box"><h2>Changed functions</h2>${R.changed.map((c) => `<div class="li"><span>${c[0]}</span><span class="mut">${c[1]}</span></div>`).join("") || '<p class="mut">None</p>'}<h2 style="margin-top:14px">Suggested tests</h2>${R.tests.map((t) => `<div class="li"><code>${t}</code></div>`).join("") || '<p class="mut">None</p>'}</div></div>${o}
<div class="box" style="margin-top:12px"><div class="row"><h2 style="margin:0">Report (Markdown)</h2><button class="btn r" data-a="copymd">Copy</button></div><pre class="ex" id="md" style="margin-top:10px">${esc(mdOf(R, title))}</pre></div>`;
}
function chg() {
  const t = tab("c", "Analyze code"),
    h =
      head("Change Analyzer", "Reads every change, checks it, and writes the report by itself.") +
      tabs("c", ["Analyze code", "Auto reports"]);
  if (t === "Auto reports")
    return (
      h +
      `<div class="box scroll"><table><tr><th>Session</th><th>Verdict</th><th>Score</th><th>Findings</th><th></th></tr>${S.map(
        (s) => {
          const R = analyze(s.rm.join("\n"), s.ad.join("\n"));
          return `<tr><td>${esc(s.title)}</td><td style="color:${vc(R.verdict)}">${R.verdict}</td><td>${R.score}</td><td>${R.F.length}</td><td><button class="btn" data-sid="${s.id}" data-rep="1">Open report</button></td></tr>`;
        },
      ).join(
        "",
      )}</table></div><p class="note">A report is generated for every session as soon as its patch exists. Open any session and use its Report tab.</p>`
    );
  const a = st.an;
  return (
    h +
    `<div class="g3"><div class="box"><h2>Before</h2><textarea class="code" data-an="b" aria-label="Code before">${esc(a.b)}</textarea></div><div class="box"><h2>After</h2><textarea class="code" data-an="a" aria-label="Code after">${esc(a.a)}</textarea></div><div class="box"><h2>Repo index</h2><textarea class="code" data-an="i" aria-label="Repo symbols and modules" style="min-height:150px">${esc(a.i)}</textarea><p class="note" style="margin:6px 0">Comma-separated names the repo really has. Edit it and the report updates.</p><button class="btn" data-a="sample">Reset to sample</button></div></div><div id="rep">${reportHTML(analyze(a.b, a.a, a.i), null)}</div>`
  );
}
document.addEventListener("input", (e) => {
  const k = e.target.dataset.an;
  if (!k) return;
  st.an[k] = e.target.value;
  $("#rep").innerHTML = reportHTML(analyze(st.an.b, st.an.a, st.an.i), null);
});
