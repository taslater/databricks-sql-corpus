"""Coverage of Databricks syntax that OSS Spark's grammar does not include.

Databricks SQL is a superset of Spark SQL. Everything the two share comes from
the vendored Spark grammar; the Databricks-only surface -- Delta operations and
Unity Catalog DDL -- is added by the fragments in grammar/extensions/ and
injected during the patch step.

GAPS is the remaining backlog, written as `xfail(strict=True)`: while a gap is
open the suite stays green and the gap stays visible, and the moment someone
closes one its XPASS turns the suite RED, forcing the entry up into SUPPORTED.
The inventory can only shrink deliberately.
"""
from __future__ import annotations

import pathlib

import pytest

from dbsqlparse.parser import ParseOptions, parse_statement

KEYWORDS_FILE = (
    pathlib.Path(__file__).resolve().parents[1] / "grammar" / "extensions" / "keywords.txt"
)


def _extension_keywords() -> list[str]:
    words = []
    for line in KEYWORDS_FILE.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            words.append(line)
    return words


# --- Databricks syntax Spark's own grammar already accepts -------------------
SPARK_NATIVE = {
    "grant": "GRANT SELECT ON TABLE main.raw.t TO `group`",
    "time-travel-version": "SELECT * FROM t VERSION AS OF 3",
    "time-travel-timestamp": "SELECT * FROM t TIMESTAMP AS OF '2024-01-01'",
    "identifier-fn": "SELECT * FROM IDENTIFIER('main.raw.t')",
    "read-files": "SELECT * FROM read_files('/vol/x', format => 'csv')",
    "describe-history": "DESCRIBE HISTORY main.raw.t",
    "liquid-clustering": "CREATE TABLE t (id BIGINT) CLUSTER BY (id)",
    "ai-query": "SELECT ai_query('ep', 'prompt')",
    "pivot": "SELECT * FROM t PIVOT (sum(x) FOR y IN ('a','b'))",
    "lateral-view": "SELECT * FROM t LATERAL VIEW explode(arr) AS e",
}

# --- Databricks-only syntax added by grammar/extensions/ ---------------------
EXTENSIONS = {
    # OPTIMIZE / ZORDER
    "optimize": "OPTIMIZE main.raw.t",
    "optimize-full": "OPTIMIZE main.raw.t FULL",
    "optimize-where": "OPTIMIZE main.raw.t WHERE dt >= '2024-01-01'",
    "optimize-zorder": "OPTIMIZE main.raw.t ZORDER BY (id, dt)",
    "optimize-zorder-bare": "OPTIMIZE main.raw.t ZORDER BY id, dt",
    "optimize-where-zorder": "OPTIMIZE t WHERE dt > '2024-01-01' ZORDER BY (id)",
    # VACUUM
    "vacuum": "VACUUM main.raw.t",
    "vacuum-retain": "VACUUM main.raw.t RETAIN 168 HOURS",
    "vacuum-dry-run": "VACUUM main.raw.t RETAIN 0 HOURS DRY RUN",
    "vacuum-path": "VACUUM '/mnt/delta/events'",
    # COPY INTO
    "copy-into": "COPY INTO main.raw.t FROM '/vol/x' FILEFORMAT = CSV",
    "copy-into-subquery": (
        "COPY INTO main.raw.t FROM (SELECT CAST(a AS BIGINT) FROM '/vol/x') "
        "FILEFORMAT = PARQUET"
    ),
    "copy-into-options": (
        "COPY INTO main.raw.t FROM '/vol/x' FILEFORMAT = CSV "
        "PATTERN = '*.csv' "
        "FORMAT_OPTIONS ('header' = 'true') "
        "COPY_OPTIONS ('mergeSchema' = 'true')"
    ),
    "copy-into-files": (
        "COPY INTO main.raw.t FROM '/vol/x' FILEFORMAT = JSON FILES = ('a.json', 'b.json')"
    ),
    "copy-into-validate": "COPY INTO main.raw.t FROM '/vol/x' FILEFORMAT = CSV VALIDATE ALL",
    "copy-into-columns": (
        "COPY INTO main.raw.t (id, nm) FROM '/vol/x' FILEFORMAT = CSV"
    ),
    # Streaming tables / materialized views
    "create-streaming-table": "CREATE STREAMING TABLE t AS SELECT * FROM STREAM(s)",
    "create-or-refresh-streaming-table": (
        "CREATE OR REFRESH STREAMING TABLE main.raw.t AS SELECT * FROM STREAM(src)"
    ),
    "create-streaming-table-cols": (
        "CREATE STREAMING TABLE t (id BIGINT COMMENT 'pk') "
        "COMMENT 'landing' TBLPROPERTIES ('quality' = 'bronze') "
        "AS SELECT * FROM STREAM(src)"
    ),
    "create-materialized-view": "CREATE MATERIALIZED VIEW mv AS SELECT 1",
    "create-materialized-view-schedule": (
        "CREATE MATERIALIZED VIEW mv COMMENT 'daily' "
        "SCHEDULE CRON '0 0 * * * ?' AS SELECT 1"
    ),
    "refresh-materialized-view": "REFRESH MATERIALIZED VIEW mv",
    "refresh-streaming-table": "REFRESH STREAMING TABLE t FULL",
    # The LIVE spelling, which every published DLT pipeline still uses.
    "create-live-table": "CREATE LIVE TABLE t AS SELECT 1",
    "create-or-refresh-live-table": "CREATE OR REFRESH LIVE TABLE t AS SELECT 1",
    "create-streaming-live-table": "CREATE STREAMING LIVE TABLE t",
    "create-or-refresh-materialized-view": (
        "CREATE OR REFRESH MATERIALIZED VIEW mv AS SELECT 1"
    ),
    "create-temporary-streaming-table": (
        "CREATE OR REFRESH TEMPORARY STREAMING TABLE t AS SELECT 1"
    ),
    # STREAM prefixing a relation, the form DLT sources are written in.
    "stream-relation": "SELECT * FROM STREAM orders_bronze",
    "stream-table-valued-function": (
        "SELECT * FROM STREAM read_files('/vol/x', format => 'json')"
    ),
    # DLT expectations, with and without an ON VIOLATION action.
    "expectation-drop-row": (
        "CREATE STREAMING TABLE t "
        "(CONSTRAINT valid EXPECT (id IS NOT NULL) ON VIOLATION DROP ROW)"
    ),
    "expectation-fail-update": (
        "CREATE STREAMING TABLE t "
        "(CONSTRAINT valid EXPECT (n > 0) ON VIOLATION FAIL UPDATE)"
    ),
    "expectation-bare": "CREATE STREAMING TABLE t (CONSTRAINT valid EXPECT (n > 0))",
    # Constraints inside a column list, inline and table-level.
    "inline-primary-key": "CREATE TABLE t (k BIGINT NOT NULL PRIMARY KEY)",
    "inline-foreign-key": (
        "CREATE TABLE t (k BIGINT NOT NULL FOREIGN KEY REFERENCES other.dim)"
    ),
    "inline-named-foreign-key": (
        "CREATE TABLE t (k BIGINT CONSTRAINT k_fk FOREIGN KEY REFERENCES other.dim)"
    ),
    "table-level-primary-key": (
        "CREATE TABLE t (k BIGINT, CONSTRAINT pk PRIMARY KEY (k))"
    ),
    # Unity Catalog objects
    "create-volume": "CREATE VOLUME main.raw.v",
    "create-external-volume": (
        "CREATE EXTERNAL VOLUME IF NOT EXISTS main.raw.v "
        "LOCATION 's3://bucket/path' COMMENT 'landing zone'"
    ),
    "drop-volume": "DROP VOLUME IF EXISTS main.raw.v",
    "create-catalog": "CREATE CATALOG IF NOT EXISTS main",
    "create-catalog-comment": "CREATE CATALOG main COMMENT 'prod' ",
    "create-catalog-share": "CREATE CATALOG main USING SHARE provider.share_name",
    "drop-catalog": "DROP CATALOG IF EXISTS main CASCADE",
    # Delta table management
    "restore-version": "RESTORE TABLE t TO VERSION AS OF 3",
    "restore-timestamp": "RESTORE TABLE main.raw.t TO TIMESTAMP AS OF '2024-01-01'",
    "shallow-clone": "CREATE TABLE b SHALLOW CLONE a",
    "deep-clone": "CREATE TABLE main.raw.b DEEP CLONE main.raw.a",
    "clone-version": "CREATE TABLE b SHALLOW CLONE a VERSION AS OF 7",
    "clone-replace": "CREATE OR REPLACE TABLE b DEEP CLONE a LOCATION '/mnt/b'",
    # Tags
    "set-tags": "ALTER TABLE t SET TAGS ('k' = 'v')",
    "unset-tags": "ALTER TABLE t UNSET TAGS ('k')",
    "set-tags-catalog": "ALTER CATALOG main SET TAGS ('owner' = 'data-eng')",
    "set-tags-schema": "ALTER SCHEMA main.raw SET TAGS ('pii' = 'false')",
    # Constraints
    "add-constraint": "ALTER TABLE t ADD CONSTRAINT c CHECK (id > 0)",
    "add-constraint-primary-key": "ALTER TABLE t ADD CONSTRAINT pk PRIMARY KEY (id)",
    "add-constraint-foreign-key": (
        "ALTER TABLE t ADD CONSTRAINT fk FOREIGN KEY (a_id) REFERENCES main.raw.a (id)"
    ),
    "drop-constraint": "ALTER TABLE t DROP CONSTRAINT IF EXISTS c",
    # QUALIFY
    "qualify": "SELECT *, row_number() OVER (ORDER BY a) rn FROM t QUALIFY rn = 1",
    "qualify-inline-window": (
        "SELECT a FROM t QUALIFY row_number() OVER (PARTITION BY a ORDER BY b) = 1"
    ),
    "qualify-with-where-group-having": (
        "SELECT a, count(*) c FROM t WHERE a > 0 GROUP BY a HAVING count(*) > 1 "
        "QUALIFY row_number() OVER (ORDER BY a) = 1"
    ),
    # Path relations
    "path-relation": "SELECT * FROM '/vol/landing/events'",
    "path-relation-aliased": "SELECT e.a FROM '/vol/landing' AS e",
    # Unity Catalog governance
    "use-catalog": "USE CATALOG main",
    "set-owner": "ALTER TABLE t SET OWNER TO `data-eng`",
    "set-owner-no-set": "ALTER SCHEMA main.raw OWNER TO `data-eng`",
    "alter-catalog-owner": "ALTER CATALOG main OWNER TO `admins`",
    "comment-on-column": "COMMENT ON COLUMN main.raw.t.id IS 'pk'",
    "comment-on-column-null": "COMMENT ON COLUMN main.raw.t.id IS NULL",
    "create-connection": "CREATE CONNECTION c TYPE mysql OPTIONS (host 'h', port '3306')",
    "drop-connection": "DROP CONNECTION IF EXISTS c",
    "create-external-location": (
        "CREATE EXTERNAL LOCATION el URL 's3://b/p' WITH (STORAGE CREDENTIAL sc) "
        "COMMENT 'landing'"
    ),
    "create-storage-credential": (
        "CREATE STORAGE CREDENTIAL sc WITH IAM_ROLE 'arn:aws:iam::1:role/r'"
    ),
    "create-share": "CREATE SHARE sh COMMENT 'x'",
    "alter-share-add-table": "ALTER SHARE sh ADD TABLE main.raw.t",
    "alter-share-remove-table": "ALTER SHARE sh REMOVE TABLE main.raw.t",
    "create-recipient": "CREATE RECIPIENT r USING ID 'abc' COMMENT 'partner'",
    # Row filters and column masks
    "row-filter": "ALTER TABLE t SET ROW FILTER f ON (region)",
    "drop-row-filter": "ALTER TABLE t DROP ROW FILTER",
    "column-mask": "ALTER TABLE t ALTER COLUMN ssn SET MASK m",
    "column-mask-using": (
        "ALTER TABLE t ALTER COLUMN ssn SET MASK m USING COLUMNS (region, tier)"
    ),
    "drop-column-mask": "ALTER TABLE t ALTER COLUMN ssn DROP MASK",
    # Maintenance
    "predictive-optimization": "ALTER TABLE t ENABLE PREDICTIVE OPTIMIZATION",
    "predictive-optimization-inherit": "ALTER SCHEMA main.raw INHERIT PREDICTIVE OPTIMIZATION",
    "sync-schema": "SYNC SCHEMA main.raw FROM hive_metastore.raw",
    "sync-table": "SYNC TABLE main.raw.t FROM hive_metastore.raw.t",
    "cache-select": "CACHE SELECT * FROM t",
    "cache-lazy-select": "CACHE LAZY SELECT a, b FROM t WHERE a > 1",
    "cluster-by-auto": "CREATE TABLE t (id BIGINT) CLUSTER BY AUTO",
    "show-volumes": "SHOW VOLUMES IN main.raw",
    "show-shares": "SHOW SHARES",
    "show-connections": "SHOW CONNECTIONS",
    # Delta table utilities
    "convert-to-delta": "CONVERT TO DELTA parquet.`/path`",
    "convert-to-delta-partitioned": "CONVERT TO DELTA parquet.`/path` PARTITIONED BY (dt DATE)",
    "fsck-repair": "FSCK REPAIR TABLE main.raw.t",
    "generate-manifest": "GENERATE symlink_format_manifest FOR TABLE main.raw.t",
    "reorg-purge": "REORG TABLE main.raw.t APPLY (PURGE)",
    "reorg-uniform": "REORG TABLE t APPLY (UPGRADE UNIFORM (ICEBERG_COMPAT_VERSION = 2))",
    "drop-feature": "ALTER TABLE t DROP FEATURE deletionVectors TRUNCATE HISTORY",
    "vacuum-lite": "VACUUM main.raw.t LITE",
    "vacuum-full": "VACUUM main.raw.t FULL RETAIN 168 HOURS",
    "list-volume-path": "LIST '/Volumes/main/raw/v'",
    # Lakeflow declarative pipelines
    "apply-changes": (
        "APPLY CHANGES INTO main.raw.t FROM STREAM(src) KEYS (id) "
        "SEQUENCE BY ts STORED AS SCD TYPE 2"
    ),
    "apply-changes-full": (
        "APPLY CHANGES INTO t FROM STREAM(src) KEYS (id) "
        "IGNORE NULL UPDATES APPLY AS DELETE WHEN op = 'D' "
        "SEQUENCE BY ts COLUMNS * EXCEPT (op) STORED AS SCD TYPE 1"
    ),
    "create-flow": "CREATE FLOW f AS INSERT INTO t BY NAME SELECT * FROM STREAM(s)",
    # Principals and privileges
    "show-groups": "SHOW GROUPS",
    "show-users": "SHOW USERS",
    "deny": "DENY SELECT ON TABLE main.raw.t TO `g`",
    "deny-multi": "DENY SELECT, MODIFY ON SCHEMA main.raw TO `g`",
    "deny-all-privileges": "DENY ALL PRIVILEGES ON CATALOG main TO `g`",
    "deny-read-volume": "DENY READ VOLUME ON VOLUME main.raw.v TO `g`",
    # Semi-structured data
    "variant-path": "SELECT v:key::string FROM t",
    "variant-nested-path": "SELECT payload:user.id FROM events",
    "variant-bracket-path": "SELECT v:['odd key']['nested'] FROM t",
    "variant-array-index": "SELECT v:items[0].name FROM t",
    "object-type": "CREATE TABLE t (o OBJECT<a: INT>)",
    "object-type-nested": "CREATE TABLE t (o OBJECT<a: MAP<STRING, INT>>)",
}


# Adding VARIANT colon paths and the OBJECT type touched the expression and
# type grammars, which is where a careless change breaks ordinary SQL. These
# pin the behaviour that had to survive.
STILL_WORKS = {
    "named-parameter": "SELECT * FROM t WHERE id = :my_param",
    "double-colon-cast": "SELECT a::bigint FROM t",
    "struct-type": "CREATE TABLE t (s STRUCT<a: INT, b: STRING>)",
    "nested-complex-type": "SELECT CAST(x AS MAP<STRING, ARRAY<INT>>) FROM t",
    "shift-right-operator": "SELECT 1 >> 2 FROM t",
    "using-delta": "CREATE TABLE t (id BIGINT) USING delta",
    "delta-tblproperties": (
        "CREATE TABLE t (id BIGINT) USING DELTA "
        "TBLPROPERTIES ('delta.minReaderVersion' = '3')"
    ),
}


@pytest.mark.parametrize("sql", STILL_WORKS.values(), ids=list(STILL_WORKS))
def test_extensions_did_not_break_existing_syntax(sql):
    assert parse_statement(sql).ok, sql


# Each added alternative shares its opening tokens with a statement Spark
# already had -- CACHE SELECT against CACHE TABLE, CREATE MATERIALIZED VIEW
# against CREATE VIEW, ALTER ... SET TAGS against ALTER ... SET TBLPROPERTIES.
# If an addition were ordered or shaped wrongly it would shadow the original,
# and the failure would look like "this ordinary statement stopped parsing".
NOT_SHADOWED = {
    "cache-table": "CACHE TABLE t",
    "cache-lazy-table": "CACHE LAZY TABLE t AS SELECT 1",
    "create-view": "CREATE VIEW v AS SELECT 1",
    "create-or-replace-view": "CREATE OR REPLACE VIEW v AS SELECT 1",
    "create-table": "CREATE TABLE t (id BIGINT) USING delta",
    "create-table-as-select": "CREATE TABLE t AS SELECT 1",
    "alter-table-set-tblproperties": "ALTER TABLE t SET TBLPROPERTIES ('a'='b')",
    "alter-table-add-columns": "ALTER TABLE t ADD COLUMNS (c STRING)",
    "alter-table-drop-column": "ALTER TABLE t DROP COLUMN c",
    "alter-table-rename": "ALTER TABLE t RENAME TO t2",
    "alter-view": "ALTER VIEW v AS SELECT 1",
    "drop-table": "DROP TABLE IF EXISTS t",
    "create-schema": "CREATE SCHEMA IF NOT EXISTS main.raw",
    "use-namespace": "USE main.raw",
    "use-schema": "USE SCHEMA main.raw",
    "show-tables": "SHOW TABLES IN main.raw",
    "show-columns": "SHOW COLUMNS IN main.raw.t",
    "refresh-table": "REFRESH TABLE main.raw.t",
    "select-from-table": "SELECT * FROM main.raw.t",
    "insert-into": "INSERT INTO t SELECT * FROM s",
    "truncate-table": "TRUNCATE TABLE t",
    "comment-on-table": "COMMENT ON TABLE t IS 'x'",
}


@pytest.mark.parametrize("sql", NOT_SHADOWED.values(), ids=list(NOT_SHADOWED))
def test_spark_statements_are_not_shadowed(sql):
    assert parse_statement(sql).ok, sql

# Still unsupported. Empty for now -- entries go here as they are discovered.
# Found by the public Databricks corpus after it was widened to ~125 files.
# Each is real Databricks syntax this parser does not yet accept, so each is a
# false positive waiting to block someone's merge request. Strict xfail: the
# suite goes red the moment one starts passing, which forces it up into
# EXTENSIONS rather than quietly disappearing.
GAPS: dict[str, str] = {
    # Notebook widget DDL. Appears at the top of most parameterised notebooks,
    # so a miss here fails the whole file.
    "create-widget-text": 'CREATE WIDGET TEXT catalog DEFAULT "main"',
    "create-widget-dropdown": (
        'CREATE WIDGET DROPDOWN d DEFAULT "a" CHOICES SELECT * FROM t'
    ),
    "remove-widget": "REMOVE WIDGET catalog",
    # `@` time travel. temporalClause covers VERSION AS OF; this is the short
    # spelling, and it works on a path as well as a name.
    "at-version-syntax": "SELECT * FROM cdf_demo@v0",
    "at-version-on-path": "SELECT count(*) FROM delta.`/mnt/p`@v524",
    # A command used as a relation.
    "describe-history-as-relation": "SELECT * FROM (DESCRIBE HISTORY my_students)",
    # Spark's showGrants expects a narrower object list than Databricks allows.
    "show-grants-on-object": "SHOW GRANTS ON demo_catalog.demo_schema.names",
    # Unity Catalog storage root for a catalog or schema.
    "managed-location": "CREATE CATALOG c MANAGED LOCATION 's3://bucket/prefix'",
    # The VIEW counterpart of STREAMING LIVE TABLE.
    "streaming-live-view": "CREATE TEMPORARY STREAMING LIVE VIEW v AS SELECT 1",
    # Tags on a column; the table-level forms are already supported.
    "column-set-tags": "ALTER TABLE t ALTER COLUMN c SET TAGS ('k' = 'v')",
    "column-unset-tags": "ALTER TABLE t ALTER COLUMN c UNSET TAGS ('k')",
}


@pytest.mark.parametrize("sql", SPARK_NATIVE.values(), ids=list(SPARK_NATIVE))
def test_spark_native_databricks_syntax(sql):
    assert parse_statement(sql).ok, sql


@pytest.mark.parametrize("sql", EXTENSIONS.values(), ids=list(EXTENSIONS))
def test_databricks_extensions(sql):
    result = parse_statement(sql)
    assert result.ok, f"{sql}\n  {result.diagnostics[0].message if result.diagnostics else ''}"


@pytest.mark.skipif(not GAPS, reason="no known gaps outstanding")
@pytest.mark.xfail(strict=True, reason="Databricks syntax not yet covered")
@pytest.mark.parametrize("sql", GAPS.values() or ["SELECT 1"], ids=list(GAPS) or ["none"])
def test_known_grammar_gaps(sql):
    assert parse_statement(sql).ok, sql


# --- the regression that adding keywords risks ------------------------------
# Defining a lexer token stops that word matching IDENTIFIER. Every keyword we
# add is therefore also registered as non-reserved, or real SQL with a column
# named `pattern`, `key` or `copy` would stop parsing -- a false positive that
# would block good merge requests. These tests are the guard on that.


@pytest.mark.parametrize("kw", _extension_keywords())
def test_extension_keyword_still_usable_as_column_name(kw):
    assert parse_statement(f"SELECT {kw} FROM t").ok, kw


@pytest.mark.parametrize("kw", _extension_keywords())
def test_extension_keyword_still_usable_as_alias(kw):
    assert parse_statement(f"SELECT a AS {kw} FROM t").ok, kw


@pytest.mark.parametrize("kw", _extension_keywords())
def test_extension_keyword_still_usable_in_ddl(kw):
    assert parse_statement(f"CREATE TABLE t ({kw} STRING) USING delta").ok, kw


@pytest.mark.parametrize("kw", _extension_keywords())
def test_extension_keyword_still_usable_as_table_name(kw):
    assert parse_statement(f"SELECT * FROM main.raw.{kw}").ok, kw


@pytest.mark.parametrize("kw", _extension_keywords())
def test_extension_keyword_usable_as_identifier_in_ansi_mode(kw):
    """ANSI mode reserves more words, but not Databricks' own extensions."""
    opts = ParseOptions(ansi_reserved_keywords=True)
    assert parse_statement(f"SELECT a AS {kw} FROM t", options=opts).ok, kw
