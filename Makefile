.DEFAULT_GOAL := help
VENV  := .venv
PY    := $(VENV)/bin/python
PIP   := $(VENV)/bin/pip
STAMP := $(VENV)/.installed

.PHONY: help setup run run-live health clean

help: ## Show this help
	@echo "Minima savings demo — targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "First run: copy .env.example -> .env and fill in your keys, then 'make run'."

$(STAMP): requirements.txt ## (internal) build venv + install deps
	python3 -m venv $(VENV)
	$(PIP) install -q --upgrade pip
	$(PIP) install -q -r requirements.txt
	@touch $(STAMP)

setup: $(STAMP) ## Create venv and install dependencies
	@echo "✓ setup complete ($(VENV))"

run: setup ## Dry-run: no model calls (free); estimated savings is real server-truth
	@echo "→ dry-run (no model calls)…"
	@$(PY) demo.py

run-live: setup ## True live: real Anthropic calls; realized cost from actual tokens
	@echo "→ LIVE (real Anthropic calls; small real cost)…"
	@MINIMA_DEMO_LIVE=1 $(PY) demo.py

health: ## Check Minima API reachability (/v1/health)
	@set -a; [ -f .env ] && . ./.env; set +a; \
		curl -fsS "$${MINIMA_URL:-https://api.minima.sh}/v1/health" | python3 -m json.tool

clean: ## Remove venv and caches
	rm -rf $(VENV) __pycache__ .pytest_cache
	@echo "✓ cleaned"
