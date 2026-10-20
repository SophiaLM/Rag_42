ARGS ?=
UV   ?= uv run

.PHONY: install run debug clean lint lint-strict

install:
	uv sync

run:
	$(UV) python -m src $(ARGS)

debug:
	$(UV) python -m pdb -m src $(ARGS)

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .mypy_cache .pytest_cache

fclean: clean
	rm -rf .venv

lint:
	$(UV) flake8 .
	$(UV) mypy . --warn-return-any --warn-unused-ignores \
		--ignore-missing-imports --disallow-untyped-defs \
		--check-untyped-defs

lint-strict:
	$(UV) flake8 .
	$(UV) mypy . --strict
