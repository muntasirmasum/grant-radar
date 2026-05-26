// site/app.js
import { renderCharts } from "./charts.js";

// --- State ---
const state = {
  notices: [],
  filters: { ics: [], mechanisms: [], topics: [], dateRange: "30d" },
  search: "",
  profile: { ics: [], mechs: [], topics: [], career: "any" },
  saved: [],
  savedOnly: false,
};

// --- DOM refs ---
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const dom = {
  feed: $("#feed"),
  feedHeading: $("#feed-heading"),
  feedMeta: $("#feed-meta"),
  search: $("#search"),
  themeToggle: $("#theme-toggle"),
  hamburger: $("#hamburger"),
  sidebar: $("#sidebar"),
  profileChips: $("#profile-chips"),
  profileEditor: $("#profile-editor"),
  profileToggle: $("#profile-toggle"),
  savedOnly: $("#saved-only"),
  clearFilters: $("#clear-filters"),
  chartTopics: $("#chart-topics"),
  chartICs: $("#chart-ics"),
  chartVolume: $("#chart-volume"),
};

// --- Init ---
async function init() {
  loadTheme();
  loadProfile();
  loadSaved();
  await loadNotices();
  buildFilterOptions();
  wireEvents();
  render();
}

async function loadNotices() {
  try {
    const resp = await fetch("notices.json");
    state.notices = await resp.json();
  } catch (e) {
    state.notices = [];
  }
}

function loadProfile() {
  try {
    const raw = localStorage.getItem("grant-radar.profile.v1");
    if (raw) state.profile = JSON.parse(raw);
  } catch (e) { /* use defaults */ }
}

function saveProfile() {
  localStorage.setItem("grant-radar.profile.v1", JSON.stringify(state.profile));
}

function loadSaved() {
  try {
    const raw = localStorage.getItem("grant-radar.saved.v1");
    if (raw) state.saved = JSON.parse(raw);
  } catch (e) { /* use defaults */ }
}

function saveSaved() {
  localStorage.setItem("grant-radar.saved.v1", JSON.stringify(state.saved));
}

// --- Theme ---
function loadTheme() {
  const saved = localStorage.getItem("grant-radar.theme");
  if (saved === "dark") {
    document.documentElement.setAttribute("data-theme", "dark");
    dom.themeToggle.textContent = "🌙";
  }
}

function toggleTheme() {
  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  if (isDark) {
    document.documentElement.removeAttribute("data-theme");
    localStorage.setItem("grant-radar.theme", "light");
    dom.themeToggle.textContent = "☀️";
  } else {
    document.documentElement.setAttribute("data-theme", "dark");
    localStorage.setItem("grant-radar.theme", "dark");
    dom.themeToggle.textContent = "🌙";
  }
  render();
}

// --- Filters ---
function collectUnique(key) {
  const set = new Set();
  for (const n of state.notices) {
    for (const v of (n[key] || [])) set.add(v);
  }
  return Array.from(set).sort();
}

function buildFilterOptions() {
  buildChecklist("filter-ics", collectUnique("issuing_orgs"), "ics");
  buildChecklist("filter-mechanisms", collectUnique("mechanisms"), "mechanisms");
  buildChecklist("filter-topics", collectUnique("topics"), "topics");
  buildDateRangeFilter();
}

function buildChecklist(containerId, options, stateKey) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";
  for (const opt of options) {
    const label = document.createElement("label");
    label.className = "filter-group__item";
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.value = opt;
    cb.addEventListener("change", () => {
      if (cb.checked) {
        state.filters[stateKey].push(opt);
      } else {
        state.filters[stateKey] = state.filters[stateKey].filter((v) => v !== opt);
      }
      updateTriggerLabel(stateKey);
      render();
    });
    const text = document.createTextNode(" " + (opt.length > 35 ? opt.slice(0, 33) + "…" : opt));
    label.appendChild(cb);
    label.appendChild(text);
    container.appendChild(label);
  }
}

function buildDateRangeFilter() {
  const container = document.getElementById("filter-dateRange");
  container.innerHTML = "";
  const ranges = [
    { label: "Last 7 days", value: "7d" },
    { label: "Last 30 days", value: "30d" },
    { label: "Last 90 days", value: "90d" },
    { label: "All notices", value: "all" },
  ];
  for (const r of ranges) {
    const label = document.createElement("label");
    label.className = "filter-group__item";
    const radio = document.createElement("input");
    radio.type = "radio";
    radio.name = "dateRange";
    radio.value = r.value;
    radio.checked = r.value === state.filters.dateRange;
    radio.addEventListener("change", () => {
      state.filters.dateRange = r.value;
      updateTriggerLabel("dateRange");
      render();
    });
    const text = document.createTextNode(" " + r.label);
    label.appendChild(radio);
    label.appendChild(text);
    container.appendChild(label);
  }
}

function updateTriggerLabel(stateKey) {
  const trigger = document.querySelector(`[data-filter="${stateKey}"]`);
  if (!trigger) return;
  if (stateKey === "dateRange") {
    const labels = { "7d": "Last 7 days", "30d": "Last 30 days", "90d": "Last 90 days", all: "All notices" };
    trigger.innerHTML = `${labels[state.filters.dateRange]} <span>▾</span>`;
    return;
  }
  const count = state.filters[stateKey].length;
  const labels = { ics: "ICs", mechanisms: "mechanisms", topics: "topics" };
  if (count === 0) {
    trigger.innerHTML = `All ${labels[stateKey]} <span>▾</span>`;
  } else {
    trigger.innerHTML = `${labels[stateKey]} <span class="badge">${count}</span> <span>▾</span>`;
  }
}

// --- Search ---
function debounce(fn, ms) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}

function matchesSearch(notice, query) {
  if (!query) return true;
  const q = query.toLowerCase();
  const haystack = [
    notice.title,
    notice.notice_id,
    notice.purpose_tldr,
    (notice.topics || []).join(" "),
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return haystack.includes(q);
}

// --- Profile ---
function renderProfileChips() {
  const parts = [];
  for (const ic of state.profile.ics) {
    parts.push(`<span class="profile-chip">${ic.replace(/^National (Institute|Center) of? /, "")}</span>`);
  }
  for (const m of state.profile.mechs) {
    parts.push(`<span class="profile-chip">${m}</span>`);
  }
  for (const t of state.profile.topics) {
    parts.push(`<span class="profile-chip">${t}</span>`);
  }
  if (state.profile.career && state.profile.career !== "any") {
    parts.push(`<span class="profile-chip">${state.profile.career}</span>`);
  }
  if (parts.length === 0) {
    dom.profileChips.innerHTML = '<span style="font-size:0.72rem;color:var(--text-muted);">No profile set. Click to configure.</span>';
  } else {
    dom.profileChips.innerHTML = parts.join("");
  }
}

function renderProfileEditor() {
  const allICs = collectUnique("issuing_orgs");
  const allMechs = collectUnique("mechanisms");
  const allTopics = collectUnique("topics");
  const careers = ["any", "early-stage", "mid-career", "established"];

  let html = '<div style="margin-top:0.5rem;font-size:0.72rem;">';
  html += buildProfileMultiSelect("ICs", allICs, state.profile.ics, "profile-ics");
  html += buildProfileMultiSelect("Mechanisms", allMechs, state.profile.mechs, "profile-mechs");
  html += buildProfileMultiSelect("Topics", allTopics, state.profile.topics, "profile-topics");
  html += `<div style="margin-top:0.4rem;"><strong>Career:</strong> <select id="profile-career" style="font-size:0.72rem;padding:0.2rem;border-radius:4px;border:1px solid var(--border);background:var(--bg-card);color:var(--text-secondary);">`;
  for (const c of careers) {
    html += `<option value="${c}" ${state.profile.career === c ? "selected" : ""}>${c}</option>`;
  }
  html += `</select></div>`;
  html += `<button id="profile-save" style="margin-top:0.5rem;padding:0.3rem 0.8rem;font-size:0.72rem;border-radius:4px;border:1px solid var(--text);background:var(--text);color:var(--bg-card);cursor:pointer;font-family:var(--font);">Save profile</button>`;
  html += "</div>";
  dom.profileEditor.innerHTML = html;

  document.getElementById("profile-save").addEventListener("click", () => {
    state.profile.ics = getCheckedValues("profile-ics");
    state.profile.mechs = getCheckedValues("profile-mechs");
    state.profile.topics = getCheckedValues("profile-topics");
    state.profile.career = document.getElementById("profile-career").value;
    saveProfile();
    dom.profileEditor.style.display = "none";
    renderProfileChips();
    render();
  });
}

function buildProfileMultiSelect(label, options, selected, id) {
  let html = `<div style="margin-top:0.4rem;"><strong>${label}:</strong><div id="${id}" style="max-height:100px;overflow-y:auto;margin-top:0.2rem;">`;
  for (const opt of options) {
    const checked = selected.includes(opt) ? "checked" : "";
    const short = opt.length > 30 ? opt.slice(0, 28) + "…" : opt;
    html += `<label style="display:block;cursor:pointer;"><input type="checkbox" value="${opt}" ${checked}> ${short}</label>`;
  }
  html += "</div></div>";
  return html;
}

function getCheckedValues(containerId) {
  const checks = document.getElementById(containerId).querySelectorAll("input:checked");
  return Array.from(checks).map((cb) => cb.value);
}

// --- Render ---
function filterNotices() {
  const today = new Date();
  let cutoff = null;
  if (state.filters.dateRange === "7d") {
    cutoff = new Date(today);
    cutoff.setDate(cutoff.getDate() - 7);
  } else if (state.filters.dateRange === "30d") {
    cutoff = new Date(today);
    cutoff.setDate(cutoff.getDate() - 30);
  } else if (state.filters.dateRange === "90d") {
    cutoff = new Date(today);
    cutoff.setDate(cutoff.getDate() - 90);
  }

  return state.notices.filter((n) => {
    if (cutoff && n.release_date && new Date(n.release_date) < cutoff) return false;
    if (state.filters.ics.length > 0) {
      if (!(n.issuing_orgs || []).some((ic) => state.filters.ics.includes(ic))) return false;
    }
    if (state.filters.mechanisms.length > 0) {
      if (!(n.mechanisms || []).some((m) => state.filters.mechanisms.includes(m))) return false;
    }
    if (state.filters.topics.length > 0) {
      if (!(n.topics || []).some((t) => state.filters.topics.includes(t))) return false;
    }
    if (!matchesSearch(n, state.search)) return false;
    if (state.savedOnly && !state.saved.includes(n.notice_id)) return false;
    return true;
  });
}

function matchScore(n) {
  const p = state.profile;
  let s = 0;
  for (const ic of (n.issuing_orgs || [])) if (p.ics.includes(ic)) s += 1;
  for (const m of (n.mechanisms || [])) if (p.mechs.includes(m)) s += 1;
  for (const t of (n.topics || [])) if (p.topics.includes(t)) s += 1;
  if (p.career && p.career !== "any" && (n.career_stages || []).includes(p.career)) s += 0.5;
  return s;
}

function profileEmpty() {
  const p = state.profile;
  return !p.ics.length && !p.mechs.length && !p.topics.length && (!p.career || p.career === "any");
}

function render() {
  const filtered = filterNotices();
  const scored = filtered.map((n) => ({ ...n, _score: matchScore(n) }));
  if (!profileEmpty()) {
    scored.sort((a, b) => b._score - a._score || (b.release_date || "").localeCompare(a.release_date || ""));
  } else {
    scored.sort((a, b) => (b.release_date || "").localeCompare(a.release_date || ""));
  }

  const headingLabels = { "7d": "Last 7 days", "30d": "Last 30 days", "90d": "Last 90 days", all: "All notices" };
  dom.feedHeading.textContent = headingLabels[state.filters.dateRange];
  const rankText = profileEmpty() ? "" : " · ranked for you";
  dom.feedMeta.textContent = `${scored.length} notice${scored.length !== 1 ? "s" : ""}${rankText}`;

  if (scored.length === 0) {
    dom.feed.innerHTML = '<div class="empty-state">No notices match your filters.</div>';
  } else {
    dom.feed.innerHTML = scored.map(renderNoticeCard).join("");
    wireCardActions();
  }

  renderCharts(filtered, {
    topics: dom.chartTopics,
    ics: dom.chartICs,
    volume: dom.chartVolume,
  });

  renderProfileChips();
}

function chipClass(type) {
  const map = {
    nofo: "chip--nofo", rfa: "chip--rfa", change: "chip--change",
    rescission: "chip--rescission", pa: "chip--pa", par: "chip--par",
    reissue: "chip--reissue",
  };
  return map[type] || "";
}

function renderNoticeCard(n) {
  const chips = [];
  chips.push(`<span class="chip chip--id">${esc(n.notice_id)}</span>`);
  chips.push(`<span class="chip ${chipClass(n.notice_type)}">${esc((n.notice_type || "notice").replace(/_/g, " "))}</span>`);
  for (const ic of (n.issuing_orgs || []).slice(0, 2)) {
    chips.push(`<span class="chip">${esc(ic.replace(/^National (Institute|Center) of? /, ""))}</span>`);
  }
  if ((n.issuing_orgs || []).length > 2) {
    chips.push(`<span class="chip">+${n.issuing_orgs.length - 2}</span>`);
  }
  if (n._score > 0) {
    chips.push(`<span class="chip chip--match">match ${n._score}</span>`);
  }

  const tldr = n.purpose_tldr
    ? `<div class="notice__tldr">${esc(n.purpose_tldr)}</div>`
    : `<div class="notice__tldr notice__tldr--pending">TL;DR pending /refresh-tldrs</div>`;

  const meta = [n.release_date, (n.mechanisms || []).join(", "), (n.topics || []).join(", ")]
    .filter(Boolean).join(" · ");

  const isSaved = state.saved.includes(n.notice_id);
  const saveLabel = isSaved ? "♥ saved" : "♡ save";
  const saveClass = isSaved ? "notice__action notice__action--saved" : "notice__action";

  let detail = "";
  const hasDos = n.dos && n.dos.length > 0;
  const hasDonts = n.donts && n.donts.length > 0;
  let keyDates = [];
  try { keyDates = JSON.parse(n.key_dates_json || "[]"); } catch (e) { /* ignore */ }
  const hasKeyDates = keyDates.filter((kd) => kd.type !== "release").length > 0;

  if (hasDos || hasDonts || hasKeyDates) {
    detail += `<div class="notice__detail" id="detail-${esc(n.notice_id)}">`;
    if (hasDos) {
      detail += `<h4>Do</h4><ul>${n.dos.map((d) => `<li>${esc(d)}</li>`).join("")}</ul>`;
    }
    if (hasDonts) {
      detail += `<h4>Don't</h4><ul>${n.donts.map((d) => `<li>${esc(d)}</li>`).join("")}</ul>`;
    }
    if (hasKeyDates) {
      detail += `<h4>Key Dates</h4><ul>${keyDates.filter((kd) => kd.type !== "release").map((kd) => `<li><strong>${esc(kd.date)}</strong> — ${esc(kd.label)}</li>`).join("")}</ul>`;
    }
    detail += "</div>";
  }

  const expandBtn = (hasDos || hasDonts || hasKeyDates)
    ? `<button class="notice__action" data-expand="${esc(n.notice_id)}">⤢ expand</button>`
    : "";

  return `<div class="notice">
    <div class="notice__chips">${chips.join("")}</div>
    <div class="notice__title"><a href="${esc(n.url)}" target="_blank" rel="noreferrer">${esc(n.title)}</a></div>
    ${tldr}
    <div class="notice__footer">
      <span>${esc(meta)}</span>
      <div class="notice__actions">
        ${expandBtn}
        <button class="${saveClass}" data-save="${esc(n.notice_id)}">${saveLabel}</button>
      </div>
    </div>
    ${detail}
  </div>`;
}

function esc(str) {
  if (!str) return "";
  return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// --- Events ---
function wireEvents() {
  dom.search.addEventListener(
    "input",
    debounce(() => {
      state.search = dom.search.value;
      render();
    }, 200)
  );

  dom.themeToggle.addEventListener("click", toggleTheme);

  dom.hamburger.addEventListener("click", () => {
    dom.sidebar.classList.toggle("open");
  });

  for (const trigger of $$(".filter-group__trigger")) {
    trigger.addEventListener("click", () => {
      const list = trigger.nextElementSibling;
      list.classList.toggle("open");
    });
  }

  dom.profileToggle.addEventListener("click", () => {
    const editor = dom.profileEditor;
    if (editor.style.display === "none") {
      editor.style.display = "block";
      renderProfileEditor();
    } else {
      editor.style.display = "none";
    }
  });

  dom.savedOnly.addEventListener("change", () => {
    state.savedOnly = dom.savedOnly.checked;
    render();
  });

  dom.clearFilters.addEventListener("click", () => {
    state.filters = { ics: [], mechanisms: [], topics: [], dateRange: "30d" };
    state.search = "";
    state.savedOnly = false;
    dom.search.value = "";
    dom.savedOnly.checked = false;
    buildFilterOptions();
    updateTriggerLabel("ics");
    updateTriggerLabel("mechanisms");
    updateTriggerLabel("topics");
    updateTriggerLabel("dateRange");
    render();
  });
}

function wireCardActions() {
  for (const btn of $$("[data-expand]")) {
    btn.addEventListener("click", () => {
      const id = btn.getAttribute("data-expand");
      const detail = document.getElementById("detail-" + id);
      if (detail) {
        detail.classList.toggle("open");
        btn.textContent = detail.classList.contains("open") ? "⤡ collapse" : "⤢ expand";
      }
    });
  }

  for (const btn of $$("[data-save]")) {
    btn.addEventListener("click", () => {
      const id = btn.getAttribute("data-save");
      if (state.saved.includes(id)) {
        state.saved = state.saved.filter((s) => s !== id);
        btn.textContent = "♡ save";
        btn.classList.remove("notice__action--saved");
      } else {
        state.saved.push(id);
        btn.textContent = "♥ saved";
        btn.classList.add("notice__action--saved");
      }
      saveSaved();
    });
  }
}

// --- Boot ---
init();
