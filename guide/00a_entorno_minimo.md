# 00a — Entorno mínimo

El objetivo de esta parte es tener un **esqueleto mínimo y limpio** que pase `make lint` desde cero. Aquí solo pones lo imprescindible: configuración, estructura de carpetas y `__init__.py`.

## 1. ¿Qué vas a crear?

Solo lo necesario para empezar:

- `.flake8`, `.gitignore`, `Makefile`, `pyproject.toml` (dependencias mínimas)
- Estructura `src/`, `data/` y `__init__.py`

No crees aún la CLI completa. Eso llega más adelante.

## Convenciones obligatorias (todo el proyecto)

Estas reglas del subject aplican a **todos** los archivos de `src/` (y a los del bonus):

- **Python 3.10+** y estilo **flake8** (línea ≤ 88).
- **Type hints** en parámetros, retornos y variables; `mypy` debe pasar con los flags de `make lint`.
- **Docstrings PEP 257** en funciones y clases (estilo Google o NumPy): propósito, parámetros y retorno. No es opcional.
- **Manejo de excepciones** con `try/except` para no reventar; usa *context managers* para recursos.

> Los ejemplos de esta guía omiten a veces los docstrings y los tipos por brevedad. **Añádelos en tu código**: el evaluador los exige.

## 2. Estructura

```text
rag42/
├── .flake8
├── .gitignore
├── Makefile
├── pyproject.toml
├── data/
│   ├── raw/
│   ├── processed/
│   ├── datasets/
│   │   ├── UnansweredQuestions/
│   │   └── AnsweredQuestions/
│   └── output/
│       ├── search_results/
│       └── search_results_and_answer/
└── src/
    └── __init__.py
```

## 3. Archivos

### `.flake8`
```ini
[flake8]
max-line-length = 88
extend-ignore = E203, W503
exclude = .venv,data,.git,__pycache__,.pytest_cache,.mypy_cache
```

### `.gitignore`
```gitignore
__pycache__/
*.py[cod]
.venv/
.mypy_cache/
.pytest_cache/
data/
```

### `Makefile`
```makefile
ARGS ?=

install:
	uv sync

run:
	uv run python -m src $(ARGS)

debug:
	uv run python -m pdb -m src $(ARGS)

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .mypy_cache .pytest_cache

lint:
	flake8 .
	mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	flake8 .
	mypy . --strict
```

### `pyproject.toml`
```toml
[project]
name = "rag42"
version = "0.1.0"
description = "RAG against the machine"
requires-python = ">=3.10"
dependencies = [
    "pydantic>=2",
    "fire",
    "tqdm",
]

[dependency-groups]
dev = [
    "pytest",
    "flake8",
    "mypy",
]

[tool.pytest.ini_options]
pythonpath = ["."]

[tool.mypy]
exclude = ["^data/", "^\\.venv/"]
```

### `src/__init__.py`
```python
"""RAG42 package."""
```

## 4. Comprobación

```bash
uv sync
make lint
```

## 5. Checklist

- [ ] Carpetas `src/` y `data/` creadas.
- [ ] `.flake8`, `.gitignore`, `Makefile`, `pyproject.toml`, `src/__init__.py` existen.
- [ ] `uv sync` funciona.
- [ ] `make lint` pasa en verde.

## 6. Tiempo estimado

**≈ 10–15 minutos.**
