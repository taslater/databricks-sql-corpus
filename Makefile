# Everything here runs on pure Python. The parser this project used to build
# needed Java; it has been retired, and SQLFluff is what gets measured now.
#
# PY picks the interpreter, and each target measures whichever SQLFluff is
# installed in its venv. The loop's normal state is an editable fork checkout
# in .venv, so to measure another branch without disturbing it -- a worktree
# checkout, or released SQLFluff -- point PY at a separate venv:
#     make corpus PY=.venv-release/bin/python
PY ?= .venv/bin/python

.PHONY: help venv test coverage corpus corpus-fetch gaps diff reference reference-gaps baseline clean

help:
	@echo "make venv          create .venv and install the harness"
	@echo "make corpus-fetch  download the pinned public SQL corpus"
	@echo "make corpus        measure SQLFluff against the corpus"
	@echo "make gaps          group the failures by construct (the PR queue)"
	@echo "make diff          advisory: sqlfluff vs sqlglot disagreements (not scored)"
	@echo "make reference     cases transcribed from the Databricks SQL reference"
	@echo "make reference-gaps  the reference divergences as gaps.md-shaped entries"
	@echo "make baseline      regenerate corpus/reports/baseline.json"
	@echo "make test          run the test suite (gates reference.py at 100%)"
	@echo "make coverage      report coverage for the whole package"
	@echo ""
	@echo "To measure an unmerged SQLFluff branch, install it over the release:"
	@echo "    .venv/bin/pip install -e ../sqlfluff"
	@echo "To regenerate the committed baseline (released SQLFluff only):"
	@echo "    make baseline PY=.venv-release/bin/python"

venv:
	python3 -m venv .venv
	$(PY) -m pip install -q --upgrade pip
	$(PY) -m pip install -q -e ".[dev]"

corpus-fetch:
	$(PY) -m dbsqlparse.corpus fetch

corpus:
	$(PY) -m dbsqlparse.corpus run $(CORPUS_ARGS)

gaps:
	$(PY) -m dbsqlparse.corpus gaps $(CORPUS_ARGS)

# Advisory triage against an independent parser (sqlglot by default). A
# disagreement is a candidate, not a verdict: the docs-derived reference is
# the oracle. Nothing here is scored and nothing lands in the baseline.
# See docs/sqlglot-plan.md.
diff:
	$(PY) -m dbsqlparse.corpus diff $(CORPUS_ARGS)

# No fetched corpus needed: the cases are committed, each citing the doc page
# it was transcribed from.
reference:
	$(PY) -m dbsqlparse.corpus reference $(CORPUS_ARGS)

# The triage step: only the divergences, with case id, doc link and a
# one-line repro, in the shape a docs/gaps.md entry wants.
reference-gaps:
	$(PY) -m dbsqlparse.corpus reference-gaps $(CORPUS_ARGS)

# The committed baseline tracks RELEASED SQLFluff, not a fork checkout, so it
# reflects what a user actually gets. Read the diff before committing it. An
# editable fork install would silently measure that branch instead, so this
# refuses to write the baseline from one.
baseline:
	@$(PY) -c "import pathlib, sqlfluff, sys; p = pathlib.Path(sqlfluff.__file__); \
		print('measuring', p); \
		sys.exit(0 if 'site-packages' in str(p) else 'refusing: not a released SQLFluff')"
	$(PY) -m dbsqlparse.corpus run --json corpus/reports/baseline.json

# The reference harness reads the oracle the scraped corpus cannot see, so a
# silent bug in it writes wrong numbers into the confidence. It is held at
# 100% line and branch coverage. The rest of the package predates that bar and
# is reported, not gated, by `make coverage`.
test:
	$(PY) -m pytest -q --cov=dbsqlparse.corpus.reference \
		--cov-report=term-missing --cov-fail-under=100

coverage:
	$(PY) -m pytest -q --cov=dbsqlparse --cov-report=term-missing

clean:
	rm -rf corpus/cache corpus/reports/latest.json .pytest_cache .coverage
	find . -name __pycache__ -type d -exec rm -rf {} +
