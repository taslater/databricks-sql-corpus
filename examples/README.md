# Example configurations

`dbsqlparse` ships no naming conventions of its own. Every rule is off until a
config turns it on, and the naming rules do nothing until a config supplies
patterns. What a column should be called is a decision for the team adopting
the tool.

These are starting points, not recommendations. Copy one to `.dbsqlparse.toml`
at the root of your repo and edit it.

| file | what it is |
| --- | --- |
| `minimal.toml` | Syntax plus the two anti-patterns almost everyone agrees on |
| `recommended.toml` | A broadly sensible set with no naming opinions |
| `strict.toml` | Everything on, tuned for a tightly governed platform |
| `snake-case-team.toml` | snake_case with type suffixes (`_ind`, `_date`, `_timestamp`) |
| `hungarian-team.toml` | Type *prefixes* instead (`is_`, `dt_`, `ts_`) -- the opposite convention, to show the rules do not favour either |

Run `dbsqlparse --list-rules` to see every rule and its options.
