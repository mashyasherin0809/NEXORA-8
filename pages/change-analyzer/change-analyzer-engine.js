/* PAGE: Change Analyzer (sidebar item "Change Analyzer")
   change-analyzer.js = page layout and report display. change-analyzer-engine.js = the checks, scoring and Markdown report.
   Engine: finds problems in a change, scores it, writes the report. */
const STD = new Set(
  "os sys re json math logging datetime typing collections itertools functools pathlib dataclasses unittest pytest time random uuid hashlib subprocess abc enum csv io copy".split(
    " ",
  ),
);
const BI = new Set(
  "print len range int str float list dict set tuple max min sum abs round sorted enumerate zip map filter any all isinstance open super type bool bytes repr id iter next reversed getattr setattr hasattr format input divmod pow".split(
    " ",
  ),
);
const KW = new Set(
  "if while for return elif and or not in is lambda yield await assert with except def class".split(
    " ",
  ),
);
const IDX0 =
  "apply_discount,checkout,paginate,parse_iso,parse_date,list_users,User,Cart,db,session,billing,billing.pricing,api.utils";
const SB = `def apply_discount(price, pct):
    return price - price * pct / 100

def checkout(cart):
    total = sum(i.price for i in cart)
    return apply_discount(total, cart.pct)`;
const SA = `import dateutil
from billing.helpers import round_money

def apply_discount(price, pct, cap=100):
    pct = max(0, min(pct, cap))
    result = price - price * pct / 100
    return round_money(result)

def checkout(cart):
    try:
        total = sum(i.price for i in cart)
    except:
        total = 0
    return apply_discount(total, cart.pct)`;
const sampleAn = () => ({ b: SB, a: SA, i: IDX0 });
st.an = sampleAn();
const lev = (a, b) => {
  const d = Array.from({ length: a.length + 1 }, (_, i) => [i, ...Array(b.length).fill(0)]);
  for (let j = 1; j <= b.length; j++) d[0][j] = j;
  for (let i = 1; i <= a.length; i++)
    for (let j = 1; j <= b.length; j++)
      d[i][j] = Math.min(
        d[i - 1][j] + 1,
        d[i][j - 1] + 1,
        d[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1),
      );
  return d[a.length][b.length];
};
const fns = (s) => {
  const m = {};
  for (const x of s.matchAll(/^\s*def\s+(\w+)\s*\(([^)]*)\)/gm))
    m[x[1]] = x[2]
      .split(",")
      .map((p) => p.trim())
      .filter(Boolean);
  return m;
};
const imps = (s) => {
  const mods = [],
    names = [];
  for (const x of s.matchAll(/^\s*from\s+([\w.]+)\s+import\s+([\w, ]+)/gm)) {
    mods.push(x[1]);
    x[2].split(",").forEach((n) => names.push(n.trim()));
  }
  for (const x of s.matchAll(/^\s*import\s+([\w., ]+)/gm))
    x[1].split(",").forEach((n) => {
      n = n.trim();
      mods.push(n);
      names.push(n.split(".")[0]);
    });
  return { mods, names };
};
const cplx = (s) => (s.match(/\b(if|elif|for|while|and|or|except)\b/g) || []).length;
const callsOf = (s) => {
  const o = new Set();
  for (const l of s.split("\n")) {
    if (/^\s*(def|class)\s/.test(l)) continue;
    for (const x of l.matchAll(/([A-Za-z_][\w.]*)\s*\(/g)) {
      if (!KW.has(x[1]) && l.slice(x.index - 1, x.index) !== ".") o.add(x[1]);
    }
  }
  return o;
};
const ld = (b, a) => {
  const c = {};
  b.split("\n").forEach((l) => {
    l = l.trimEnd();
    if (l.trim()) c[l] = (c[l] || 0) + 1;
  });
  const add = [];
  a.split("\n").forEach((l) => {
    l = l.trimEnd();
    if (!l.trim()) return;
    if (c[l] > 0) c[l]--;
    else add.push(l);
  });
  const rem = [];
  for (const k in c) for (let i = 0; i < c[k]; i++) rem.push(k);
  return { add, rem };
};
const SEV = { high: 25, med: 10, low: 3 };
const PAT = [
  [
    /\beval\(|\bexec\(/,
    "high",
    "Dynamic code execution",
    "eval/exec runs arbitrary code. Use ast.literal_eval or a safe parser.",
  ],
  [
    /except\s*:/,
    "med",
    "Bare except",
    "Catches every error, including KeyboardInterrupt. Catch specific exceptions.",
  ],
  [
    /shell\s*=\s*True/,
    "high",
    "Shell injection risk",
    "Pass a list of arguments and drop shell=True.",
  ],
  [
    /(execute|query)\(.*(\+|%|\.format|f["'])/,
    "high",
    "SQL built from strings",
    "Use parameterized queries.",
  ],
  [
    /def\s+\w+\(.*=\s*(\[\]|\{\})/,
    "med",
    "Mutable default argument",
    "Use None and create the object inside the function.",
  ],
  [
    /(password|secret|token)\s*=\s*["'][^"']+["']/i,
    "high",
    "Hardcoded secret",
    "Move it to an environment variable.",
  ],
  [/\bprint\(/, "low", "Debug print", "Use logging instead."],
  [/#\s*(TODO|FIXME)/, "low", "Unfinished work", "Resolve or track the TODO."],
];
function analyze(B, A, idxStr = IDX0) {
  const idx = new Set(
      idxStr
        .split(",")
        .map((x) => x.trim())
        .filter(Boolean),
    ),
    { add, rem } = ld(B, A),
    fb = fns(B),
    fa = fns(A),
    ia = imps(A),
    ib = imps(B),
    F = [],
    ca = callsOf(A),
    cb = callsOf(B);
  const f = (sev, rule, line, msg) => F.push({ sev, rule, line: (line || "").trim(), msg });
  for (const m of ia.mods)
    if (!ib.mods.includes(m) && !idx.has(m) && !STD.has(m.split(".")[0]))
      f(
        "high",
        "Unresolved import",
        "import " + m,
        `Module "${m}" is not in the repo index or the standard library. Add it to the index if it exists, or remove the import.`,
      );
  const known = new Set([...idx, ...BI, ...ia.names, ...Object.keys(fa), ...Object.keys(fb)]);
  for (const c of ca)
    if (!cb.has(c)) {
      const r = c.split(".")[0];
      if (!known.has(r) && !known.has(c) && r !== "self" && r !== "cls") {
        const near = [...known]
          .filter((k) => lev(k, c) <= 3)
          .sort((x, y) => lev(x, c) - lev(y, c))[0];
        f(
          "high",
          "Unknown call",
          c + "(...)",
          `"${c}" is not defined in the repo, the imports or the builtins.` +
            (near ? ` Closest real name: ${near}.` : ""),
        );
      }
    }
  for (const n in fb)
    if (!(n in fa))
      f(
        ca.has(n) ? "high" : "med",
        "Function removed",
        "def " + n,
        ca.has(n)
          ? `"${n}" was removed but is still called.`
          : `"${n}" was removed. Check its callers in other files.`,
      );
  for (const n in fa)
    if (n in fb && fb[n].join() !== fa[n].join()) {
      const ok =
        fa[n].length >= fb[n].length && fa[n].slice(fb[n].length).every((p) => p.includes("="));
      f(
        ok ? "low" : "med",
        "Signature changed",
        `def ${n}(${fa[n].join(", ")})`,
        `Parameters went from (${fb[n].join(", ")}) to (${fa[n].join(", ")}). ` +
          (ok
            ? "New parameters have defaults, so existing callers still work."
            : "Existing callers may break."),
      );
    }
  add.forEach((l) => PAT.forEach(([re, s, r, m]) => re.test(l) && f(s, r, l, m)));
  const dc = cplx(A) - cplx(B);
  if (dc >= 4)
    f(
      "med",
      "Complexity jump",
      "+" + dc + " branches",
      "Many new branches. Consider splitting the function and testing each path.",
    );
  if (add.length + rem.length > st.cfg.diff)
    f(
      "med",
      "Diff too large",
      add.length + rem.length + " lines",
      `Over the ${st.cfg.diff}-line limit set in Settings.`,
    );
  const bl = {};
  let cu = null;
  A.split("\n").forEach((l) => {
    const m = l.match(/^\s*def\s+(\w+)/);
    if (m) cu = m[1];
    if (cu) (bl[cu] = bl[cu] || []).push(l.trimEnd());
  });
  const as = new Set(add),
    changed = Object.keys(bl)
      .filter((n) => bl[n].some((l) => l.trim() && as.has(l)))
      .map((n) => [n, n in fb ? "modified" : "new"]);
  const score = Math.max(0, 100 - F.reduce((s, x) => s + SEV[x.sev], 0)),
    hi = F.filter((x) => x.sev === "high").length;
  const verdict = hi ? "Block" : score < 85 ? "Needs review" : "Safe to merge",
    cnt = (k) => F.filter((x) => x.sev === k).length;
  const tests = changed
    .map(
      ([n, k]) => `test_${n}_${k === "new" ? "basic_behaviour" : "still_handles_existing_callers"}`,
    )
    .concat(
      F.some((x) => x.rule === "Bare except") ? ["test_error_paths_raise_specific_exceptions"] : [],
    );
  const summary = `${changed.length} function(s) touched${changed.length ? " (" + changed.map((c) => c[0]).join(", ") + ")" : ""}, +${add.length} / -${rem.length} lines, complexity ${dc >= 0 ? "+" : ""}${dc}. Findings: ${cnt("high")} high, ${cnt("med")} medium, ${cnt("low")} low. Verdict: ${verdict}.`;
  return { add, rem, F, changed, dc, score, verdict, tests, summary };
}
const vc = (v) =>
  v === "Block" ? "var(--bad)" : v === "Needs review" ? "var(--warn)" : "var(--ok)";
function mdOf(R, title) {
  return `# Change report: ${title}\n\n**Verdict:** ${R.verdict} (score ${R.score}/100)\n\n${R.summary}\n\n## Findings\n${R.F.map((x) => `- [${x.sev.toUpperCase()}] ${x.rule}: ${x.msg}${x.line ? " (\`" + x.line + "\`)" : ""}`).join("\n") || "- None"}\n\n## Changed functions\n${R.changed.map((c) => `- ${c[0]} (${c[1]})`).join("\n") || "- None"}\n\n## Suggested tests\n${R.tests.map((t) => "- " + t).join("\n") || "- None"}\n`;
}
