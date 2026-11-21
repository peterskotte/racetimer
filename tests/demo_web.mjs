// Demoløb i browser-udgaven (web/demo.js): hver løbstype "løbes" færdig og regnes af browserens løbsmotor.
// Kør: node tests/demo_web.mjs
import assert from "node:assert/strict";
import {createDemo, plan, presetList} from "../web/demo.js";
import {compute} from "../web/engine.js";

let id = 1;
const newId = () => id++, T0 = 1800000000;
function run(type, extra = {}, opts = {}) {
  const {race, parts} = createDemo(type, {newId, now: T0, sim: true, ...opts});
  Object.assign(race.config, extra);
  Object.assign(race, {status: "running", started_at: T0});
  const end = T0 + 40 * 60;
  const reads = plan(race, parts, race.id).filter(([ts]) => ts <= end).map(([ts, pid], i) => ({id: i + 1, participant_id: pid, ts, approved: 0}));
  const [rows, info] = compute(race, parts, reads, end);
  return {race, parts, rows, info, reads};
}

for (const p of presetList()) {
  const {race, parts, rows} = run(p.type, {}, {canicross: p.canicross});
  assert.ok(race.test.demo && race.test.no_dedup && parts.length === p.n && parts.length <= 12, p.type);
  assert.equal(new Set(parts.map(x => x.name)).size, parts.length);
  if (p.canicross) assert.ok(parts.every(x => x.dog1));
  assert.ok(rows.some(r => r.laps > 0 || r.status === "finished"), p.type);
}
const by = run("backyard");
assert.equal(by.info.phase, "ended");
assert.equal(by.rows.filter(r => r.status === "winner").length, 1);
for (const extra of [{chip_start: true}, {callout: true, callout_sec: 15}]) {
  const r = run("p2p", extra);
  assert.ok(r.rows.filter(x => x.status === "finished").length >= 8, JSON.stringify(extra));
}
assert.deepEqual(plan(run("timed").race, run("timed").parts, 1).length > 0, true);
assert.throws(() => createDemo("nope", {newId, now: T0}));
console.log("ok – demoløb i browser-udgaven");
