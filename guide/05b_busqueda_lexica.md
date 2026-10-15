# 05b — Búsqueda léxica (BM25)

Ya tienes el índice construido. Ahora **puntúas y ordenas** para responder una consulta.

## 1. Código

Añade a `src/index.py`:

```python
import math

from src.models import MinimalSource
from src.tokenizer import tokenize


def bm25_score(index: InvertedIndex, query_terms: list[str], doc_id: int) -> float:
    n = index.n_docs
    avgdl = index.avg_doc_len or 1.0
    dl = index.doc_lengths[doc_id]
    score = 0.0
    for term in query_terms:
        docs = index.postings.get(term)
        if not docs or doc_id not in docs:
            continue
        tf = docs[doc_id]
        df = len(docs)
        idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
        denom = tf + index.k1 * (1 - index.b + index.b * dl / avgdl)
        score += idf * (tf * (index.k1 + 1)) / denom
    return score


def search(index: InvertedIndex, query: str, k: int,
           max_source_len: int = 2000) -> list[MinimalSource]:
    if k <= 0:
        return []
    terms = tokenize(query)
    candidates: set[int] = set()
    for term in terms:
        candidates.update(index.postings.get(term, {}))
    scored = sorted(
        ((bm25_score(index, terms, d), d) for d in candidates),
        reverse=True,
    )
    results: list[MinimalSource] = []
    for _, doc_id in scored[:k]:
        chunk = index.chunks[doc_id]
        end = min(chunk.end, chunk.start + max_source_len)
        results.append(MinimalSource(
            file_path=chunk.file_path,
            first_character_index=chunk.start,
            last_character_index=end,
        ))
    return results
```

> **El recorte a `max_source_len` es una red de seguridad.** Con el default (2000) no recorta nada; si indexas con un `--max_chunk_size` mayor, evita que alguna fuente supere el techo que valida la moulinette. No uses `assert` (se desactiva con `python -O`).

## 2. Testers

Añade a `tests/test_index.py`:

```python
def test_rare_term_outranks_common_term() -> None:
    idx = make_index()
    assert bm25_score(idx, ["server"], 1) > bm25_score(idx, ["server"], 0)


def test_search_returns_top_k() -> None:
    idx = make_index()
    results = search(idx, "launch server", k=1)
    assert len(results) == 1
    assert results[0].file_path == "b.py"


def test_degenerate_inputs() -> None:
    idx = make_index()
    assert search(idx, "", k=5) == []
    assert search(idx, "launch", k=0) == []
    assert search(idx, "palabraquenoexiste", k=5) == []
```

## 3. Checklist

- [ ] `bm25_score` y `search` implementados.
- [ ] Implementaste **al menos uno** de los métodos clásicos: BM25 **o** TF-IDF.
- [ ] La búsqueda **solo** puntúa candidatos (no recorre todo el corpus).
- [ ] Resultados ordenados y devueltos como `MinimalSource`.
- [ ] `k=0`, pregunta vacía y sin coincidencias devuelven `[]`.
- [ ] `make lint` pasa.

## 4. Tiempo estimado

**≈ 45–60 minutos.**
