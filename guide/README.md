# guide — la parte práctica, paso a paso

Esta carpeta es la **continuación práctica** de `teory_openai/`. Ya leíste la teoría; aquí **la convertimos en un sistema que funciona**. Cada archivo es una *etapa* del pipeline y se puede leer y ejecutar de forma independiente.

La regla de oro: **una etapa terminada, un checklist cerrado**. No pases de archivo hasta que el anterior compile, pase el lint y sus *testers* estén en verde.

## Qué tiene cada archivo

Todos siguen el mismo formato:

1. **Qué vas a construir** — la etapa en sencillo, conectada con su teoría.
2. **Estructura del código** — qué módulos y archivos aparecen (o cambian).
3. **Funciones que vas a necesitar** — *qué hace, qué recibe y qué retorna*, con ejemplo mínimo y de uso **real**.
4. **Testers** — cómo verificar con `pytest` y con comandos reales.
5. **Checklist de esta parte**.
6. **Tiempo estimado**.

## Mapa de la guía

| Archivo | Etapa | Teoría |
|---|---|---|
| `00a_entorno_minimo.md` | `uv`, Makefile, lint y layout mínimos | — |
| `00b_cli_minimo.md` | Paquete y CLI con Fire (stub de `index`) | — |
| `01_corpus_offsets.md` | Leer el corpus siempre igual y manejar coordenadas | `02` |
| `02_chunking.md` | Partir código (AST) y documentación (títulos) | `03` |
| `03_modelos_datos.md` | Modelos pydantic y (de)serialización JSON | `04` |
| `04_tokenizacion.md` | Tokenizador de búsqueda (identificadores incluidos) | `05` |
| `05a_indice_estructura.md` | Índice invertido: estructura y construcción | `06` |
| `05b_busqueda_lexica.md` | BM25 y búsqueda top-k | `06` |
| `05c_persistencia_indice.md` | Guardar/cargar el índice y comando `index` | `06` |
| `06a_retriever_lote.md` | `search_dataset` y `dataset_scope` | `01`, `06` |
| `06b_cli_busqueda.md` | CLI `search`/`search_dataset` y robustez | `01`, `06` |
| `07_evaluacion.md` | Tu propio `evaluate`: IoU + recall@k | `07` |
| `08a_contexto_prompt.md` | Releer contexto y construir el prompt | `00`, `08` |
| `08b_modelo_generacion.md` | Qwen3-0.6B y generación determinista | `00`, `08` |
| `08c_generacion_lote.md` | `answer` y `answer_dataset` | `00`, `08` |
| `09_cierre_readme_y_defensa.md` | README, edge cases, end-to-end, defensa | — |

El orden importa: cada archivo usa cosas del anterior.

## Estructura final del repositorio

```
rag42/
├── Makefile
├── pyproject.toml
├── uv.lock
├── README.md
├── .gitignore
├── data/                              # NO se sube a git
│   ├── raw/vllm-0.10.1/               # el corpus provisto
│   ├── processed/                     # el índice persistido
│   ├── datasets/
│   │   ├── UnansweredQuestions/
│   │   └── AnsweredQuestions/
│   └── output/
│       ├── search_results/<Scope>/
│       └── search_results_and_answer/<Scope>/
└── src/
    ├── __init__.py
    ├── __main__.py        # entrada de Fire
    ├── cli.py             # comandos de la CLI
    ├── corpus.py          # lectura, rutas, offsets
    ├── chunking.py        # corte (código / markdown)
    ├── models.py          # modelos pydantic
    ├── tokenizer.py       # tokenizador de búsqueda
    ├── index.py           # índice invertido + BM25 + persistencia
    ├── retriever.py       # búsqueda (single y batch)
    ├── evaluator.py       # IoU + recall@k
    ├── generator.py       # contexto, prompt y generación con Qwen
    └── io_utils.py        # helpers de JSON
```

> **Nota sobre el corpus.** El material provisto vive en `proyect/vllm-0.10.1/vllm-0.10.1/` (anidado). El subject espera `data/raw/vllm-0.10.1/`, y **las rutas de tu salida deben empezar por `data/raw/vllm-0.10.1/`** porque el `file_path` se compara *verbatim*. Copia (o enlaza) el corpus a esa ruta al preparar el entorno.

## Criterios de aprobado que persigue todo esto

| Criterio | Umbral | Dónde |
|---|---|---|
| Recall@5 en `docs` | **≥ 80%** | `02`, `04`, `05b`, `07` |
| Recall@5 en `code` | **≥ 50%** | `02`, `04`, `05b`, `07` |
| Indexado del corpus | **≤ 5 min** | `05c` |
| Recuperación de 200 preguntas | **≤ 90 s** | `06a`, `06b` |
| Ancho de cada fuente | **≤ 2000 caracteres** | `02`, `05b` |
| Solape para contar acierto (IoU) | **≥ 0.05** | `07` |
| Modelo de generación | `Qwen/Qwen3-0.6B` | `08b`, `08c` |

El recall **oficial** lo calcula la `moulinette`; tu comando `evaluate` es solo para iterar.

## Línea de tiempo sugerida

| Etapa | Días |
|---|---|
| `00a`/`00b` entorno y CLI mínimos | 0.5 |
| `01` corpus y offsets | 0.5 |
| `02` chunking | 1.5 |
| `03` modelos de datos | 0.5 |
| `04` tokenización | 0.5 |
| `05a`–`05c` índice y búsqueda | 2 |
| `06a`/`06b` recuperación en lote | 1 |
| `07` evaluación propia | 1 |
| `08a`–`08c` generación | 2 |
| `09` cierre y defensa | 1.5 |
| **Total** | **≈ 12–13 días** |

## Checklist global (el proyecto completo)

- [ ] `uv sync` funciona desde la raíz del repositorio.
- [ ] `make lint` pasa (`flake8 .` y `mypy .` con los flags del subject).
- [ ] `uv run python -m src index --max_chunk_size 2000` indexa en **≤ 5 min**.
- [ ] `search_dataset` sobre `docs` y `code` produce JSON válido y cumple los tiempos.
- [ ] `moulinette` reporta **docs ≥ 80% recall@5** y **code ≥ 50% recall@5**.
- [ ] `answer_dataset` genera respuestas coherentes y ancladas.
- [ ] `README.md` cumple *todas* las secciones exigidas.
- [ ] Ningún camino de entrada revienta con traceback.
- [ ] El repositorio **no** incluye `data/`, pesos ni salidas generadas.

Empieza por `00a_entorno_minimo.md`.
