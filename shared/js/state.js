/* Global UI state: current view, tabs, filters, settings */
const st = {
  v: "dash",
  lang: "en",
  col: false,
  tab: {},
  sid: null,
  sf: "all",
  st: "tabs",
  exp: false,
  cfg: { ast: true, imp: true, test: true, lint: true, tries: 3, diff: 60 },
  rv: { repo: 1, team: 1, range: 1 },
};
