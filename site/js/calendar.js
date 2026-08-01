import { initTheme } from "./ui.js";
import { DEFAULT_PROFILE, dueInfo, matchReasons } from "./logic.js";
import { soonRowInner } from "./cards.js";

const PROFILE_KEY = "grant-radar.profile.v2";
const MONTHS = ["January","February","March","April","May","June",
  "July","August","September","October","November","December"];

let items = [];
let scope = "all";
const todayIso = new Date().toISOString().slice(0, 10);
let profile = DEFAULT_PROFILE;
try { profile = JSON.parse(localStorage.getItem(PROFILE_KEY)) || DEFAULT_PROFILE; } catch {}

function render() {
  const withDue = items
    .map((i) => ({ item: i, due: dueInfo(i, todayIso) }))
    .filter((x) => x.due)
    .filter((x) => scope === "all" || matchReasons(x.item, profile).length > 0)
    .sort((a, b) => a.due.date.localeCompare(b.due.date));
  const byMonth = new Map();
  for (const x of withDue) {
    const key = x.due.date.slice(0, 7);
    if (!byMonth.has(key)) byMonth.set(key, []);
    byMonth.get(key).push(x);
  }
  document.getElementById("calendar").innerHTML = [...byMonth.entries()].map(([ym, rows]) => {
    const [y, m] = ym.split("-").map(Number);
    return `<h2 class="cal-month">${MONTHS[m - 1]} ${y}</h2>` +
      rows.map((x) => `<div class="cal-row">${soonRowInner(x.item, x.due)}</div>`).join("");
  }).join("") || `<p class="load-note">No upcoming deadlines in this view.</p>`;
}

async function boot() {
  initTheme();
  document.getElementById("cal-chips").addEventListener("click", (e) => {
    const b = e.target.closest("[data-scope]");
    if (!b) return;
    scope = b.dataset.scope;
    for (const chip of e.currentTarget.querySelectorAll(".chip"))
      chip.classList.toggle("chip--on", chip === b);
    render();
  });
  try {
    const payload = await (await fetch("notices.json")).json();
    items = payload.items || [];
    render();
  } catch {
    document.getElementById("calendar").innerHTML =
      `<div class="error-card">Couldn't load the data file.</div>`;
  }
}

boot();
