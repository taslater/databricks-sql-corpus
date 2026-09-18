"""Where corpus SQL comes from, and what we expect the parser to do with it.

A corpus of only-valid SQL measures one thing: that we do not reject good code
(recall). It says nothing about whether we would catch bad code, because a
parser that accepts literally everything scores 100% on it. So every source
declares an `expectation`, and the harness reports the two directions
separately:

    valid    -- every statement must parse. Failures are false positives, the
                kind that would block a good merge request.
    invalid  -- every statement must fail. Successes are false negatives, the
                kind that would wave broken SQL through CI.
    mixed    -- known to contain both; reported but not scored, since we have
                no per-file ground truth.

Two families of remote source, for different reasons:

    Spark      -- breadth. Thousands of statements exercising the grammar this
                  parser is built from, including the benchmark suites that
                  recall is judged on.
    Databricks -- shape. Spark's test resources are bare .sql files: not one
                  carries a notebook header, a `-- COMMAND ----------` cell
                  separator, a `-- MAGIC` cell or a `${widget}`. Everything
                  preprocess.py exists to handle is therefore invisible to the
                  Spark corpus, and was covered only by unit tests. These
                  sources are small, but they are the only ones that exercise
                  a real file as a Databricks user would commit it.

Every remote source is pinned to an exact revision. A corpus that tracks a
moving branch makes `baseline.json` drift on someone else's schedule, and an
accuracy "regression" that nobody caused is worse than no baseline at all.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Source:
    name: str
    description: str
    expectation: str  # "valid" | "invalid" | "mixed"
    # Remote sources: a GitHub repo pinned to an exact ref, and the subtree
    # within it. `prefix` is stripped from cached paths.
    repo: str | None = None
    ref: str | None = None
    prefix: str = ""
    # Local sources: directories on this machine.
    local_paths: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_remote(self) -> bool:
        return self.repo is not None


SPARK_TAG = "v4.0.4"
SPARK_REPO = "apache/spark"

SPARK_SOURCES = (
    Source(
        name="spark-tpcds",
        description="TPC-DS benchmark queries shipped with Spark",
        expectation="valid",
        repo=SPARK_REPO, ref=SPARK_TAG,
        prefix="sql/core/src/test/resources/tpcds/",
    ),
    Source(
        name="spark-tpcds-v2.7.0",
        description="TPC-DS v2.7.0 variants",
        expectation="valid",
        repo=SPARK_REPO, ref=SPARK_TAG,
        prefix="sql/core/src/test/resources/tpcds-v2.7.0/",
    ),
    Source(
        name="spark-tpcds-modified",
        description="Modified TPC-DS queries",
        expectation="valid",
        repo=SPARK_REPO, ref=SPARK_TAG,
        prefix="sql/core/src/test/resources/tpcds-modifiedQueries/",
    ),
    Source(
        name="spark-tpch",
        description="TPC-H benchmark queries",
        expectation="valid",
        repo=SPARK_REPO, ref=SPARK_TAG,
        prefix="sql/core/src/test/resources/tpch/",
    ),
    Source(
        name="spark-ssb",
        description="Star Schema Benchmark queries",
        expectation="valid",
        repo=SPARK_REPO, ref=SPARK_TAG,
        prefix="sql/core/src/test/resources/ssb/",
    ),
    Source(
        name="spark-sql-tests",
        description="Spark's own SQL golden-file tests (includes deliberate error cases)",
        expectation="mixed",
        repo=SPARK_REPO, ref=SPARK_TAG,
        prefix="sql/core/src/test/resources/sql-tests/",
    ),
)

# Public Databricks SQL, pinned. Only genuine .sql notebook exports qualify:
# most published Databricks notebooks are .py files carrying SQL in
# `# MAGIC %sql` cells, and this tool lints .sql files.
#
# Chosen for licence and for syntactic range rather than raw file count. A
# search of public code finds ~12k `.sql` files carrying the notebook header,
# but most sit in small personal repos that repeat the same few statements;
# these four between them cover declarative pipelines, administration, Unity
# Catalog, widget DDL and everyday analytics.
DATABRICKS_SOURCES = (
    Source(
        name="dbx-dlt-notebooks",
        description="Delta Live Tables example pipelines (SQL notebook exports)",
        expectation="valid",
        repo="databricks/delta-live-tables-notebooks",
        ref="1d8b163cfc4c45aad40c3c552807a2a0c2890cf6",
    ),
    Source(
        name="dbx-devrel",
        description="Databricks developer-relations demo notebooks",
        expectation="valid",
        repo="databricks/devrel",
        ref="edf902c419eee5bb891805ee75b5a52c5a8534bf",
    ),
    Source(
        name="dbx-learn-databricks",
        description="Jacek Laskowski's Databricks course notebooks (Apache-2.0)",
        expectation="valid",
        repo="jaceklaskowski/learn-databricks",
        ref="5ede8a53f642e23fadb70a3fffe73977858a6632",
    ),
    Source(
        name="dbx-packt-cookbook",
        description="Data Engineering with Databricks Cookbook, Packt (MIT)",
        expectation="valid",
        repo="PacktPublishing/Data-Engineering-with-Databricks-Cookbook",
        ref="fa1657c3808c0d520ea19a49f967df510b4f627d",
    ),
    Source(
        name="dbx-descomplicando-sql",
        description="Databricks SQL course notebooks, pt-BR (Unlicense)",
        expectation="valid",
        repo="TeoMeWhy/descomplicando-sql",
        ref="0ce1ea5ecc64dc80e16560259fad2103b7c43b63",
    ),
)

REMOTE_SOURCES = SPARK_SOURCES + DATABRICKS_SOURCES


def local_sources(paths: list[str]) -> list[Source]:
    """Build a source for each local directory of SQL.

    Ad hoc by design: local results are never written to the committed
    baseline (see harness.write_json), so pointing this at a private repo
    measures recall without leaking any of it into a shared artefact.
    """
    return [
        Source(
            name=f"local:{p.rstrip('/').split('/')[-1]}",
            description=f"Local SQL under {p}",
            expectation="valid",
            local_paths=(p,),
        )
        for p in paths
    ]


def by_name(name: str) -> Source | None:
    for s in REMOTE_SOURCES:
        if s.name == name:
            return s
    return None
