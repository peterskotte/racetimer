// Løbsmotor i JavaScript – en tro kopi af racetimer/engine.py til browser-udgaven.
// Rene funktioner: stillingen genberegnes altid ud fra løb, deltagere og læsninger.
// tests/engine_parity.mjs kører de samme scenarier gennem begge versioner, så reglerne ikke glider fra hinanden.

export const BACKYARD_KM = 6.7056;

export const RACE_TYPES = {
  backyard: {label: "Backyard Ultra (officiel)", locked: true,
    config: {checkin_min: 30, loop_km: BACKYARD_KM, interval_min: 60, warnings_min: [3, 2, 1], start_window_min: 3, goal_window_min: 25}},
  backyard_custom: {label: "Backyard Ultra (custom)",
    config: {checkin_min: 30, loop_km: BACKYARD_KM, interval_min: 60, warnings_min: [3, 2, 1], start_window_min: 3, goal_window_min: 25,
             min_lap_min: 10, end_mode: "last_man", max_yards: 5, total_h: 3}},
  p2p: {label: "Alm. tidtagning (A til B)", config: {checkin_min: 30, distance_km: 10.0, min_time_min: 5, canicross: false}},
  record: {label: "Rekordløb (Årets rekord)",
    config: {checkin_min: 30, loop_km: 1.0, min_lap_min: 2, record_km: 0, record_label: "Årets rekord", canicross: false}},
  timed: {label: "Tidsbaseret (6/12/24/48 t)", config: {checkin_min: 30, duration_h: 24, loop_km: 1.0, min_lap_min: 2, canicross: false}},
  timetrial: {label: "Intervalstart / enkeltstart",
    config: {checkin_min: 30, distance_km: 10.0, start_mode: "interval", interval_sec: 30, min_time_min: 5, canicross: false,
             waves: [{name: "Bølge 1", from_bib: 1, to_bib: 20, offset_sec: 0}, {name: "Bølge 2", from_bib: 21, to_bib: 40, offset_sec: 120}]}},
};

export const STATUS_LABELS = {
  waiting: "Venter", active: "Aktiv", resting: "I mål", finished: "Færdig", winner: "Vinder", dnf: "DNF", rtc: "RTC",
  dsq: "DSQ", dns: "DNS", checkedin: "Tjekket ind", nocheckin: "Ikke tjekket ind",
};

const clone = o => JSON.parse(JSON.stringify(o));
// afrunding som Pythons round(): ud fra tallets præcise værdi (toFixed), lige tilfælde mod lige ciffer
function pyRound(x, n) {
  const f = Number(x.toFixed(n));
  // præcis midt imellem (fx 0.125 → 2 decimaler): Python vælger det lige ciffer. Kun hvis decimalerne efter
  // position n er præcis "5000…" i tallets eksakte værdi – ellers giver toFixed allerede det rigtige.
  const exact = Math.abs(x).toFixed(Math.min(100, n + 60)), tail = exact.slice(exact.indexOf(".") + 1 + n);
  if (/^50*$/.test(tail)) {
    const step = 10 ** -n, low = Number((f - Math.sign(x) * step).toFixed(n));
    return Math.round(Math.abs(f) / step) % 2 ? low : f;
  }
  return f;
}
// sum() som i Python 3.12+: kompenseret (Neumaier), så kommatal lægges præcist sammen
function pySum(xs) {
  let sum = 0, c = 0;
  for (const x of xs) {
    const t = sum + x;
    c += Math.abs(sum) >= Math.abs(x) ? (sum - t) + x : (x - t) + sum;
    sum = t;
  }
  return sum + c;
}
const r3 = x => pyRound(x, 3);
const r2 = x => pyRound(x, 2);
// sortering efter en "tuple" som i Python (false < true, tal stigende, tekst efter tegnkode)
const cmpTuple = key => (a, b) => {
  const ka = key(a), kb = key(b);
  for (let i = 0; i < ka.length; i++) {
    const x = typeof ka[i] === "boolean" ? +ka[i] : ka[i], y = typeof kb[i] === "boolean" ? +kb[i] : kb[i];
    if (x < y) return -1;
    if (x > y) return 1;
  }
  return 0;
};

export function mergedConfig(type, cfg) {
  const base = clone(RACE_TYPES[type].config);
  return RACE_TYPES[type].locked ? base : Object.assign(base, cfg || {});
}

export const TEST_SPEEDS = [1, 10, 60, 120];
const SCALE_MIN = ["checkin_min", "interval_min", "start_window_min", "goal_window_min", "min_lap_min", "min_time_min"];

export function testConfig(cfg, opts) {
  cfg = clone(cfg);
  const speed = TEST_SPEEDS.includes(opts.speed) ? opts.speed : 1;
  if (speed !== 1) {
    for (const k of SCALE_MIN) if (cfg[k]) cfg[k] = cfg[k] / speed;
    for (const k of ["total_h", "duration_h", "interval_sec"]) if (cfg[k]) cfg[k] = cfg[k] / speed;
    if (cfg.warnings_min && cfg.warnings_min.length) {
      cfg._warn_labels = [...cfg.warnings_min];
      cfg.warnings_min = cfg.warnings_min.map(m => m / speed);
    }
    if (cfg.waves && cfg.waves.length) cfg.waves = cfg.waves.map(w => ({...w, offset_sec: (w.offset_sec || 0) / speed}));
  }
  if (opts.no_minimum) {
    Object.assign(cfg, {min_lap_min: 0, min_time_min: 0});
    if ("goal_window_min" in cfg) Object.assign(cfg, {goal_window_min: 0, start_window_min: 0});
  }
  if (opts.no_checkin) cfg.checkin_min = 0;
  return cfg;
}

export function effectiveConfig(race) {
  const cfg = mergedConfig(race.type, race.config);
  return race.test ? testConfig(cfg, race.test) : cfg;
}

const manual = p => (p.status || "").toLowerCase() || null;
const outBefore = (p, ts) => ["rtc", "dsq"].includes(manual(p)) && (p.status_at || 0) <= ts;

export function dogNames(p) {
  const n = p.dogs || 0;
  return [p.dog1, p.dog2].slice(0, n).filter(Boolean);
}

function row(p, kw = {}) {
  const r = {id: p.id, bib: p.bib ?? null, name: p.name, sex: p.sex || "", club: p.club || "", dogs: dogNames(p),
             laps: 0, distance_km: 0.0, total_time: null, last_lap: null, best_lap: null, status: "waiting", ...kw};
  r.status_label = STATUS_LABELS[r.status] ?? r.status;
  return r;
}

function readsByPid(reads) {
  const by = new Map();
  for (const r of [...reads].sort((a, b) => a.ts - b.ts)) {
    if (!r.participant_id) continue;
    if (!by.has(r.participant_id)) by.set(r.participant_id, []);
    by.get(r.participant_id).push(r.ts);
  }
  return by;
}

function place(rows, key) {
  rows.sort(cmpTuple(key));
  rows.forEach((r, i) => { r.place = i + 1; });
  return rows;
}

// ---------------------------------------------------------------- backyard

function computeBackyardOpen(race, cfg, parts, reads, now) {
  const mode = cfg.end_mode, start = race.started_at, loop = cfg.loop_km;
  const maxYards = mode === "yards" ? Math.max(1, Math.trunc(cfg.max_yards || 1)) : null;
  const total = mode === "duration" ? Number(cfg.total_h || 0) * 3600 : null;
  const info = {loop_km: loop, continuous: true, end_mode: mode, max_yards: maxYards, duration_sec: total};
  if (!start) {
    Object.assign(info, {phase: "before", next_start: race.scheduled_start ?? null});
    return [parts.map(p => row(p, {status: manual(p) === "dns" ? "dns" : "waiting"})), info];
  }
  const end = total ? start + total : null, stop = race.finished_at || null;
  const lims = [end, stop].filter(Boolean), limit = lims.length ? Math.min(...lims) : null;
  const timeUp = Boolean(stop) || Boolean(end && now >= end);
  const by = readsByPid(reads), ok = approvedByPid(reads);
  const rows = [];
  for (const p of parts) {
    let laps = countLaps(by.get(p.id) || [], start, limit, (cfg.min_lap_min || 0) * 60, ok.get(p.id) || new Set());
    if (maxYards) laps = laps.slice(0, maxYards);
    const splits = laps.map((b, i) => b - (i ? laps[i - 1] : start));
    const m = manual(p);
    const st = m ? m : maxYards && laps.length >= maxYards ? "finished" : timeUp ? (mode === "duration" ? "finished" : "dnf") : "active";
    rows.push(row(p, {status: st, laps: laps.length, distance_km: r3(laps.length * loop),
      total_time: laps.length ? laps[laps.length - 1] - start : null, last_lap: splits.length ? splits[splits.length - 1] : null,
      best_lap: splits.length ? Math.min(...splits) : null, last_ts: laps.length ? laps[laps.length - 1] : null}));
  }
  place(rows, r => [["dsq", "dns"].includes(r.status), -r.laps, r.last_ts || 9e18]);
  const stillRunning = rows.some(r => r.status === "active");
  const ended = timeUp || (maxYards !== null && rows.length > 0 && !stillRunning);
  const leader = rows.length && rows[0].laps ? rows[0] : null;
  Object.assign(info, {
    phase: ended ? "ended" : "running", end_at: end, remaining: end ? Math.max(0, end - now) : null,
    resolved_at: ended && !stop ? (end && now >= end ? end : now) : null,
    finishers: rows.filter(r => r.status === "finished").length, on_course: rows.filter(r => r.status === "active").length,
    total_km: r2(pySum(rows.map(r => r.distance_km))),
    leader: leader ? leader.name : null, leader_laps: leader ? leader.laps : 0, leader_time: leader ? leader.total_time : null,
    completed_yards: leader ? leader.laps : 0,
  });
  return [rows, info];
}

function computeBackyard(race, cfg, parts, reads, now) {
  if ((cfg.end_mode || "last_man") !== "last_man") return computeBackyardOpen(race, cfg, parts, reads, now);
  const start = race.started_at, I = cfg.interval_min * 60, loop = cfg.loop_km;
  const warn = cfg.warnings_min ?? [3, 2, 1];
  const info = {interval_sec: I, warnings_min: warn, loop_km: loop, warnings_labels: (cfg._warn_labels && cfg._warn_labels.length) ? cfg._warn_labels : warn};
  if (!start) {
    Object.assign(info, {phase: "before", next_start: race.scheduled_start ?? null});
    return [parts.map(p => row(p, {status: manual(p) === "dns" ? "dns" : "waiting"})), info];
  }
  // Tidsvinduer i hver runde (officielt: 0–3 min afgang, 3–25 min flagzone, 25–60 min målvindue)
  const goal = (cfg.goal_window_min ?? cfg.min_lap_min ?? 0) * 60;
  const startw = Math.min((cfg.start_window_min || 0) * 60, goal);
  const laps = new Map(), started = new Map(), flags = [];
  for (const r of [...reads].sort((a, b) => a.ts - b.ts)) {
    const pid = r.participant_id, ts = r.ts, b = Math.floor((ts - start) / I);
    if (!pid || b < 0) continue;
    const off = ts - (start + b * I);
    if (off >= goal || r.approved) {
      if (!laps.has(pid)) laps.set(pid, new Map());
      if (!laps.get(pid).has(b)) laps.get(pid).set(b, ts);
    } else if (off < startw) {
      if (!started.has(pid)) started.set(pid, new Set());
      started.get(pid).add(b);
    } else {
      flags.push({read_id: r.id ?? null, participant_id: pid, ts, yard: b + 1, minute: off / 60});
    }
  }
  const endTs = race.finished_at || now;
  const cur = Math.max(0, Math.floor((endTs - start) / I));
  let alive = parts.filter(p => manual(p) !== "dns");
  const out = new Map();
  let winner = null, winnerLaps = 0, endedAt = null, resolvedAt = null, current = new Map();
  for (let k = 0; k <= cur; k++) {
    const bs = start + k * I;
    const still = [];
    for (const p of alive) {
      if (outBefore(p, bs)) out.set(p.id, [manual(p), k]);
      else still.push(p);
    }
    alive = still;
    const finished = p => {
      const ts = laps.get(p.id)?.get(k);
      return ts !== undefined && !outBefore(p, ts) ? ts : null;
    };
    const fin = alive.filter(p => finished(p));
    const pending = alive.filter(p => !finished(p) && !outBefore(p, endTs));
    const blockOver = bs + I <= endTs;
    if (blockOver || !pending.length) {
      const finIds = new Set(fin.map(p => p.id));
      for (const p of alive) {
        if (!finIds.has(p.id)) {
          const m = manual(p);
          out.set(p.id, [["rtc", "dsq"].includes(m) ? m : "dnf", k]);
        }
      }
      alive = fin;
      if (fin.length <= 1) {
        resolvedAt = blockOver ? bs + I : endTs;
        if (fin.length === 1) {
          winner = fin[0];
          winnerLaps = k + 1;
          endedAt = laps.get(winner.id).get(k);
        } else {
          endedAt = resolvedAt;
        }
        break;
      }
    }
    if (k === cur) current = new Map(alive.map(p => [p.id, finished(p)]));
  }

  const rows = [];
  for (const p of parts) {
    const pid = p.id, pl = laps.get(pid) || new Map();
    let n, st;
    if (winner !== null && pid === winner.id) { n = winnerLaps; st = "winner"; }
    else if (out.has(pid)) { [st, n] = out.get(pid); }
    else if (current.has(pid)) {
      n = cur + (current.get(pid) ? 1 : 0);
      st = current.get(pid) ? "resting" : "active";
      if (outBefore(p, endTs)) st = manual(p);  // meldt fra i denne runde/hvilepausen → vis det med det samme
    } else { st = manual(p) || "dnf"; n = 0; }
    const times = [];
    for (let b = 0; b < n; b++) if (pl.has(b)) times.push(pl.get(b) - (start + b * I));
    rows.push(row(p, {status: st, laps: n, distance_km: r3(n * loop),
      total_time: times.length ? pySum(times) : null,
      last_lap: times.length ? times[times.length - 1] : null, best_lap: times.length ? Math.min(...times) : null,
      current_lap_done: current.has(pid) ? current.get(pid) : null, started_current: (started.get(pid) || new Set()).has(cur),
      flags: flags.filter(f => f.participant_id === pid).length}));
  }
  const group = {winner: 0, resting: 1, active: 1};
  place(rows, r => [group[r.status] ?? 2, -r.laps, r.total_time || 9e18]);
  Object.assign(info, {
    phase: endedAt ? "ended" : "running", yard: cur + 1, block_start: start + cur * I, next_start: start + (cur + 1) * I,
    runners_left: rows.filter(r => ["active", "resting", "winner"].includes(r.status)).length,
    on_course: rows.filter(r => r.status === "active").length,
    winner: winner ? winner.name : null, ended_at: endedAt, resolved_at: resolvedAt,
    completed_yards: rows.length ? Math.max(...rows.map(r => r.laps)) : 0,
    no_winner: Boolean(endedAt && !winner), flags, goal_window_min: goal / 60, start_window_min: startw / 60,
  });
  // Én løber tilbage med lige så mange runder som de andre → skal løbe én runde alene for at vinde
  const left = rows.filter(r => ["active", "resting"].includes(r.status));
  if (!endedAt && left.length === 1) {
    const others = rows.filter(r => r !== left[0]).reduce((m, r) => Math.max(m, r.laps), 0);
    if (left[0].laps <= others || left[0].status === "active")
      info.solo = {name: left[0].name, state: left[0].status === "active" ? "running" : "next"};
  }
  return [rows, info];
}

// ---------------------------------------------------------------- omgangsløb

function approvedByPid(reads) {
  // manuelle/godkendte læsninger er officialens afgørelse, så minimumstiden gælder ikke
  const by = new Map();
  for (const r of reads) {
    if (!r.approved || !r.participant_id) continue;
    if (!by.has(r.participant_id)) by.set(r.participant_id, new Set());
    by.get(r.participant_id).add(r.ts);
  }
  return by;
}

function countLaps(tss, start, end, minlap, approved) {
  const laps = [];
  let last = start;
  for (const ts of tss) {
    if (ts < start || (end && ts > end)) continue;
    if (ts - last >= minlap || (approved.has(ts) && ts > last)) { laps.push(ts); last = ts; }
  }
  return laps;
}

function lapRows(parts, reads, start, end, minlap, loop, done) {
  const by = readsByPid(reads), ok = approvedByPid(reads), rows = [];
  for (const p of parts) {
    const laps = countLaps(by.get(p.id) || [], start, end, minlap, ok.get(p.id) || new Set());
    const splits = laps.map((b, i) => b - (i ? laps[i - 1] : start));
    const m = manual(p);
    rows.push(row(p, {status: m ? m : done ? "finished" : "active", laps: laps.length, distance_km: r3(laps.length * loop),
      total_time: laps.length ? laps[laps.length - 1] - start : null, last_lap: splits.length ? splits[splits.length - 1] : null,
      best_lap: splits.length ? Math.min(...splits) : null, last_ts: laps.length ? laps[laps.length - 1] : null}));
  }
  return place(rows, r => [["dsq", "dns"].includes(r.status), -r.laps, r.last_ts || 9e18]);
}

function computeTimed(race, cfg, parts, reads, now) {
  const start = race.started_at, dur = cfg.duration_h * 3600;
  const info = {duration_sec: dur, loop_km: cfg.loop_km};
  if (!start) {
    Object.assign(info, {phase: "before", next_start: race.scheduled_start ?? null});
    return [parts.map(p => row(p)), info];
  }
  const end = start + dur, done = now >= end || Boolean(race.finished_at);
  const rows = lapRows(parts, reads, start, end, (cfg.min_lap_min || 0) * 60, cfg.loop_km, done);
  Object.assign(info, {phase: done ? "ended" : "running", end_at: end, remaining: Math.max(0, end - now),
    total_km: r2(pySum(rows.map(r => r.distance_km)))});
  return [rows, info];
}

function computeRecord(race, cfg, parts, reads, now) {
  const start = race.started_at;
  const info = {loop_km: cfg.loop_km, record_km: cfg.record_km || 0, record_label: cfg.record_label || "Årets rekord"};
  if (!start) {
    Object.assign(info, {phase: "before", next_start: race.scheduled_start ?? null, total_km: 0});
    return [parts.map(p => row(p)), info];
  }
  const done = Boolean(race.finished_at);
  const rows = lapRows(parts, reads, start, race.finished_at || null, (cfg.min_lap_min || 0) * 60, cfg.loop_km, done);
  const total = r2(pySum(rows.map(r => r.distance_km)));
  Object.assign(info, {phase: done ? "ended" : "running", total_km: total, total_laps: rows.reduce((s, r) => s + r.laps, 0),
    new_record: Boolean(info.record_km) && total > info.record_km});
  return [rows, info];
}

// ---------------------------------------------------------------- A→B og tidskørsel

function finishRows(parts, reads, starts, minimum, now) {
  const by = readsByPid(reads), ok = approvedByPid(reads), rows = [];
  for (const p of parts) {
    const ps = starts.has(p.id) ? starts.get(p.id) : null, m = manual(p);
    let fin = null;
    if (ps !== null) {
      const mine = ok.get(p.id) || new Set();
      fin = (by.get(p.id) || []).find(ts => ts >= ps + minimum || (mine.has(ts) && ts > ps)) ?? null;
    }
    const st = m === "rtc" ? "dnf" : m ? m : fin ? "finished" : ps === null || now < ps ? "waiting" : "active";
    rows.push(row(p, {status: st, start_ts: ps, finish_ts: fin, total_time: fin ? fin - ps : null,
      elapsed: ps && !fin && now >= ps ? now - ps : null, laps: fin ? 1 : 0}));
  }
  const order = {finished: 0, active: 1, waiting: 2};
  return place(rows, r => [order[r.status] ?? 3, r.total_time || 9e18, r.start_ts || 9e18, r.bib || 0]);
}

function computeP2p(race, cfg, parts, reads, now) {
  const start = race.started_at, info = {distance_km: cfg.distance_km};
  if (!start) {
    Object.assign(info, {phase: "before", next_start: race.scheduled_start ?? null});
    return [parts.map(p => row(p)), info];
  }
  const rows = finishRows(parts, reads, new Map(parts.map(p => [p.id, start])), (cfg.min_time_min || 0) * 60, now);
  Object.assign(info, {phase: race.finished_at ? "ended" : "running", elapsed: now - start,
    finished: rows.filter(r => r.status === "finished").length});
  return [rows, info];
}

export function timetrialStarts(race, cfg, parts, reads) {
  // hver løbers starttid (epoch); manuel start_offset vinder altid
  const start = race.started_at, starts = new Map();
  if (!start) return starts;
  const mode = cfg.start_mode || "interval";
  if (mode === "chip") {
    const by = readsByPid(reads);
    for (const p of parts) {
      const first = (by.get(p.id) || []).find(ts => ts >= start);
      if (first !== undefined) starts.set(p.id, first);
    }
  } else if (mode === "waves") {
    for (const p of parts) {
      for (const w of cfg.waves || []) {
        if (p.bib !== null && p.bib !== undefined && w.from_bib <= p.bib && p.bib <= w.to_bib) { starts.set(p.id, start + w.offset_sec); break; }
      }
    }
  } else {
    const ordered = [...parts].sort(cmpTuple(p => [p.bib === null || p.bib === undefined, p.bib || 0, p.id]));
    ordered.forEach((p, i) => starts.set(p.id, start + i * (cfg.interval_sec ?? 30)));
  }
  for (const p of parts) if (p.start_offset !== null && p.start_offset !== undefined) starts.set(p.id, start + p.start_offset);
  return starts;
}

function computeTimetrial(race, cfg, parts, reads, now) {
  const start = race.started_at, info = {distance_km: cfg.distance_km, start_mode: cfg.start_mode || "interval"};
  if (!start) {
    Object.assign(info, {phase: "before", next_start: race.scheduled_start ?? null});
    return [parts.map(p => row(p)), info];
  }
  const starts = timetrialStarts(race, cfg, parts, reads), minimum = (cfg.min_time_min || 0) * 60;
  // chipstart: første læsning er start – mållæsning skal derfor ligge efter minimumstiden
  if (info.start_mode === "chip") reads = reads.filter(r => r.ts !== starts.get(r.participant_id));
  const rows = finishRows(parts, reads, starts, minimum, now);
  const upcoming = rows.filter(r => r.status === "waiting" && r.start_ts).sort((a, b) => a.start_ts - b.start_ts);
  Object.assign(info, {phase: race.finished_at ? "ended" : "running", elapsed: now - start,
    next_starters: upcoming.slice(0, 5).map(r => ({bib: r.bib, name: r.name, start_ts: r.start_ts})),
    finished: rows.filter(r => r.status === "finished").length});
  return [rows, info];
}

const COMPUTE = {backyard: computeBackyard, backyard_custom: computeBackyard, timed: computeTimed, record: computeRecord,
                 p2p: computeP2p, timetrial: computeTimetrial};

export function checkinWindow(race, cfg) {
  if (race.type === "timetrial" && cfg.start_mode === "chip") return 0;
  return Number(cfg.checkin_min || 0) * 60;
}

export function checkedIn(race, cfg, reads, now) {
  const w = checkinWindow(race, cfg), ref = race.started_at || now, end = ref + (race.started_at ? 0 : 1);
  return new Set(reads.filter(r => r.participant_id && r.ts < end && (r.ts >= ref - w || r.approved)).map(r => r.participant_id));
}

export function compute(race, parts, reads, now) {
  const cfg = effectiveConfig(race), w = checkinWindow(race, cfg);
  const ok = w ? checkedIn(race, cfg, reads, now) : new Set();
  const started = Boolean(race.started_at);
  let hold = new Set();
  if (w && started) {
    // ikke tjekket ind → intet tæller (og de er ikke med i fx backyards "sidste mand"-regel)
    hold = new Set(parts.filter(p => !ok.has(p.id) && manual(p) !== "dns").map(p => p.id));
    reads = reads.filter(r => !hold.has(r.participant_id));
  }
  const keepAll = race.type === "timetrial";  // intervalstart: startrækkefølgen må ikke rykke sig
  const cparts = keepAll ? parts : parts.filter(p => !hold.has(p.id));
  let [rows, info] = COMPUTE[race.type](race, cfg, cparts, reads, now);
  if (hold.size) {
    const held = [...rows.filter(r => hold.has(r.id)), ...(keepAll ? [] : parts.filter(p => hold.has(p.id)).map(p => row(p)))];
    for (const r of held) Object.assign(r, {status: "nocheckin", status_label: STATUS_LABELS.nocheckin, laps: 0, distance_km: 0.0,
      total_time: null, last_lap: null, best_lap: null, elapsed: null, finish_ts: null});
    rows = rows.filter(r => !hold.has(r.id));
    rows.forEach((r, i) => { r.place = i + 1; });
    for (const r of held) r.place = null;
    rows = rows.concat(held.sort(cmpTuple(r => [r.bib === null, r.bib || 0, r.name])));
  }
  if (w) info.checkin = {min: w / 60, count: parts.filter(p => ok.has(p.id)).length, total: parts.length};
  if (info.phase === "before") {
    for (const r of rows) if (ok.has(r.id) && r.status === "waiting") Object.assign(r, {status: "checkedin", status_label: STATUS_LABELS.checkedin});
    rows.sort(cmpTuple(r => [r.bib === null, r.bib || 0, r.name]));
    for (const r of rows) r.place = null;
  }
  if (race.test) info.test = race.test;
  info.type = race.type;
  info.type_label = RACE_TYPES[race.type].label;
  return [rows, info];
}
