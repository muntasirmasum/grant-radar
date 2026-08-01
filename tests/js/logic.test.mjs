import { test } from "node:test";
import assert from "node:assert/strict";
import {
  DEFAULT_PROFILE, isOpportunity, isNosi, isCareer, weekMonday, weekLabel,
  daysUntil, dueInfo, matchReasons, applyChip, searchFilter, closingSoon,
} from "../../site/js/logic.js";

const TODAY = "2026-07-31";

const nosi = {
  notice_id: "NOT-AA-26-012", doctype: "NOT",
  title: "Notice of Special Interest (NOSI): Alcohol Use Among Older Adults",
  release_date: "2026-07-28", expiration_date: "2026-11-17",
  due_dates: [], activity_codes: [], primary_ic: "NIAAA",
  synopsis_truncated: "Drinking patterns and mortality in adults 50+.",
};
const par = {
  notice_id: "PAR-26-118", doctype: "PAR", title: "K01 in Aging Research",
  release_date: "2026-06-01", expiration_date: "2027-05-08",
  due_dates: [{ label: "Application receipt", date: "2026-10-12" }],
  activity_codes: ["K01"], primary_ic: "NIA", synopsis_truncated: "Career development.",
};
const policy = {
  notice_id: "NOT-OD-26-104", doctype: "NOT", title: "FORMS-J Required",
  release_date: "2026-07-27", due_dates: [], activity_codes: [], primary_ic: "OD",
};

test("classification", () => {
  assert.equal(isOpportunity(nosi), true);   // NOSI counts
  assert.equal(isNosi(nosi), true);
  assert.equal(isOpportunity(par), true);
  assert.equal(isNosi(par), false);
  assert.equal(isOpportunity(policy), false);
  assert.equal(isCareer(par), true);         // K01
  assert.equal(isCareer(nosi), false);
});

test("week helpers", () => {
  assert.equal(weekMonday("2026-07-31"), "2026-07-27"); // Friday -> that week's Monday
  assert.equal(weekMonday("2026-07-27"), "2026-07-27"); // Monday stays
  assert.equal(weekLabel("2026-07-27"), "Week of July 27");
});

test("daysUntil and dueInfo", () => {
  assert.equal(daysUntil("2026-08-12", TODAY), 12);
  assert.equal(daysUntil("2026-07-30", TODAY), -1);
  const d = dueInfo(par, TODAY);
  assert.deepEqual(d, { date: "2026-10-12", days: 73, label: "Next due" });
  const e = dueInfo(nosi, TODAY);
  assert.equal(e.label, "Closes");
  assert.equal(e.date, "2026-11-17");
  assert.equal(dueInfo(policy, TODAY), null);
  const past = { ...par, due_dates: [{ label: "x", date: "2026-01-01" }] };
  assert.equal(dueInfo(past, TODAY).date, "2027-05-08"); // skips past receipt, uses expiration
  // Boundary: a due date equal to today is kept (`>=`, not `>`), reported as 0 days out.
  const dueToday = { ...par, due_dates: [{ label: "Application receipt", date: TODAY }] };
  assert.deepEqual(dueInfo(dueToday, TODAY), { date: TODAY, days: 0, label: "Next due" });
});

test("matchReasons needs two dimensions of evidence", () => {
  const profile = { ics: ["NIA", "NIAAA"], codes: ["K01", "R21"], keywords: ["alcohol", "aging"] };
  assert.deepEqual(matchReasons(par, profile), ["NIA", "K01", "aging"]);
  assert.deepEqual(matchReasons(nosi, profile), ["NIAAA", "alcohol"]);
  assert.deepEqual(matchReasons(policy, profile), []);
  assert.ok(DEFAULT_PROFILE.ics.includes("NIA"));
});

test("applyChip and searchFilter", () => {
  const items = [nosi, par, policy];
  const profile = DEFAULT_PROFILE;
  assert.deepEqual(applyChip(items, "nosi", profile, new Set()).map(i => i.notice_id), ["NOT-AA-26-012"]);
  assert.deepEqual(applyChip(items, "policy", profile, new Set()).map(i => i.notice_id), ["NOT-OD-26-104"]);
  assert.deepEqual(applyChip(items, "career", profile, new Set()).map(i => i.notice_id), ["PAR-26-118"]);
  assert.deepEqual(applyChip(items, "saved", profile, new Set(["PAR-26-118"])).map(i => i.notice_id), ["PAR-26-118"]);
  assert.deepEqual(applyChip(items, "foryou", profile, new Set()).map(i => i.notice_id), ["NOT-AA-26-012", "PAR-26-118"]);
  assert.deepEqual(searchFilter(items, "forms-j").map(i => i.notice_id), ["NOT-OD-26-104"]);
  assert.equal(searchFilter(items, "").length, 3);
});

test("closingSoon picks for-you items with future dates, soonest first", () => {
  const soon = closingSoon([nosi, par, policy], DEFAULT_PROFILE, TODAY, 5);
  assert.deepEqual(soon.map(i => i.notice_id), ["PAR-26-118", "NOT-AA-26-012"]);
});

test("dueInfo gates on isOpportunity: policy items never carry deadlines", () => {
  const policyWithDueDate = {
    notice_id: "NOT-OD-26-200", doctype: "NOT",
    title: "Reminder: Upcoming Council Round Deadlines for NIA Aging Research Applications",
    primary_ic: "NIA", activity_codes: [],
    due_dates: [{ label: "Council round", date: "2026-09-01" }], // future
    expiration_date: "2026-12-31", // future
    synopsis_truncated: "Timelines for NIA aging research application review.",
  };
  assert.equal(isOpportunity(policyWithDueDate), false);
  // Profile-matching (>=2 reasons) despite not being an opportunity.
  assert.deepEqual(matchReasons(policyWithDueDate, DEFAULT_PROFILE), ["NIA", "aging"]);
  // 1. A populated due_dates entry AND a future expiration_date must not produce a due chip
  //    for a non-opportunity item (spec §4.2: gold cards never show deadline chips).
  assert.equal(dueInfo(policyWithDueDate, TODAY), null);
  // 2. Even though it matches the profile, it must not appear in "closing soon".
  const soon = closingSoon([nosi, par, policy, policyWithDueDate], DEFAULT_PROFILE, TODAY, 5);
  assert.ok(!soon.some((i) => i.notice_id === "NOT-OD-26-200"));
  assert.deepEqual(soon.map((i) => i.notice_id), ["PAR-26-118", "NOT-AA-26-012"]);
  // 3. Sanity: opportunity fixtures (NOSI, PAR) still produce their existing dueInfo results.
  assert.deepEqual(dueInfo(par, TODAY), { date: "2026-10-12", days: 73, label: "Next due" });
  const e2 = dueInfo(nosi, TODAY);
  assert.equal(e2.label, "Closes");
  assert.equal(e2.date, "2026-11-17");
});

test("word-boundary keyword matching prevents false positives", () => {
  const managingTitle = {
    notice_id: "NOT-TEST-01", doctype: "NOT",
    title: "Managing Chronic Disease in Primary Care",
    primary_ic: "NIA", activity_codes: [], due_dates: [],
    synopsis_truncated: "Disease management strategies.",
  };
  const healthyAgingTitle = {
    notice_id: "NOT-TEST-02", doctype: "NOT",
    title: "Healthy Aging and Alcohol Use",
    primary_ic: "NIA", activity_codes: [], due_dates: [],
    synopsis_truncated: "Aging adults and alcohol consumption.",
  };
  const lifeCourseTitle = {
    notice_id: "NOT-TEST-03", doctype: "NOT",
    title: "Life Course Approaches to Mortality",
    primary_ic: "NIA", activity_codes: [], due_dates: [],
    synopsis_truncated: "Mortality patterns across lifespan.",
  };
  assert.deepEqual(matchReasons(managingTitle, DEFAULT_PROFILE), []);
  assert.deepEqual(matchReasons(healthyAgingTitle, DEFAULT_PROFILE), ["NIA", "aging", "alcohol"]);
  assert.deepEqual(matchReasons(lifeCourseTitle, DEFAULT_PROFILE), ["NIA", "mortality", "life course"]);
});
