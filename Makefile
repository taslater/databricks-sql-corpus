# Regenerating the parser needs Java; running it does not.
SPARK_VERSION ?= v4.0.4
PY := .venv/bin/python

.PHONY: help venv grammar verify-generated test corpus corpus-fetch clean

help:
	@echo "make venv          create .venv and install the package"
	@echo "make grammar       re-vendor + patch + regenerate the parser (needs Java)"
	@echo "make corpus-fetch  download the pinned public SQL corpus"
	@echo "make corpus        measure parser accuracy against the corpus"
	@echo "make test          run the test suite"
	@echo "make verify-generated  check committed parser matches the grammar"

venv:
	python3 -m venv .venv
	$(PY) -m pip install -q --upgrade pip
	$(PY) -m pip install -q -e ".[dev]"

grammar:
	$(PY) scripts/fetch_grammar.py --spark-version $(SPARK_VERSION)
	$(PY) scripts/patch_grammar.py
	./scripts/generate_parser.sh

# Guards against the committed parser drifting from the grammar it came from.
# Generation is reproducible across checkouts, so any diff here is real.
verify-generated:
	./scripts/generate_parser.sh >/dev/null
	@if ! git diff --quiet -- src/dbsqlparse/generated; then \
		echo "ERROR: committed parser does not match the grammar." >&2; \
		git diff --stat -- src/dbsqlparse/generated >&2; \
		echo "Run 'make grammar' and commit the result." >&2; \
		exit 1; \
	fi
	@echo "generated parser matches the grammar"

corpus-fetch:
	$(PY) -m dbsqlparse.corpus fetch

corpus:
	$(PY) -m dbsqlparse.corpus run $(CORPUS_ARGS)

test:
	$(PY) -m pytest -q

clean:
	rm -rf corpus/cache corpus/reports .pytest_cache
	find . -name __pycache__ -type d -exec rm -rf {} +
