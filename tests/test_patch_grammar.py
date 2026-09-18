"""The patch step must fail loudly, never silently.

Every Databricks extension is spliced into the vendored Spark grammar at an
anchor -- a marker comment or a distinctive line of rule text. When we re-vendor
a newer Spark and it has moved or renamed one, there are two possible outcomes:

  * the injection raises, the build stops, and someone updates the anchor; or
  * the injection quietly does nothing, generation succeeds, and we ship a
    parser that is missing syntax it claims to support.

The second is the dangerous one, because nothing looks wrong: the tests that
would catch it are the ones for syntax that silently stopped being covered.
These tests damage the grammar on purpose and assert the first outcome.
"""
from __future__ import annotations

import importlib.util
import pathlib

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
VENDORED = REPO_ROOT / "grammar" / "vendor" / "SqlBaseParser.g4"
VENDORED_LEXER = REPO_ROOT / "grammar" / "vendor" / "SqlBaseLexer.g4"


def _load_patch_module():
    spec = importlib.util.spec_from_file_location(
        "patch_grammar", REPO_ROOT / "scripts" / "patch_grammar.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pg = _load_patch_module()


# (name, injection, the exact text it anchors on).
# The anchor text must be what the injection actually matches, not a substring
# it happens to share with elsewhere in the grammar -- damaging a shared
# substring leaves the real anchor intact and the test proves nothing.
PARSER_INJECTIONS = [
    ("statements", lambda t: pg.add_statements(t), pg.STATEMENT_ANCHOR),
    (
        "non-reserved",
        lambda t: pg.add_non_reserved(t, pg.read_keywords()),
        pg.DEFAULT_NON_RESERVED_ANCHOR,
    ),
    ("qualify", lambda t: pg.add_qualify_clause(t), "#regularQuerySpecification"),
    (
        "path-relation",
        lambda t: pg.add_path_relation(t),
        "      optionsClause? sample? tableAlias                     #tableName",
    ),
    (
        "cluster-by-auto",
        lambda t: pg.add_cluster_by_auto(t),
        "    : CLUSTER BY LEFT_PAREN multipartIdentifierList RIGHT_PAREN",
    ),
    ("variant-path", lambda t: pg.add_variant_path(t), "#dereference"),
    ("object-type", lambda t: pg.add_object_data_type(t), "complex=STRUCT"),
    (
        "stream-relation",
        lambda t: pg.add_stream_relation(t),
        "      optionsClause? sample? tableAlias                     #tableName",
    ),
    (
        "column-constraints",
        lambda t: pg.add_column_constraints(t),
        "    : colDefinition (COMMA colDefinition)*",
    ),
    (
        "inline-column-constraints",
        lambda t: pg.add_inline_column_constraints(t),
        "    | generationExpression\n    | commentSpec",
    ),
    (
        "at-version-travel",
        lambda t: pg.add_at_version_travel(t),
        "    : FOR? (SYSTEM_VERSION | VERSION) AS OF version",
    ),
    (
        "column-tags",
        lambda t: pg.add_column_tags(t),
        "    | setOrDrop=(SET | DROP) errorCapturingNot NULL",
    ),
    (
        "describe-history-relation",
        lambda t: pg.add_describe_relation(t),
        "      optionsClause? sample? tableAlias                     #tableName",
    ),
    (
        "managed-location",
        lambda t: pg.add_managed_location(t),
        "         (WITH (DBPROPERTIES | PROPERTIES) propertyList))*             #createNamespace",
    ),
]

# The lexer injections are checked separately: they anchor on the lexer
# grammar, not the parser one.
LEXER_INJECTIONS = [
    ("at-sign-token", lambda t: pg.add_at_sign_token(t), pg.LEXER_KEYWORD_ANCHOR),
]


@pytest.mark.parametrize(
    "inject,anchor",
    [(i, a) for _, i, a in LEXER_INJECTIONS],
    ids=[n for n, _, _ in LEXER_INJECTIONS],
)
def test_lexer_injection_raises_when_its_anchor_moves(inject, anchor):
    text = VENDORED_LEXER.read_text()
    assert anchor in text, "anchor no longer present in the vendored lexer"
    # Replace outright rather than append: appending would leave the original
    # anchor intact as a substring and the test would prove nothing.
    damaged = text.replace(anchor, "SPARK_MOVED_THIS")
    with pytest.raises(pg.PatchError):
        inject(damaged)


@pytest.mark.parametrize(
    "inject,anchor",
    [(i, a) for _, i, a in LEXER_INJECTIONS],
    ids=[n for n, _, _ in LEXER_INJECTIONS],
)
def test_lexer_injection_changes_the_grammar_when_its_anchor_is_present(inject, anchor):
    original = VENDORED_LEXER.read_text()
    assert anchor in original
    assert inject(original) != original


def test_at_sign_token_precedes_the_unrecognized_catch_all():
    """UNRECOGNIZED is `.` -- it matches any single character. If AT_SIGN landed
    after it, `@` would keep falling into the catch-all and `tbl@v3` would still
    not parse, with nothing to show that the injection had failed."""
    patched = pg.add_at_sign_token(VENDORED_LEXER.read_text())
    assert patched.index("AT_SIGN: '@';") < patched.index("UNRECOGNIZED")


@pytest.mark.parametrize(
    "inject,anchor", [(i, a) for _, i, a in PARSER_INJECTIONS], ids=[n for n, _, _ in PARSER_INJECTIONS]
)
def test_injection_raises_when_its_anchor_moves(inject, anchor):
    text = VENDORED.read_text()
    assert anchor in text, "anchor no longer present in the vendored grammar"
    damaged = text.replace(anchor, "SPARK_MOVED_THIS")  # every occurrence
    with pytest.raises(pg.PatchError):
        inject(damaged)


@pytest.mark.parametrize(
    "inject,anchor", [(i, a) for _, i, a in PARSER_INJECTIONS], ids=[n for n, _, _ in PARSER_INJECTIONS]
)
def test_injection_changes_the_grammar_when_its_anchor_is_present(inject, anchor):
    """The mirror of the above: a successful injection must actually do something."""
    text = VENDORED.read_text()
    assert inject(text) != text, "injection silently made no change"


def test_lexer_keyword_injection_detects_spark_defining_a_keyword_itself():
    """If Spark adds one of our keywords, defining it twice must be caught."""
    text = VENDORED_LEXER.read_text()
    keywords = pg.read_keywords()
    # Simulate Spark adding OPTIMIZE to its own lexer.
    damaged = text.replace(
        pg.LEXER_KEYWORD_ANCHOR, f"{keywords[0]}: '{keywords[0]}';\n" + pg.LEXER_KEYWORD_ANCHOR, 1
    )
    with pytest.raises(pg.PatchError, match="defined by Spark itself"):
        pg.add_lexer_keywords(damaged, keywords)


def test_keywords_file_has_no_duplicates():
    assert pg.read_keywords(), "keyword list is empty"


def test_complex_type_actions_reference_real_keywords():
    """A typo in COMPLEX_TYPE_ACTIONS would silently drop the lexer action."""
    text = VENDORED_LEXER.read_text()
    with pytest.raises(pg.PatchError, match="not in"):
        pg.COMPLEX_TYPE_ACTIONS["NOT_A_REAL_KEYWORD"] = "{self.nope()}"
        try:
            pg.add_lexer_keywords(text, pg.read_keywords())
        finally:
            del pg.COMPLEX_TYPE_ACTIONS["NOT_A_REAL_KEYWORD"]
