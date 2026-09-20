# Staying current with the Databricks SQL reference

The corpus measures SQLFluff against a reference that keeps moving. Two things
go stale independently: the **reference pages** (Databricks edits a production)
and the **SQLFluff engine** (a release fixes a gap or introduces a regression).
This is the cadence that catches both, and what to do with what it finds.

The corpus is the oracle. Every check below **reports**; none of them edits
`corpus/reference/`. A finding is dispositioned by a person (or an agent) who
re-reads the page and changes the file — otherwise the corpus would just mirror
whatever the page last said, which is the opposite of an oracle.

## The checks

| command | what it catches | network |
| --- | --- | --- |
| `make stale` | pages not re-read in `STALE_DAYS` (default 90) | no |
| `make drift` | a production that changed under its transcription | yes |
| `make index-check` | documented statement pages with no file; files whose page is gone | yes |
| `make sources-check` | a pinned scraped-corpus source that is behind its repo | yes |
| `make baseline PY=.venv-release/bin/python` | the released engine's behaviour | no |

`make drift`, `make index-check` and `make sources-check` are `stale`-agnostic:
run them whenever, they always compare against the live site.

## Cadence

**Monthly** — `.github/workflows/drift.yml` runs the four checks and opens one
rolling issue labelled `drift`. It runs on GitHub's infrastructure against
public pages, so it is not work hardware. To run it by hand:

```bash
make stale
make drift
make index-check
make sources-check          # set GITHUB_TOKEN to avoid the anonymous rate limit
```

**On every SQLFluff release, and after any dialect merge of ours:**

```bash
make baseline PY=.venv-release/bin/python
git diff corpus/reports/baseline.json
```

Read the diff, not just the totals. `scripts/compare_baseline.py` distinguishes
a newly added case that fails (new coverage, the corpus working) from a case
flipping from conforming to not (a regression). A reference case that newly
*passes* is a gap closing — strike it from `docs/gaps.md`.

**Quarterly** — revisit the scraped corpus: `make sources-check` lists how far
each pinned revision is behind. To bump one, edit its `ref:` in
`src/dbsqlparse/corpus/sources.py` to the current default-branch SHA, then
`make corpus` and read the baseline diff. Adding a new source is documented in
`AGENTS.md`.

## What to do with a `make drift` finding

- **`changed`** — the page's production no longer matches `syntax:`. Read the
  live page, update `syntax:` to the new production and add or adjust cases for
  any clause that appeared or disappeared, then set `checked:` to today. If the
  new syntax is not parseable, add the case and record the gap in
  `docs/gaps.md`. The report prints a token diff against the closest block so
  the review has a starting point.
- **`moved`** — the page redirected or 404s. Update `doc:` to the new URL, or
  retire the file if the statement is gone.
- **`uncertain`** — no diffable production on the page (`magic_cells.yml` is
  the standing example, and is permanently uncertain). Re-read it by hand when
  touching the file; it is not a mechanical check, and it does not open the
  monthly issue on its own, or the issue would never close.
- **`fetch-error`** — the site was unreachable. Re-run; if it persists, check
  the URL.

## What to do with a `make index-check` finding

- **`new`** — a documented statement page with no file. Decide: transcribe it
  (a `done` file, per the workflow in `docs/reference-corpus-plan.md`), mark it
  `n/a` in `docs/reference-coverage.md` (a catalogue, a landing page, an alias),
  or suppress it in `docs/reference-index-ignore.txt` if it is inside a watched
  family but is known not to be a statement of its own.
- **`gone`** — a file's page is no longer in the sitemap. Find where it moved
  and update `doc:`, or retire the file.

`docs/reference-drift.md` is the ledger: the open findings, and what was
decided about the resolved ones. Update it whenever a finding is dispositioned.

## The one thing not to automate

Do **not** make the checks rewrite `corpus/reference/*.yml`. A transcription is
a reading of the page plus a judgement about which partial forms to pin as
`must-reject`; overwriting it from the page would discard the judgement and
make the corpus agree with whatever the page last rendered. The checks exist to
tell a human which pages to read, not to read them.
