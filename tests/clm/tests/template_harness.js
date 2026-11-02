// מריץ את הסקריפט של לוח הבקרה ב-node עם DOM מינימלי, ומחזיר JSON של ביטויים לבדיקה.
// שימוש: node template_harness.js <html> <expressions.json>
const fs = require("fs");
const html = fs.readFileSync(process.argv[2], "utf8");
const exprs = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
const code = html.split("<script>")[1].split("</script>")[0];
const cache = {};
const mk = () => ({innerHTML: "", textContent: "", value: "", dataset: {}, style: {},
  classList: {add() {}, remove() {}, toggle() {}, contains() { return false; }},
  insertAdjacentHTML() {}, addEventListener() {}, scrollIntoView() {}});
global.__L = {};
global.document = {querySelector: s => cache[s] || (cache[s] = mk()), querySelectorAll: () => [],
  addEventListener(type, fn) { (global.__L[type] = global.__L[type] || []).push(fn); }, getElementById: () => null, documentElement: {dataset: {}}};
global.localStorage = {getItem: () => null, setItem() {}};
global.window = global;
global.scrollTo = () => {};
global.matchMedia = () => ({matches: false});
global.innerWidth = 1200;
const out = eval(code + "\n;(function(){const r={};for (const [k, x] of Object.entries(exprs)) { r[k] = eval(x); } return r;})()");
process.stdout.write(JSON.stringify(out));
