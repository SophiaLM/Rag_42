# 00a — Entorno mínimo

Todo lo que construyas después (leer el corpus, cortarlo en trozos, indexar, generar respuestas) necesita un **sitio donde vivir** y unas **reglas de calidad que se cumplan desde el primer commit**. Esta etapa no añade funcionalidad RAG: monta el andamiaje y deja el repositorio en verde. Es aburrida a propósito.

---

## 0. Por qué esta etapa merece un archivo propio

Dos cosas del subject convierten el andamiaje en algo **evaluable**, no en decoración:

- **El layout es un contrato.** Durante la defensa el pipeline se ejecuta con scripts de referencia que leen `data/raw/`, escriben en `data/processed/` y `data/output/...`, y buscan los datasets en `data/datasets/...`. Si las rutas no coinciden, esos scripts no arrancan y los checks correspondientes *se consideran fallidos por diseño*.
- **El lint es una puerta.** El subject exige `flake8` y `mypy` con unos flags concretos. Si el esqueleto no pasa `uv run make lint`, ninguna etapa posterior puede darse por terminada.

Por eso aquí explicamos **qué es cada pieza y por qué existe**, aunque sea "solo" configuración.

---

## 1. Las reglas que hereda TODO el proyecto (subject, V.1)

Estas reglas no son de esta etapa: aplican a **cada** archivo de `src/` (y del bonus). Las tienes aquí una vez para no repetirlas en cada archivo:

- **Python 3.10 o posterior.**
- **Estilo `flake8`.**
- **Excepciones controladas:** `try/except` para que ningún camino del programa reviente, y *context managers* (`with`) para liberar recursos (ficheros, conexiones).
- **Type hints** en parámetros, retornos y variables; `mypy` debe pasar **sin errores** con los flags de la regla `lint`.
- **Docstrings PEP 257** (estilo Google o NumPy) en funciones y clases: propósito, parámetros y retorno.

> Los fragmentos de esta guía a veces omiten docstrings y tipos **por brevedad**. Tú los añades **siempre**: el evaluador los exige y forman parte del `mypy --disallow-untyped-defs`.

---

## 2. Dónde vive cada obligación

Esta tabla es el mapa *requisito del subject → archivo que lo cumple*. Si algo se cae en la defensa, la respuesta está aquí:

| Obligación (subject) | Dónde la cumples |
|---|---|
| Python ≥ 3.10 (V.1) | `requires-python` en `pyproject.toml` |
| Estilo `flake8` (V.1) | `.flake8` |
| `uv` como gestor, el evaluador solo corre `uv sync` (V.4) | regla `install` + variable `UV` del `Makefile` |
| `mypy` con los flags exigidos (V.2) | regla `lint` del `Makefile` |
| `pydantic`, `Fire`, `tqdm` (V.4) | `dependencies` en `pyproject.toml` |
| CLI con `Fire` (V.4/VI.6) | `src/__main__.py` (siguiente etapa, `00b`) |
| No subir `data/`, pesos ni salidas (X) | `.gitignore` |

---

## 3. La estructura de carpetas, y para qué sirve cada una

```text
rag42/
├── .flake8
├── .gitignore
├── Makefile
├── pyproject.toml
├── uv.lock                 # lo genera `uv sync`; SÍ se commitea (subject X)
├── data/                   # NO se versiona (ver .gitignore)
│   ├── raw/                # el corpus provisto (vLLM)
│   ├── processed/          # el índice persistido
│   ├── datasets/
│   │   ├── UnansweredQuestions/   # preguntas de entrada
│   │   └── AnsweredQuestions/     # ground truth para puntuar
│   └── output/
│       ├── search_results/                # salida de search_dataset
│       └── search_results_and_answer/     # salida de answer_dataset
└── src/
    └── __init__.py
```

Ahora el por qué, carpeta a carpeta — esto es justo lo que suele faltar:

| Carpeta | Para qué | Quién la llena |
|---|---|---|
| `src/` | tu paquete Python; el evaluador lo ejecuta como `uv run python -m src <command>` | tú |
| `data/raw/` | el corpus provisto (vLLM). Tus rutas de salida deben empezar por `data/raw/vllm-0.10.1/...` | tú, copiando el corpus (`01`) |
| `data/processed/` | el índice que construye el comando `index` | comando `index` (`05c`) |
| `data/datasets/UnansweredQuestions/` | preguntas **sin** respuesta: la entrada de `search_dataset`/`answer_dataset` | material provisto |
| `data/datasets/AnsweredQuestions/` | las mismas preguntas **con** sus fuentes correctas (ground truth) | material provisto |
| `data/output/search_results/<Scope>/` | resultado de `search_dataset` | comando `search_dataset` (`06b`) |
| `data/output/search_results_and_answer/<Scope>/` | resultado de `answer_dataset` | comando `answer_dataset` (`08c`) |

Tres consecuencias que importan:

- **`<Scope>` no es decorativo.** Los datasets públicos comparten nombre de fichero (`dataset_docs_public.json`), así que si no separas por `UnansweredQuestions`/`AnsweredQuestions`, una ejecución pisa a la otra y pierdes resultados.
- **`data/` no viaja en git.** Está en `.gitignore`. Por eso el árbol de arriba es **local**: las carpetas de salida **no** las creas a mano — cada comando las abre con `mkdir(parents=True, exist_ok=True)`. La única que preparas tú es `data/raw/`, para colocar el corpus.
- **`data/raw/` fija la ruta exacta.** El grader compara `file_path` *verbatim* (carácter a carácter), así que el prefijo tiene que ser `data/raw/vllm-0.10.1/` y **no** `proyect/...` ni `./data/...`.

> `data/processed/`, `data/output/...`, etc. pueden no existir todavía: aparecerán cuando su comando corra. No hace falta crearlas ni dejar `.gitkeep` (no hay nada que versionar dentro de `data/`).

---

## 4. Los archivos, uno a uno

### `.flake8`

**Por qué el archivo:** `flake8` busca su configuración automáticamente; tenerla en un fichero evita escribir flags a mano en cada ejecución y deja la regla del `Makefile` limpia.

```ini
[flake8]
max-line-length = 88
extend-ignore = E203, W503
exclude = .venv,data,.git,__pycache__,.pytest_cache,.mypy_cache
```

- **`exclude = ...data...`.** Aquí está la clave: **`data/` contiene el corpus de vLLM, que no es tu código**. Si lo linteas, obtendrás miles de avisos de archivos ajenos y `make lint` tardará una eternidad. Igual con `.venv` (las librerías instaladas) y las cachés.

### `.gitignore`

**Por qué:** el subject (X) prohíbe subir datos grandes, pesos del modelo y salidas generadas; V.3 pide excluir artefactos de Python.

```gitignore
__pycache__/
*.py[cod]
.venv/
.mypy_cache/
.pytest_cache/
data/
```

- `__pycache__/` y `*.py[cod]` → bytecode compilado, se regenera solo.
- `.venv/` → el entorno virtual; cualquiera lo recrea con `uv sync`.
- `.mypy_cache/` y `.pytest_cache/` → cachés de herramientas.
- `data/` → **todo** el directorio (corpus, índice, datasets, salidas). Es el punto X del subject: el evaluador genera esos datos durante la evaluación, no los recibe de tu repo.

> Nota práctica: `uv.lock` **sí** se commitea (lo exige el subject para reproducir el entorno), aunque `data/` no. Son cosas distintas: uno es tu código/entorno, el otro son datos generados.

### `Makefile`

**Por qué:** el subject (V.2) exige reglas concretas. Este `Makefile` es la interfaz con la que el evaluador (y tú) ejecutáis todo:

```makefile
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

lint:
	$(UV) flake8 .
	$(UV) mypy . --warn-return-any --warn-unused-ignores \
		--ignore-missing-imports --disallow-untyped-defs \
		--check-untyped-defs

lint-strict:
	$(UV) flake8 .
	$(UV) mypy . --strict
```

Qué hace cada pieza, y por qué así:

- **`UV ?= uv run`** (con `?=` para poder sobreescribirla). Existe por un motivo concreto: `flake8` y `mypy` viven **dentro** del entorno del proyecto (grupo `dev`), no en el sistema. Ejecutar `flake8 .` a pelo da `command not found`; `uv run flake8 .` lo lanza dentro del venv correcto. Por eso la variable se usa **también en `lint`**, no solo en `run`.
- **`ARGS ?=`** permite `make run ARGS="index --max_chunk_size 2000"` sin tocar el fichero.
- **`install`** → `uv sync` a secas. El subject (V.4) es tajante: el evaluador **solo** corre `uv sync`. Nada de `pip install`.
- **`run`** → `python -m src` es **la** forma de invocar el programa que fija el subject (VI.6); el `$(ARGS)` deja pasar el comando (`index`, `search`, ...).
- **`debug`** → el mismo arranque bajo `pdb` (depurador de la stdlib), como pide V.2.
- **`clean`** → borra bytecode y cachés de mypy/pytest.
- **`lint`** → los comandos y flags **exactos** de V.2. No los cambies: el evaluador los comprueba.
- **`lint-strict`** → misma pareja con `--strict` (opcional "muy recomendado" por el subject). Úsalo cuando quieras endurecer.

### `pyproject.toml`

**Por qué:** es donde declaras versión de Python, dependencias y la configuración de las herramientas. `uv` lo lee para crear el entorno.

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

- **`requires-python = ">=3.10"`** → refleja la regla V.1; `uv` se niega a usar un intérprete más antiguo.
- **`dependencies`** → las tres que el proyecto usa **de punta a punta** y que el subject (V.4) exige: `pydantic` (modelos de datos), `fire` (CLI), `tqdm` (barras de progreso). Deliberadamente **no** declaramos `torch`/`transformers` todavía: llegan en `08a` y pesan varios GB; meterlos ahora obligaría a descargarlos en cada `uv sync` de etapas que aún no generan nada.
- **`[dependency-groups] dev`** → herramientas de desarrollo: `pytest` (V.3 recomienda tests), `flake8` y `mypy` (V.1). Van separadas porque no son runtime; `uv sync` instala los dos grupos por defecto, pero podrías hacer `uv sync --no-dev` para un entorno de solo ejecución.
- **`[tool.pytest.ini_options] pythonpath = ["."]`** → para que los tests hagan `from src... import ...` sin instalar el paquete.
- **`[tool.mypy] exclude`** → `data/` (el corpus de terceros: no queremos que `mypy` analice miles de archivos de vLLM) y `.venv/`.

> `uv.lock` no lo escribes tú: lo genera `uv sync` y fija las versiones **exactas**. Commitéalo: con él, el evaluador reproduce tu mismo entorno.

### `src/__init__.py`

**Por qué existe:** un directorio se convierte en *paquete* Python cuando contiene `__init__.py`. Sin él, `uv run python -m src` no encuentra `src` como paquete. De momento basta con su docstring:

```python
"""RAG42 package."""
```

---

## 5. Comprobación

```bash
uv sync
uv run make lint
```

Qué debe pasar: `uv sync` crea `.venv/` y `uv.lock`; `make lint` termina **en verde** (sin errores ni de `flake8` ni de `mypy`). Si `mypy` se queja de que no hay nada que comprobar, es normal en este punto — todavía solo existe `__init__.py`.

---

## 6. Qué NO cubre esta parte

- **La CLI y `__main__.py`** → `00b`.
- **El corpus dentro de `data/raw/`** → lo colocas en `01`.
- **Tests de verdad (`pytest`)** → llegan con la primera función con lógica (`01`); aquí no hay nada que testear.
- **`torch`/`transformers`** → `08a`, cuando toque cargar el modelo.

---

## 7. Checklist

- [ ] Carpetas `src/` y `data/` creadas (solo `src/__init__.py` es obligatorio de momento).
- [ ] `.flake8`, `.gitignore`, `Makefile`, `pyproject.toml`, `src/__init__.py` existen.
- [ ] `uv sync` funciona desde la raíz.
- [ ] `uv run make lint` pasa en verde.

## 8. Tiempo estimado

**≈ 10–15 minutos.**
