// Pure data logic. No DOM access: everything here is node-testable.

export const DEFAULT_PROFILE = {
  ics: ["NIA", "NIAAA", "NICHD", "NIMHD"],
  codes: ["K01", "K99", "R03", "R21", "R01"],
  keywords: ["aging", "alcohol", "mortality", "demography", "life course",
    "disparities", "epidemiology"],
};

const OPP_DOCTYPES = new Set(["RFA", "PA", "PAR", "PAS"]);

export function isNosi(item) {
  return (item.title || "").startsWith("Notice of Special Interest");
}

export function isOpportunity(item) {
  return OPP_DOCTYPES.has(item.doctype) || isNosi(item);
}

export function codesOf(item) {
  const codes = item.activity_codes?.length ? item.activity_codes : (item.mechanisms || []);
  return codes || [];
}

export function isCareer(item) {
  return codesOf(item).some((c) => /^[KF]/.test(c));
}

const DAY = 86400000;

export function weekMonday(iso) {
  const d = new Date(iso + "T00:00:00Z");
  const shift = (d.getUTCDay() + 6) % 7; // Mon=0 ... Sun=6
  return new Date(d.getTime() - shift * DAY).toISOString().slice(0, 10);
}

const MONTHS = ["January","February","March","April","May","June",
  "July","August","September","October","November","December"];

export function weekLabel(mondayIso) {
  const [, m, d] = mondayIso.split("-").map(Number);
  return `Week of ${MONTHS[m - 1]} ${d}`;
}

export function daysUntil(iso, todayIso) {
  return Math.round((Date.parse(iso + "T00:00:00Z") - Date.parse(todayIso + "T00:00:00Z")) / DAY);
}

export function dueInfo(item, todayIso) {
  for (const d of item.due_dates || []) {
    if (d.date >= todayIso) {
      return { date: d.date, days: daysUntil(d.date, todayIso), label: "Next due" };
    }
  }
  const exp = item.expiration_date;
  if (isOpportunity(item) && exp && exp >= todayIso) {
    return { date: exp, days: daysUntil(exp, todayIso), label: "Closes" };
  }
  return null;
}

function haystack(item) {
  return [item.title, item.synopsis_truncated, item.purpose_tldr,
    (item.topics || []).join(" ")].filter(Boolean).join(" ").toLowerCase();
}

export function matchReasons(item, profile) {
  const reasons = [];
  const ics = new Set([item.primary_ic, item.parent_ic].filter(Boolean));
  for (const ic of profile.ics) if (ics.has(ic)) reasons.push(ic);
  const codes = new Set(codesOf(item));
  for (const c of profile.codes) if (codes.has(c)) reasons.push(c);
  const hay = haystack(item);
  for (const kw of profile.keywords) if (hay.includes(kw.toLowerCase())) reasons.push(kw);
  return reasons.length >= 2 ? reasons : [];
}

export function applyChip(items, chip, profile, savedSet) {
  switch (chip) {
    case "foryou": return items.filter((i) => matchReasons(i, profile).length > 0);
    case "opps": return items.filter((i) => isOpportunity(i) && !isNosi(i));
    case "nosi": return items.filter(isNosi);
    case "career": return items.filter(isCareer);
    case "policy": return items.filter((i) => !isOpportunity(i));
    case "saved": return items.filter((i) => savedSet.has(i.notice_id));
    default: return items;
  }
}

export function chipCounts(items, profile, savedSet) {
  const chips = ["all", "foryou", "opps", "nosi", "career", "policy", "saved"];
  return Object.fromEntries(chips.map((c) => [c, applyChip(items, c, profile, savedSet).length]));
}

export function searchFilter(items, query) {
  const q = (query || "").trim().toLowerCase();
  if (!q) return items;
  return items.filter((i) => (i.notice_id.toLowerCase() + " " + haystack(i)).includes(q));
}

export function closingSoon(items, profile, todayIso, n = 5) {
  return items
    .filter((i) => matchReasons(i, profile).length > 0)
    .map((i) => ({ item: i, due: dueInfo(i, todayIso) }))
    .filter((x) => x.due)
    .sort((a, b) => a.due.days - b.due.days)
    .slice(0, n)
    .map((x) => x.item);
}
