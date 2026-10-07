/* App shell: view registry, sidebar, drawing, click and change handlers, start-up */
const V = { dash, kan, ses, chg, act, ana, qual, rev, wf, set };
function side() {
  const t = L[st.lang];
  $("#side").innerHTML =
    `<div class="brand"><div class="mark">N</div><div><b>NEXORA-8</b><span>AI Software Engineer</span></div></div>` +
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
    const taskText = ($("#ti") ? $("#ti").value : "").trim() || "Fix negative total in apply_discount()";
    const s = gen(taskText);
    S.unshift(s);
    st.v = "ses";
    st.sid = s.id;
    st.tab.sd = "Conversation";
    draw();

    // Call live NEXORA-8 Backend API
    fetch("/api/run-task?async=true", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task: taskText, repo_path: "" })
    })
      .then(res => res.json())
      .then(data => {
        if (data.session_id) {
          const evtSource = new EventSource(`/api/sessions/${data.session_id}/stream`);
          evtSource.addEventListener("agent_event", (ev) => {
            try {
              const eventData = JSON.parse(ev.data);
              s.log.push(`[${eventData.agent_name}] ${eventData.message}`);
              if (st.v === "ses" && st.sid === s.id) draw();
            } catch (err) {}
          });
          evtSource.addEventListener("session_state", (ev) => {
            try {
              const state = JSON.parse(ev.data);
              if (state.status === "success") {
                s.s = "ok";
                s.add = 6;
                s.del = 2;
                evtSource.close();
              } else if (state.status === "failed" || state.status === "rolled_back") {
                s.s = "bad";
                evtSource.close();
              }
              if (st.v === "ses" && st.sid === s.id) draw();
            } catch (err) {}
          });
        }
      })
      .catch(() => {
        // Fallback demo timer if offline
        setTimeout(() => {
          s.s = "ok";
          s.add = 7;
          s.del = 2;
          if (st.v === "ses" && st.sid === s.id) draw();
        }, 3200);
      });
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
