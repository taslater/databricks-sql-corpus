@AGENTS.md

## Claude Code

The file above is the single source of truth for this repo. Nothing
Claude-specific is kept here — add new guidance to `AGENTS.md`.

Use plan mode before changing `src/dbsqlparse/corpus/sources.py` or the
mutation tiers in `corpus/mutate.py`. A wrong source silently reshapes every
number the harness reports, and a mis-tiered mutation reports correct
behaviour as a failure — both fail quietly rather than loudly.
