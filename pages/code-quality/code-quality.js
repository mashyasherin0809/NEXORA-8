/* PAGE: Code Quality (sidebar item "Code Quality")
   Issue tiles, OWASP trend, issues list, dependencies table.
   Script for this page. */
function qual() {
  const t = tab("q", "Overview"),
    I = [
      ["Bug risk", "api/users.py", "Unchecked None before .id access"],
      ["Security", "etl/loader.py", "SQL built by string concatenation"],
      ["Performance", "billing/pricing.py", "Query inside a loop"],
      ["Anti pattern", "app/utils.py", "Mutable default argument"],
    ];
  const b =
    t === "Overview"
      ? `<div class="g21"><div class="box"><div class="g3" style="margin:0">${[
          ["Bug risks", 62],
          ["Anti patterns", 60],
          ["Style issues", 0],
          ["Security issues", 22],
          ["Performance issues", 16],
          ["Documentation issues", 0],
        ]
          .map(([n, v]) => kpi(n.toUpperCase(), v))
          .join(
            "",
          )}</div></div><div class="box"><div class="li"><span class="mut">Active issues</span><b>160</b></div><div class="li"><span class="mut">Issues prevented</span><b>41</b></div><div class="li"><span class="mut">Default branch</span><b>main</b></div><div class="li"><span class="mut">Analyzers</span><b>AST · imports · pytest · lint</b></div><div class="li"><span class="mut">Last analyzed</span><b>a day ago</b></div></div></div>
<div class="g2"><div class="box"><h2>OWASP Top 10 <span class="badge b-bad">Failing</span></h2>${line(rn(12, 18, 22))}</div><div class="box"><h2>Issue distribution by category</h2>${bars(rn(12, 60, 160), 120, "var(--acc)")}</div></div><div class="g2"><div class="box"><h2>Issues prevented by category</h2>${hb(
          [
            ["Hallucinated call", 41],
            ["Unresolved import", 23],
            ["Syntax error", 12],
          ],
        )}</div><div class="box"><h2>Code health trend</h2>${line(rn(14, 5, 25), 120, "var(--ok)")}<p class="mut">Net new issues this month: 0</p></div></div>`
      : t === "Issues"
        ? `<div class="box scroll"><table><tr><th>Type</th><th>File</th><th>Finding</th></tr>${I.map((r) => `<tr><td>${r[0]}</td><td>${r[1]}</td><td>${r[2]}</td></tr>`).join("")}</table></div>`
        : `<div class="box scroll"><table><tr><th>Package</th><th>Version</th><th>Status</th></tr>${[
            ["requests", "2.32.3", "ok"],
            ["flask", "3.0.3", "ok"],
            ["pyyaml", "5.3", "outdated, 1 advisory"],
            ["python-dateutil", "2.9.0", "ok"],
          ]
            .map(
              (r) =>
                `<tr><td>${r[0]}</td><td>${r[1]}</td><td class="${r[2] === "ok" ? "up" : "dn"}">${r[2]}</td></tr>`,
            )
            .join("")}</table></div>`;
  return (
    head("Code Quality", "acme/shop · main") + tabs("q", ["Overview", "Issues", "Dependencies"]) + b
  );
}
