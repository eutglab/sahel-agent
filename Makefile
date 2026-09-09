.DEFAULT_GOAL := help
PY := .venv/bin/python
PIP := .venv/bin/pip

.PHONY: help setup test test-all health integrations demo run seed benchmark clean

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

setup:  ## Create venv + install deps + seed demo assets
	python3 -m venv .venv
	$(PIP) install -q --upgrade pip
	$(PIP) install -q -r requirements.txt
	$(PY) scripts/seed_demo.py

seed:  ## Regenerate synthetic demo assets
	$(PY) scripts/seed_demo.py

test:  ## Run unit + offline tests (no external providers)
	$(PY) -m pytest -m "not integration"

test-all:  ## Run every test (integration tests skip themselves if unconfigured)
	$(PY) -m pytest

health:  ## Run the health check
	$(PY) healthcheck.py

integrations:  ## Run the integration pre-flight check
	$(PY) scripts/test_integrations.py

benchmark:  ## Run the local benchmark over the demo scenarios
	$(PY) benchmark/run_benchmark.py

demo run:  ## Launch the Streamlit UI
	$(PY) -m streamlit run ui/streamlit_app.py

clean:  ## Remove caches, logs and the local run DB
	rm -rf .pytest_cache **/__pycache__ logs data/runs.sqlite3
