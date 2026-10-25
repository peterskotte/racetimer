// RaceTimer i browseren: race director tager tid manuelt for op til 12 løbere – ingen Pi eller RFID.
// Alt gemmes i browseren (localStorage). Løbsregler, resultatskærm, splash og hjemmeside er som på Pi'en.
import {compute, mergedConfig, RACE_TYPES, STATUS_LABELS, TEST_SPEEDS} from "./engine.js";
import {evaluate} from "./outcome.js";

const KEY = "racetimer-lite-v1", MAX_RUNNERS = 12, DOUBLE_TAP_SEC = 3;
const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
const nowS = () => Date.now() / 1000;
const hms = s => { if (s == null) return "–"; s = Math.max(0, Math.floor(s)); const p = n => String(n).padStart(2, "0");
  return `${Math.floor(s / 3600)}:${p(Math.floor(s % 3600 / 60))}:${p(s % 60)}`; };
const clock = ts => ts ? new Date(ts * 1000).toLocaleTimeString("da-DK") : "–";
const day = ts => ts ? new Date(ts * 1000).toLocaleDateString("da-DK", {day: "numeric", month: "short", year: "numeric"}) : "–";

// ------------------------------------------------------------------ data i browseren

const EMPTY = {v: 1, nextId: 1, races: [], parts: [], reads: [],
  branding: {name: "RaceTimer", logo: null, splash: "builtin:racetiming", splash_upload: null, splash_text: "", scan_banner: true, v: 1},
  sync: {url: "", key: "", interval_sec: 60, on_finish: true, final_sent: [], brand_v: null, last_ok: null, last_error: null}};
let db = load();

function load() {
  try {
    const d = JSON.parse(localStorage.getItem(KEY));
    if (d && d.v === 1) return {...structuredClone(EMPTY), ...d, branding: {...EMPTY.branding, ...d.branding}, sync: {...EMPTY.sync, ...d.sync}};
  } catch (_) { /* tom eller ødelagt – start forfra */ }
  return structuredClone(EMPTY);
}
function save() {
  try { localStorage.setItem(KEY, JSON.stringify(db)); }
  catch (e) { toast("Kunne ikke gemme i browseren: " + e.message, true); }
  broadcast();
}
const newId = () => db.nextId++;
// bed browseren om ikke at rydde data automatisk (fx ved pladsmangel)
navigator.storage?.persist?.();

const activeRace = () => db.races.find(r => r.is_active && !r.archived_at) || null;
const partsOf = rid => db.parts.filter(p => p.race_id === rid);
const readsOf = rid => db.reads.filter(r => r.race_id === rid && !r.deleted && !r.duplicate);

function standings(race, now = nowS()) {
  const [rows, info] = compute(race, partsOf(race.id), readsOf(race.id), now);
  // afslut løbet af sig selv, når reglerne siger, det er afgjort (som på Pi'en)
  if (race.status === "running" && info.phase === "ended" && !race.finished_at) {
    race.finished_at = info.resolved_at || info.end_at || now;
    race.status = "finished";
    pushEvent({type: "race.finished", race: race.name});
    save();
  }
  return [rows, info];
}

// ------------------------------------------------------------------ hændelser (scan-besked på skærmen)

let seq = 0;
const events = [];
function pushEvent(ev) {
  events.push({seq: ++seq, ts: nowS(), ...ev});
  while (events.length > 40) events.shift();
}

// ------------------------------------------------------------------ registrering af passager

function tap(pid) {
  const race = activeRace();
  if (!race) return;
  const ts = nowS();
  const recent = readsOf(race.id).find(r => r.participant_id === pid && Math.abs(r.ts - ts) < DOUBLE_TAP_SEC);
  const read = {id: newId(), race_id: race.id, participant_id: pid, ts, approved: 0, deleted: 0,
                duplicate: recent && !race.test?.no_dedup ? 1 : 0};
  db.reads.push(read);
  const ev = evaluate(race, partsOf(race.id), readsOf(race.id), read, Boolean(read.duplicate));
  pushEvent(ev);
  lastTap = {pid, ev, at: Date.now()};
  save();
  render();
  if (navigator.vibrate) navigator.vibrate(ev.type === "read.counted" || ev.type === "read.checkin" ? 30 : [60, 40, 60]);
}
let lastTap = null;

function undo() {
  const race = activeRace();
  if (!race) return;
  // den seneste registrering, der tæller (et afvist dobbelttryk tæller alligevel ikke)
  const last = db.reads.filter(r => r.race_id === race.id && !r.deleted && !r.duplicate).sort((a, b) => b.ts - a.ts)[0];
  if (!last) return toast("Intet at fortryde");
  const p = db.parts.find(x => x.id === last.participant_id);
  last.deleted = 1;
  save(); render();
  toast(`Fortrudt: ${p ? (p.bib != null ? "#" + p.bib + " " : "") + p.name : "registrering"} kl. ${clock(last.ts)}`);
}

// manuel tid (fx glemt tryk): officialens afgørelse – tæller som på Pi'en uden om minimumstiden
function manualTime(pid) {
  const race = activeRace(), p = db.parts.find(x => x.id === pid);
  if (!race?.started_at) return toast("Start løbet først", true);
  const v = prompt(`Tid for ${p.name} – løbstid fra start (t:mm:ss) eller klokkeslæt (tt:mm:ss med "kl")`, "");
  if (!v) return;
  const m = v.trim().match(/^(kl\.?\s*)?(\d{1,2}):(\d{2})(?::(\d{2}))?$/i);
  if (!m) return toast("Skriv fx 1:23:45 eller kl 14:05:30", true);
  let ts;
  if (m[1]) {
    const d = new Date(); d.setHours(+m[2], +m[3], +(m[4] || 0), 0); ts = d.getTime() / 1000;
  } else {
    ts = race.started_at + (m[4] !== undefined ? +m[2] * 3600 + +m[3] * 60 + +m[4] : +m[2] * 60 + +m[3]);
  }
  db.reads.push({id: newId(), race_id: race.id, participant_id: pid, ts, approved: 1, deleted: 0, duplicate: 0});
  save(); render();
  toast(`Tid gemt for ${p.name}: ${hms(ts - race.started_at)}`);
}

function setStatus(pid, status) {
  const p = db.parts.find(x => x.id === pid);
  p.status = status; p.status_at = status ? nowS() : null;
  save(); render();
}

// ------------------------------------------------------------------ løb

function raceAction(act) {
  const race = activeRace();
  if (!race) return;
  if (act === "start") Object.assign(race, {status: "running", started_at: nowS(), finished_at: null}), pushEvent({type: "race.started", race: race.name});
  if (act === "finish" && confirm("Afslut løbet nu?")) Object.assign(race, {status: "finished", finished_at: nowS()}), pushEvent({type: "race.finished", race: race.name});
  if (act === "resume") Object.assign(race, {status: "running", finished_at: null});
  if (act === "reset" && confirm("Nulstil løbet? Starttid og alle registreringer fjernes (kan ikke fortrydes).")) {
    Object.assign(race, {status: "planned", started_at: null, finished_at: null});
    db.reads.forEach(r => { if (r.race_id === race.id) r.deleted = 1; });
    partsOf(race.id).forEach(p => { p.status = null; p.status_at = null; });
  }
  if (act === "archive") { race.archived_at = nowS(); race.is_active = false; toast("Løbet er arkiveret – find det under Arkiv"); }
  save(); render();
}

function csv(race) {
  const [rows] = standings(race);
  const cc = Boolean(mergedConfig(race.type, race.config).canicross);
  const head = ["Placering", "Startnr", "Navn", "Køn", "Klub", ...(cc ? ["Hunde"] : []), "Status", "Omgange", "Distance km", "Tid (s)", "Sidste omgang (s)", "Bedste omgang (s)"];
  const r1 = x => x == null ? "" : Math.round(x * 10) / 10;
  const lines = [head, ...rows.map(r => [r.place ?? "", r.bib ?? "", r.name, r.sex, r.club, ...(cc ? [r.dogs.join(" & ")] : []),
    r.status_label, r.laps, r.distance_km, r1(r.total_time), r1(r.last_lap), r1(r.best_lap)])];
  const text = "﻿" + lines.map(l => l.map(v => /[;"\n]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : v).join(";")).join("\n");
  download(`resultater-${race.name}.csv`, text, "text/csv");
}

function download(name, text, type) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([text], {type}));
  a.download = name.replace(/[^\wæøåÆØÅ .-]+/g, "_");
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

// ------------------------------------------------------------------ resultatskærm (andet vindue) via BroadcastChannel

const bc = new BroadcastChannel("racetimer-lite");
bc.onmessage = e => { if (e.data?.type === "hello") broadcast(); };

function brandPublic() {
  const b = db.branding;
  const splash = b.splash === "builtin:plain" ? null : b.splash === "upload" && b.splash_upload ? b.splash_upload : "static/splash/racetiming.webp";
  return {name: b.name, logo: b.logo, splash, splash_text: b.splash_text || "", scan_banner: b.scan_banner !== false, v: b.v};
}

function livePayload() {
  const race = activeRace(), now = nowS();
  const base = {now, brand: brandPublic(), events: events.filter(e => e.ts > now - 12)};
  if (!race) return {race: null, ...base};
  const [rows, info] = standings(race, now);
  const pub = ({id, name, type, status, scheduled_start, started_at, finished_at, test}) => ({id, name, type, status, scheduled_start, started_at, finished_at, test});
  return {race: pub(race), info, rows, readers: [], ...base};
}
function broadcast() { try { bc.postMessage({type: "live", data: livePayload()}); } catch (_) { /* fx under lukning */ } }

// ------------------------------------------------------------------ hjemmeside (samme modtag.php som Pi'en)

async function imageB64(src) {
  if (!src) return null;
  const blob = await (await fetch(src)).blob();
  const data = await new Promise(res => { const fr = new FileReader(); fr.onload = () => res(fr.result); fr.readAsDataURL(blob); });
  const ext = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}[blob.type] || ".png";
  return {ext, data: data.split(",")[1]};
}

async function sendToWebsite(final = false, manual = false) {
  const s = db.sync;
  if (!s.url) { if (manual) toast("Skriv adressen til modtag.php først", true); return false; }
  const race = activeRace() && !activeRace().test ? activeRace() : null;  // testløb sendes aldrig ud
  const b = db.branding, brand = brandPublic();
  const branding = {name: b.name, splash_text: b.splash_text || "", v: b.v, splash: brand.splash ? "image" : "plain",
                    splash_choice: b.splash === "upload" ? "upload" : b.splash, logo: Boolean(b.logo), images: {}};
  if (s.brand_v !== b.v) {  // billeder kun, når udseendet er ændret (eller hjemmesiden mangler dem)
    if (b.logo) branding.images.logo = await imageB64(b.logo);
    if (brand.splash) branding.images.splash = await imageB64(brand.splash);
  }
  const payload = {event: final ? "final" : "update", sent_at: nowS(), race: null, brand: b.name, branding,
                   archived: db.races.filter(r => r.archived_at).map(r => r.id)};
  if (race) {
    const [rows, info] = standings(race);
    payload.race = {id: race.id, name: race.name, type: race.type, status: race.status, scheduled_start: race.scheduled_start,
                    started_at: race.started_at, finished_at: race.finished_at};
    payload.info = info;
    payload.results = rows.map(r => ({place: r.place, bib: r.bib, name: r.name, sex: r.sex, club: r.club, status: r.status,
      status_label: r.status_label, laps: r.laps, distance_km: r.distance_km, total_time: r.total_time, last_lap: r.last_lap,
      best_lap: r.best_lap, dogs: r.dogs}));
  }
  try {
    const res = await fetch(s.url, {method: "POST", headers: {"Content-Type": "application/json", "X-RaceTimer-Key": s.key},
                                    body: JSON.stringify(payload)});
    const out = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(out.besked || `HTTP ${res.status}`);
    s.brand_v = "brand_v" in out && out.brand_v !== b.v ? null : b.v;
    Object.assign(s, {last_ok: nowS(), last_error: null});
    save();
    if (manual) toast(final ? "Endelige resultater sendt" : "Sendt til hjemmesiden");
    return true;
  } catch (e) {
    s.last_error = e.message.includes("Failed to fetch")
      ? "Ingen forbindelse – eller hjemmesiden tillader ikke browser-udgaven (upload den nyeste modtag.php)" : e.message;
    save();
    if (manual) toast(s.last_error, true);
    return false;
  }
}

let nextSync = 0;
async function syncTick() {
  const s = db.sync, race = activeRace();
  if (!s.url) return;
  const fk = race?.status === "finished" && race.finished_at ? `${race.id}:${Math.round(race.finished_at)}` : null;
  if (s.on_finish && fk && !s.final_sent.includes(fk) && !race.test) {
    if (await sendToWebsite(true)) { s.final_sent.push(fk); save(); }
    return;
  }
  if (s.interval_sec > 0 && Date.now() / 1000 >= nextSync) {
    nextSync = nowS() + s.interval_sec;
    await sendToWebsite(false);
  }
}

// ------------------------------------------------------------------ visning

let tab = "race";
function toast(msg, err) {
  const t = $("toast"); t.textContent = msg; t.className = err ? "err" : ""; t.hidden = false;
  clearTimeout(t._h); t._h = setTimeout(() => { t.hidden = true; }, 3500);
}

function showTab(t) {
  tab = t;
  document.querySelectorAll("nav.tabs button").forEach(b => b.classList.toggle("on", b.dataset.tab === t));
  document.querySelectorAll("section.tab").forEach(s => s.hidden = s.id !== "tab-" + t);
  render();
}

function render() {
  const b = db.branding;
  $("brand").innerHTML = b.logo ? `<img src="${b.logo}" alt="${esc(b.name)}">` : `<span class="txt">${esc(b.name)}</span>`;
  document.title = b.name + " – Race director";
  if (tab === "race") renderRace();
  if (tab === "setup") renderSetup();
  if (tab === "people") renderPeople();
  if (tab === "archive") renderArchive();
  if (tab === "settings") renderSettings();
}

const OUT = ["dnf", "rtc", "dsq", "dns"];
function renderRace() {
  const race = activeRace();
  if (!race) {
    $("raceHead").innerHTML = `<p class="muted">Der er intet aktivt løb. Opret et under <b>Opsæt løb</b>.</p>`;
    $("tiles").innerHTML = ""; return;
  }
  const [rows, info] = standings(race);
  const t = nowS(), tt = ["p2p", "timetrial"].includes(race.type);
  const status = {planned: "Planlagt", running: "Kører", finished: "Afsluttet"}[race.status];
  let extra = "";
  if (info.type.startsWith("backyard") && info.phase === "running" && !info.continuous) extra = ` · Yard ${info.yard} · næste start ${hms(info.next_start - t)}`;
  if ((race.type === "timed" || info.end_mode === "duration") && info.phase === "running") extra = ` · ${hms(info.end_at - t)} tilbage`;
  if (info.winner) extra = ` · 🏆 ${esc(info.winner)}`;
  $("raceHead").innerHTML = `<div class="rh"><div><div class="rname">${esc(race.name)} ${race.test ? '<span class="pill test">🧪 TESTLØB</span>' : ""}</div>
      <div class="muted small">${status} · ${esc(RACE_TYPES[race.type].label)}${race.started_at ? " · start " + clock(race.started_at) : ""}${extra}</div></div>
    <div class="btns">
      ${race.status === "planned" ? `<button class="go" data-act="start">▶ Start nu</button>` : ""}
      ${race.status === "running" ? `<button class="danger" data-act="finish">■ Afslut</button>` : ""}
      ${race.status === "finished" ? `<button data-act="resume">Genoptag</button><button data-act="archive">🗄 Arkivér</button>` : ""}
      ${race.status !== "planned" ? `<button data-act="reset">Nulstil</button>` : ""}
      <button data-act="undo" ${readsOf(race.id).length || race.status !== "planned" ? "" : "disabled"}>↶ Fortryd sidste</button>
      <button data-act="csv">⬇ CSV</button>
    </div></div>`;
  $("raceHead").querySelectorAll("[data-act]").forEach(btn => btn.onclick = () =>
    btn.dataset.act === "undo" ? undo() : btn.dataset.act === "csv" ? csv(race) : raceAction(btn.dataset.act));

  const byId = new Map(rows.map(r => [r.id, r]));
  const parts = partsOf(race.id).sort((a, b) => (a.bib ?? 999) - (b.bib ?? 999));
  const lastRead = pid => readsOf(race.id).filter(r => r.participant_id === pid).reduce((m, r) => Math.max(m, r.ts), 0);
  $("tiles").innerHTML = parts.length ? parts.map(p => {
    const r = byId.get(p.id) || {status: "waiting", status_label: "Venter", laps: 0};
    const lr = lastRead(p.id), flash = lastTap && lastTap.pid === p.id && Date.now() - lastTap.at < 2500 ? lastTap.ev : null;
    const flashCls = flash ? (["read.counted", "read.checkin", "read.started", "read.departure"].includes(flash.type) ? "ok" : "warn") : "";
    const main = tt ? (r.total_time != null ? hms(r.total_time) : r.elapsed != null ? hms(r.elapsed) : "–") : `${r.laps} <small>omg.</small>`;
    return `<div class="tile st-${r.status} ${OUT.includes(r.status) ? "out" : ""} ${flashCls}" data-pid="${p.id}">
      <button class="tap" data-pid="${p.id}" aria-label="Registrér passage for ${esc(p.name)}">
        <span class="tbib">${p.bib ?? ""}</span><span class="tname">${esc(p.name)}</span>
        <span class="tmain num">${main}</span>
        <span class="tsub"><i class="dot"></i>${esc(r.status_label)}${r.place ? ` · nr. ${r.place}` : ""}${lr ? ` · sidst ${hms(t - lr)} siden` : ""}</span>
        ${flash ? `<span class="tflash">${esc(flash.type === "read.counted" ? (flash.finish ? "✓ I mål" : `✓ Omgang ${flash.lap}`) : flash.type === "read.checkin" ? "✓ Tjekket ind" : flash.type === "read.departure" ? "✓ Afgang" : flash.type === "read.started" ? "✓ Startet" : flash.reason_label || "")}</span>` : ""}
      </button>
      <button class="tmenu" data-menu="${p.id}" aria-label="Flere valg for ${esc(p.name)}">⋯</button>
    </div>`;
  }).join("") : `<p class="muted">Ingen deltagere endnu – tilføj dem under <b>Deltagere</b>.</p>`;
  layoutTiles(parts.length);
  $("tiles").querySelectorAll("button.tap").forEach(btn => btn.onclick = () => tap(+btn.dataset.pid));
  $("tiles").querySelectorAll("button.tmenu").forEach(btn => btn.onclick = () => openMenu(+btn.dataset.menu));
}

// Felterne fylder skærmen: få løbere → store felter, 12 løbere → 4×3 (eller 2/3 kolonner på en mobil på højkant)
const LANDSCAPE_COLS = [1, 2, 3, 2, 3, 3, 4, 4, 3, 4, 4, 4];
function layoutTiles(n) {
  const el = $("tiles");
  if (!n) { el.style.gridTemplateColumns = ""; el.style.gridAutoRows = ""; return; }
  const portrait = innerWidth < 600 || innerHeight > innerWidth * 1.15;
  const cols = portrait ? (n <= 2 ? 1 : n <= 8 ? 2 : 3) : LANDSCAPE_COLS[Math.min(n, 12) - 1];
  const rows = Math.ceil(n / cols), gap = portrait ? 8 : 12;
  const top = el.getBoundingClientRect().top + scrollY, help = ($("tapHelp")?.offsetHeight || 40) + 12 + 24;
  const th = Math.max(portrait ? 110 : 120, Math.floor((innerHeight - top - help - (rows - 1) * gap) / rows));
  const tw = Math.floor((el.clientWidth - (cols - 1) * gap) / cols);
  Object.assign(el.style, {gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))`, gridAutoRows: `minmax(${th}px, auto)`});
  el.style.setProperty("--th", th + "px");
  el.style.setProperty("--tw", tw + "px");
}
addEventListener("resize", () => { if (tab === "race") renderRace(); });

function openMenu(pid) {
  const p = db.parts.find(x => x.id === pid);
  const dlg = $("menu");
  $("menuTitle").textContent = `${p.bib != null ? "#" + p.bib + " " : ""}${p.name}`;
  $("menuBtns").innerHTML = `<button data-m="time">⏱ Indtast tid</button><button data-m="RTC">RTC (udgået)</button><button data-m="DNS">DNS (startede ikke)</button>
    <button data-m="DSQ">DSQ (diskvalificeret)</button><button data-m="clear">↺ Fjern status</button><button data-m="close">Luk</button>`;
  $("menuBtns").querySelectorAll("button").forEach(b => b.onclick = () => {
    dlg.close();
    const m = b.dataset.m;
    if (m === "time") manualTime(pid);
    else if (m === "clear") setStatus(pid, null);
    else if (m !== "close") setStatus(pid, m);
  });
  dlg.showModal();
}

// ------------------------------------------------------------------ opsæt løb

const FIELD_LABELS = {checkin_min: "Indtjekning: min. før start (0 = fra)", loop_km: "Omgangslængde (km)", interval_min: "Starter hvert (min)",
  warnings_min: "Advarsler før start (min, komma)", start_window_min: "Afgangsvindue (min)", goal_window_min: "Målvindue starter (min)",
  min_lap_min: "Min. omgangstid (min)", end_mode: "Slutter når", max_yards: "Antal omgange (cutoff)", total_h: "Samlet tid (timer)",
  distance_km: "Distance (km)", min_time_min: "Min. tid (min)", canicross: "Canicross (1–2 hunde)", record_km: "Rekord at slå (km)",
  record_label: "Rekordens navn", duration_h: "Varighed (timer)", start_mode: "Start", interval_sec: "Startinterval (sek)",
  cutoff_min: "Cutoff: maks. tid (min, 0 = ingen)"};
const SELECTS = {end_mode: [["last_man", "Sidste mand tilbage"], ["duration", "Samlet tid"], ["yards", "Fast antal omgange"]],
                 start_mode: [["interval", "Enkeltstart med interval"], ["waves", "Bølgestart"], ["chip", "Start ved første tryk"]]};

function cfgFields(type, cfg) {
  const locked = RACE_TYPES[type].locked;
  return `<div class="grid">${Object.entries(cfg).filter(([k]) => k !== "waves" && !k.startsWith("_")).map(([k, v]) => {
    const lbl = FIELD_LABELS[k] || k, dis = locked ? "disabled" : "";
    if (SELECTS[k]) return `<label>${lbl}<select name="cfg.${k}" ${dis}>${SELECTS[k].map(([o, l]) => `<option value="${o}" ${o === v ? "selected" : ""}>${l}</option>`).join("")}</select></label>`;
    if (typeof v === "boolean") return `<label class="chk"><input type="checkbox" name="cfg.${k}" ${v ? "checked" : ""} ${dis}> ${lbl}</label>`;
    if (Array.isArray(v)) return `<label>${lbl}<input name="cfg.${k}" data-list value="${v.join(", ")}" ${dis}></label>`;
    return `<label>${lbl}<input name="cfg.${k}" ${typeof v === "number" ? 'type="number" step="any"' : ""} value="${esc(v)}" ${dis}></label>`;
  }).join("")}</div>${locked ? `<p class="muted small">Officielle backyard-regler er låst. Vælg "Backyard Ultra (custom)" for at ændre dem.</p>` : ""}`;
}
function readCfg(form) {
  const cfg = {};
  form.querySelectorAll("[name^='cfg.']").forEach(el => {
    const k = el.name.slice(4);
    cfg[k] = el.type === "checkbox" ? el.checked : el.dataset.list !== undefined ? el.value.split(",").map(Number).filter(n => !isNaN(n))
      : el.type === "number" ? parseFloat(el.value) : el.value;
  });
  return cfg;
}

function renderSetup() {
  const list = db.races.filter(r => !r.archived_at).sort((a, b) => b.created_at - a.created_at);
  $("raceList").innerHTML = list.length ? list.map(r => `<div class="row-item"><div><b>${esc(r.name)}</b> ${r.is_active ? '<span class="pill">AKTIVT</span>' : ""}
      ${r.test ? '<span class="pill test">🧪</span>' : ""}<div class="muted small">${esc(RACE_TYPES[r.type].label)} · ${partsOf(r.id).length} deltagere</div></div>
      <div class="btns">${r.is_active ? "" : `<button data-act="activate" data-id="${r.id}">Gør aktivt</button>`}<button class="danger" data-act="del" data-id="${r.id}">Slet</button></div></div>`).join("")
    : `<p class="muted">Ingen løb endnu.</p>`;
  $("raceList").querySelectorAll("button").forEach(b => b.onclick = () => {
    const r = db.races.find(x => x.id === +b.dataset.id);
    if (b.dataset.act === "activate") { db.races.forEach(x => { x.is_active = x === r; }); toast(`${r.name} er nu aktivt`); }
    if (b.dataset.act === "del") {
      if (!confirm(`Slet "${r.name}" med deltagere og tider? Kan ikke fortrydes.`)) return;
      db.races = db.races.filter(x => x !== r); db.parts = db.parts.filter(p => p.race_id !== r.id); db.reads = db.reads.filter(x => x.race_id !== r.id);
    }
    save(); render();
  });
  const f = $("newRace");
  if (!f.dataset.ready) {
    f.type.innerHTML = Object.entries(RACE_TYPES).map(([k, t]) => `<option value="${k}">${esc(t.label)}</option>`).join("");
    // indtjekning er slået fra som standard (RD trykker alligevel) – undtagen i det låste, officielle backyard
    f.type.onchange = () => { $("newCfg").innerHTML = cfgFields(f.type.value, mergedConfig(f.type.value, {checkin_min: 0})); };
    f.type.onchange();
    f.test.onchange = () => { $("newTest").hidden = !f.test.checked; };
    $("newTest").innerHTML = `<label>Tid<select name="speed">${TEST_SPEEDS.map(s => `<option value="${s}" ${s === 60 ? "selected" : ""}>${s === 1 ? "Normal tid" : s + "× hurtigere"}</option>`).join("")}</select></label>
      <label class="chk"><input type="checkbox" name="no_minimum"> Ingen minimumstid</label><label class="chk"><input type="checkbox" name="no_dedup"> Intet dobbelttryk-filter</label>`;
    f.onsubmit = e => {
      e.preventDefault();
      const r = {id: newId(), name: f.name.value.trim() || "Nyt løb", type: f.type.value, config: mergedConfig(f.type.value, readCfg(f)),
                 status: "planned", scheduled_start: null, started_at: null, finished_at: null, created_at: nowS(), archived_at: null,
                 test: f.test.checked ? {speed: +f.speed.value, no_minimum: f.no_minimum.checked, no_checkin: true, no_dedup: f.no_dedup.checked} : null};
      db.races.forEach(x => { x.is_active = false; });
      r.is_active = true;
      db.races.push(r);
      save(); f.reset(); f.type.onchange(); $("newTest").hidden = true;
      toast("Løbet er oprettet – tilføj deltagere");
      showTab("people");
    };
    f.dataset.ready = 1;
  }
}

// ------------------------------------------------------------------ deltagere (op til 12)

function renderPeople() {
  const race = activeRace();
  $("peopleRace").textContent = race ? race.name : "– intet aktivt løb –";
  const ps = race ? partsOf(race.id).sort((a, b) => (a.bib ?? 999) - (b.bib ?? 999)) : [];
  const cc = race && Boolean(mergedConfig(race.type, race.config).canicross);
  $("countBox").hidden = !race;
  $("runnerCount").innerHTML = Array.from({length: MAX_RUNNERS}, (_, i) => `<option value="${i + 1}" ${i + 1 === (ps.length || 4) ? "selected" : ""}>${i + 1}</option>`).join("");
  $("setCount").onclick = () => setRunnerCount(race, +$("runnerCount").value);
  $("peopleList").innerHTML = ps.length ? `<table><thead><tr><th>Nr</th><th>Navn</th><th>Køn</th><th>Klub</th>${cc ? "<th>Hunde</th>" : ""}<th></th></tr></thead><tbody>` +
    ps.map(p => `<tr><td><input data-edit="bib" data-id="${p.id}" type="number" min="1" value="${p.bib ?? ""}" style="width:70px"></td>
      <td><input data-edit="name" data-id="${p.id}" value="${esc(p.name)}"></td><td>${esc(p.sex || "")}</td><td>${esc(p.club || "")}</td>
      ${cc ? `<td>${esc([p.dog1, p.dog2].slice(0, p.dogs || 0).filter(Boolean).join(" & "))}</td>` : ""}
      <td><button class="danger" data-del="${p.id}">Slet</button></td></tr>`).join("") + "</tbody></table>" : `<p class="muted" style="padding:12px">Ingen deltagere endnu.</p>`;
  $("peopleList").querySelectorAll("[data-edit]").forEach(inp => inp.onchange = () => {
    const p = db.parts.find(x => x.id === +inp.dataset.id);
    if (inp.dataset.edit === "name") {
      if (!inp.value.trim()) { inp.value = p.name; return toast("Navnet må ikke være tomt", true); }
      p.name = inp.value.trim();
    } else {
      const bib = inp.value.trim() ? parseInt(inp.value, 10) : null;
      if (bib != null && partsOf(p.race_id).some(x => x !== p && x.bib === bib)) { inp.value = p.bib ?? ""; return toast(`Startnummer ${bib} er allerede brugt`, true); }
      p.bib = bib;
    }
    save(); toast("Gemt");
  });
  $("peopleList").querySelectorAll("[data-del]").forEach(b => b.onclick = () => {
    if (!confirm("Slet deltageren og deres tider?")) return;
    const id = +b.dataset.del;
    db.parts = db.parts.filter(p => p.id !== id); db.reads = db.reads.filter(r => r.participant_id !== id);
    save(); render();
  });
  const f = $("addPerson");
  f.hidden = !race || ps.length >= MAX_RUNNERS;
  $("peopleFull").hidden = !race || ps.length < MAX_RUNNERS;
  $("dogFields").hidden = !cc;
  f.onsubmit = e => {
    e.preventDefault();
    if (partsOf(race.id).length >= MAX_RUNNERS) return toast(`Højst ${MAX_RUNNERS} deltagere i browser-udgaven`, true);
    const bib = f.bib.value.trim() ? parseInt(f.bib.value, 10) : null;
    if (bib != null && partsOf(race.id).some(p => p.bib === bib)) return toast(`Startnummer ${bib} er allerede brugt`, true);
    const dogs = cc ? (f.dog2.value.trim() ? 2 : f.dog1.value.trim() ? 1 : 0) : null;
    if (cc && !dogs) return toast("Canicross: skriv mindst én hunds navn", true);
    db.parts.push({id: newId(), race_id: race.id, bib, name: f.name.value.trim(), sex: f.sex.value, club: f.club.value.trim(),
                   status: null, status_at: null, dogs, dog1: cc ? f.dog1.value.trim() : null, dog2: cc ? f.dog2.value.trim() || null : null, start_offset: null});
    save(); f.reset(); f.bib.value = (bib ?? 0) + 1; f.name.focus(); render();
  };
}

// Vælg antal løbere: felter tilføjes som "Løber N" – eller de sidste fjernes (spørger, hvis de har tider)
function setRunnerCount(race, n) {
  const ps = partsOf(race.id).sort((a, b) => (a.bib ?? 999) - (b.bib ?? 999));
  if (n > ps.length) {
    let bib = Math.max(0, ...ps.map(p => p.bib || 0));
    for (let i = ps.length; i < n; i++) {
      bib++;
      db.parts.push({id: newId(), race_id: race.id, bib, name: `Løber ${bib}`, sex: "", club: "", status: null, status_at: null,
                     dogs: null, dog1: null, dog2: null, start_offset: null});
    }
  } else if (n < ps.length) {
    const gone = ps.slice(n), withTimes = gone.filter(p => readsOf(race.id).some(r => r.participant_id === p.id));
    if (!confirm(`Fjern ${gone.map(p => p.name).join(", ")}?${withTimes.length ? `\n\n${withTimes.map(p => p.name).join(", ")} har allerede tider, som også slettes.` : ""}`)) return;
    const ids = new Set(gone.map(p => p.id));
    db.parts = db.parts.filter(p => !ids.has(p.id));
    db.reads = db.reads.filter(r => !ids.has(r.participant_id));
  }
  save(); render();
  toast(`${n} ${n === 1 ? "felt" : "felter"} klar`);
}

// ------------------------------------------------------------------ arkiv

function renderArchive() {
  const list = db.races.filter(r => r.archived_at || r.status === "finished").sort((a, b) => (b.started_at || 0) - (a.started_at || 0));
  $("archiveList").innerHTML = list.length ? list.map(r => `<div class="row-item"><div><b>${esc(r.name)}</b> ${r.archived_at ? '<span class="pill">arkiveret</span>' : ""}
      <div class="muted small">${day(r.started_at || r.created_at)} · ${esc(RACE_TYPES[r.type].label)} · ${partsOf(r.id).length} deltagere</div></div>
      <div class="btns"><button data-a="csv" data-id="${r.id}">⬇ CSV</button>${r.archived_at ? `<button data-a="restore" data-id="${r.id}">↩ Gendan</button>` : ""}</div></div>`).join("")
    : `<p class="muted">Ingen afsluttede løb endnu.</p>`;
  $("archiveList").querySelectorAll("button").forEach(b => b.onclick = () => {
    const r = db.races.find(x => x.id === +b.dataset.id);
    if (b.dataset.a === "csv") csv(r);
    if (b.dataset.a === "restore") { r.archived_at = null; save(); render(); toast("Gendannet"); }
  });
}

// ------------------------------------------------------------------ indstillinger

function readImage(file, maxW) {
  // gem billedet nedskaleret som data-URL, så browserens lager ikke fyldes op
  return new Promise((res, rej) => {
    if (!/^image\/(png|jpeg|webp)$/.test(file.type)) return rej(new Error("Billedet skal være PNG, JPG eller WebP"));
    const img = new Image();
    img.onload = () => {
      const k = Math.min(1, maxW / img.width), c = document.createElement("canvas");
      c.width = Math.round(img.width * k); c.height = Math.round(img.height * k);
      c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
      res(c.toDataURL(file.type === "image/png" ? "image/png" : "image/webp", 0.85));
    };
    img.onerror = () => rej(new Error("Kunne ikke læse billedet"));
    img.src = URL.createObjectURL(file);
  });
}

function renderSettings() {
  const b = db.branding, s = db.sync, f = $("settingsForm");
  f.bname.value = b.name; f.splash_text.value = b.splash_text || ""; f.scan_banner.checked = b.scan_banner !== false;
  f.splash.value = b.splash === "upload" ? "upload" : b.splash;
  f.url.value = s.url; f.key.value = s.key; f.interval.value = String(s.interval_sec); f.on_finish.checked = s.on_finish;
  $("logoPrev").innerHTML = b.logo ? `<img src="${b.logo}" style="height:40px">` : `<span class="muted small">Intet logo – navnet vises som tekst</span>`;
  $("syncStatus").innerHTML = s.last_error ? `<span class="err-text">✗ ${esc(s.last_error)}</span>` : s.last_ok ? `✓ Sendt ${clock(s.last_ok)}` : `<span class="muted">Ikke sendt endnu</span>`;
  $("storageInfo").textContent = `${db.races.length} løb · ${db.parts.length} deltagere · ${db.reads.length} registreringer gemt i denne browser`;
}

function bindSettings() {
  const f = $("settingsForm");
  f.onsubmit = async e => {
    e.preventDefault();
    const b = db.branding;
    try {
      if (f.logo.files[0]) b.logo = await readImage(f.logo.files[0], 600);
      if (f.splash_file.files[0]) { b.splash_upload = await readImage(f.splash_file.files[0], 1920); f.splash.value = "upload"; }
    } catch (err) { return toast(err.message, true); }
    Object.assign(b, {name: f.bname.value.trim() || "RaceTimer", splash_text: f.splash_text.value.trim().slice(0, 160),
                      scan_banner: f.scan_banner.checked, splash: f.splash.value === "upload" && !b.splash_upload ? "builtin:racetiming" : f.splash.value, v: b.v + 1});
    Object.assign(db.sync, {url: f.url.value.trim(), key: f.key.value.trim(), interval_sec: +f.interval.value, on_finish: f.on_finish.checked});
    f.logo.value = ""; f.splash_file.value = "";
    save(); render(); toast("Gemt");
  };
  $("logoDel").onclick = () => { db.branding.logo = null; db.branding.v++; save(); render(); };
  $("sendNow").onclick = async () => {
    const race = activeRace();
    await sendToWebsite(Boolean(race && race.status === "finished"), true);
    render();
  };
  $("exportBtn").onclick = () => download(`racetimer-backup-${new Date().toISOString().slice(0, 10)}.json`, JSON.stringify(db), "application/json");
  $("importFile").onchange = async e => {
    const file = e.target.files[0];
    if (!file) return;
    try {
      const d = JSON.parse(await file.text());
      if (d.v !== 1 || !Array.isArray(d.races)) throw new Error("Det er ikke en RaceTimer-sikkerhedskopi");
      if (!confirm("Erstat alt i denne browser med sikkerhedskopien?")) return;
      db = {...structuredClone(EMPTY), ...d}; save(); render(); toast("Sikkerhedskopien er indlæst");
    } catch (err) { toast(err.message, true); }
    e.target.value = "";
  };
  $("wipeBtn").onclick = () => {
    if (!confirm("Slet ALLE løb, deltagere og indstillinger i denne browser? Tag en sikkerhedskopi først.")) return;
    db = structuredClone(EMPTY); save(); render(); toast("Alt er slettet");
  };
}

// ------------------------------------------------------------------ start

document.querySelectorAll("nav.tabs button").forEach(b => b.onclick = () => showTab(b.dataset.tab));
$("openScreen").onclick = () => window.open("display.html?local=1&kiosk=1", "racetimer-skaerm", "popup");
bindSettings();
showTab(activeRace() ? "race" : "setup");
setInterval(() => {
  if (tab === "race" && !document.querySelector("dialog[open]")) renderRace();
  broadcast();
}, 1000);
setInterval(() => { syncTick().catch(() => {}); }, 5000);
window.addEventListener("beforeunload", e => { if (activeRace()?.status === "running") { e.preventDefault(); e.returnValue = ""; } });
// til test i browseren
window.__lite = {get db() { return db; }, tap, undo, standings, livePayload, sendToWebsite, STATUS_LABELS};
