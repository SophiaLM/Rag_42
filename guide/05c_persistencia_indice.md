# 05c — Persistencia del índice

Guardas el índice en `data/processed/` para no reconstruirlo en cada comando.

## 1. Código

Añade a `src/index.py` (imports al inicio del módulo):

```python
import json
from dataclasses import asdict
from pathlib import Path

from tqdm import tqdm

from src.chunking import chunk_file
from src.corpus import iter_corpus_files, project_root, read_text, to_corpus_path
from src.tokenizer import tokenize_source
```

Métodos **dentro** de `InvertedIndex`:

```python
    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "chunks.json").write_text(
            json.dumps([asdict(c) for c in self.chunks]), encoding="utf-8")
        (directory / "index.json").write_text(json.dumps({
            "postings": {t: {str(d): tf for d, tf in docs.items()}
                         for t, docs in self.postings.items()},
            "doc_lengths": self.doc_lengths,
            "k1": self.k1, "b": self.b,
        }), encoding="utf-8")

    @classmethod
    def load(cls, directory: Path) -> "InvertedIndex":
        chunks = [Chunk(**c) for c in
                  json.loads((directory / "chunks.json").read_text(encoding="utf-8"))]
        raw = json.loads((directory / "index.json").read_text(encoding="utf-8"))
        postings = {t: {int(d): tf for d, tf in docs.items()}
                    for t, docs in raw["postings"].items()}
        return cls(chunks=chunks, postings=postings,
                   doc_lengths=raw["doc_lengths"], k1=raw["k1"], b=raw["b"])
```

Orquestador del comando `index`:

```python
def build_and_save(corpus_root: Path, max_chunk_size: int,
                   processed_dir: Path) -> InvertedIndex:
    root = project_root()
    entries: list[tuple[Chunk, list[str]]] = []
    for path in tqdm(list(iter_corpus_files(corpus_root)), desc="Indexing"):
        text = read_text(path)
        rel = to_corpus_path(path, root)
        for chunk in chunk_file(rel, text, max_chunk_size):
            entries.append((chunk, tokenize_source(text[chunk.start:chunk.end], rel)))
    index = build_index(entries)
    index.save(processed_dir)
    return index
```

## 2. Testers

Añade a `tests/test_index.py`:

```python
from pathlib import Path


def test_save_and_load(tmp_path: Path) -> None:
    idx = make_index()
    idx.save(tmp_path)
    loaded = InvertedIndex.load(tmp_path)
    assert loaded.chunks == idx.chunks
    assert loaded.postings == idx.postings
    assert loaded.doc_lengths == idx.doc_lengths


def test_real_index_respects_max_len() -> None:
    from src.corpus import project_root
    idx = InvertedIndex.load(project_root() / "data/processed")
    for c in idx.chunks:
        assert c.end - c.start <= 2000
```

Comando real (objetivo **≤ 5 min**):

```bash
time uv run python -m src index --max_chunk_size 2000
ls -lh data/processed/
```

Conecta el comando en `src/cli.py`:

```python
def index(max_chunk_size: int = 2000) -> None:
    from src.corpus import project_root
    from src.index import build_and_save
    root = project_root()
    index_obj = build_and_save(
        root / "data/raw/vllm-0.10.1", max_chunk_size, root / "data/processed")
    print(f"Indexed {index_obj.n_docs} chunks")
```

## 3. Checklist

- [ ] Índice persistido en `data/processed/` y recargado **idéntico**.
- [ ] `index` conectado en la CLI.
- [ ] Indexado completo **≤ 5 min**.
- [ ] `make lint` pasa.

## 4. Tiempo estimado

**≈ 30 minutos.**
