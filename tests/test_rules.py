"""Tests for the rule engine.

The behaviour these pin hardest is what the linter does NOT do: it ships no
naming opinions, it never guesses a column's type, and it never reports a
clean bill of health for a file it could not parse.
"""
from __future__ import annotations

import pathlib

import pytest

from dbsqlparse.analysis import analyse, canonical_type
from dbsqlparse.linter import lint_text
from dbsqlparse.parser import parse_statement
from dbsqlparse.rules import Config, ConfigError, load_config, rule_ids

EXAMPLES = pathlib.Path(__file__).resolve().parents[1] / "examples"


def config_from(toml: str, tmp_path: pathlib.Path) -> Config:
    path = tmp_path / ".dbsqlparse.toml"
    path.write_text(toml)
    return load_config(path)


def rule_names(result) -> list[str]:
    return sorted(v.rule for v in result.violations)


# --- the project ships no conventions ---------------------------------------


def test_no_config_means_no_violations():
    """Syntax is still checked; style is not. A linter that invents opinions
    on first run gets uninstalled."""
    sql = "CREATE TABLE T (BadlyNamed BOOLEAN); SELECT * FROM t; DROP TABLE x;"
    result = lint_text(sql, config=Config())
    assert result.parsed
    assert result.violations == []


def test_type_naming_is_inert_without_patterns(tmp_path):
    config = config_from("[rules.type-naming]\n", tmp_path)
    result = lint_text("CREATE TABLE t (anything BOOLEAN)", config=config)
    assert result.violations == []


# --- type-based naming ------------------------------------------------------


def test_type_naming_flags_a_mismatched_column(tmp_path):
    config = config_from(
        '[rules.type-naming]\npatterns = { BOOLEAN = "_ind$" }\n', tmp_path
    )
    result = lint_text("CREATE TABLE t (active BOOLEAN)", config=config)
    assert rule_names(result) == ["type-naming"]
    assert "BOOLEAN" in result.violations[0].message


def test_type_naming_accepts_a_matching_column(tmp_path):
    config = config_from(
        '[rules.type-naming]\npatterns = { BOOLEAN = "_ind$" }\n', tmp_path
    )
    assert lint_text("CREATE TABLE t (active_ind BOOLEAN)", config=config).violations == []


def test_type_naming_reads_explicit_casts(tmp_path):
    config = config_from(
        '[rules.type-naming]\npatterns = { BOOLEAN = "_ind$" }\n', tmp_path
    )
    result = lint_text("SELECT CAST(x AS BOOLEAN) AS active FROM t", config=config)
    assert rule_names(result) == ["type-naming"]


def test_type_naming_skips_columns_whose_type_is_unknown(tmp_path):
    """The rule must never guess. `foo AS bar` has no locally knowable type."""
    config = config_from(
        '[rules.type-naming]\npatterns = { BOOLEAN = "_ind$" }\n', tmp_path
    )
    assert lint_text("SELECT foo AS active FROM t", config=config).violations == []


def test_type_naming_honours_type_aliases(tmp_path):
    """INT and INTEGER are the same type; a config should not have to say both."""
    config = config_from(
        '[rules.type-naming]\npatterns = { INTEGER = "_num$" }\n', tmp_path
    )
    result = lint_text("CREATE TABLE t (thing INT)", config=config)
    assert rule_names(result) == ["type-naming"]


def test_type_naming_ignores_type_parameters(tmp_path):
    config = config_from(
        '[rules.type-naming]\npatterns = { DECIMAL = "_amount$" }\n', tmp_path
    )
    result = lint_text("CREATE TABLE t (price DECIMAL(10,2))", config=config)
    assert rule_names(result) == ["type-naming"]


def test_type_naming_can_be_restricted_to_declarations(tmp_path):
    config = config_from(
        '[rules.type-naming]\npatterns = { BOOLEAN = "_ind$" }\norigins = ["declaration"]\n',
        tmp_path,
    )
    assert lint_text("SELECT CAST(x AS BOOLEAN) AS active FROM t", config=config).violations == []


# --- identifier style -------------------------------------------------------


@pytest.mark.parametrize(
    "case,name,ok",
    [
        ("snake", "order_id", True),
        ("snake", "orderId", False),
        ("snake", "Order_Id", False),
        ("upper_snake", "ORDER_ID", True),
        ("upper_snake", "order_id", False),
        ("camel", "orderId", True),
        ("camel", "order_id", False),
        ("pascal", "OrderId", True),
        ("pascal", "orderId", False),
    ],
)
def test_identifier_case(case, name, ok, tmp_path):
    # tables = false: this test is about the column, and the table name `t`
    # would itself fail upper_snake and pascal.
    config = config_from(
        f'[rules.identifier-case]\ncase = "{case}"\ntables = false\n', tmp_path
    )
    result = lint_text(f"CREATE TABLE t ({name} STRING)", config=config)
    assert (result.violations == []) is ok


def test_identifier_length(tmp_path):
    config = config_from("[rules.identifier-length]\nmax_length = 5\n", tmp_path)
    result = lint_text("CREATE TABLE t (way_too_long STRING)", config=config)
    assert rule_names(result) == ["identifier-length"]


def test_forbidden_name_reports_the_configured_reason(tmp_path):
    config = config_from(
        '[rules.forbidden-name]\npatterns = { "^tmp_" = "do not commit temp tables" }\n',
        tmp_path,
    )
    result = lint_text("CREATE TABLE t (tmp_value STRING)", config=config)
    assert rule_names(result) == ["forbidden-name"]
    assert result.violations[0].suggestion == "do not commit temp tables"


# --- metadata ---------------------------------------------------------------


def test_require_comment_on_tables(tmp_path):
    config = config_from("[rules.require-comment]\ntables = true\n", tmp_path)
    assert rule_names(lint_text("CREATE TABLE t (a STRING)", config=config)) == [
        "require-comment"
    ]
    assert lint_text("CREATE TABLE t (a STRING) COMMENT 'x'", config=config).violations == []


def test_require_comment_on_columns(tmp_path):
    config = config_from(
        "[rules.require-comment]\ntables = false\ncolumns = true\n", tmp_path
    )
    assert rule_names(lint_text("CREATE TABLE t (a STRING)", config=config)) == [
        "require-comment"
    ]
    assert (
        lint_text("CREATE TABLE t (a STRING COMMENT 'why')", config=config).violations == []
    )


def test_require_table_properties_checks_values(tmp_path):
    config = config_from(
        '[rules.require-table-properties]\nrequired_values = { "delta.cdf" = "true" }\n',
        tmp_path,
    )
    missing = lint_text("CREATE TABLE t (a STRING)", config=config)
    assert rule_names(missing) == ["require-table-properties"]

    wrong = lint_text(
        "CREATE TABLE t (a STRING) TBLPROPERTIES ('delta.cdf' = 'false')", config=config
    )
    assert rule_names(wrong) == ["require-table-properties"]

    right = lint_text(
        "CREATE TABLE t (a STRING) TBLPROPERTIES ('delta.cdf' = 'true')", config=config
    )
    assert right.violations == []


def test_require_table_provider(tmp_path):
    config = config_from(
        '[rules.require-table-provider]\nallowed = ["delta"]\n', tmp_path
    )
    assert lint_text("CREATE TABLE t (a STRING) USING delta", config=config).violations == []
    assert rule_names(lint_text("CREATE TABLE t (a STRING) USING parquet", config=config)) == [
        "require-table-provider"
    ]
    # A missing USING is only a violation when the config asks for it.
    assert lint_text("CREATE TABLE t (a STRING)", config=config).violations == []


def test_require_table_provider_can_demand_an_explicit_using(tmp_path):
    config = config_from(
        '[rules.require-table-provider]\nallowed = ["delta"]\nrequire_explicit = true\n',
        tmp_path,
    )
    assert rule_names(lint_text("CREATE TABLE t (a STRING)", config=config)) == [
        "require-table-provider"
    ]


# --- anti-patterns ----------------------------------------------------------


def test_no_select_star(tmp_path):
    config = config_from("[rules.no-select-star]\n", tmp_path)
    assert rule_names(lint_text("SELECT * FROM t", config=config)) == ["no-select-star"]
    assert lint_text("SELECT a FROM t", config=config).violations == []


def test_no_select_star_can_allow_qualified(tmp_path):
    config = config_from(
        "[rules.no-select-star]\nallow_qualified = true\n", tmp_path
    )
    assert lint_text("SELECT t.* FROM t", config=config).violations == []
    assert rule_names(lint_text("SELECT * FROM t", config=config)) == ["no-select-star"]


def test_drop_requires_if_exists(tmp_path):
    config = config_from("[rules.drop-requires-if-exists]\n", tmp_path)
    assert rule_names(lint_text("DROP TABLE t", config=config)) == [
        "drop-requires-if-exists"
    ]
    assert lint_text("DROP TABLE IF EXISTS t", config=config).violations == []


def test_insert_requires_column_list(tmp_path):
    config = config_from("[rules.insert-requires-column-list]\n", tmp_path)
    assert rule_names(lint_text("INSERT INTO t SELECT * FROM s", config=config)) == [
        "insert-requires-column-list"
    ]
    assert (
        lint_text("INSERT INTO t (a) SELECT a FROM s", config=config).violations == []
    )
    assert (
        lint_text("INSERT INTO t BY NAME SELECT 1 AS a", config=config).violations == []
    )


# --- config handling --------------------------------------------------------


def test_unknown_rule_is_an_error_naming_the_valid_ones(tmp_path):
    with pytest.raises(ConfigError) as exc:
        config_from("[rules.no-such-rule]\n", tmp_path)
    assert "no-such-rule" in str(exc.value)
    assert "no-select-star" in str(exc.value)  # lists what is available


def test_unknown_option_is_an_error(tmp_path):
    """A typo in a config key must fail, not silently do nothing."""
    with pytest.raises(ConfigError) as exc:
        config_from("[rules.no-select-star]\nallow_qualifed = true\n", tmp_path)
    assert "allow_qualifed" in str(exc.value)


def test_invalid_severity_is_an_error(tmp_path):
    with pytest.raises(ConfigError):
        config_from('[rules.no-select-star]\nseverity = "critical"\n', tmp_path)


def test_invalid_regex_is_an_error(tmp_path):
    with pytest.raises(ConfigError) as exc:
        config_from('[rules.type-naming]\npatterns = { BOOLEAN = "([" }\n', tmp_path)
    assert "regex" in str(exc.value)


def test_rule_can_be_disabled_in_place(tmp_path):
    config = config_from(
        "[rules.no-select-star]\nenabled = false\n", tmp_path
    )
    assert config.rules == []


def test_severity_is_configurable(tmp_path):
    config = config_from('[rules.no-select-star]\nseverity = "error"\n', tmp_path)
    result = lint_text("SELECT * FROM t", config=config)
    assert result.violations[0].severity == "error"
    assert result.error_count == 1


def test_warnings_do_not_count_as_errors(tmp_path):
    config = config_from('[rules.no-select-star]\nseverity = "warning"\n', tmp_path)
    result = lint_text("SELECT * FROM t", config=config)
    assert result.violations and result.error_count == 0


def test_config_is_discovered_by_walking_upward(tmp_path):
    from dbsqlparse.rules import find_config

    (tmp_path / ".dbsqlparse.toml").write_text("[rules.no-select-star]\n")
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    assert find_config(nested) == tmp_path / ".dbsqlparse.toml"


def test_pyproject_section_is_discovered(tmp_path):
    from dbsqlparse.rules import find_config, load_config

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "x"\n\n[tool.dbsqlparse.rules.no-select-star]\nseverity = "error"\n'
    )
    assert find_config(tmp_path) == pyproject
    assert len(load_config(pyproject).rules) == 1


def test_pyproject_without_our_section_is_ignored(tmp_path):
    from dbsqlparse.rules import find_config

    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n')
    assert find_config(tmp_path) is None


# --- the unparseable-file contract ------------------------------------------


def test_unparseable_file_is_reported_and_not_silently_clean():
    """A file no rule could check must not look like a file that passed."""
    result = lint_text("SELECT ((( FROM", config=Config())
    assert not result.parsed
    assert result.statements_checked == 0
    assert result.error_count > 0


def test_rules_skip_statements_that_failed_to_parse(tmp_path):
    config = config_from("[rules.no-select-star]\n", tmp_path)
    result = lint_text("SELECT * FROM t;\nSELECT ((( FROM;", config=config)
    # The good statement is still checked; the broken one is not.
    assert result.statements_checked == 1
    assert rule_names(result) == ["no-select-star"]
    assert not result.parsed


# --- shipped examples -------------------------------------------------------


@pytest.mark.parametrize(
    "name", sorted(p.name for p in EXAMPLES.glob("*.toml"))
)
def test_example_config_loads(name):
    config = load_config(EXAMPLES / name)
    assert config.rules, f"{name} enables no rules"


def test_examples_show_opposite_conventions():
    """The two team examples must genuinely disagree, or they prove nothing
    about the engine being convention-neutral."""
    suffix = load_config(EXAMPLES / "snake-case-team.toml")
    prefix = load_config(EXAMPLES / "hungarian-team.toml")

    naming = {"type-naming", "forbidden-name"}

    def naming_violations(sql: str, config) -> list[str]:
        return [v.rule for v in lint_text(sql, config=config).violations if v.rule in naming]

    # Each convention accepts its own spelling and rejects the other's.
    assert naming_violations("CREATE TABLE t (active_ind BOOLEAN)", suffix) == []
    assert naming_violations("CREATE TABLE t (active_ind BOOLEAN)", prefix) != []

    assert naming_violations("CREATE TABLE t (is_active BOOLEAN)", suffix) != []
    assert naming_violations("CREATE TABLE t (is_active BOOLEAN)", prefix) == []


def test_every_registered_rule_is_documented():
    from dbsqlparse.rules import get

    for rule_id in rule_ids():
        rule_cls = get(rule_id)
        assert rule_cls.description, f"{rule_id} has no description"
        assert rule_cls.default_severity in ("error", "warning", "info")


# --- analysis layer ---------------------------------------------------------


@pytest.mark.parametrize(
    "written,expected",
    [
        ("BOOLEAN", "BOOLEAN"),
        ("boolean", "BOOLEAN"),
        ("INT", "INTEGER"),
        ("DECIMAL(10,2)", "DECIMAL"),
        ("ARRAY<INT>", "ARRAY"),
        ("TIMESTAMP_NTZ", "TIMESTAMP"),
        ("varchar(10)", "STRING"),
        (None, None),
    ],
)
def test_canonical_type(written, expected):
    assert canonical_type(written) == expected


def test_analysis_extracts_table_metadata():
    sql = (
        "CREATE TABLE main.raw.t (id BIGINT COMMENT 'pk') USING delta "
        "COMMENT 'table doc' TBLPROPERTIES ('k' = 'v')"
    )
    analysis = analyse(parse_statement(sql).tree)
    assert len(analysis.tables) == 1
    table = analysis.tables[0]
    assert table.name == "main.raw.t"
    assert table.provider == "delta"
    assert table.comment == "table doc"
    assert table.properties == {"k": "v"}
    assert table.columns[0].comment == "pk"


def test_analysis_strips_backticks_from_identifiers():
    analysis = analyse(parse_statement("CREATE TABLE `odd name` (`a b` STRING)").tree)
    assert analysis.tables[0].name == "odd name"
    assert analysis.columns[0].name == "a b"


def test_analysis_does_not_infer_types_through_arithmetic():
    """CAST(a AS INT) + 1 is an addition, not a cast. We do not infer."""
    analysis = analyse(parse_statement("SELECT CAST(a AS INT) + 1 AS total FROM t").tree)
    total = [c for c in analysis.columns if c.name == "total"][0]
    assert total.data_type is None
