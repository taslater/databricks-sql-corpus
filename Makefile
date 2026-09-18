# Everything here runs on pure Python. The parser this project used to build
# needed Java; it has been retired, and SQLFluff is what gets measured now.
PY := .venv/bin/python

.PHONY: help venv test corpus corpus-fetch gaps baseline clean

help:
	@echo "make venv          create .venv and install the harness"
	@echo "make corpus-fetch  download the pinned public SQL corpus"
	@echo "make corpus        measure SQLFluff against the corpus"
	@echo "make gaps          group the failures by construct (the PR queue)"
	@echo "make baseline      regenerate corpus/reports/baseline.json"
	@echo "make test          run the test suite"
	@echo ""
	@echo "To measure an unmerged SQLFluff branch, install it over the release:"
	@echo "    .venv/bin/pip install -e ../sqlfluff"

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

# The committed baseline tracks RELEASED SQLFluff, not a fork checkout, so it
# reflects what a user actually gets. Read the diff before committing it.
baseline:
	$(PY) -m dbsqlparse.corpus run --json corpus/reports/baseline.json

test:
	$(PY) -m pytest -q

clean:
	rm -rf corpus/cache corpus/reports/latest.json .pytest_cache
	find . -name __pycache__ -type d -exec rm -rf {} +
