import { initTheme } from "./ui.js";
import { codesOf, dueInfo, isOpportunity, weekMonday } from "./logic.js";

/* global Plot */

const todayIso = new Date().toISOString().slice(0, 10);

function accent() {
  return getComputedStyle(document.documentElement).getPropertyValue("--accent").trim();
}

function textColor() {
  return getComputedStyle(document.documentElement).getPropertyValue("--muted").trim();
}

function draw(items) {
  const style = { background: "transparent", color: textColor(), fontFamily: "'IBM Plex Sans',sans-serif" };
  const cutoffWeek = new Date(Date.now() - 12 * 7 * 86400000).toISOString().slice(0, 10);
  const weekly = d3.rollups(
    items.filter((i) => (i.release_date || "") >= cutoffWeek),
    (v) => v.length, (i) => weekMonday(i.release_date)).map(([week, n]) => ({ week, n }));
  document.getElementById("chart-volume").replaceChildren(Plot.plot({
    style, height: 220, x: { label: null, tickFormat: (w) => w.slice(5) }, y: { label: "items", grid: true },
    marks: [Plot.barY(weekly, { x: "week", y: "n", fill: accent(), rx: 3 })],
  }));

  const cutoff90 = new Date(Date.now() - 90 * 86400000).toISOString().slice(0, 10);
  const ics = d3.rollups(
    items.filter((i) => (i.release_date || "") >= cutoff90 && i.primary_ic),
    (v) => v.length, (i) => i.primary_ic)
    .sort((a, b) => b[1] - a[1]).slice(0, 10).map(([ic, n]) => ({ ic, n }));
  document.getElementById("chart-ics").replaceChildren(Plot.plot({
    style, height: 260, marginLeft: 70, x: { label: "items", grid: true }, y: { label: null },
    marks: [Plot.barX(ics, { y: "ic", x: "n", fill: accent(), rx: 3, sort: { y: "-x" } })],
  }));

  const codes = d3.rollups(
    items.filter((i) => isOpportunity(i) && dueInfo(i, todayIso)).flatMap((i) => codesOf(i)),
    (v) => v.length, (c) => c)
    .sort((a, b) => b[1] - a[1]).slice(0, 10).map(([code, n]) => ({ code, n }));
  document.getElementById("chart-codes").replaceChildren(Plot.plot({
    style, height: 260, marginLeft: 60, x: { label: "open opportunities", grid: true }, y: { label: null },
    marks: [Plot.barX(codes, { y: "code", x: "n", fill: accent(), rx: 3, sort: { y: "-x" } })],
  }));
}

async function boot() {
  initTheme();
  try {
    const payload = await (await fetch("notices.json")).json();
    draw(payload.items || []);
    document.getElementById("theme-toggle").addEventListener("click", () =>
      draw(payload.items || []));
  } catch {
    document.getElementById("chart-volume").innerHTML =
      `<div class="error-card">Couldn't load the data file.</div>`;
  }
}

boot();
