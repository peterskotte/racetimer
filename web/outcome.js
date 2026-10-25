// Vurdering af én registrering – kopi af racetimer/outcome.py til browser-udgaven.
// Stillingen beregnes uden og med registreringen; forskellen fortæller, hvad der skete.
import {compute} from "./engine.js";

export const REASONS = {
  duplicate: "Allerede registreret",
  too_early: "For tidligt – tæller ikke",
  not_checked_in: "Ikke tjekket ind – kontakt en official",
  flag_zone: "Uden for målvinduet – en official vurderer",
  after_finish: "Løbet er slut",
  already_finished: "Allerede i mål",
  already_checked_in: "Allerede tjekket ind",
  already_lap: "Runden er allerede registreret",
  not_started: "Løbet er ikke startet",
  out: "Udgået",
};

const ignored = (reason, who) => ({type: "read.ignored", reason, reason_label: REASONS[reason], ...who});

export function evaluate(race, parts, reads, read, duplicate = false) {
  const p = parts.find(x => x.id === read.participant_id);
  const base = {reader: "manual", ts: read.ts};
  if (!p) return {type: "read.unknown", ...base};
  const who = {bib: p.bib ?? null, name: p.name, ...base};
  if (duplicate) return ignored("duplicate", who);
  if (["rtc", "dsq", "dns"].includes((p.status || "").toLowerCase())) return ignored("out", who);

  const now = read.ts + 0.001;
  const find = rows => rows.find(r => r.id === p.id) || {};
  const before = find(compute(race, parts, reads.filter(r => r.id !== read.id), now)[0]);
  const [afterRows, info] = compute(race, parts, reads, now);
  const after = find(afterRows);

  if (!race.started_at || read.ts < race.started_at) {
    if (after.status === "checkedin" && before.status !== "checkedin") return {type: "read.checkin", ...who};
    if (after.status === "checkedin") return ignored("already_checked_in", who);
    return ignored("not_started", who);
  }
  if (race.finished_at && read.ts > race.finished_at) return ignored("after_finish", who);
  if (after.start_ts && !before.start_ts && race.type === "timetrial") return {type: "read.started", ...who};
  if ((after.laps || 0) > (before.laps || 0) || (after.finish_ts && !before.finish_ts)) {
    const finish = ["p2p", "timetrial"].includes(race.type) || Boolean(info.continuous && after.status === "finished");
    return {type: "read.counted", lap: after.laps, finish,
            time: finish || info.continuous ? after.total_time : after.last_lap, ...who};
  }
  if (after.started_current && !before.started_current) return {type: "read.departure", ...who};
  if (after.status === "nocheckin") return ignored("not_checked_in", who);
  if ((after.flags || 0) > (before.flags || 0)) return ignored("flag_zone", who);
  if (before.current_lap_done) return ignored("already_lap", who);
  if (["finished", "winner"].includes(before.status) || before.finish_ts) return ignored("already_finished", who);
  return ignored("too_early", who);
}
