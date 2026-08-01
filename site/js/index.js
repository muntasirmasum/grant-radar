import { initTheme, fmtDateLong, esc } from "./ui.js";
import {
  DEFAULT_PROFILE, applyChip, chipCounts, closingSoon, dueInfo,
  searchFilter, weekLabel, weekMonday,
} from "./logic.js";
import { renderCard, renderSoonRow } from "./cards.js";

const PROFILE_KEY = "grant-radar.profile.v2";
const SAVED_KEY = "grant-radar.saved.v1";
const WEEKS_PER_PAGE = 4;

const state = {
  items: [],
  chip: "all",
  query: "",
  weeksShown: WEEKS_PER_PAGE,
  expanded: new Set(),
  todayIso: new Date().toISOString().slice(0, 10),
  profile: loadJSON(PROFILE_KEY) || DEFAULT_PROFILE,
  savedSet: new Set(loadJSON(SAVED_KEY) || []),
};

function loadJSON(key) {
  try { return JSON.parse(localStorage.getItem(key)); } catch { return null; }
}

function save(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

const CHIP_LABELS = [["all", "All"], ["foryou", "For you"], ["opps", "Opportunities"],
  ["nosi", "NOSIs"], ["career", "Career K/F"], ["policy", "Policy"], ["saved", "♡ Saved"]];

function visibleItems() {
  return searchFilter(applyChip(state.items, state.chip, state.profile, state.savedSet), state.query);
}

function renderChips() {
  const counts = chipCounts(searchFilter(state.items, state.query), state.profile, state.savedSet);
  document.getElementById("chips").innerHTML = CHIP_LABELS.map(([id, label]) =>
    `<button class="chip${state.chip === id ? " chip--on" : ""}" data-chip="${id}">
      ${label} <span class="n">${counts[id]}</span></button>`).join("")
    + `<button class="chip" data-edit-profile>Edit profile</button>`;
}

function renderSoon() {
  const soon = closingSoon(state.items, state.profile, state.todayIso, 5);
  const box = document.getElementById("soon");
  box.hidden = soon.length === 0;
  document.getElementById("soon-rows").innerHTML = soon.map((i) =>
    renderSoonRow(i, dueInfo(i, state.todayIso))).join("");
}

function renderFeed() {
  const ctx = { profile: state.profile, savedSet: state.savedSet,
    todayIso: state.todayIso, expanded: state.expanded };
  const groups = new Map();
  for (const item of visibleItems()) {
    const wk = weekMonday(item.release_date || state.todayIso);
    if (!groups.has(wk)) groups.set(wk, []);
    groups.get(wk).push(item);
  }
  const weeks = [...groups.keys()].sort().reverse().slice(0, state.weeksShown);
  document.getElementById("feed").innerHTML = weeks.map((wk) =>
    `<div class="week"><span>${weekLabel(wk)}</span></div>` +
    groups.get(wk).map((i) => renderCard(i, ctx)).join("")).join("")
    || `<p class="load-note">Nothing matches — clear the search or switch chips.</p>`;
  document.getElementById("load-note").hidden = weeks.length >= groups.size;
}

function renderAll() {
  renderChips();
  renderSoon();
  renderFeed();
}

function renderProfileEditor() {
  const slot = document.getElementById("profile-editor-slot");
  const p = state.profile;
  slot.innerHTML = `<div class="profile-editor">
    <label for="pf-ics">Institutes (codes, comma-separated)</label>
    <input id="pf-ics" value="${esc(p.ics.join(", "))}">
    <label for="pf-codes">Activity codes</label>
    <input id="pf-codes" value="${esc(p.codes.join(", "))}">
    <label for="pf-kw">Keywords</label>
    <input id="pf-kw" value="${esc(p.keywords.join(", "))}">
    <div class="row">
      <button class="btn" id="pf-save">Save profile</button>
      <button class="btn btn--ghost" id="pf-reset">Reset to default</button>
      <button class="btn btn--ghost" id="pf-close">Close</button>
    </div></div>`;
  const parse = (id) => document.getElementById(id).value
    .split(",").map((s) => s.trim()).filter(Boolean);
  document.getElementById("pf-save").onclick = () => {
    state.profile = { ics: parse("pf-ics"), codes: parse("pf-codes"), keywords: parse("pf-kw") };
    save(PROFILE_KEY, state.profile);
    slot.innerHTML = "";
    renderAll();
  };
  document.getElementById("pf-reset").onclick = () => {
    state.profile = DEFAULT_PROFILE;
    localStorage.removeItem(PROFILE_KEY);
    slot.innerHTML = "";
    renderAll();
  };
  document.getElementById("pf-close").onclick = () => { slot.innerHTML = ""; };
}

function wireEvents() {
  document.getElementById("chips").addEventListener("click", (e) => {
    const chip = e.target.closest("[data-chip]");
    if (chip) { state.chip = chip.dataset.chip; state.weeksShown = WEEKS_PER_PAGE; renderAll(); }
    if (e.target.closest("[data-edit-profile]")) renderProfileEditor();
  });
  document.getElementById("feed").addEventListener("click", (e) => {
    const saveBtn = e.target.closest("[data-save]");
    if (saveBtn) {
      const id = saveBtn.dataset.save;
      state.savedSet.has(id) ? state.savedSet.delete(id) : state.savedSet.add(id);
      save(SAVED_KEY, [...state.savedSet]);
      renderAll();
    }
    const expandBtn = e.target.closest("[data-expand]");
    if (expandBtn) {
      const id = expandBtn.dataset.expand;
      state.expanded.has(id) ? state.expanded.delete(id) : state.expanded.add(id);
      renderFeed();
    }
  });
  let timer;
  document.getElementById("search").addEventListener("input", (e) => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      state.query = e.target.value;
      state.weeksShown = WEEKS_PER_PAGE;
      renderAll();
    }, 200);
  });
  new IntersectionObserver((entries) => {
    if (entries.some((en) => en.isIntersecting)) {
      state.weeksShown += WEEKS_PER_PAGE;
      renderFeed();
    }
  }).observe(document.getElementById("load-note"));
}

async function boot() {
  initTheme();
  try {
    const resp = await fetch("notices.json");
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const payload = await resp.json();
    state.items = payload.items || [];
    const newest = state.items.filter((i) => weekMonday(i.release_date || "1900-01-01")
      === weekMonday(state.todayIso)).length;
    const weekOf = fmtDateLong(weekMonday(state.todayIso)).split(",")[0];
    document.getElementById("page-eyebrow").textContent = `NIH Guide · Week of ${weekOf}`;
    const stamp = payload.generated_at ? new Date(payload.generated_at).toLocaleString() : "unknown";
    const foryou = applyChip(state.items, "foryou", state.profile, state.savedSet).length;
    document.getElementById("page-lead").textContent =
      `${state.items.length} items tracked · ${newest} new this week · ${foryou} match your profile · refreshed ${stamp}`;
    wireEvents();
    renderAll();
  } catch (err) {
    document.getElementById("feed").innerHTML =
      `<div class="error-card"><strong>Couldn't load the data file.</strong><br>
       ${err.message}. Try reloading; if it persists the weekly refresh may have failed —
       <a href="https://github.com/muntasirmasum/grant-radar/actions">check the Actions log</a>.</div>`;
    document.getElementById("page-lead").textContent = "Data unavailable.";
  }
}

boot();
