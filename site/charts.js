// site/charts.js

export function renderCharts(notices, containers) {
  renderTopics(notices, containers.topics);
  renderICs(notices, containers.ics);
  renderVolume(notices, containers.volume);
}

function renderTopics(notices, el) {
  const counts = new Map();
  for (const n of notices) {
    for (const t of (n.topics || [])) {
      counts.set(t, (counts.get(t) || 0) + 1);
    }
  }
  const data = Array.from(counts, ([topic, n]) => ({ topic, n }))
    .sort((a, b) => b.n - a.n)
    .slice(0, 8);

  el.innerHTML = "";
  if (data.length === 0) {
    el.innerHTML = '<div class="empty-state">No topic data</div>';
    return;
  }

  const style = getComputedStyle(document.documentElement);
  const fill = style.getPropertyValue("--chart-primary").trim();

  el.appendChild(
    Plot.plot({
      marginLeft: 140,
      height: 260,
      y: { label: null },
      x: { label: "notices", grid: true, ticks: 4 },
      style: { fontSize: "11px", background: "transparent" },
      marks: [
        Plot.barX(data, {
          y: "topic", x: "n", fill,
          sort: { y: "x", reverse: true },
        }),
        Plot.text(data, {
          y: "topic", x: "n", text: "n",
          dx: 5, textAnchor: "start", fill: style.getPropertyValue("--text").trim(), fontWeight: 600,
        }),
        Plot.ruleX([0]),
      ],
    })
  );
}

function renderICs(notices, el) {
  const counts = new Map();
  for (const n of notices) {
    for (const ic of (n.issuing_orgs || [])) {
      counts.set(ic, (counts.get(ic) || 0) + 1);
    }
  }
  const data = Array.from(counts, ([ic, n]) => ({ ic, n }))
    .sort((a, b) => b.n - a.n)
    .slice(0, 8);

  el.innerHTML = "";
  if (data.length === 0) {
    el.innerHTML = '<div class="empty-state">No IC data</div>';
    return;
  }

  const style = getComputedStyle(document.documentElement);
  const fill = style.getPropertyValue("--chart-secondary").trim();

  el.appendChild(
    Plot.plot({
      marginLeft: 200,
      height: 260,
      y: { label: null },
      x: { label: "notices", grid: true, ticks: 4 },
      style: { fontSize: "11px", background: "transparent" },
      marks: [
        Plot.barX(data, {
          y: (d) => d.ic.length > 38 ? d.ic.slice(0, 36) + "…" : d.ic,
          x: "n", fill,
          sort: { y: "x", reverse: true },
        }),
        Plot.text(data, {
          y: (d) => d.ic.length > 38 ? d.ic.slice(0, 36) + "…" : d.ic,
          x: "n", text: "n",
          dx: 5, textAnchor: "start", fill: style.getPropertyValue("--text").trim(), fontWeight: 600,
        }),
        Plot.ruleX([0]),
      ],
    })
  );
}

function renderVolume(notices, el) {
  const buckets = new Map();
  for (const n of notices) {
    if (!n.release_date) continue;
    const d = new Date(n.release_date);
    const mon = new Date(d);
    mon.setDate(d.getDate() - ((d.getDay() + 6) % 7));
    const key = mon.toISOString().slice(0, 10);
    buckets.set(key, (buckets.get(key) || 0) + 1);
  }
  const data = Array.from(buckets, ([week, n]) => ({ week: new Date(week), n }))
    .sort((a, b) => a.week - b.week)
    .slice(-12);

  el.innerHTML = "";
  if (data.length === 0) {
    el.innerHTML = '<div class="empty-state">No volume data</div>';
    return;
  }

  const style = getComputedStyle(document.documentElement);
  const stroke = style.getPropertyValue("--chart-primary").trim();

  el.appendChild(
    Plot.plot({
      height: 260,
      y: { label: "notices / week", grid: true, ticks: 4 },
      x: { label: null, type: "time" },
      style: { fontSize: "11px", background: "transparent" },
      marks: [
        Plot.areaY(data, {
          x: "week", y: "n",
          fill: stroke, fillOpacity: 0.12, curve: "monotone-x",
        }),
        Plot.lineY(data, {
          x: "week", y: "n",
          stroke, strokeWidth: 2.5, curve: "monotone-x",
        }),
        Plot.dot(data, { x: "week", y: "n", fill: stroke, r: 3.5 }),
        Plot.ruleY([0]),
      ],
    })
  );
}
