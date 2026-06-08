.PHONY: backend frontend test build-web eval eval-download eval-prepare eval-numeric-checks eval-validate

PYTHON ?= python

backend:
	$(PYTHON) -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

frontend:
	cd web && npm run dev -- --host 127.0.0.1

test:
	PYTHONPATH=. $(PYTHON) -m pytest -q

build-web:
	cd web && npm run build

eval-download:
	PYTHONPATH=. $(PYTHON) evals/download_datasets.py

eval-prepare:
	PYTHONPATH=. $(PYTHON) evals/prepare_snapshots.py

eval-numeric-checks: eval-prepare
	PYTHONPATH=. $(PYTHON) evals/generate_numeric_checks.py

eval-validate: eval-prepare
	PYTHONPATH=. $(PYTHON) evals/download_datasets.py --validate

eval: eval-prepare
	PYTHONPATH=. $(PYTHON) evals/run_eval.py --manifest evals/manifest.json --questions evals/questions --out evals/reports/latest.md --mode fast
