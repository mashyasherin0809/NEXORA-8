/* PAGE: Settings (sidebar item "Settings")
   Safeguard switches, limits and the theme buttons.
   Script for this page. */
function set() {
  const c = st.cfg,
    sw = (k, l) =>
      `<div class="sw"><label for="c_${k}">${l}</label><input type="checkbox" id="c_${k}" data-c="${k}"${c[k] ? " checked" : ""}></div>`;
  return (
    head("Settings", "Safeguards and display options.") +
    `<div class="g2"><div class="box"><h2>Safeguards</h2>${sw("ast", "Symbol check (AST index)")}${sw("imp", "Import resolution check")}${sw("test", "Run full test suite")}${sw("lint", "Linter pass")}<div class="sw"><label for="c_tries">Max repair attempts</label><input type="number" id="c_tries" data-c="tries" min="1" max="10" value="${c.tries}" style="width:70px"></div><div class="sw"><label for="c_diff">Diff size limit (lines)</label><input type="number" id="c_diff" data-c="diff" min="5" max="500" value="${c.diff}" style="width:80px"></div></div><div class="box"><h2>Display</h2><div class="sw"><span>Theme</span><div class="seg" style="width:200px"><button data-th="auto">System</button><button data-th="dark">Dark</button><button data-th="light">Light</button></div></div><p class="note">Language is set from the sidebar.</p></div></div>`
  );
}
