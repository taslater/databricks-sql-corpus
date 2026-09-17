#!/usr/bin/env bash
# Generate the Python parser from the patched grammar.
#
# The generated sources are committed to the repo on purpose: it means
# installing this tool needs only `pip install`, with no Java on the machine.
# Java is a build-time dependency for maintainers regenerating the grammar,
# not a runtime dependency for anyone linting SQL.
set -euo pipefail

ANTLR_VER="${ANTLR_VER:-4.13.2}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
JAR="$REPO_ROOT/tools/antlr-$ANTLR_VER-complete.jar"
GRAMMAR_DIR="$REPO_ROOT/grammar/databricks"
OUT_DIR="$REPO_ROOT/src/dbsqlparse/generated"

# The jar is gitignored (2MB binary), so a fresh clone will not have it.
# Fetch it on demand rather than making the maintainer read an error first.
if [ ! -f "$JAR" ]; then
  echo "ANTLR $ANTLR_VER jar not present, downloading..."
  mkdir -p "$(dirname "$JAR")"
  if ! curl -fsSL --max-time 300 -o "$JAR" \
      "https://www.antlr.org/download/antlr-$ANTLR_VER-complete.jar"; then
    rm -f "$JAR"
    echo "failed to download the ANTLR jar" >&2
    exit 1
  fi
fi

if ! command -v java >/dev/null 2>&1; then
  echo "java is required to regenerate the parser (runtime does not need it)" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"
# Delete ANTLR's own output only -- SqlBase*Base.py are hand-written shims.
for f in SqlBaseLexer SqlBaseParser; do
  rm -f "$OUT_DIR/$f.py" "$OUT_DIR/$f.tokens" "$OUT_DIR/$f.interp"
done
rm -f "$OUT_DIR/SqlBaseParserListener.py" "$OUT_DIR/SqlBaseParserVisitor.py"

# The lexer must be generated first: it emits SqlBaseLexer.tokens, which the
# parser grammar's `tokenVocab` option reads via -lib.
# -Werror is deliberate. ANTLR reports an undefined token used in a parser
# rule as a *warning* ("implicit definition of token X"), and the result is an
# alternative that can never match -- syntax we think we support but silently
# do not. Failing the build is the only way that does not slip through.
echo "generating lexer..."
java -jar "$JAR" -Dlanguage=Python3 -Werror -o "$OUT_DIR" -lib "$OUT_DIR" \
  "$GRAMMAR_DIR/SqlBaseLexer.g4"

echo "generating parser (visitor + listener)..."
java -jar "$JAR" -Dlanguage=Python3 -Werror -visitor -o "$OUT_DIR" -lib "$OUT_DIR" \
  "$GRAMMAR_DIR/SqlBaseParser.g4"

# ANTLR stamps the grammar's ABSOLUTE path into each generated header. Since
# the generated sources are committed, that would make every regeneration from
# a different checkout produce a spurious one-line diff on a 37k-line file.
# Rewrite it to a repo-relative path so output is identical everywhere.
for f in "$OUT_DIR"/SqlBase*.py; do
  sed -i.bak 's|^# Generated from .*/grammar/|# Generated from grammar/|' "$f"
  rm -f "$f.bak"
done

touch "$OUT_DIR/__init__.py"

echo
echo "generated into $OUT_DIR:"
ls -lh "$OUT_DIR" | awk 'NR>1 {printf "  %-40s %s\n", $9, $5}'
