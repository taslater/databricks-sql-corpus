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
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Source:
    name: str
    description: str
    expectation: str  # "valid" | "invalid" | "mixed"
    # Remote sources: paths within the apache/spark tree.
    spark_prefix: str | None = None
    # Local sources: directories on this machine.
    local_paths: tuple[str, ...] = field(default_factory=tuple)


SPARK_TAG = "v4.0.4"

SPARK_SOURCES = (
    Source(
        name="spark-tpcds",
        description="TPC-DS benchmark queries shipped with Spark",
        expectation="valid",
        spark_prefix="sql/core/src/test/resources/tpcds/",
    ),
    Source(
        name="spark-tpcds-v2.7.0",
        description="TPC-DS v2.7.0 variants",
        expectation="valid",
        spark_prefix="sql/core/src/test/resources/tpcds-v2.7.0/",
    ),
    Source(
        name="spark-tpcds-modified",
        description="Modified TPC-DS queries",
        expectation="valid",
        spark_prefix="sql/core/src/test/resources/tpcds-modifiedQueries/",
    ),
    Source(
        name="spark-tpch",
        description="TPC-H benchmark queries",
        expectation="valid",
        spark_prefix="sql/core/src/test/resources/tpch/",
    ),
    Source(
        name="spark-ssb",
        description="Star Schema Benchmark queries",
        expectation="valid",
        spark_prefix="sql/core/src/test/resources/ssb/",
    ),
    Source(
        name="spark-sql-tests",
        description="Spark's own SQL golden-file tests (includes deliberate error cases)",
        expectation="mixed",
        spark_prefix="sql/core/src/test/resources/sql-tests/",
    ),
)


def local_sources(paths: list[str]) -> list[Source]:
    """Build a source for each local directory of team SQL."""
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
    for s in SPARK_SOURCES:
        if s.name == name:
            return s
    return None
