/* Pi'ens skærm: sort flade, mens skærmen sover (se screen.py). Første tryk vækker kun skærmen og trykker ikke på noget.
   Tryk og taster meldes til Pi'en (højst hvert 20. sek.), så den ved, at skærmen bruges. Gør intet uden for Pi'ens skærm. */
(function () {
  "use strict";
  var asleep = false, lastSent = 0, swallowUntil = 0;
  var ov = document.createElement("div");
  ov.id = "screenSleep";
  ov.hidden = true;
  ov.style.cssText = "position:fixed;inset:0;z-index:2147483647;background:#000;cursor:none;touch-action:none";
  document.body.appendChild(ov);

  function post(path) { return fetch(path, {method: "POST"}).catch(function () {}); }
  function show(v) { asleep = v; ov.hidden = !v; }

  function onInput(e) {
    if (asleep || Date.now() < swallowUntil) {
      e.preventDefault(); e.stopPropagation();
      if (asleep) { show(false); swallowUntil = Date.now() + 800; lastSent = Date.now(); post("/api/screen/activity"); }
      return;
    }
    if (Date.now() - lastSent > 20000) { lastSent = Date.now(); post("/api/screen/activity"); }
  }
  ["touchstart", "pointerdown", "mousedown", "keydown", "wheel"].forEach(function (t) {
    window.addEventListener(t, onInput, {capture: true, passive: false});
  });
  ["click", "touchend", "pointerup", "mouseup"].forEach(function (t) {  // klikket efter det vækkende tryk
    window.addEventListener(t, function (e) { if (Date.now() < swallowUntil) { e.preventDefault(); e.stopPropagation(); } }, {capture: true, passive: false});
  });

  function poll() {
    fetch("/api/screen", {cache: "no-store"}).then(function (r) {
      if (r.status === 403 || r.status === 404) return null;  // ikke Pi'ens skærm (eller ældre Pi) → stop
      return r.json().then(function (d) { if (!(Date.now() < swallowUntil)) show(!!d.asleep); setTimeout(poll, 1500); });
    }).catch(function () { setTimeout(poll, 3000); });
  }
  poll();
})();
