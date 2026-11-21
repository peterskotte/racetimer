// Demoløb i browseren: et færdigt testløb af en valgfri løbstype med tilfældige løbere (højst 12) – og evt.
// simulerede løbere, så passagerne registreres af sig selv. Samme idé som racetimer/demo.py på Pi'en.
import {calloutSec, chipStart, effectiveConfig, mergedConfig, RACE_TYPES, timetrialStarts} from "./engine.js";

const FIRST_F = ["Anna", "Mette", "Louise", "Camilla", "Sofie", "Ida", "Maria", "Line", "Julie", "Emma", "Karen", "Signe",
  "Laura", "Freja", "Rikke", "Helle", "Pernille", "Trine", "Marie", "Cecilie", "Nanna", "Astrid", "Maja", "Clara"];
const FIRST_M = ["Peter", "Jens", "Lars", "Michael", "Søren", "Thomas", "Rasmus", "Mads", "Anders", "Morten", "Jesper",
  "Kasper", "Martin", "Niels", "Christian", "Henrik", "Frederik", "Mikkel", "Jonas", "Emil", "Ole", "Bo", "Jakob", "Magnus"];
const LAST = ["Jensen", "Nielsen", "Hansen", "Pedersen", "Andersen", "Christensen", "Larsen", "Sørensen", "Rasmussen",
  "Jørgensen", "Petersen", "Madsen", "Kristensen", "Olsen", "Thomsen", "Poulsen", "Møller", "Lund", "Holm", "Bach",
  "Skov", "Dahl", "Kjær", "Frost", "Krogh", "Østergaard"];
const CLUBS = ["Rebild Trail", "Skørping IF", "Støvring Løbeklub", "Hobro IK", "Rold Skov Runners", "Arden Løbeklub",
  "Hadsund Trail", "Team Himmerland"];
const DOGS = ["Bella", "Luna", "Max", "Molly", "Charlie", "Rocky", "Freja", "Balder", "Loke", "Sif", "Kaj", "Nala", "Odin", "Kira"];

// Opsætninger pr. løbstype: kort nok til at kunne følges på få minutter i hurtig tid
export const PRESETS = {
  backyard: {name: "Backyard Ultra", speed: 60, n: 8, about: "Ny runde hvert minut (en time i virkeligheden). Løberne falder fra, til der er én vinder.", config: {}},
  backyard_custom: {name: "Backyard custom · 6 timer", speed: 60, n: 8, about: "Omgange i træk fra start. Flest omgange på 6 timer (her 6 min) vinder.",
    config: {end_mode: "duration", total_h: 6, min_lap_min: 10, checkin_min: 0}},
  p2p: {name: "A til B · 5 km", speed: 10, n: 10, about: "Fælles start, alle løber 5 km. Tryk, når løberen er i mål.",
    config: {distance_km: 5, min_time_min: 12, checkin_min: 0}},
  record: {name: "Rekordløb", speed: 10, n: 10, about: "1 km-omgange, så længe løberne vil. Fælles kilometer mod årets rekord. Afslut løbet selv.",
    config: {loop_km: 1, min_lap_min: 2, record_km: 150, checkin_min: 0}},
  timed: {name: "3-timersløb", speed: 60, n: 10, about: "Flest omgange på 3 timer (her 3 min) på en 1 km-omgang.",
    config: {duration_h: 3, loop_km: 1, min_lap_min: 2, checkin_min: 0}},
  timetrial: {name: "Enkeltstart · 5 km", speed: 10, n: 10, about: "En løber hvert 30. sek. (her hvert 3. sek.). Tiden måles fra hver løbers egen start.",
    config: {distance_km: 5, start_mode: "interval", interval_sec: 30, min_time_min: 10, checkin_min: 0}},
};
export const CANICROSS_TYPES = ["p2p", "record", "timed", "timetrial"];
export const MAX_DEMO = 12;

// tilfældighed med frø (samme løb giver samme forløb – også hvis siden genindlæses)
export function rng(seed) {
  let a = seed >>> 0;
  const next = () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  const r = {random: next, uniform: (lo, hi) => lo + (hi - lo) * next(), int: (lo, hi) => lo + Math.floor(next() * (hi - lo + 1)),
    choice: xs => xs[Math.floor(next() * xs.length)],
    gauss: (mu, sd) => mu + sd * Math.sqrt(-2 * Math.log(1 - next())) * Math.cos(2 * Math.PI * next())};
  return r;
}

export function makePeople(n, r, canicross = false) {
  const used = new Set(), out = [], year = new Date().getFullYear();
  for (let i = 0; i < n; i++) {
    let sex, name;
    for (let k = 0; k < 50; k++) {
      sex = r.random() < 0.5 ? "Kvinde" : "Mand";
      name = `${r.choice(sex === "Kvinde" ? FIRST_F : FIRST_M)} ${r.choice(LAST)}`;
      if (!used.has(name)) break;
    }
    used.add(name);
    const p = {bib: i + 1, name, sex, club: r.random() < 0.7 ? r.choice(CLUBS) : "", birth_year: year - r.int(16, 68),
               dogs: null, dog1: null, dog2: null};
    if (canicross) {
      p.dogs = r.random() < 0.15 ? 2 : 1;
      const d1 = r.choice(DOGS);
      let d2 = r.choice(DOGS);
      while (d2 === d1) d2 = r.choice(DOGS);
      Object.assign(p, {dog1: d1, dog2: p.dogs === 2 ? d2 : null});
    }
    out.push(p);
  }
  return out;
}

/** Nyt demoløb (ikke startet) med deltagere. newId giver id'er fra browserens database. */
export function createDemo(type, {n, speed, sim = false, canicross = false, newId, now}) {
  const pre = PRESETS[type];
  if (!pre) throw new Error("Ukendt løbstype");
  n = Math.max(1, Math.min(MAX_DEMO, Math.round(n || pre.n)));
  const cfg = mergedConfig(type, {...pre.config, ...(canicross && CANICROSS_TYPES.includes(type) ? {canicross: true} : {})});
  const race = {id: newId(), name: `🎲 Demo: ${pre.name}${cfg.canicross ? " · canicross" : ""}`, type, config: cfg, status: "planned",
    scheduled_start: null, started_at: null, finished_at: null, created_at: now, archived_at: null,
    test: {speed: [1, 10, 60, 120].includes(speed) ? speed : pre.speed, no_minimum: false, no_checkin: true, no_dedup: true, demo: true, sim: Boolean(sim)}};
  const r = rng(race.id * 7919 + Math.floor(now));
  const parts = makePeople(n, r, Boolean(cfg.canicross)).map(p => ({id: newId(), race_id: race.id, ...p, status: null, status_at: null, start_offset: null}));
  return {race, parts};
}

// ------------------------------------------------------------------ simulerede løbere

const runner = r => ({pace: Math.min(560, Math.max(220, r.gauss(345, 55))), jitter: r.uniform(0.02, 0.07),
  dns: r.random() < 0.03, dnf: r.random() < 0.06, stamina: r.uniform(0.35, 1)});
const lap = (x, km, r, fatigue = 1) => km * x.pace * fatigue * (1 + r.gauss(0, x.jitter));

/** Alle simulerede passager: [[ts, pid], …] sorteret. Samme regler som motoren (start, interval, backyard-timer, callout). */
export function plan(race, parts, seed = 0) {
  const start = race.started_at;
  if (!start) return [];
  const cfg = effectiveConfig(race), speed = Math.max(1, race.test?.speed || 1), type = race.type, out = [];
  const scan = Boolean(calloutSec(type, cfg) || chipStart(type, cfg) || (type === "timetrial" && cfg.start_mode === "chip"));
  const tt = type === "timetrial" && !scan ? timetrialStarts(race, cfg, parts, []) : {};
  const racers = parts.filter(p => !p.status).sort((a, b) => a.id - b.id);
  if (type.startsWith("backyard") && (cfg.end_mode || "last_man") === "last_man") return planBackyard(race, cfg, racers, seed, speed);
  for (const p of racers) {
    const r = rng(seed * 1000003 + p.id), x = runner(r);
    if (x.dns) continue;
    let base = type === "timetrial" && !scan ? (tt[p.id] ?? start) : start;
    if (p.start_offset != null) base = start + p.start_offset;
    let own = base;
    if (scan) {
      const s = base + r.uniform(3, 150) / speed;
      out.push([s, p.id]);
      own = s + calloutSec(type, cfg);
    }
    let t = own;
    if (type === "p2p" || type === "timetrial") {
      if (!x.dnf) out.push([t + lap(x, cfg.distance_km, r) / speed, p.id]);
      continue;
    }
    const minlap = (cfg.min_lap_min || 0) * 60, loop = cfg.loop_km;
    let end, maxlaps = 1e6;
    if (type === "timed") end = own + cfg.duration_h * 3600;
    else if (type === "record") end = own + r.uniform(25, 150) * 60 / speed;
    else {
      end = own + (Number(cfg.total_h) || 48 / speed) * 3600;
      if (cfg.end_mode === "yards") maxlaps = Math.max(1, cfg.max_yards || 1);
    }
    if (x.dnf && type !== "record") end = own + (end - own) * x.stamina;
    for (let n = 0; n < maxlaps && n < 5000; n++) {
      const dt = Math.max(minlap + 1 / speed, lap(x, loop, r, 1 + 0.25 * n * loop / 50) / speed);
      if (t + dt > end) break;
      t += dt;
      out.push([t, p.id]);
    }
  }
  return out.sort((a, b) => a[0] - b[0]);
}

function planBackyard(race, cfg, racers, seed, speed) {
  const start = race.started_at, I = cfg.interval_min * 60, goal = (cfg.goal_window_min ?? cfg.min_lap_min ?? 0) * 60;
  const startw = Math.min((cfg.start_window_min || 0) * 60, goal), realI = I * speed, r0 = rng(seed * 7 + 1);
  const yards = new Map(racers.map(p => [p.id, Math.min(13, Math.floor(-Math.log(1 - r0.random()) * 4) + 1)]));
  if (racers.length) {  // den bedste løber én runde mere end nummer to (solo-runden), så der altid er én vinder
    const ranked = [...racers].sort((a, b) => yards.get(b.id) - yards.get(a.id));
    const second = ranked.length > 1 ? yards.get(ranked[1].id) : 0;
    yards.set(ranked[0].id, second + 1);
    for (const p of ranked.slice(1)) yards.set(p.id, Math.min(yards.get(p.id), second));
  }
  const out = [];
  for (const p of racers) {
    const r = rng(seed * 1000003 + p.id), x = runner(r);
    for (let k = 0; k < yards.get(p.id); k++) {
      const bs = start + k * I;
      if (startw) out.push([bs + r.uniform(0.05, 0.9) * startw, p.id]);
      const lo = goal / I * realI + 60, hi = realI - 90;
      out.push([bs + Math.min(hi, Math.max(lo, lap(x, cfg.loop_km, r, 1 + 0.02 * k))) / speed, p.id]);
    }
  }
  return out.sort((a, b) => a[0] - b[0]);
}

export const presetList = () => Object.entries(PRESETS).map(([type, p]) => ({type, label: RACE_TYPES[type].label, ...p,
  canicross: CANICROSS_TYPES.includes(type)}));
