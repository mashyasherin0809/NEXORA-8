/* Shared UI pieces: charts (bar, line, donut, heatmap, radar), KPI cards, tabs, headers, session rows */
const ic = (s) =>
  s === "ok"
    ? '<span class="ic ok">✓</span>'
    : s === "bad"
      ? '<span class="ic bad">!</span>'
      : '<span class="ic run">…</span>';
const rn = (n, a = 3, b = 20) => Array.from({ length: n }, () => Math.round(a + rnd() * (b - a)));
const bars = (v, h = 120, c = "var(--acc)") => {
  const w = 560,
    bw = w / v.length,
    m = Math.max(...v) || 1;
  return (
    `<svg viewBox="0 0 ${w} ${h}" width="100%" role="img" aria-label="Bar chart">` +
    v
      .map(
        (n, i) =>
          `<rect x="${i * bw + 2}" y="${h - (n / m) * (h - 4)}" width="${bw - 4}" height="${(n / m) * (h - 4)}" rx="2" fill="${c}" opacity="${0.45 + (n / m) * 0.5}"/>`,
      )
      .join("") +
    "</svg>"
  );
};
const line = (v, h = 120, c = "var(--acc)") => {
  const w = 560,
    m = Math.max(...v) || 1,
    p = v.map((n, i) => [10 + (i * (w - 20)) / (v.length - 1), h - 8 - (n / m) * (h - 20)]);
  return `<svg viewBox="0 0 ${w} ${h}" width="100%" role="img" aria-label="Trend line"><polygon points="10,${h - 8} ${p.map((x) => x.join(",")).join(" ")} ${w - 10},${h - 8}" fill="${c}" opacity=".12"/><polyline fill="none" stroke="${c}" stroke-width="2.5" points="${p.map((x) => x.join(",")).join(" ")}"/></svg>`;
};
const donut = (d, t) => {
  const r = 54,
    c = 2 * Math.PI * r;
  let o = 0;
  return (
    `<svg viewBox="0 0 140 140" width="140" role="img" aria-label="Donut chart"><g transform="rotate(-90 70 70)" fill="none" stroke-width="18">` +
    d
      .map(([n, p, col]) => {
        const s = `<circle cx="70" cy="70" r="${r}" stroke="${col}" stroke-dasharray="${(c * p) / 100} ${c}" stroke-dashoffset="${(-c * o) / 100}"/>`;
        o += p;
        return s;
      })
      .join("") +
    `</g><text x="70" y="76" text-anchor="middle" fill="var(--fg)" font-size="19">${t}</text></svg>`
  );
};
const leg = (d) =>
  `<div class="legend" style="flex-direction:column;gap:6px;margin:0">${d.map(([n, p, c]) => `<span><i style="background:${c}"></i>${n} ${p}%</span>`).join("")}</div>`;
const hb = (a) =>
  a
    .map(
      ([n, v, t]) =>
        `<div>${n} <span class="mut">· ${t || v}</span></div><div class="bar"><i style="width:${(v / Math.max(...a.map((x) => x[1]))) * 100}%"></i></div>`,
    )
    .join("");
const heat = () => {
  let s = `<svg viewBox="0 0 640 96" width="100%" role="img" aria-label="Activity heatmap, last 52 weeks">`;
  for (let x = 0; x < 52; x++)
    for (let y = 0; y < 7; y++) {
      const o = rnd();
      s += `<rect x="${x * 12}" y="${y * 13}" width="10" height="10" rx="2" fill="var(--acc)" opacity="${o < 0.3 ? 0.08 : 0.15 + o * 0.8}"/>`;
    }
  return s + "</svg>";
};
const radar = () => {
  const P = (a, r) => [70 + r * Math.cos(a), 72 + r * Math.sin(a)],
    A = [-Math.PI / 2, Math.PI / 6, (5 * Math.PI) / 6],
    poly = (r) => r.map((v, i) => P(A[i], v * 52).join(",")).join(" ");
  return (
    `<svg viewBox="0 0 140 140" width="170" role="img" aria-label="Severity radar">` +
    [1, 0.66, 0.33]
      .map((k) => `<polygon points="${poly([k, k, k])}" fill="none" stroke="var(--line)"/>`)
      .join("") +
    `<polygon points="${poly([0.3, 0.7, 0.9])}" fill="var(--acc)" opacity=".35" stroke="var(--acc)"/><polygon points="${poly([0.2, 0.35, 0.5])}" fill="var(--ok)" opacity=".35" stroke="var(--ok)"/><text x="70" y="10" text-anchor="middle" font-size="9" fill="var(--muted)">Critical</text><text x="122" y="118" font-size="9" fill="var(--muted)" text-anchor="end">Minor</text><text x="18" y="118" font-size="9" fill="var(--muted)">Major</text></svg>`
  );
};
const kpi = (a, b, c) =>
  `<div class="box kpi"><small>${a}</small><strong>${b}</strong><em>${c || ""}</em></div>`;
const tabs = (k, items) => {
  const t = st.tab[k] || items[0];
  return `<div class="tabs" role="tablist">${items.map((i) => `<button class="tab" role="tab" aria-selected="${i === t}" data-tab="${k}|${i}">${i}</button>`).join("")}</div>`;
};
const tab = (k, d) => st.tab[k] || d;
const head = (t, s, x = "") =>
  `<div class="head"><div><h1>${t}</h1><p class="sub">${s}</p></div>${x}<button class="btn" data-a="refresh">↻ Refresh</button><button class="btn" data-a="export">Export</button></div>${
    st.exp
      ? `<pre class="ex">${esc(
          JSON.stringify(
            S.map(({ id, title, repo, s, add, del, cost }) => ({
              id,
              title,
              repo,
              status: s,
              add,
              del,
              cost,
            })),
            null,
            2,
          ),
        )}</pre>`
      : ""
  }`;
const sessRows = (l) =>
  l
    .map(
      (s) =>
        `<button class="sess" data-sid="${s.id}">${ic(s.s)}<div class="t"><b>${esc(s.title)}</b><span>${s.repo}#${s.id} · ${s.when} · ${s.s === "ok" ? "Ready for review" : s.s === "bad" ? "Blocked, needs a human" : "Running"}</span></div><span class="pm"><span class="up">+${s.add}</span> <span class="dn">−${s.del}</span></span></button>`,
    )
    .join("");
const filt = () => {
  const o = S.filter((s) => s.open).length,
    c = S.length - o + 15;
  return `<div class="row" style="margin-bottom:6px"><button class="chip" data-sf="all" aria-pressed="${st.sf === "all"}">All</button><button class="chip" data-sf="open">Open ${o}</button><button class="chip" data-sf="closed">Closed ${c}</button></div>`;
};
const fl = () => S.filter((s) => st.sf === "all" || (st.sf === "open") === s.open);
