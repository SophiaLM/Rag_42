# 06a — Recuperación en lote

Una consulta que funciona no basta: el evaluador lanza **todo un dataset** y mide el tiempo. Aquí produces el JSON `StudentSearchResults`.

## 1. Código

`src/retriever.py`:
```python
from pathlib import Path

from tqdm import tqdm

from src.index import InvertedIndex, search
from src.models import MinimalSearchResults, RagDataset, StudentSearchResults

SCOPES = ("UnansweredQuestions", "AnsweredQuestions")


def search_dataset(index: InvertedIndex, dataset: RagDataset,
                   k: int) -> StudentSearchResults:
    results: list[MinimalSearchResults] = []
    for question in tqdm(dataset.rag_questions, desc="Searching"):
        sources = search(index, question.question, k)
        results.append(MinimalSearchResults(
            question_id=question.question_id,
            question=question.question,
            retrieved_sources=sources,
        ))
    return StudentSearchResults(search_results=results, k=k)


def dataset_scope(path: str | Path) -> str:
    parts = Path(path).resolve().parts
    for scope in SCOPES:
        if scope in parts:
            return scope
    return Path(path).parent.name or "misc"
```

> Detalle del subject: los datasets públicos comparten el **mismo nombre de archivo** (`dataset_docs_public.json`) entre `UnansweredQuestions` y `AnsweredQuestions`. Si escribes todo en la misma carpeta, **te pisas** los resultados. De ahí `dataset_scope`.

Uso real:
```python
from src.corpus import project_root
from src.io_utils import load_dataset
from src.index import InvertedIndex
from src.retriever import search_dataset

idx = InvertedIndex.load(project_root() / "data/processed")   # una sola vez
ds = load_dataset("data/datasets/UnansweredQuestions/dataset_docs_public.json")
out = search_dataset(idx, ds, k=10)
print(len(out.search_results), "preguntas resueltas")
```

## 2. Rendimiento

1. **Carga el índice una sola vez.** No lo cargues dentro del bucle: cargar decenas de MB 200 veces revienta los 90 s.
2. **No releas el corpus al buscar.** El índice ya tiene los offsets; el texto solo se relee al **generar** (`08`).

Presupuesto: **≤ 90 s para 200 preguntas** (≈0,45 s por pregunta).

## 3. Testers

`tests/test_retriever.py`:
```python
from src.corpus import project_root
from src.index import InvertedIndex
from src.io_utils import load_dataset
from src.retriever import dataset_scope, search_dataset
from src.models import StudentSearchResults


def test_search_dataset_shape() -> None:
    idx = InvertedIndex.load(project_root() / "data/processed")
    ds = load_dataset("data/datasets/UnansweredQuestions/dataset_docs_public.json")
    out = search_dataset(idx, ds, k=10)
    assert len(out.search_results) == len(ds.rag_questions)
    assert out.k == 10
    for r in out.search_results:
        assert len(r.retrieved_sources) <= 10


def test_scope_detection() -> None:
    a = "data/datasets/UnansweredQuestions/dataset_docs_public.json"
    b = "data/datasets/AnsweredQuestions/dataset_docs_public.json"
    assert dataset_scope(a) == "UnansweredQuestions"
    assert dataset_scope(b) == "AnsweredQuestions"
```

## 4. Checklist

- [ ] `search_dataset` y `dataset_scope` implementados.
- [ ] Índice cargado **una vez** por batch.
- [ ] `--save_directory` **scopeado por dataset**.
- [ ] `make lint` pasa.

## 5. Tiempo estimado

**≈ 30–45 minutos.**
