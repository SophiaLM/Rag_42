# 09 — Cierre: README, robustez, end-to-end y defensa

La última etapa no es "escribir más código", sino **demostrar** que el sistema es correcto, reproducible y explicable.

## 1. Flujo end-to-end (como lo corre el evaluador)

```bash
# 1. Indexar (objetivo: <= 5 min)
time uv run python -m src index --max_chunk_size 2000

# 2. Buscar sobre un dataset (objetivo: <= 90 s / 200 preguntas)
time uv run python -m src search_dataset \
    --dataset_path data/datasets/UnansweredQuestions/dataset_docs_public.json \
    --k 10 --save_directory data/output/search_results

# 3. Puntuar con la moulinette (tu salida PRIMERO, ground truth SEGUNDO)
./moulinette evaluate_student_search_results \
    data/output/search_results/UnansweredQuestions/dataset_docs_public.json \
    data/datasets/AnsweredQuestions/dataset_docs_public.json \
    --k 10 --max_context_length 2000

# 4. Generar respuestas
time uv run python -m src answer_dataset \
    --student_search_results_path data/output/search_results/UnansweredQuestions/dataset_docs_public.json \
    --save_directory data/output/search_results_and_answer
```

Repite con `dataset_code_public.json` (docs **≥ 80%**, code **≥ 50%** en recall@5).

> Renombra `moulinette-ubuntu`/`moulinette-fedora` a `moulinette` antes de usarlo. Tu solución **nunca** importa ni llama a la moulinette.

## 2. Matriz de robustez (ningún traceback)

| Entrada | Comando | Resultado esperado |
|---|---|---|
| query vacía | `search "" --k 5` | salida vacía, sin error |
| query absurda | `search "asdfghjkl" --k 5` | lista vacía |
| `k = 0` | `search "cache" --k 0` | lista vacía |
| `k` enorme | `search "cache" --k 100000` | todos los que haya |
| archivo que falta | `search_dataset --dataset_path no/existe.json ...` | mensaje claro |
| JSON mal formado | `search_dataset --dataset_path bad.json ...` | mensaje claro |
| archivo del corpus borrado | `answer "..." --k 5` | salta la fuente |
| índice ausente | `search "..." --k 5` (sin indexar) | mensaje claro |

```bash
uv run python -m src search "" --k 5
uv run python -m src search "asdfghjkl" --k 5
uv run python -m src search "cache" --k 0
printf '{not json' > /tmp/bad.json
uv run python -m src search_dataset --dataset_path /tmp/bad.json --k 5 --save_directory /tmp/o
uv run python -m src search_dataset --dataset_path no/existe.json --k 5 --save_directory /tmp/o
echo "Si no ves Traceback, esta parte esta bien."
```

## 3. `README.md` (secciones obligatorias, en inglés)

- [ ] **Primera línea en cursiva:** *"This project has been created as part of the 42 curriculum by &lt;login1&gt;[...]."*
- [ ] **Description**
- [ ] **Instructions** (`uv sync` y comandos)
- [ ] **Resources** (referencias **y** cómo se usó la IA)
- [ ] **System architecture** (pipeline RAG)
- [ ] **Chunking strategy**
- [ ] **Retrieval method** (BM25/TF-IDF, `k1`, `b`)
- [ ] **Performance analysis** (recall@k y tiempos)
- [ ] **Design decisions**
- [ ] **Challenges faced**
- [ ] **Example usage**

> Escribe el README con **tus números reales**, no con los del subject.

## 4. Contenido del repositorio (entrega)

- [ ] `src/`, `pyproject.toml`, `uv.lock`, `Makefile`, `README.md`, config necesaria.
- [ ] **NO** incluir `data/`, pesos del modelo ni salidas generadas.

```bash
git status --short      # sin data/, *.json de salida, ni pesos
uv sync                 # desde un clon limpio
make lint
```

## 5. Checklist global

**Funcional**: `index` ≤ 5 min; `search`/`search_dataset`; `answer`/`answer_dataset`; `evaluate`.
**Calidad**: docs ≥ 80% y code ≥ 50% (recall@5); 200 preguntas ≤ 90 s; fuentes ≤ 2000 chars; robustez sin tracebacks.
**Entrega**: `make lint` verde; `uv sync` desde raíz; README completo; `.gitignore` excluye `data/`; sin rutas *hardcodeadas*.

## 6. Defensa y *recode*

Prepárate para explicar con tus palabras: por qué RAG y no fine-tuning; cómo lees el corpus (offsets en caracteres); cómo chunkas código y docs; cómo tokenizas (mismo tokenizador en ambos lados); cómo puntúas con BM25 (`k1`, `b`); cómo mides con IoU y recall@k; cómo generas contexto y por qué la salida la construye tu código.

Para el **recode**: ten una **tabla de palancas** (`max_chunk_size`, `k1`, `b`, `k`, `stopwords`, `stemming`); practica añadir un campo **opcional** (`score`) a `MinimalSearchResults`; practica responder una pregunta nueva por CLI.

## 7. Bonus (solo si el obligatorio está cerrado)

1. Embeddings semánticos (`all-MiniLM-L6-v2`).
2. Recuperación híbrida (léxica + semántica).
3. Indexado incremental.
4. Caché (índice y resultados).
5. API HTTP local.

## 8. Tiempo estimado

**≈ 1–1.5 días** (README con números reales y matriz de robustez).

---

## Y ahora, el resumen de todo el camino

Leer el corpus sin mover un offset (`01`) → partirlo respetando su significado (`02`) → vestir cada dato con un modelo (`03`) → convertirlo en términos comparables (`04`) → indexarlo y puntuarlo (`05a`–`05c`) → buscar en lote dentro del presupuesto (`06a`/`06b`) → medirlo honestamente (`07`) → generar respuestas ancladas (`08a`–`08c`) → y demostrarlo (`09`).

Eso **es** RAG: transformar "que el modelo lo sepa todo" en dos problemas tratables, **encontrar** y **resumir**.
