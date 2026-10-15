# 07 — Evaluación: recall@k e IoU

Un sistema sin medida es una caja negra: puedes cambiar cosas pero no sabes si mejoras. Aquí implementas **tu propio `evaluate`** con **IoU** (cuánto solapa lo que devolviste con lo correcto) y **recall@k** (cuántas fuentes correctas quedaron en tu top-k). El número **oficial** lo dará la moulinette.

## 1. Código

`src/evaluator.py`:
```python
from src.io_utils import load_dataset, load_search_results
from src.models import AnsweredQuestion, MinimalSearchResults, MinimalSource


def iou(a_start: int, a_end: int, b_start: int, b_end: int) -> float:
    inter = max(0, min(a_end, b_end) - max(a_start, b_start))
    union = (a_end - a_start) + (b_end - b_start) - inter
    return inter / union if union > 0 else 0.0


def is_hit(result: MinimalSource, truth: MinimalSource,
           threshold: float = 0.05) -> bool:
    if result.file_path != truth.file_path:
        return False
    return iou(result.first_character_index, result.last_character_index,
               truth.first_character_index, truth.last_character_index) >= threshold


def question_recall(results: list[MinimalSource], truths: list[MinimalSource],
                    k: int, threshold: float = 0.05) -> float:
    if not truths:
        return 0.0
    top = results[:k]
    found = sum(
        1 for truth in truths
        if any(is_hit(r, truth, threshold) for r in top)
    )
    return found / len(truths)


def recall_at_k(students: list[MinimalSearchResults],
                truths: list[AnsweredQuestion],
                k: int, threshold: float = 0.05) -> float:
    by_id = {q.question_id: q for q in truths}
    scores: list[float] = []
    for result in students:
        truth = by_id.get(result.question_id)
        if truth is None:
            continue
        scores.append(question_recall(
            result.retrieved_sources, list(truth.sources), k, threshold))
    return sum(scores) / len(scores) if scores else 0.0


def evaluate(student_search_results_path: str, dataset_path: str,
             k: int = 10) -> None:
    try:
        students = load_search_results(student_search_results_path)
        gt = load_dataset(dataset_path)
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(f"Could not load input: {exc}")
        return
    truths = [q for q in gt.rag_questions if isinstance(q, AnsweredQuestion)]
    print("Evaluation Results")
    print("=" * 40)
    cutoffs = tuple(c for c in (1, 3, 5, 10) if c <= students.k)
    if not cutoffs:
        cutoffs = (min(students.k, 1),)
    for cutoff in cutoffs:
        value = recall_at_k(students.search_results, truths, cutoff)
        print(f"Recall@{cutoff}: {value:.3f}")
```

> Reglas: el umbral de solape es **bajo** (0.05) para no castigar offsets imperfectos, y el **mismo `file_path`** es obligatorio. El ejemplo de la teoría: `iou(100, 300, 250, 350) == 0.2`.

Conecta el comando en `src/cli.py` y el mapa de `src/__main__.py`:

```python
"evaluate": cli.evaluate,
```

## 2. Testers

`tests/test_evaluator.py`:
```python
from src.evaluator import iou, is_hit, question_recall, recall_at_k
from src.models import AnsweredQuestion, MinimalSearchResults, MinimalSource


def test_iou_known_values() -> None:
    assert iou(100, 300, 250, 350) == 0.2
    assert iou(0, 100, 0, 100) == 1.0
    assert iou(0, 100, 200, 300) == 0.0
    assert iou(0, 100, 100, 200) == 0.0


def test_different_file_never_hits() -> None:
    a = MinimalSource(file_path="a.py", first_character_index=0, last_character_index=100)
    b = MinimalSource(file_path="b.py", first_character_index=0, last_character_index=100)
    assert is_hit(a, b) is False


def test_question_recall_counts_each_truth_once() -> None:
    truths = [
        MinimalSource(file_path="a.py", first_character_index=0, last_character_index=100),
        MinimalSource(file_path="a.py", first_character_index=1000, last_character_index=1100),
    ]
    results = [
        MinimalSource(file_path="a.py", first_character_index=10, last_character_index=90),
    ]
    assert question_recall(results, truths, k=5) == 0.5


def test_duplicates_do_not_double_count() -> None:
    truths = [
        MinimalSource(file_path="a.py", first_character_index=0, last_character_index=100),
        MinimalSource(file_path="a.py", first_character_index=1000, last_character_index=1100),
    ]
    results = [
        MinimalSource(file_path="a.py", first_character_index=10, last_character_index=90),
        MinimalSource(file_path="a.py", first_character_index=20, last_character_index=95),
    ]
    assert question_recall(results, truths, k=5) == 0.5


def test_system_recall_is_the_mean() -> None:
    t1 = MinimalSource(file_path="a.py", first_character_index=0, last_character_index=100)
    t2 = MinimalSource(file_path="b.py", first_character_index=0, last_character_index=100)
    truths = [
        AnsweredQuestion(question="q1", answer="x", sources=[t1]),
        AnsweredQuestion(question="q2", answer="y", sources=[t2]),
    ]
    students = [
        MinimalSearchResults(question_id=truths[0].question_id, question="q1",
                             retrieved_sources=[t1]),
        MinimalSearchResults(question_id=truths[1].question_id, question="q2",
                             retrieved_sources=[]),
    ]
    assert recall_at_k(students, truths, k=5) == 0.5
```

Uso real:
```bash
uv run python -m src evaluate \
    --student_search_results_path data/output/search_results/UnansweredQuestions/dataset_docs_public.json \
    --dataset_path data/datasets/AnsweredQuestions/dataset_docs_public.json
```

> **Separa `docs` de `code`.** Nunca mezcles ambos en una cifra: corre `evaluate` dos veces, una por dataset.

## 3. Bucle de mejora

| Síntoma | Causa probable | Qué tocar |
|---|---|---|
| Archivo equivocado | Vocabulario ausente en el chunk | Tokenización (`04`), stemming, ruta |
| Archivo correcto, solape bajo | Chunk grande/mal cortado | Chunking (`02`) |
| Archivo no indexado | Extensión excluida | `iter_corpus_files` (`01`) |
| Correcto fuera del top-k | Ranking flojo | `k1`, `b`, deduplicar |

Un cambio por experimento; prefiere mejoras generales al sobreajuste.

## 4. Checklist

- [ ] `iou`, `is_hit`, `question_recall`, `recall_at_k` y `evaluate` implementados.
- [ ] Acierto exige mismo `file_path` e IoU ≥ 0.05.
- [ ] `evaluate` imprime recall@1/3/5/10 y mides `docs`/`code` por separado.
- [ ] Línea base anotada y al menos una palanca probada de una en una.
- [ ] `make lint` pasa.

## 5. Tiempo estimado

**≈ 45–60 minutos** de código; el grueso es medir y analizar fallos.
