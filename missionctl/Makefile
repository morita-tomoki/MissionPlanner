# Single entry point for every check Claude runs. Keep these targets stable —
# CLAUDE.md, the skills, and CI all depend on them by name.
.DEFAULT_GOAL := help
.PHONY: help setup check lint format typecheck test contracts sitl run clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

setup: ## Install core + dev deps into a local venv (uv)
	uv sync --extra dev

check: lint typecheck contracts test ## The green-baseline gate (run at start & end of every session)

lint: ## Ruff lint + format check
	uv run ruff check .
	uv run ruff format --check .

format: ## Auto-format
	uv run ruff format .
	uv run ruff check --fix .

typecheck: ## Pyright strict
	uv run pyright

contracts: ## Enforce architecture invariants (core must not import Qt)
	uv run lint-imports --config .importlinter

test: ## Unit + tlog-replay regression tests (headless, no Qt/hardware)
	uv run pytest

sitl: ## Run SITL smoke scenario (requires ArduPilot SITL; see docs + /run-sitl skill)
	uv run pytest -m sitl

run: ## Launch the GUI app (needs the 'gui' extra: uv sync --extra gui)
	uv run python -m missionctl.qt.app

clean: ## Remove caches
	rm -rf .pytest_cache .ruff_cache **/__pycache__ .venv
