---
description: Fill in LLM-extracted fields (TL;DRs, do's/don'ts, topics) for items the API refresh can't summarize. Uses your Claude subscription, not the API.
---

You are completing the enrichment step of the `grant-radar` pipeline. The
weekly refresh has already filled every structured field from the NIH Guide
and Grants.gov APIs. Your job is the free-text fields only.

# Ownership rules (do not violate)

- You may write ONLY: `purpose_tldr`, `eligibility_tldr`, `budget`,
  `mechanisms`, `career_stages`, `topics`, `dos`, `donts`,
  `strategic_priorities`, `llm_model`, `enriched_at`.
- Never edit pipeline-owned fields (`title`, dates, `activity_codes`,
  `synopsis`, `award_*`, `url`, ...). The refresh will not touch your
  fields either — that contract goes both ways.

# Workflow

## 1. Build the queue

```sh
python3 - <<'EOF'
import json, pathlib
items = [json.loads(p.read_text()) for p in pathlib.Path("data/notices").glob("*/*.json")]
queue = [i for i in items if not i.get("purpose_tldr")]
# Priority: profile matches, then nearest due date, then newest.
PROFILE_ICS = {"NIA", "NIAAA", "NICHD", "NIMHD"}
def key(i):
    matches = i.get("primary_ic") in PROFILE_ICS
    due = i.get("next_due_date") or i.get("expiration_date") or "9999"
    return (not matches, due, i.get("release_date") or "")
for i in sorted(queue, key=key)[:40]:
    year = (i.get("release_date") or "1900")[:4]
    print(f"{i['notice_id']}\tdata/notices/{year}/{i['notice_id']}.json\t{i.get('next_due_date') or i.get('expiration_date') or '-'}")
print(f"-- {len(queue)} total in queue")
EOF
```

If the queue is empty, stop.

## 2. For each item, in order

a. **Get the text.** Prefer `data/raw/nih/<year>/<id>.html` (Read tool). If
   absent, fetch `url` from the item JSON (WebFetch). For opportunities the
   item's `synopsis` field is also good input.

b. **Extract.** Produce exactly these keys — faithful to the notice, no
   invented figures, `null` where unstated, summaries 2-3 plain sentences:

```json
{
  "purpose_tldr": "...",
  "eligibility_tldr": "...",
  "budget": {"direct_cost_cap": null, "total_cost_cap": null, "project_period_max": null},
  "mechanisms": ["R01"],
  "career_stages": ["any"],
  "topics": ["aging"],
  "dos": ["..."],
  "donts": ["..."],
  "strategic_priorities": []
}
```

- `career_stages` from: trainee, early_career, midcareer, established, any.
- `topics` from the keys of `data/taxonomy.json` `topics`; 0-4 tags.
- For funding opportunities, aim for 3-7 concrete items per list; for administrative notices, 1-2 suffice.

c. **Apply.** Edit the item JSON directly with the Edit tool: add your keys
   plus `"llm_model": "claude-via-claude-code"` and
   `"enriched_at": "<current UTC ISO>"`. Keep JSON valid, 2-space indented,
   keys sorted (match the file's existing style).

## 3. Every 10 items, checkpoint

```sh
python3 -m pipeline.refresh --emit-only
git add data/
git commit -m "data: LLM enrichment batch ($(date -u +%Y-%m-%d))"
```

## 4. When done

```sh
python3 -m pipeline.refresh --emit-only
git add data/
git commit -m "data: LLM enrichment complete ($(date -u +%Y-%m-%d))" || true
git push
```
