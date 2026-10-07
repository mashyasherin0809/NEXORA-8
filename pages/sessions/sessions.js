/* PAGE: Sessions (sidebar item "Sessions")
   Session list, session detail tabs (Agents, Conversation, Timeline, Report). Sample sessions are in sessions-data.js.
   Script for this page. */
function ses() {
  const s = S.find((x) => x.id === st.sid);
  if (!s)
    return (
      head("Sessions", "Every task the agent has worked on.") +
      `<div class="box">${filt()}${sessRows(fl())}</div>`
    );
  const run = s.s === "run",
    t = tab("sd", "Conversation"),
    nl = (a) => a.map((l, i) => `<span data-n="${i + 1}">${esc(l)}</span>`).join("");
  const body = t.startsWith("Agents")
    ? `<div class="box"><h2>Agents</h2>${AG.map((a) => `<div class="li"><span><b>${a[0]}</b><br><span class="mut">${a[1]}</span></span><span class="${a[2] === "completed" ? "up" : a[2] === "working" ? "" : "mut"}">${a[2]}</span></div>`).join("")}</div>`
    : t === "Report"
      ? reportHTML(analyze(s.rm.join("\n"), s.ad.join("\n")), s)
      : t === "Timeline"
        ? `<div class="box"><h2>Timeline</h2>${s.log.map((l, i) => `<div class="li"><span>${esc(l)}</span><span class="mut">+${i * 38 + 4}s</span></div>`).join("")}</div>`
        : `<div class="g2"><div class="box"><h2>Messages <span class="mut">${s.log.length * 3}</span></h2>${(run ? s.log.slice(0, 2) : s.log).map((l) => `<div class="li"><span><small class="mut">Agent</small><br>${esc(l)}</span></div>`).join("")}${run ? '<div class="li"><span class="mut">Working…</span></div>' : ""}</div><div class="box"><h2>Verification gates</h2>${run ? '<p class="mut">Gates run after the patch is written.</p>' : s.gates.map(([n, v]) => `<div class="gate"><span>${esc(n)}</span><span class="${v === 1 ? "up" : v === 0 ? "dn" : "mut"}">${v === 1 ? "✓ pass" : v === 0 ? "✕ fail" : "skipped"}</span></div>`).join("")}</div></div>
<div class="box"><h2>Patch · ${s.file}</h2><div class="blk rm"><header><span>REMOVED</span><span>${s.rm.length} lines</span></header><pre>${nl(s.rm)}</pre></div><div class="blk ad"><header><span>ADDED</span><span>${s.ad.length} lines</span></header><pre>${nl(s.ad)}</pre></div>${run ? "" : `<div class="scroll"><table><tr><th>Test</th><th>Before</th><th>After</th></tr>${s.tests.map(([n, a, b]) => `<tr><td>${esc(n)}</td><td class="${a === "pass" ? "up" : "dn"}">${a}</td><td class="${b === "pass" ? "up" : b === "fail" ? "dn" : "mut"}">${b}</td></tr>`).join("")}</table></div>`}</div>`;
  return (
    `<button class="btn" data-a="back" style="margin-bottom:10px">← All sessions</button>` +
    head(
      esc(s.title) +
        `<span class="badge ${run ? "b-run" : s.s === "ok" ? "b-ok" : "b-bad"}">${run ? "Running" : s.s === "ok" ? "Ready for review" : "Blocked"}</span>`,
      `${s.repo}#${s.id} · ${s.model} · $${s.cost.toFixed(2)}`,
    ) +
    tabs("sd", ["Agents (4)", "Conversation", "Timeline", "Report"]) +
    `<div class="row" style="margin-bottom:10px"><select aria-label="Agent"><option>Main Agent</option><option>Locator</option><option>Patcher</option><option>Verifier</option></select><span class="chip">${s.log.length * 3} messages</span></div>` +
    body
  );
}
