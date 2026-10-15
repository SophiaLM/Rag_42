# 05a — Índice invertido: estructura y construcción

Aquí solo construyes la **estructura** del índice. Sin BM25, sin búsqueda, sin persistencia todavía.

## 1. Código

`src/index.py`:
```python
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field

from src.chunking import Chunk


@dataclass
class InvertedIndex:
    chunks: list[Chunk] = field(default_factory=list)
    postings: dict[str, dict[int, int]] = field(default_factory=dict)
    doc_lengths: list[int] = field(default_factory=list)
    k1: float = 1.5
    b: float = 0.75

    @property
    def n_docs(self) -> int:
        return len(self.chunks)

    @property
    def avg_doc_len(self) -> float:
        return (sum(self.doc_lengths) / self.n_docs) if self.n_docs else 0.0

    def doc_freq(self, term: str) -> int:
        return len(self.postings.get(term, {}))


def build_index(entries: Iterable[tuple[Chunk, list[str]]],
                k1: float = 1.5, b: float = 0.75) -> InvertedIndex:
    index = InvertedIndex(k1=k1, b=b)
    for doc_id, (chunk, terms) in enumerate(entries):
        counts = Counter(terms)
        index.chunks.append(chunk)
        index.doc_lengths.append(sum(counts.values()))
        for term, tf in counts.items():
            index.postings.setdefault(term, {})[doc_id] = tf
    return index
```

## 2. Testers

`tests/test_index.py`:
```python
from src.chunking import Chunk
from src.index import InvertedIndex, build_index


def make_index() -> InvertedIndex:
    entries = [
        (Chunk("a.py", 0, 10), ["cache", "kv", "cache"]),
        (Chunk("b.py", 0, 10), ["server", "launch", "http"]),
    ]
    return build_index(entries)


def test_postings_and_lengths() -> None:
    idx = make_index()
    assert idx.n_docs == 2
    assert idx.doc_lengths == [3, 3]
    assert idx.postings["cache"] == {0: 2}
    assert idx.doc_freq("cache") == 1
```

## 3. Checklist

- [ ] `InvertedIndex` y `build_index` implementados.
- [ ] Testers pasan.
- [ ] `make lint` pasa.

## 4. Tiempo estimado

**≈ 45–60 minutos.**
