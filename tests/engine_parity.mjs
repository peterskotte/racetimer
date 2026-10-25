// Sammenlign web/engine.js med Python-motorens resultater (genereret af tests/engine_parity.py).
import {readFileSync} from "node:fs";
import {compute} from "../web/engine.js";

const cases = JSON.parse(readFileSync(process.argv[2], "utf8"));
let bad = 0;

function same(a, b, path) {
  if (typeof a === "number" && typeof b === "number") {
    // afrunding til km kan i sjældne tilfælde lande forskelligt i Python og JavaScript
    const tol = /km/.test(path) ? 0.0011 : 1e-6;
    return Math.abs(a - b) <= tol || `${path}: ${a} ≠ ${b}`;
  }
  if (a === null || b === null || typeof a !== "object" || typeof b !== "object")
    return a === b || `${path}: ${JSON.stringify(a)} ≠ ${JSON.stringify(b)}`;
  if (Array.isArray(a) !== Array.isArray(b)) return `${path}: liste ≠ objekt`;
  const keys = new Set([...Object.keys(a), ...Object.keys(b)]);
  for (const k of keys) {
    if (!(k in a) || !(k in b)) return `${path}.${k}: mangler i ${k in a ? "JavaScript" : "Python"}`;
    const r = same(a[k], b[k], `${path}.${k}`);
    if (r !== true) return r;
  }
  return true;
}

cases.forEach((c, i) => {
  const [rows, info] = compute(c.race, c.parts, c.reads, c.now);
  const r = same(c.expected, JSON.parse(JSON.stringify({rows, info})), "");
  if (r !== true) {
    bad++;
    if (bad <= 5) console.log(`✗ case ${i} (${c.race.type}${c.race.config.end_mode ? "/" + c.race.config.end_mode : ""}): ${r}`);
  }
});
console.log(bad ? `${bad} af ${cases.length} løb regnes forskelligt` : `ok – ${cases.length} løb regnes ens i Python og JavaScript`);
process.exit(bad ? 1 : 0);
