# Reference corpus coverage

Which Databricks SQL reference pages the reference corpus covers, which
are queued, and which cannot produce statement cases. The queue order is
in `docs/reference-corpus-plan.md`; this file answers "what is left".

Generated 2026-09-19 from the
[SQL language reference index](https://docs.databricks.com/aws/en/sql/language-manual/)
and the [Pipeline SQL language reference](https://docs.databricks.com/aws/en/ldp/developer/sql-ref).
A page appears once even when the index links it from several sections.

- **done** — a file in `corpus/reference/` transcribes this page, or, for a
  catalogue page like Data types, its per-type pages
- **queued** — statement or clause syntax still to transcribe
- **n/a** — not a statement-grammar surface: concepts, function catalogues,
  configuration parameters, Runtime-only I/O commands, and prose-only
  reference. Type syntax is not covered "through the table statements";
  the Tier 1.5 batch disproved that and the per-type pages have their own
  files

The notebook magic-cell cases (`magic_cells.yml`) come from outside both
indexes; the Unity Catalog privileges reference supplies the privilege
names for the GRANT-family cases. Both are listed below.

## General reference (4 done, 3 queued, 44 n/a)

| page | status |
| --- | --- |
| [How to use the SQL reference](https://docs.databricks.com/aws/en/sql/language-manual/how-to-use) | n/a |
| [Adding comments to SQL statements](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-comment) | n/a |
| [Reserved words and schemas](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-reserved-words) | n/a |
| [Identifiers](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-identifiers) | n/a |
| [Names](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-names) | n/a |
| [IDENTIFIER clause](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-names-identifier-clause) | queued |
| [SQL expression](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-expression) | done |
| [NULL semantics](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-null-semantics) | n/a |
| [Parameter markers](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-parameter-marker) | n/a |
| [Variables](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-variables) | n/a |
| [Name resolution](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-name-resolution) | n/a |
| [JSON path expression](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-json-path-expression) | done |
| [Collation](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-collation) | n/a |
| [Partitions](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-partition) | n/a |
| [Data types](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-datatypes) | done |
| [SQL data type rules](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-datatype-rules) | n/a |
| [Datetime patterns](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-datetime-pattern) | n/a |
| [Configuration parameters](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-parameters) | n/a |
| [ANSI_MODE](https://docs.databricks.com/aws/en/sql/language-manual/parameters/ansi_mode) | n/a |
| [LEGACY_TIME_PARSER_POLICY](https://docs.databricks.com/aws/en/sql/language-manual/parameters/legacy_time_parser_policy) | n/a |
| [MAX_FILE_PARTITION_BYTES](https://docs.databricks.com/aws/en/sql/language-manual/parameters/max_partition_bytes) | n/a |
| [READ_ONLY_EXTERNAL_METASTORE](https://docs.databricks.com/aws/en/sql/language-manual/parameters/read_only_external_metastore) | n/a |
| [STATEMENT_TIMEOUT](https://docs.databricks.com/aws/en/sql/language-manual/parameters/statement_timeout) | n/a |
| [TIMEZONE](https://docs.databricks.com/aws/en/sql/language-manual/parameters/timezone) | n/a |
| [USE_CACHED_RESULT](https://docs.databricks.com/aws/en/sql/language-manual/parameters/use_cached_result) | n/a |
| [Functions](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-functions) | n/a |
| [Built-in functions](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-functions-builtin) | n/a |
| [Alphabetical list of built-in functions](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-functions-builtin-alpha) | n/a |
| [Window functions](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-window-functions) | n/a |
| [Lambda functions](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-lambda-functions) | n/a |
| [H3 geospatial functions](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-h3-geospatial-functions) | n/a |
| [ST geospatial functions](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-st-geospatial-functions) | n/a |
| [IP functions](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-ip-functions) | n/a |
| [User-defined aggregate functions (UDAFs)](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-functions-udf-aggregate) | n/a |
| [External user-defined scalar functions (UDFs)](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-functions-udf-scalar) | n/a |
| [Integration with Hive UDFs, UDAFs, and UDTFs](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-functions-udf-hive) | n/a |
| [Function invocation](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-function-invocation) | queued |
| [Principal](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-principal) | n/a |
| [Privileges and securable objects in Unity Catalog](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-privileges) | done |
| [Privileges and securable objects in the Hive metastore](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-privileges-hms) | queued |
| [External locations](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-external-locations) | n/a |
| [External tables](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-external-tables) | n/a |
| [Credentials](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-storage-credentials) | n/a |
| [Volumes](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-volumes) | n/a |
| [ANSI compliance in Databricks Runtime](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-ansi-compliance) | n/a |
| [Apache Hive compatibility](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-hive-compatibility) | n/a |
| [SQL scripting](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-scripting) | n/a |
| [Authorized user and session user](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-authorized-user) | n/a |
| [OpenSharing](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-sharing) | n/a |
| [Federated queries (Lakehouse Federation)](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-federated-queries) | n/a |
| [Information schema](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-information-schema) | n/a |

Data types is covered page by page: `array_type.yml`, `map_type.yml`,
`struct_type.yml` and `variant_type.yml` transcribe its per-type pages.
`OBJECT` is deliberately uncovered: its page documents
`OBJECT < [fieldName [:] fieldType [, ...] ] >` but shows no statement that
writes the type as input, so a case would have to invent the position.

## DDL statements (46 done, 12 queued, 4 n/a)

| page | status |
| --- | --- |
| [ALTER CATALOG](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-alter-catalog) | done |
| [ALTER CONNECTION](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-alter-connection) | done |
| [ALTER CREDENTIAL](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-alter-credential) | done |
| [ALTER DATABASE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-alter-database) | n/a |
| [ALTER EXTERNAL LOCATION](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-alter-location) | done |
| [ALTER MATERIALIZED VIEW](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-alter-materialized-view) | done |
| [ALTER PROVIDER](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-alter-provider) | done |
| [ALTER RECIPIENT](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-alter-recipient) | done |
| [ALTER SCHEMA](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-alter-schema) | done |
| [ALTER SHARE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-alter-share) | done |
| [ALTER STREAMING TABLE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-alter-streaming-table) | done |
| [ALTER TABLE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-alter-table) | done |
| [ALTER VIEW](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-alter-view) | done |
| [ALTER VOLUME](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-alter-volume) | done |
| [CREATE CATALOG](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-catalog) | done |
| [CREATE CONNECTION](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-connection) | done |
| [CREATE DATABASE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-database) | n/a |
| [CREATE FUNCTION (SQL, Python, Scala, and Java)](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-sql-function) | done |
| [CREATE FUNCTION (External)](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-function) | done |
| [CREATE EXTERNAL LOCATION](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-location) | done |
| [CREATE MATERIALIZED VIEW](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-materialized-view) | done |
| [CREATE POLICY](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-policy) | done |
| [CREATE PROCEDURE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-procedure) | done |
| [CREATE RECIPIENT](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-recipient) | done |
| [CREATE SCHEMA](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-schema) | done |
| [CREATE SERVER](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-server) | n/a |
| [CREATE SHARE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-share) | done |
| [CREATE STREAMING TABLE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-streaming-table) | done |
| [CREATE TABLE [USING]](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-table-using) | done |
| [CREATE TABLE (Hive format)](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-table-hiveformat) | done |
| [CREATE TABLE LIKE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-table-like) | done |
| [CREATE TABLE CLONE](https://docs.databricks.com/aws/en/sql/language-manual/delta-clone) | done |
| [CREATE VIEW](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-view) | done |
| [CREATE VOLUME](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-volume) | done |
| [DROP CATALOG](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-drop-catalog) | done |
| [DROP CONNECTION](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-drop-connection) | done |
| [DROP CREDENTIAL](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-drop-credential) | done |
| [DROP DATABASE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-drop-database) | n/a |
| [DROP FUNCTION](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-drop-function) | done |
| [DROP EXTERNAL LOCATION](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-drop-location) | done |
| [DROP POLICY](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-drop-policy) | done |
| [DROP PROCEDURE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-drop-procedure) | done |
| [DROP PROVIDER](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-drop-provider) | done |
| [DROP RECIPIENT](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-drop-recipient) | done |
| [DROP SCHEMA](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-drop-schema) | done |
| [DROP SHARE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-drop-share) | done |
| [DROP TABLE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-drop-table) | done |
| [DROP VARIABLE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-drop-variable) | done |
| [DROP VIEW](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-drop-view) | done |
| [DROP VOLUME](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-drop-volume) | done |
| [COMMENT ON](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-comment) | queued |
| [DECLARE VARIABLE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-declare-variable) | queued |
| [REPAIR TABLE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-repair-table) | queued |
| [REFRESH FOREIGN (CATALOG, SCHEMA, and TABLE)](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-refresh-foreign) | queued |
| [REFRESH (MATERIALIZED VIEW or STREAMING TABLE)](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-refresh-full) | queued |
| [SET TAG](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-set-tag) | queued |
| [TRUNCATE TABLE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-truncate-table) | queued |
| [UNDROP](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-undrop-table) | queued |
| [UNSET TAG](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-unset-tag) | queued |
| [USE CATALOG](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-use-catalog) | queued |
| [USE DATABASE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-usedb) | queued |
| [USE SCHEMA](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-use-schema) | queued |

ALTER TABLE's syntax block only names its clause productions; each lives on a
sub-page, which is still queued and where the clause's partial forms belong
(`sql-ref-syntax-ddl-alter-table-manage-column`, `...-add-constraint`,
`...-drop-constraint`, `...-manage-partition`, `sql-ref-syntax-ddl-row-filter`,
`sql-ref-syntax-ddl-cluster-by`, `sql-ref-syntax-ddl-tblproperties`). The
`alter_table.yml` file pins the clause menu itself.

## DML statements (4 done, 0 queued, 0 n/a)

| page | status |
| --- | --- |
| [INSERT](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-dml-insert-into) | done |
| [INSERT OVERWRITE DIRECTORY](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-dml-insert-overwrite-directory) | done |
| [INSERT OVERWRITE DIRECTORY with Hive format](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-dml-insert-overwrite-directory-hive) | done |
| [LOAD DATA](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-dml-load) | done |

## Data retrieval statements (29 done, 0 queued, 0 n/a)

| page | status |
| --- | --- |
| [SQL Pipeline Syntax](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-pipeline) | done |
| [Query](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-query) | done |
| [SELECT (subselect)](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-select) | done |
| [VALUES clause](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-select-values) | done |
| [EXPLAIN](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-explain) | done |
| [SELECT clause](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-select-column-list) | done |
| [\* (star) clause](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-star) | done |
| [table reference](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-select-table-reference) | done |
| [JOIN](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-select-join) | done |
| [WHERE clause](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-select-where) | done |
| [GROUP BY clause](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-select-groupby) | done |
| [HAVING clause](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-select-having) | done |
| [QUALIFY clause](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-select-qualify) | done |
| [ORDER BY clause](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-select-orderby) | done |
| [SORT BY clause](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-select-sortby) | done |
| [CLUSTER BY clause (SELECT)](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-select-clusterby) | done |
| [DISTRIBUTE BY clause](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-select-distributeby) | done |
| [LIMIT clause](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-select-limit) | done |
| [OFFSET clause](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-select-offset) | done |
| [MATCH_RECOGNIZE clause](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-select-match-recognize) | done |
| [PIVOT clause](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-select-pivot) | done |
| [UNPIVOT clause](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-select-unpivot) | done |
| [LATERAL VIEW clause](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-select-lateral-view) | done |
| [TABLESAMPLE clause](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-select-sampling) | done |
| [Table-valued function (TVF) invocation](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-select-tvf) | done |
| [Common table expression (CTE)](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-select-cte) | done |
| [Set operators](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-select-setops) | done |
| [WINDOW clause](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-select-named-window) | done |
| [Hints](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-select-hints) | done |

## Delta Lake (14 done, 0 queued, 1 n/a)

| page | status |
| --- | --- |
| [CREATE BLOOM FILTER INDEX (deprecated)](https://docs.databricks.com/aws/en/sql/language-manual/delta-create-bloomfilter-index) | n/a |
| [DROP BLOOM FILTER INDEX](https://docs.databricks.com/aws/en/sql/language-manual/delta-drop-bloomfilter-index) | done |
| [COPY INTO](https://docs.databricks.com/aws/en/sql/language-manual/delta-copy-into) | done |
| [DELETE FROM](https://docs.databricks.com/aws/en/sql/language-manual/delta-delete-from) | done |
| [MERGE INTO](https://docs.databricks.com/aws/en/sql/language-manual/delta-merge-into) | done |
| [UPDATE](https://docs.databricks.com/aws/en/sql/language-manual/delta-update) | done |
| [CACHE SELECT](https://docs.databricks.com/aws/en/sql/language-manual/delta-cache) | done |
| [CONVERT TO DELTA](https://docs.databricks.com/aws/en/sql/language-manual/delta-convert-to-delta) | done |
| [DESCRIBE HISTORY](https://docs.databricks.com/aws/en/sql/language-manual/delta-describe-history) | done |
| [FSCK REPAIR TABLE](https://docs.databricks.com/aws/en/sql/language-manual/delta-fsck) | done |
| [GENERATE](https://docs.databricks.com/aws/en/sql/language-manual/delta-generate) | done |
| [OPTIMIZE](https://docs.databricks.com/aws/en/sql/language-manual/delta-optimize) | done |
| [REORG TABLE](https://docs.databricks.com/aws/en/sql/language-manual/delta-reorg-table) | done |
| [RESTORE](https://docs.databricks.com/aws/en/sql/language-manual/delta-restore) | done |
| [VACUUM](https://docs.databricks.com/aws/en/sql/language-manual/delta-vacuum) | done |

## SQL scripting (0 done, 12 queued, 0 n/a)

| page | status |
| --- | --- |
| [BEGIN END compound statement](https://docs.databricks.com/aws/en/sql/language-manual/control-flow/compound-stmt) | queued |
| [CASE statement](https://docs.databricks.com/aws/en/sql/language-manual/control-flow/case-stmt) | queued |
| [FOR statement](https://docs.databricks.com/aws/en/sql/language-manual/control-flow/for-stmt) | queued |
| [GET DIAGNOSTICS statement](https://docs.databricks.com/aws/en/sql/language-manual/control-flow/get-diagnostics-stmt) | queued |
| [IF THEN ELSE statement](https://docs.databricks.com/aws/en/sql/language-manual/control-flow/if-stmt) | queued |
| [ITERATE statement](https://docs.databricks.com/aws/en/sql/language-manual/control-flow/iterate-stmt) | queued |
| [LEAVE statement](https://docs.databricks.com/aws/en/sql/language-manual/control-flow/leave-stmt) | queued |
| [LOOP statement](https://docs.databricks.com/aws/en/sql/language-manual/control-flow/loop-stmt) | queued |
| [REPEAT statement](https://docs.databricks.com/aws/en/sql/language-manual/control-flow/repeat-stmt) | queued |
| [RESIGNAL statement](https://docs.databricks.com/aws/en/sql/language-manual/control-flow/resignal-stmt) | queued |
| [SIGNAL statement](https://docs.databricks.com/aws/en/sql/language-manual/control-flow/signal-stmt) | queued |
| [WHILE statement](https://docs.databricks.com/aws/en/sql/language-manual/control-flow/while-stmt) | queued |

## Auxiliary statements (2 done, 55 queued, 9 n/a)

| page | status |
| --- | --- |
| [ANALYZE TABLE … COMPUTE STATISTICS](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-analyze-compute-statistics) | queued |
| [ANALYZE TABLE … COMPUTE STORAGE METRICS](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-analyze-compute-storage-metrics) | queued |
| [SYNC](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-sync) | queued |
| [CACHE TABLE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-cache-cache-table) | queued |
| [CLEAR CACHE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-cache-clear-cache) | queued |
| [REFRESH CACHE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-cache-refresh) | queued |
| [REFRESH FUNCTION](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-cache-refresh-function) | queued |
| [REFRESH TABLE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-cache-refresh-table) | queued |
| [UNCACHE TABLE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-cache-uncache-table) | queued |
| [DESCRIBE CATALOG](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-describe-catalog) | queued |
| [DESCRIBE CONNECTION](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-describe-connection) | queued |
| [DESCRIBE CREDENTIAL](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-describe-credential) | queued |
| [DESCRIBE DATABASE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-describe-database) | queued |
| [DESCRIBE FUNCTION](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-describe-function) | queued |
| [DESCRIBE EXTERNAL LOCATION](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-describe-location) | queued |
| [DESCRIBE POLICY](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-describe-policy) | queued |
| [DESCRIBE PROCEDURE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-describe-procedure) | queued |
| [DESCRIBE PROVIDER](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-describe-provider) | queued |
| [DESCRIBE QUERY](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-describe-query) | queued |
| [DESCRIBE RECIPIENT](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-describe-recipient) | queued |
| [DESCRIBE SCHEMA](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-describe-schema) | queued |
| [DESCRIBE SHARE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-describe-share) | queued |
| [DESCRIBE TABLE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-describe-table) | done |
| [DESCRIBE VOLUME](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-describe-volume) | queued |
| [LIST](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-list) | queued |
| [SHOW ALL IN SHARE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-show-all-in-share) | queued |
| [SHOW CATALOGS](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-show-catalogs) | queued |
| [SHOW COLUMNS](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-show-columns) | queued |
| [SHOW CONNECTIONS](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-show-connections) | queued |
| [SHOW CREATE TABLE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-show-create-table) | queued |
| [SHOW CREDENTIALS](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-show-credentials) | queued |
| [SHOW DATABASES](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-show-databases) | queued |
| [SHOW FUNCTIONS](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-show-functions) | queued |
| [SHOW GROUPS](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-show-groups) | queued |
| [SHOW EXTERNAL LOCATIONS](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-show-locations) | queued |
| [SHOW PARTITIONS](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-show-partitions) | queued |
| [SHOW POLICIES](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-show-policies) | queued |
| [SHOW PROCEDURES](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-show-procedures) | queued |
| [SHOW PROVIDERS](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-show-providers) | queued |
| [SHOW RECIPIENTS](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-show-recipients) | queued |
| [SHOW SCHEMAS](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-show-schemas) | queued |
| [SHOW SHARES](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-show-shares) | queued |
| [SHOW SHARES IN PROVIDER](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-show-shares-in-provider) | queued |
| [SHOW TABLE EXTENDED](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-show-table) | queued |
| [SHOW TABLES](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-show-tables) | queued |
| [SHOW TABLES DROPPED](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-show-tables-dropped) | queued |
| [SHOW TBLPROPERTIES](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-show-tblproperties) | queued |
| [SHOW USERS](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-show-users) | queued |
| [SHOW VIEWS](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-show-views) | queued |
| [SHOW VOLUMES](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-show-volumes) | queued |
| [CALL](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-call) | queued |
| [EXECUTE IMMEDIATE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-execute-immediate) | done |
| [RESET](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-conf-mgmt-reset) | queued |
| [SET](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-conf-mgmt-set) | queued |
| [SET RECIPIENT](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-set-recipient) | queued |
| [SET TIME ZONE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-conf-mgmt-set-timezone) | queued |
| [SET variable](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-set-variable) | queued |
| [ADD ARCHIVE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-resource-mgmt-add-archive) | n/a |
| [ADD FILE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-resource-mgmt-add-file) | n/a |
| [ADD JAR](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-resource-mgmt-add-jar) | n/a |
| [LIST ARCHIVE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-resource-mgmt-list-archive) | n/a |
| [LIST FILE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-resource-mgmt-list-file) | n/a |
| [LIST JAR](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-resource-mgmt-list-jar) | n/a |
| [GET](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-connector-get) | n/a |
| [PUT INTO](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-connector-put-into) | n/a |
| [REMOVE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-connector-remove) | n/a |

## Security (3 done, 9 queued, 0 n/a)

| page | status |
| --- | --- |
| [ALTER GROUP](https://docs.databricks.com/aws/en/sql/language-manual/security-alter-group) | queued |
| [CREATE GROUP](https://docs.databricks.com/aws/en/sql/language-manual/security-create-group) | queued |
| [DENY](https://docs.databricks.com/aws/en/sql/language-manual/security-deny) | queued |
| [DROP GROUP](https://docs.databricks.com/aws/en/sql/language-manual/security-drop-group) | queued |
| [GRANT](https://docs.databricks.com/aws/en/sql/language-manual/security-grant) | done |
| [GRANT ON SHARE](https://docs.databricks.com/aws/en/sql/language-manual/security-grant-share) | queued |
| [MSCK REPAIR PRIVILEGES](https://docs.databricks.com/aws/en/sql/language-manual/security-msck) | queued |
| [REVOKE](https://docs.databricks.com/aws/en/sql/language-manual/security-revoke) | done |
| [REVOKE ON SHARE](https://docs.databricks.com/aws/en/sql/language-manual/security-revoke-share) | queued |
| [SHOW GRANTS](https://docs.databricks.com/aws/en/sql/language-manual/security-show-grant) | done |
| [SHOW GRANTS ON SHARE](https://docs.databricks.com/aws/en/sql/language-manual/security-show-grant-on-share) | queued |
| [SHOW GRANTS TO RECIPIENT](https://docs.databricks.com/aws/en/sql/language-manual/security-show-grant-to-recipient) | queued |

## Lakeflow pipelines (2 done, 5 queued, 1 n/a)

| page | status |
| --- | --- |
| [Pipeline SQL language reference](https://docs.databricks.com/aws/en/ldp/developer/sql-ref) | n/a |
| [AUTO CDC INTO](https://docs.databricks.com/aws/en/ldp/developer/ldp-sql-ref-apply-changes-into) | queued |
| [CREATE FLOW](https://docs.databricks.com/aws/en/ldp/developer/ldp-sql-ref-create-flow) | done |
| [CREATE MATERIALIZED VIEW](https://docs.databricks.com/aws/en/ldp/developer/ldp-sql-ref-create-materialized-view) | queued |
| [CREATE STREAMING TABLE](https://docs.databricks.com/aws/en/ldp/developer/ldp-sql-ref-create-streaming-table) | done |
| [CREATE TABLE ... FLOW](https://docs.databricks.com/aws/en/ldp/developer/ldp-sql-ref-create-table-flow) | queued |
| [CREATE TEMPORARY VIEW](https://docs.databricks.com/aws/en/ldp/developer/ldp-sql-ref-create-temporary-view) | queued |
| [CREATE VIEW](https://docs.databricks.com/aws/en/ldp/developer/ldp-sql-ref-create-view) | queued |

## Not statement pages, still in the corpus

| page | status |
| --- | --- |
| [Work with code cells](https://docs.databricks.com/aws/en/notebooks/notebooks-code) | done |
| [Unity Catalog privileges reference](https://docs.databricks.com/aws/en/data-governance/unity-catalog/access-control/privileges-reference) | done |
| [`::` (colon colon sign) operator](https://docs.databricks.com/aws/en/sql/language-manual/functions/coloncolonsign) | done |
| [`from_json` function](https://docs.databricks.com/aws/en/sql/language-manual/functions/from_json) | done |
| [`from_xml` function](https://docs.databricks.com/aws/en/sql/language-manual/functions/from_xml) | done |
| [`read_files` table-valued function](https://docs.databricks.com/aws/en/sql/language-manual/functions/read_files) | done |
