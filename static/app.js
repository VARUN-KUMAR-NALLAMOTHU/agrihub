const $ = (sel, root = document) => root.querySelector(sel);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const show = (v, unit = "") => (v === null || v === undefined ? "n/a" : `${esc(v)}${unit}`);
const calm = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// Tiny, safe markdown: **bold**, *italic*, and bullet lists (input is escaped first).
function md(text) {
  const inline = (s) => s.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/\*(.+?)\*/g, "<em>$1</em>");
  let html = "", inList = false;
  for (const raw of esc(text).split("\n")) {
    const line = raw.trim();
    const item = line.match(/^[*\-•]\s+(.*)$/);
    if (item) {
      if (!inList) { html += "<ul>"; inList = true; }
      html += `<li>${inline(item[1])}</li>`;
    } else {
      if (inList) { html += "</ul>"; inList = false; }
      if (line) html += `<p>${inline(line)}</p>`;
    }
  }
  return html + (inList ? "</ul>" : "");
}

function weatherHtml(w) {
  if (!w) return "";
  if (w.error) return `<p class="muted">Weather is unavailable: ${esc(w.error)}</p>`;
  return `<div class="wx">
      <div class="wx-temp">${show(w.temperature_c, "°")}</div>
      <div class="wx-meta"><strong>${show(w.condition)}</strong><span>${esc(w.location)}</span></div>
    </div>
    <dl class="facts">
      <div><dt>Feels like</dt><dd>${show(w.feels_like_c, " °C")}</dd></div>
      <div><dt>Humidity</dt><dd>${show(w.humidity, "%")}</dd></div>
      <div><dt>Wind</dt><dd>${show(w.wind_kmh, " km/h")}</dd></div>
      <div><dt>Rain chance</dt><dd>${show(w.rain_chance, "%")}</dd></div>
    </dl>
    ${w.source ? `<p class="muted">Source: ${esc(w.source)}</p>` : ""}`;
}

// ---------- Weather check ----------
$("#weather-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const box = $("#weather-result");
  const btn = e.submitter;
  btn.disabled = true;
  box.innerHTML = '<p class="muted">Checking the weather…</p>';
  try {
    const res = await fetch(`/api/weather?city=${encodeURIComponent(new FormData(e.target).get("city"))}`);
    box.innerHTML = weatherHtml(await res.json());
  } catch {
    box.innerHTML = '<p class="muted">Could not reach the server. Check your connection and try again.</p>';
  }
  btn.disabled = false;
});

// ---------- Recommendation ----------
const recForm = $("#rec-form");
const resultBox = $("#result");

function resultHtml(data) {
  const r = data.recommendation;
  const notes = r.weather_notes.length
    ? `<h3>Weather today</h3><ul class="plain">${r.weather_notes.map((n) => `<li>${esc(n)}</li>`).join("")}</ul>` : "";
  const alts = !r.suitable && r.alternatives.length
    ? `<h3>Crops that suit ${esc(r.soil.toLowerCase())} soil better</h3>
       <div class="chips">${r.alternatives.map((c) => `<button type="button" class="chip" data-crop="${esc(c)}">${esc(c)}</button>`).join("")}</div>` : "";
  return `<div class="verdict ${r.suitable ? "" : "care"}">
      <h2>${esc(r.crop)} on ${esc(r.soil.toLowerCase())} soil</h2>
      <p>${esc(r.verdict)}</p>
    </div>
    <dl class="facts">
      <div><dt>Season</dt><dd>${esc(r.season)}</dd></div>
      <div><dt>Water</dt><dd>${esc(r.water)}</dd></div>
      <div><dt>Sowing</dt><dd>${esc(r.sowing)}</dd></div>
      <div><dt>Fertilizer</dt><dd>${esc(r.fertilizer)}</dd></div>
    </dl>
    <h3>Field practices</h3>
    <ul class="plain">${r.practices.map((p) => `<li>${esc(p)}</li>`).join("")}</ul>
    ${notes}${alts}
    ${data.weather ? `<h3>Current conditions</h3>${weatherHtml(data.weather)}` : ""}`;
}

recForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = e.submitter || $("button[type=submit]", recForm);
  btn.disabled = true;
  resultBox.innerHTML = '<p class="muted">Preparing your advice…</p>';
  try {
    const res = await fetch("/api/recommend", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(Object.fromEntries(new FormData(recForm))),
    });
    const data = await res.json();
    resultBox.innerHTML = data.error ? `<p>${esc(data.error)}</p>` : resultHtml(data);
    if (window.innerWidth < 900) resultBox.scrollIntoView({ behavior: calm ? "smooth" : "auto", block: "start" });
  } catch {
    resultBox.innerHTML = "<p>Could not reach the server. Check your connection and try again.</p>";
  }
  btn.disabled = false;
});

function fillAndRun({ soil, crop, city }) {
  const radio = recForm.querySelector(`input[name=soil][value="${soil}"]`);
  if (radio) radio.checked = true;
  recForm.crop.value = crop || "";
  recForm.city.value = city || "";
  recForm.requestSubmit();
}
resultBox.addEventListener("click", (e) => {
  const chip = e.target.closest("[data-crop]");
  if (chip) { recForm.crop.value = chip.dataset.crop; recForm.requestSubmit(); }
});
document.querySelectorAll(".recent [data-soil]").forEach((b) => b.addEventListener("click", () => fillAndRun(b.dataset)));

// ---------- AgriBot ----------
const log = $("#chat-log");
const chatForm = $("#chat-form");
const chatInput = $("#chat-input");

function addMsg(text, who, pending = false) {
  const d = document.createElement("div");
  d.className = `msg ${who}${pending ? " pending" : ""}`;
  if (who === "bot" && !pending) d.innerHTML = md(text); else d.textContent = text;
  log.appendChild(d);
  log.scrollTop = log.scrollHeight;
  return d;
}
log.querySelectorAll(".msg.bot").forEach((m) => { m.innerHTML = md(m.textContent); });
log.scrollTop = log.scrollHeight;

chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = chatInput.value.trim();
  if (!text) return;
  chatInput.value = "";
  const btn = e.submitter || $("button", chatForm);
  btn.disabled = true;
  addMsg(text, "user");
  const pending = addMsg("AgriBot is thinking…", "bot", true);
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });
    const data = await res.json();
    pending.classList.remove("pending");
    pending.innerHTML = md(data.reply || data.error || "AgriBot sent no answer. Try asking again.");
  } catch {
    pending.classList.remove("pending");
    pending.textContent = "Could not reach the server. Check your connection and try again.";
  }
  log.scrollTop = log.scrollHeight;
  btn.disabled = false;
  chatInput.focus();
});
document.querySelectorAll(".chips [data-q]").forEach((c) => c.addEventListener("click", () => {
  chatInput.value = c.dataset.q;
  chatForm.requestSubmit();
}));
