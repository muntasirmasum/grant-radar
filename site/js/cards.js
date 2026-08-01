import { esc, fmtDate } from "./ui.js";
import { codesOf, dueInfo, isOpportunity, matchReasons } from "./logic.js";

function duePill(item, todayIso) {
  const due = dueInfo(item, todayIso);
  if (!due) return "";
  const hot = due.days <= 30 ? " due--hot" : "";
  return `<span class="due${hot}">${due.label} ${esc(fmtDate(due.date))}</span>`;
}

function metaLine(item) {
  const kind = item.title?.startsWith("Notice of Special Interest") ? "NOSI"
    : (isOpportunity(item) ? item.doctype : "Policy");
  const org = item.primary_ic || (item.issuing_orgs || [])[0] || "NIH";
  return `${esc(kind)} · ${esc(org)} <span class="meta-id">${esc(item.notice_id)}</span>`;
}

function detailBlock(item) {
  if (!item.dos?.length && !item.donts?.length && !item.key_dates?.length) return "";
  const list = (title, cls, entries) => entries?.length
    ? `<div class="${cls}"><h6>${title}</h6><ul>${entries.map((e) => `<li>${esc(e)}</li>`).join("")}</ul></div>`
    : "";
  const dates = item.key_dates?.length
    ? `<div><h6>Key dates</h6><ul>${item.key_dates.map((k) =>
        `<li>${esc(k.label)}: ${esc(fmtDate(k.date))}</li>`).join("")}</ul></div>`
    : "";
  return `<div class="detail">${list("Do", "do", item.dos)}${list("Don't", "dont", item.donts)}${dates}</div>`;
}

export function renderCard(item, ctx) {
  const { profile, savedSet, todayIso, expanded } = ctx;
  const gold = isOpportunity(item) ? "" : " card--gold";
  const body = item.purpose_tldr
    ? `<p class="tldr"><b>TL;DR</b>${esc(item.purpose_tldr)}</p>`
    : (item.synopsis_truncated
      ? `<p class="syn"><b>Synopsis</b>${esc(item.synopsis_truncated)}</p>` : "");
  const compact = !body ? " card--compact" : "";
  const reasons = matchReasons(item, profile);
  const foryou = reasons.length
    ? `<div class="foryou"><i></i>For you <em>· matches ${esc(reasons.join(" · "))}</em></div>` : "";
  const pills = codesOf(item).map((c) => `<span class="pill">${esc(c)}</span>`).join("");
  const topics = (item.topics || []).map((t) => `<span class="pill pill--gold">${esc(t)}</span>`).join("");
  const cash = item.award_ceiling
    ? `<span class="pill pill--gold">≤ $${esc(Number(item.award_ceiling).toLocaleString("en-US"))}</span>` : "";
  const saved = savedSet.has(item.notice_id);
  const isOpen = expanded.has(item.notice_id);
  const hasDetail = Boolean(item.dos?.length || item.donts?.length || item.key_dates?.length);
  const actions = `<span class="actions">
      <button data-save="${esc(item.notice_id)}" class="${saved ? "saved" : ""}"
        aria-label="Save for later">${saved ? "♥ saved" : "♡"}</button>
      ${hasDetail ? `<button data-expand="${esc(item.notice_id)}">${isOpen ? "Collapse ▴" : "Details ▾"}</button>` : ""}
      <a href="${esc(item.url)}" target="_blank" rel="noopener">NIH ↗</a>
    </span>`;
  const pillrow = `<div class="pillrow">${duePill(item, todayIso)}${pills}${topics}${cash}${actions}</div>`;
  return `<article class="card${gold}${compact}" data-id="${esc(item.notice_id)}">
    <div class="meta">${metaLine(item)}</div>
    <h2 class="title"><a href="${esc(item.url)}" target="_blank" rel="noopener">${esc(item.title)}</a></h2>
    ${body}${foryou}${isOpen ? detailBlock(item) : ""}${pillrow}
  </article>`;
}

export function soonRowInner(item, due) {
  const mid = due.days > 30 ? " days--mid" : "";
  const org = item.primary_ic || (item.issuing_orgs || [])[0] || "NIH";
  return `<div class="days${mid}">${due.days}<small>DAYS</small></div>
    <div><div class="soon-title"><a href="${esc(item.url)}" target="_blank" rel="noopener">${esc(item.title)}</a></div>
    <div class="soon-meta">${esc(item.doctype || "Notice")} · ${esc(org)} · ${esc(due.label.toLowerCase())} ${esc(fmtDate(due.date))}</div></div>`;
}

export function renderSoonRow(item, due) {
  return `<div class="soon-row">${soonRowInner(item, due)}</div>`;
}
