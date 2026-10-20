# 09 — Cierre: README, robustez, end-to-end y defensa

La última etapa **no es escribir más código**: es **demostrar** que el sistema es correcto, reproducible y explicable. Todo lo que construiste en `01`–`08` ya funciona por partes; aquí lo pruebas **de extremo a extremo**, lo documentas y lo preparas para la defensa. Un grader no evalúa lo que sabes hacer, evalúa lo que **se ve** en el repositorio y lo que **respondes** en vivo.

---

## 1. Flujo end-to-end (como lo corre el evaluador)

Este es el recorrido completo, **en el orden real**. Cópialo y ejecútalo tal cual:

```bash
# 1. Indexar (objetivo: <= 5 min)
time uv run python -m src index --max_chunk_size 2000

# 2. Buscar sobre un dataset (objetivo: <= 90 s / 200 preguntas)
#    El scope lo aporta el llamante: --save_directory ya viene scopeado.
time uv run python -m src search_dataset \
    --dataset_path data/datasets/UnansweredQuestions/dataset_docs_public.json \
    --k 10 --save_directory data/output/search_results/UnansweredQuestions

# 3. Puntuar con la moulinette (tu salida PRIMERO, ground truth SEGUNDO)
./moulinette evaluate_student_search_results \
    data/output/search_results/UnansweredQuestions/dataset_docs_public.json \
    data/datasets/AnsweredQuestions/dataset_docs_public.json \
    --k 10 --max_context_length 2000

# 4. Generar respuestas
time uv run python -m src answer_dataset \
    --student_search_results_path data/output/search_results/UnansweredQuestions/dataset_docs_public.json \
    --save_directory data/output/search_results_and_answer/UnansweredQuestions
```

Repite con `dataset_code_public.json`. Objetivos: **docs ≥ 80%** y **code ≥ 50%** en recall@5.

> Dos avisos que valen puntos: (1) renombra `moulinette-ubuntu`/`moulinette-fedora` a `moulinette` antes de usarlo; (2) **tu solución nunca importa ni llama a la moulinette** (subject VI.6) — es una herramienta *externa* de medida. Y fíjate en el **orden** de los argumentos: primero lo tuyo, después el ground truth.

---

## 2. Matriz de robustez (ningún traceback)

El subject (VI.6) es tajante: **ningún camino de entrada puede producir un `Traceback`**. Esta tabla es tu red de seguridad; cada fila la resolviste en una etapa anterior:

| Entrada | Comando | Resultado esperado | ¿Dónde se resuelve? |
|---|---|---|---|
| query vacía | `search "" --k 5` | salida vacía, sin error | `05b` |
| query absurda | `search "asdfghjkl" --k 5` | lista vacía | `05b` |
| `k = 0` | `search "cache" --k 0` | lista vacía | `05b` |
| `k` enorme | `search "cache" --k 100000` | todos los que haya | `05b` |
| archivo que falta | `search_dataset --dataset_path no/existe.json ...` | mensaje claro | `06b` |
| JSON mal formado | `search_dataset --dataset_path bad.json ...` | mensaje claro | `06b` |
| archivo del corpus borrado | `answer "..." --k 5` | salta la fuente | `08a` |
| índice ausente | `search "..." --k 5` (sin indexar) | mensaje claro | `06b` |

```bash
uv run python -m src search "" --k 5
uv run python -m src search "asdfghjkl" --k 5
uv run python -m src search "cache" --k 0
printf '{not json' > /tmp/bad.json
uv run python -m src search_dataset --dataset_path /tmp/bad.json --k 5 --save_directory /tmp/o
uv run python -m src search_dataset --dataset_path no/existe.json --k 5 --save_directory /tmp/o
echo "Si no ves Traceback, esta parte esta bien."
```

La única aserción es siempre la misma: **"no veo `Traceback`"**. Es literalmente lo que exige el subject.

---

## 3. `README.md` (secciones obligatorias, en inglés)

El README **es el entregable** del sistema: quien lo lee debe entender qué hiciste y por qué. Cada sección, y **por qué existe**:

- [ ] **Primera línea en cursiva:** *"This project has been created as part of the 42 curriculum by &lt;login1&gt;[...]."* — identificación obligatoria.
- [ ] **Description** — qué es el sistema y qué problema resuelve (RAG sobre un corpus).
- [ ] **Instructions** — `uv sync` y **todos** los comandos; el evaluador solo corre `uv sync`, así que aquí no puede faltar nada.
- [ ] **Resources** — referencias **y** cómo usaste la IA (obligatorio; sé honesto y concreto).
- [ ] **System architecture** — el pipeline RAG (`01`→`08`).
- [ ] **Chunking strategy** — `02`: cómo partes código y docs, solape, techo de tamaño.
- [ ] **Retrieval method** — `05a`/`05b`: ¿BM25 o TF-IDF?, y **qué `k1`/`b`** usaste.
- [ ] **Performance analysis** — `07`: recall@k y **tiempos reales** (docs y code por separado).
- [ ] **Design decisions** — las bifurcaciones y por qué elegiste cada rama.
- [ ] **Challenges faced** — qué se rompió y cómo lo resolviste (aquí brilla quien iteró midiendo).
- [ ] **Example usage** — un ejemplo de comando + salida.

> Escribe el README con **tus números reales**, no con los del subject. Un README con números inventados es peor que uno sin números: se detecta en la defensa.

---

## 4. Contenido del repositorio (la entrega)

Qué se versiona y qué **no** (subject X):

- [ ] **Sí:** `src/`, `pyproject.toml`, `uv.lock`, `Makefile`, `README.md`, la config necesaria (`.flake8`, etc.).
- [ ] **No:** `data/` (corpus, datasets, índice, salidas), pesos del modelo ni salidas generadas.

```bash
git status --short      # sin data/, *.json de salida, ni pesos
uv sync                 # debe funcionar desde un clon limpio
make lint
```

`data/` ya está en `.gitignore` desde `00a`. Si aparece en `git status`, algo se coló.

---

## 5. Checklist global

**Funcional:** `index` ≤ 5 min; `search`/`search_dataset`; `answer`/`answer_dataset`; `evaluate`.
**Calidad:** docs ≥ 80% y code ≥ 50% (recall@5); 200 preguntas ≤ 90 s; fuentes ≤ 2000 caracteres; robustez sin `Traceback`.
**Entrega:** `make lint` verde; `uv sync` desde la raíz; README completo; `.gitignore` excluye `data/`; sin rutas *hardcodeadas*.

---

## 6. Defensa y *recode*

Prepárate para explicar **con tus palabras** (no leyendo): por qué RAG y no fine-tuning; cómo lees el corpus (offsets en **caracteres**, no bytes); cómo chunkas código y docs; cómo tokenizas (**mismo** tokenizador en ambos lados); cómo puntúas con BM25 (`k1`, `b`); cómo mides con IoU y recall@k; cómo generas contexto y por qué **la estructura la construye tu código**.

Para el **recode**:

- Ten a mano una **tabla de palancas**: `max_chunk_size`, `k1`, `b`, `k`, `stopwords`, `stemming` — y qué esperas que cambie cada una.
- Practica añadir un campo **opcional** (p. ej. `score`) a un modelo sin romper el JSON.
- Practica responder una pregunta nueva por CLI y explicar cada paso del recorrido.

---

## 7. Bonus (solo si el obligatorio está cerrado)

1. Embeddings semánticos (`all-MiniLM-L6-v2`).
2. Recuperación híbrida (léxica + semántica).
3. Indexado incremental.
4. Caché (índice y resultados).
5. API HTTP local.

> No toques el bonus si el obligatorio no está verde: el bonus **no** compensa un recall por debajo del umbral.

---

## 8. Tiempo estimado

**≈ 1–1.5 días** (README con números reales + matriz de robustez + ensayo de defensa).

---

## Y ahora, el resumen de todo el camino

Leer el corpus sin mover un offset (`01`) → partirlo respetando su significado (`02`) → vestir cada dato con un modelo (`03`) → convertirlo en términos comparables (`04`) → indexarlo y puntuarlo (`05a`–`05c`) → buscar en lote dentro del presupuesto (`06a`/`06b`) → medirlo honestamente (`07`) → generar respuestas ancladas (`08a`–`08c`) → y demostrarlo (`09`).

Eso **es** RAG: transformar "que el modelo lo sepa todo" en dos problemas tratables, **encontrar** y **resumir**.
