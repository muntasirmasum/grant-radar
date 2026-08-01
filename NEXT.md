# Where we left off — 2026-07-31

## State

- Full revision shipped: editorial digest UI (muntasirmasum.com design system)
  + Python API pipeline (NIH Guide + Grants.gov). Spec:
  `docs/superpowers/specs/2026-07-31-grant-radar-revision-design.md`.
- R package, Quarto remnants, and parquet are gone (git history has them).
- Weekly cron refreshes structured data; `/refresh-tldrs` remains the manual,
  free enrichment step and can never be clobbered by the cron.

## To resume

```sh
cd ~/projects/grant-radar && git pull
python -m pytest pipeline/tests && node --test tests/js/*.test.mjs
```

## Open items, ranked

1. Run `/refresh-tldrs` for the current profile-matched queue.
2. Watch the next two Sunday crons (Actions tab); first unattended runs.
3. Link Grant Radar from muntasirmasum.com (studio/tools page).
4. Later (spec §10): NSF/AHRQ sources, automated enrichment, OG images,
   per-item permalinks.
