/* App shell: view registry, sidebar, drawing, click and change handlers, start-up */
const V = { dash, kan, ses, chg, act, ana, qual, rev, wf, set };
function side() {
  const t = L[st.lang];
  $("#side").innerHTML =
    `<div class="brand"><div class="mark">P</div><div><b>Patchwright</b><span>AI software engineer</span></div></div>` +
    NAV.map(
      ([k, g]) =>
        `<button class="nav" data-v="${k}" title="${t[k]}"${st.v === k ? ' aria-current="page"' : ""}><i>${g}</i><span>${t[k]}</span></button>`,
    ).join("") +
    `<div class="side-x"><div>${t.lang}</div><div class="seg">${[
      ["en", "EN"],
      ["zh", "中文"],
      ["vi", "VI"],
    ]
      .map(([k, l]) => `<button data-l="${k}" aria-pressed="${st.lang === k}">${l}</button>`)
      .join(
        "",
      )}</div><button class="btn" data-a="col">${t.col}</button><div><span class="dot"></span>Sandbox online</div></div>`;
  $("#app").classList.toggle("col", st.col);
}
function draw() {
  side();
  $("#main").innerHTML = V[st.v]();
}
document.addEventListener("click", (e) => {
  const x = e.target.closest(
    "[data-v],[data-tab],[data-sid],[data-sf],[data-l],[data-a],[data-th]",
  );
  if (!x) return;
  const d = x.dataset;
  if (d.v) {
    st.v = d.v;
    st.sid = null;
    st.exp = false;
  } else if (d.tab) {
    const [k, v] = d.tab.split("|");
    st.tab[k] = v;
  } else if (d.sid) {
    st.v = "ses";
    st.sid = +d.sid;
    st.tab.sd = d.rep ? "Report" : "Conversation";
  } else if (d.sf) st.sf = d.sf;
  else if (d.l) st.lang = d.l;
  else if (d.th) {
    d.th === "auto"
      ? document.documentElement.removeAttribute("data-theme")
      : document.documentElement.setAttribute("data-theme", d.th);
    return;
  } else if (d.a === "col") st.col = !st.col;
  else if (d.a === "refresh") sd = Math.floor(Math.random() * 9000) + 1;
  else if (d.a === "export") st.exp = !st.exp;
  else if (d.a === "back") st.sid = null;
  else if (d.a === "sample") st.an = sampleAn();
  else if (d.a === "copymd") {
    const t = $("#md").textContent;
    (navigator.clipboard ? navigator.clipboard.writeText(t) : Promise.reject()).then(
      () => {
        x.textContent = "Copied";
      },
      () => {
        x.textContent = "Copy blocked: select the text below";
      },
    );
    return;
  } else if (d.a === "run") {
    const s = gen(($("#ti").value || "").trim() || "Untitled task");
    S.unshift(s);
    st.v = "ses";
    st.sid = 33;
    st.tab.sd = "Conversation";
    setTimeout(() => {
      s.s = "ok";
      s.add = 7;
      s.del = 2;
      if (st.v === "ses" && st.sid === 33) draw();
    }, 3200);
  }
  const y = scrollY;
  draw();
  scrollTo(0, y);
});
document.addEventListener("change", (e) => {
  const t = e.target;
  if (t.dataset.f) {
    st.rv[t.dataset.f] = +t.value;
    draw();
  } else if (t.dataset.c) {
    const k = t.dataset.c;
    st.cfg[k] = t.type === "checkbox" ? t.checked : +t.value;
  }
});
draw();
