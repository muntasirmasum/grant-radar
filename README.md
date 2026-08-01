# grant-radar

**Live: <https://muntasirmasum.github.io/grant-radar/>**

A weekly radar for NIH funding. Every Sunday a GitHub Action pulls structured
records from the official NIH Guide search API and joins funding opportunities
to Grants.gov for synopses, award ceilings, and close dates. For the newer
NOFOs that NIH no longer publishes HTML pages for (about a quarter of open
opportunities), the Grants.gov detail page also serves as the card's canonical
link. The result is published as a static editorial digest: real opportunities
with deadline countdowns up front, policy chatter demoted, and a client-side
profile that ranks what matters to you.

## Architecture

```
NIH Guide API ─┐
               ├─ pipeline/refresh.py ── data/notices/<yr>/<id>.json  (one file per item)
Grants.gov  ───┘        │
                        ├── data/notices.json   (site payload)
                        └── data/feed.xml       (RSS)
                                 │
                    pages-deploy stages both into site/ → GitHub Pages
```

- **Anti-clobber contract:** the refresh only writes structured fields. LLM
  fields (`purpose_tldr`, `dos`, `donts`, ...) are added manually by running
  `/refresh-tldrs` in Claude Code and are never overwritten.
- **Site:** plain HTML/CSS/JS in `site/`, no build step. Design system shared
  with [muntasirmasum.com](https://muntasirmasum.com).

## Local development

```sh
pip install -r pipeline/requirements.txt pytest
python -m pytest pipeline/tests          # pipeline tests
node --test tests/js/*.test.mjs          # frontend logic tests

python -m pipeline.refresh               # real refresh (writes data/)
cp data/notices.json data/feed.xml site/
python -m http.server 8080 --directory site
```

## Enrichment

Open the repo in Claude Code and run `/refresh-tldrs`. It walks every item
missing a `purpose_tldr` (profile matches and nearest deadlines first), writes
the LLM-owned fields, and rebuilds the site payload with
`python -m pipeline.refresh --emit-only`.

## License

MIT.
