# 08c — Generación en lote

Cierras el pipeline con `answer` y `answer_dataset`, produciendo `StudentSearchResultsAndAnswer` válido.

## 1. Código

Añade a `src/generator.py`:

```python
from tqdm import tqdm

from src.models import MinimalAnswer, StudentSearchResults, StudentSearchResultsAndAnswer


def answer_dataset(search_results: StudentSearchResults, model: Any,
                   tokenizer: Any, root: Path) -> StudentSearchResultsAndAnswer:
    answers: list[MinimalAnswer] = []
    for item in tqdm(search_results.search_results, desc="Answering"):
        blocks = build_context(item.retrieved_sources, root)
        text = generate_answer(item.question, blocks, model, tokenizer)
        answers.append(MinimalAnswer(
            question_id=item.question_id,
            question=item.question,
            retrieved_sources=item.retrieved_sources,
            answer=text,
        ))
    return StudentSearchResultsAndAnswer(search_results=answers, k=search_results.k)
```

Comandos en `src/cli.py` (reutiliza `_load_index` de `06b`):

```python
from src.generator import answer_dataset as run_answer_dataset
from src.generator import build_context, generate_answer, load_model
from src.index import search as run_search
from src.io_utils import load_search_results


def answer(query: str, k: int = 10,
           index_directory: str = "data/processed") -> None:
    root = project_root()
    idx = _load_index(index_directory)
    if idx is None:
        return
    query_str = str(query)
    model, tokenizer = load_model()
    blocks = build_context(run_search(idx, query_str, k), root)
    print(generate_answer(query_str, blocks, model, tokenizer))


def answer_dataset(student_search_results_path: str,
                   save_directory: str = "data/output/search_results_and_answer") -> None:
    root = project_root()
    try:
        results = load_search_results(student_search_results_path)
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(f"Could not load input: {exc}")
        return
    print(f"Loaded {len(results.search_results)} questions")
    model, tokenizer = load_model()
    out = run_answer_dataset(results, model, tokenizer, root)
    scope = dataset_scope(student_search_results_path)
    dest_dir = root / save_directory / scope
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / Path(student_search_results_path).name
    save_model(out, dest)
    print(f"Saved student_search_results_and_answer to {dest}")
```

Mapa en `src/__main__.py`:
```python
fire.Fire({
    "index": cli.index,
    "search": cli.search,
    "search_dataset": cli.search_dataset,
    "answer": cli.answer,
    "answer_dataset": cli.answer_dataset,
    "evaluate": cli.evaluate,
})
```

> `answer_dataset` **no** necesita el índice: trabaja sobre las fuentes ya recuperadas. `answer` **sí** lo reconstruye desde el índice.

## 2. Casos degenerados

- Búsqueda sin fuentes → responde honestamente, sin alucinar.
- Fuente que apunta a archivo inexistente → `build_context` la salta.
- Contexto que no cabe → se recorta el fragmento menos relevante.

En todos los casos el JSON valida contra `StudentSearchResultsAndAnswer`.

## 3. Testers

```python
def test_answer_dataset_output_is_valid(tmp_path) -> None:
    from src.generator import answer_dataset, load_model
    from src.index import InvertedIndex
    from src.io_utils import load_dataset, save_model
    from src.models import StudentSearchResultsAndAnswer
    from src.retriever import search_dataset

    idx = InvertedIndex.load(ROOT / "data/processed")
    ds = load_dataset("data/datasets/UnansweredQuestions/dataset_docs_public.json")
    sr = search_dataset(idx, ds, k=3)
    model, tokenizer = load_model()
    out = answer_dataset(sr, model, tokenizer, ROOT)
    dest = tmp_path / "ans.json"
    save_model(out, dest)
    StudentSearchResultsAndAnswer.model_validate_json(dest.read_text())
```

Integración:
```bash
uv run python -m src answer "How to dynamically load a LoRA adapter?" --k 5
uv run python -m src answer_dataset \
    --student_search_results_path data/output/search_results/UnansweredQuestions/dataset_docs_public.json \
    --save_directory data/output/search_results_and_answer
```

## 4. Checklist

- [ ] `answer` y `answer_dataset` conectados en la CLI.
- [ ] Salida escribe `save_directory/<nombre>.json` y valida.
- [ ] La estructura la construye tu código, no el modelo.
- [ ] Sin fichero o JSON mal formado, `answer_dataset` avisa sin traceback.
- [ ] `make lint` pasa.

## 5. Tiempo estimado

**≈ 30–45 minutos.**
