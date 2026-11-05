ARGS ?=
UV   ?= uv run

.DEFAULT_GOAL := help
.PHONY: help install run debug clean fclean lint lint-strict

help: ## Show this help message
	@echo "Usage: make <target> [ARGS=\"...\"]"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*## "} {printf "  %-12s %s\n", $$1, $$2}'
	@echo ""
	@echo "Example: make run ARGS=\"index --max_chunk_size 2000\""

install: ## Install project dependencies (uv sync)
	uv sync

run: ## Run the program, passing options with ARGS="..."
	$(UV) python -m src $(ARGS)

debug: ## Run the program inside the Python debugger (pdb)
	$(UV) python -m pdb -m src $(ARGS)

clean: ## Remove __pycache__ and the mypy/pytest caches
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .mypy_cache .pytest_cache

fclean: clean ## Run clean and also delete the virtual environment (.venv)
	rm -rf .venv

lint: ## Check the code with flake8 and mypy (subject flags)
	$(UV) flake8 .
	$(UV) mypy . --warn-return-any --warn-unused-ignores \
		--ignore-missing-imports --disallow-untyped-defs \
		--check-untyped-defs

lint-strict: ## Check the code with flake8 and mypy --strict (optional)
	$(UV) flake8 .
	$(UV) mypy . --strict
