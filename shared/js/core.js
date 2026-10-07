/* Tiny helpers: DOM selector, HTML escape, seeded random */
const $ = (s) => document.querySelector(s),
  esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;");
let sd = 5;
const rnd = () => (sd = (sd * 9301 + 49297) % 233280) / 233280;
