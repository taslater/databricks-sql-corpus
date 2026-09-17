@AGENTS.md

## Claude Code

The file above is the single source of truth for this repo. Nothing
Claude-specific is kept here — add new guidance to `AGENTS.md`.

Use plan mode for anything touching `grammar/` or `scripts/patch_grammar.py`:
a change there regenerates `src/dbsqlparse/generated/`, so the diff is large
and the failure mode (a silently broken parser) is quiet.
