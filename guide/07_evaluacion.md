# 07 — Evaluación: recall@k e IoU

Un sistema sin medida es una **caja negra**: puedes cambiar cosas pero no sabes si mejoras. Esta etapa implementa **tu propio comando `evaluate`** con las dos métricas de la teoría `07`: **IoU** (cuánto solapa lo que devolviste con lo correcto) y **recall@k** (cuántas fuentes correctas entraron en tu top-k).

> El número **oficial** lo calcula la **moulinette**, no tu código. `evaluate` es tu herramienta **interna** para iterar rápido. Tu solución **nunca** importa ni llama a la moulinette (subject VI.6).

---

## 1. Qué vas a construir

Un módulo `src/evaluator.py` con la métrica completa, más el **comando `evaluate`** en la CLI. Cuatro funciones que se apoyan una en otra:

```text
iou            ── ¿cuánto se solapan dos rangos?
is_hit         ── ¿este resultado acierta esta fuente correcta?
question_recall── ¿qué fracción de las fuentes correctas encontré (top-k)?
recall_at_k    ── media de esa fracción sobre todas las preguntas
```

**Dónde vive cada cosa:**

| Símbolo | Ubicación | Por qué ahí |
|---|---|---|
| `iou`, `is_hit` | `evaluator.py` | Reglas de acierto: solo las usa la métrica |
| `question_recall`, `recall_at_k` | `evaluator.py` | Agregación del recall |
| `evaluate` | `evaluator.py` + `cli.py` | Reporte por consola de una tanda |
| `"evaluate"` | mapa de `__main__.py` | Un comando más |

---

## 2. Las piezas que necesitas

Firmas (con docstring). **La lógica**, debajo.

```python
from src.io_utils import load_dataset, load_search_results
from src.models import AnsweredQuestion, MinimalSearchResults, MinimalSource


def iou(a_start: int, a_end: int, b_start: int, b_end: int) -> float:
    """Intersección sobre unión de dos rangos [start, end)."""


def is_hit(result: MinimalSource, truth: MinimalSource,
           threshold: float = 0.05) -> bool:
    """¿`result` cuenta como acierto de `truth`? (mismo archivo + IoU suficiente)."""


def question_recall(results: list[MinimalSource], truths: list[MinimalSource],
                    k: int, threshold: float = 0.05) -> float:
    """Fracción de `truths` encontrada en los primeros `k` resultados."""


def recall_at_k(students: list[MinimalSearchResults],
                truths: list[AnsweredQuestion],
                k: int, threshold: float = 0.05) -> float:
    """Media de `question_recall` sobre todas las preguntas."""


def evaluate(student_search_results_path: str, dataset_path: str,
             k: int = 10) -> None:
    """Imprime Recall@1/3/5/10 comparando tu salida con el ground truth."""
```

### La lógica detrás de cada una

**`iou`** — la fórmula de la teoría `07`, literal:

```text
intersección = max(0, min(a_end, b_end) − max(a_start, b_start))
unión        = (a_end − a_start) + (b_end − b_start) − intersección
IoU          = intersección / unión        (0.0 si la unión es 0)
```

Devuelve entre `0` (no se tocan) y `1` (coinciden exacto). El `if union > 0 else 0.0` protege dos rangos vacíos.

**`is_hit(result, truth, threshold)`** — las **dos** condiciones de la teoría `07`, en este orden:

1. **Mismo `file_path`** (comparación exacta, `02`): si el archivo difiere, **nunca** cuenta — ni se calcula el IoU.
2. **IoU ≥ `threshold`** (default **0.05**): basta con solapar **un poco**. El umbral es bajo a propósito: reproducir offsets exactos es casi imposible (depende del chunking), así que se premia traer la **región correcta** del archivo correcto.

**`question_recall(results, truths, k, threshold)`** — para **una** pregunta:

- Tomar los primeros `k` de `results` (el top-k).
- Contar cuántas fuentes correctas `truth` tienen **al menos un** resultado que sea `is_hit`.
- Devolver `encontradas / len(truths)`, o `0.0` si no hay fuentes correctas.

**El detalle que se escapa:** cada `truth` cuenta **una vez**, y **solo una**. Dos resultados que cubren el **mismo** sitio no valen por dos fuentes correctas distintas (teoría `07`). Por eso el `any(...)` se evalúa **por verdad**, no por resultado.

**`recall_at_k(students, truths, k, threshold)`** — la cifra del sistema:

- Indexar el ground truth por `question_id` (emparejar por id, no por orden).
- Para cada resultado de búsqueda cuyo `question_id` exista en el ground truth, calcular su `question_recall`.
- Devolver la **media**. Preguntas del sistema que no estén en el ground truth se **saltan** (no cuentan ni arriba ni abajo).

**`evaluate(...)`** — el comando:

1. Cargar tu salida (`load_search_results`) y el ground truth (`load_dataset`), capturando `FileNotFoundError`/`OSError`/`ValueError` → aviso sin traceback.
2. Quedarse solo con las preguntas `AnsweredQuestion` (las que traen `sources`).
3. Imprimir **Recall@1, @3, @5, @10** (los que quepan según tu `k`).

---

## 3. Reglas que este paso debe respetar

| Regla (teoría `07` / subject VII) | Implementación |
|---|---|
| **Mismo archivo** obligatorio | `is_hit` corta si `file_path` difiere |
| Umbral de solape bajo | `threshold = 0.05` |
| Cada fuente correcta cuenta **una vez** | `any(...)` por verdad, no por resultado |
| Media sobre preguntas | `recall_at_k` promedia `question_recall` |
| Docs y **code** se miden aparte | Correr `evaluate` dos veces, una por dataset |
| El número oficial es de la moulinette | `evaluate` es solo para iterar; no la importes |

> Mide **docs y code por separado**, siempre. Una sola cifra mezclada esconde que un perfil mejora mientras el otro empeora (teoría `07`). Y no sobreajustes: prefiere mejoras **generales** (mejor tokenización) a trucos sobre las preguntas que ves.

---

## 4. El bucle de mejora (por qué esta etapa es el motor del desarrollo)

Medir no es el trámite del final; es **cómo se mejora**. La teoría `07` lo resume: anota una **línea base**, clasifica cada fallo y cambia **una cosa cada vez**.

| Síntoma | Causa probable | Qué tocar |
|---|---|---|
| Archivo equivocado | El vocabulario de la pregunta no está en el chunk | Tokenización (`04`), enriquecer con la ruta |
| Archivo correcto, solape bajo | Chunk demasiado grande o mal cortado | Chunking (`02`) |
| Archivo no indexado | Extensión excluida sin querer | `iter_corpus_files` (`01`) |
| Correcta pero fuera del top-k | Ranking flojo | `k1`, `b` (`05b`), deduplicar |

---

## 5. Caso de uso mínimo

```bash
uv run python -m src evaluate \
    --student_search_results_path data/output/search_results/UnansweredQuestions/dataset_docs_public.json \
    --dataset_path data/datasets/AnsweredQuestions/dataset_docs_public.json
```

Salida esperada (formato del subject), por ejemplo:

```text
Evaluation Results
========================================
Recall@1: 0.450
Recall@3: 0.590
Recall@5: 0.650
Recall@10: 0.720
```

(Los objetivos son **docs ≥ 80%** y **code ≥ 50%** en recall@5; estos números son solo ilustrativos.)

---

## 6. Comprobación

`tests/test_evaluator.py`. Qué demuestra cada test:

| Test | Qué demuestra |
|---|---|
| `test_iou_known_values` | `iou(100,300,250,350) == 0.2`, idénticos `1.0`, disjuntos `0.0` |
| `test_different_file_never_hits` | Distinto `file_path` ⇒ `is_hit` **False**, aunque solapen |
| `test_question_recall_counts_each_truth_once` | Dos verdades, una encontrada ⇒ `0.5` |
| `test_duplicates_do_not_double_count` | Dos resultados sobre **la misma** verdad siguen dando `0.5` |
| `test_system_recall_is_the_mean` | Una pregunta perfecta y otra vacía ⇒ media `0.5` |

Los dos del medio son los que atrapan el error sutil de contar aciertos dos veces.

---

## 7. Qué NO cubre esta parte

- **Generar respuestas** (el siguiente y último tramo del pipeline) → `08`.
- **Mejorar la métrica**: `evaluate` te da el número; el trabajo de subirlo es iterar sobre `02`, `04` y `05b`.

## 8. Checklist

- [ ] `iou`, `is_hit`, `question_recall`, `recall_at_k` y `evaluate` implementados.
- [ ] Acierto = **mismo `file_path`** + IoU ≥ 0.05.
- [ ] Una fuente correcta cuenta una sola vez.
- [ ] Mides **docs y code por separado**; línea base anotada.
- [ ] `uv run pytest` y `uv run make lint` en verde.

## 9. Tiempo estimado

**≈ 45–60 minutos** de código; el grueso es medir y analizar fallos.
