# 06b — CLI de búsqueda

Conectas los comandos `search` y `search_dataset` a la CLI real y blindas el manejo de errores.

## 1. Código

Añade a `src/cli.py`:

```python
from pathlib import Path
import json

from src.corpus import project_root
from src.index import InvertedIndex
from src.index import search as run_search
from src.io_utils import load_dataset, save_model
from src.retriever import dataset_scope
from src.retriever import search_dataset as run_search_dataset


def _load_index(index_directory: str) -> InvertedIndex | None:
    path = project_root() / index_directory
    if not (path / "index.json").exists() or not (path / "chunks.json").exists():
        print(f"No index found in {index_directory}. Run the 'index' command first.")
        return None
    try:
        return InvertedIndex.load(path)
    except (FileNotFoundError, json.JSONDecodeError, ValueError, KeyError) as exc:
        print(f"Could not load index from {index_directory}: {exc}")
        return None


def search(query: str, k: int = 10,
           index_directory: str = "data/processed") -> None:
    idx = _load_index(index_directory)
    if idx is None:
        return
    for source in run_search(idx, str(query), k):
        print(source.model_dump_json())


def search_dataset(dataset_path: str, k: int = 10,
                   save_directory: str = "data/output/search_results",
                   index_directory: str = "data/processed") -> None:
    idx = _load_index(index_directory)
    if idx is None:
        return
    try:
        ds = load_dataset(dataset_path)
    except (FileNotFoundError, OSError):
        print(f"Dataset not found: {dataset_path}")
        return
    except ValueError as exc:
        print(f"Malformed dataset JSON: {exc}")
        return
    result = run_search_dataset(idx, ds, k)
    scope = dataset_scope(dataset_path)
    dest_dir = project_root() / save_directory / scope
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / Path(dataset_path).name
    save_model(result, dest)
    print(f"Saved student_search_results to {dest}")
```

Y actualiza el mapa en `src/__main__.py`:

```python
fire.Fire({
    "index": cli.index,
    "search": cli.search,
    "search_dataset": cli.search_dataset,
})
```

> Fire usa el nombre de la función como subcomando; por eso la pública se llama `search` y la de `index.py` se importa **con alias** (`run_search`).

## 2. Manejo de errores

El subject se prueba con **query vacía, query absurda, `k=0`, ficheros faltantes y JSON mal formado**, y **ningún** camino puede acabar en traceback. Patrón:
- Índice ausente → `_load_index` avisa sin excepción.
- Fichero faltante → `FileNotFoundError`.
- JSON mal formado → pydantic lanza `ValueError`.
- Entradas degeneradas → `search` ya devuelve `[]`.

## 3. Testers (integración)

```bash
uv run python -m src search "" --k 5
uv run python -m src search "cache" --k 0
uv run python -m src search_dataset --dataset_path no/existe.json --k 5 --save_directory /tmp/o
printf '{not json' > /tmp/bad.json
uv run python -m src search_dataset --dataset_path /tmp/bad.json --k 5 --save_directory /tmp/o
```

Ninguno debe imprimir `Traceback`.

```bash
time uv run python -m src search_dataset \
    --dataset_path data/datasets/UnansweredQuestions/dataset_docs_public.json \
    --k 10 --save_directory data/output/search_results
```

## 4. Checklist

- [ ] `search` y `search_dataset` conectados; sin rutas *hardcodeadas*.
- [ ] `--save_directory` scopeado por dataset.
- [ ] Ninguna entrada rara produce traceback.
- [ ] Recuperación de un batch dentro del presupuesto.
- [ ] `make lint` pasa.

## 5. Tiempo estimado

**≈ 15–30 minutos.**
