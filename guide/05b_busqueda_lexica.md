# 05b — Búsqueda léxica (BM25)

Con el índice construido (`05a`) ya tienes el "almacén": palabra → documentos. Ahora añades los "verbos": dada una **pregunta**, **puntuar** los chunks candidatos y devolver el **top-k**. Esto es la búsqueda léxica de `06_la_busqueda_lexica.md`.

El subject (VI.1) exige implementar **al menos uno** de los dos métodos clásicos: **BM25** o **TF-IDF**. Aquí usamos **BM25** porque es el que mejor rinde en texto según la teoría `06`, pero TF-IDF también valida. Lo que **sí** es obligatorio en ambos casos: usar el índice invertido para **no recorrer todo el corpus** en cada consulta.

Añades **dos funciones** a `src/index.py`: no creas un módulo nuevo, porque puntuar es un verbo **sobre el índice** y vive junto a su estructura.

---

## 1. Qué vas a construir

- `bm25_score(index, query_terms, doc_id) -> float` — la **puntuación** de un documento para una consulta.
- `search(index, query, k, max_source_len=2000) -> list[MinimalSource]` — el **ranking**: tokeniza la pregunta, reúne candidatos, puntúa, ordena y devuelve el top-k ya en el modelo de la etapa `03`.

**Dónde vive cada cosa:**

| Símbolo | Ubicación | Por qué ahí |
|---|---|---|
| `bm25_score` | `index.py` | Peso de un documento: solo lo usa el ranking del índice |
| `search` | `index.py` | El algoritmo de búsqueda sobre el índice |

---

## 2. Las piezas que necesitas

Firmas (con docstring). **La lógica**, debajo.

```python
import math

from src.models import MinimalSource
from src.tokenizer import tokenize


def bm25_score(index: InvertedIndex, query_terms: list[str], doc_id: int) -> float:
    """Puntuación BM25 del documento `doc_id` para los términos de la consulta."""


def search(index: InvertedIndex, query: str, k: int,
           max_source_len: int = 2000) -> list[MinimalSource]:
    """Devuelve las `k` mejores fuentes para `query`, ya como MinimalSource."""
```

### La lógica detrás de cada una

**`bm25_score`** — implementa la fórmula de la teoría `06`, término a término:

```text
score = Σ  idf(t) × [ tf(t) × (k1 + 1) ] / [ tf(t) + k1 × (1 − b + b × dl / avgdl) ]
        t
   idf(t) = ln( 1 + (N − df + 0.5) / (df + 0.5) )       N = nº docs, df = en cuántos aparece t
```

Cómo se traduce a código, y **por qué cada pieza**:

- Se recorre **solo** los términos de la pregunta (no todo el vocabulario).
- Para cada término con presencia en el documento: `tf` = su frecuencia (`postings[term][doc_id]`), `df` = `len(postings[term])`.
- El `idf` premia términos **raros en el corpus** y casi anula los comunes (teoría `06`): un término que aparece en todos los documentos apenas suma.
- El numerador `tf × (k1 + 1)` sobre el denominador con `k1` produce la **saturación**: repetir 50 veces no vale 50 veces más que repetir 5 (mando `k1`, teoría `06`).
- `dl / avgdl` con el mando `b` aplica la **penalización por longitud**: un documento largo tiene más términos "por azar" y se corrige (teoría `06`).
- Si el término no está en el documento (o no está en el índice), se salta; si no hay coincidencia alguna, el score es `0.0`.

> Dos cuidados: (1) recuerda proteger la división por cero de `avg_doc_len` (usa `1.0` si no hay documentos); (2) `bm25_score` **no** reordena ni recorta: solo da un número. Ordenar es trabajo de `search`.

**`search`** — el ranking, en cinco pasos:

1. **Guardas**: si `k <= 0`, devolver `[]` de inmediato (entrada degenerada; no puntúes para nada).
2. **Tokenizar** la pregunta con `tokenize` (el **mismo** colador que el indexado, teoría `05`).
3. **Reunir candidatos**: la **unión** de los `doc_id` de `postings[term]` para cada término de la consulta. Este es el paso que usa el índice invertido (teoría `06`): solo se consideran los documentos que contienen algún término; los demás tienen score 0 y no compiten.
4. **Puntuar y ordenar**: calcular `bm25_score` de cada candidato y ordenar de mayor a menor.
5. **Recortar al top-k** y **convertir** cada chunk en `MinimalSource(file_path, start, end)`.

**El recorte a `max_source_len`:** al construir la fuente, `end` se limita a `min(chunk.end, chunk.start + max_source_len)`. **Por qué:** el moulinette rechaza cualquier fuente de más de 2000 caracteres; con el default (2000) no recorta nada, pero si alguien indexó con un `--max_chunk_size` mayor, esta es la **red de seguridad** que evita invalidar el resultado. No uses `assert` para esto: con `python -O` se desactivan las aserciones y la guardia desaparecería.

**Por qué devuelve `MinimalSource` y no `Chunk`:** el crate de la etapa `03` es lo que el resto del sistema (y el grader) entiende. `Chunk` es la pieza interna; `MinimalSource` es su forma pública validada.

---

## 3. Reglas que este paso debe respetar

| Regla (teoría `06` / subject) | Implementación |
|---|---|
| Implementar **BM25 o TF-IDF** | `bm25_score` con `k1` y `b` |
| Solo puntuar **candidatos** | Se reúnen `doc_id` desde `postings`; nunca se recorre todo el corpus |
| Mismo tokenizador que al indexar | `search` usa `tokenize` (etapa `04`) |
| `idf` premia lo raro | `ln(1 + (N − df + 0.5)/(df + 0.5))` |
| Saturación y longitud | Mandos `k1` (saturación) y `b` (longitud) desde el índice |
| Ninguna fuente > 2000 caracteres | Recorte a `max_source_len` al construir el `MinimalSource` |
| Entradas degeneradas no revientan | `k <= 0` → `[]`; sin candidates, `[]` |

> Truco de depuración: si una búsqueda "no encuentra nada", revisa el **tokenizador** antes que BM25. La causa más común de candidatos vacíos es indexar y consultar con coladores distintos (teoría `05`: es una condición de correctitud, no de estilo).

---

## 4. Caso de uso mínimo

```python
idx = build_index(entries)          # de 05a

search(idx, "launch server", k=2)
# [MinimalSource("b.py", 0, 10), ...]  ordenado por BM25

search(idx, "", k=5)                # []  (query vacía: sin términos, sin candidatos)
search(idx, "launch", k=0)          # []  (k=0: nada que devolver)
search(idx, "palabraquenoexiste", k=5)   # []  (ningún candidato)
```

---

## 5. Comprobación

`tests/test_index.py` (parte 2). Qué demuestra cada test:

| Test | Qué demuestra |
|---|---|
| `test_rare_term_outranks_common_term` | Un término raro puntúa más que uno común: el `idf` funciona |
| `test_search_returns_top_k` | `search(..., k=1)` devuelve **una** fuente y es la del documento correcto |
| `test_degenerate_inputs` | `""`, `k=0` y una palabra inexistente devuelven `[]` sin excepción |

El de los degenerados es el que protege el requisito transversal del subject: **ningún camino de entrada puede terminar en `Traceback`** (VI.6).

---

## 6. Qué NO cubre esta parte

- **Buscar sobre un dataset entero** (una pregunta detrás de otra) y escribir el JSON → `06a`/`06b`.
- **La CLI** que expone `search` → `06b`; aquí `search` es una función, aún no un comando.
- **Ajustar `k1`/`b`** para subir recall → es el bucle de mejora de `07`.

## 7. Checklist

- [ ] `bm25_score` y `search` implementados sobre el índice.
- [ ] Se implementó **BM25 o TF-IDF** (requisito del subject).
- [ ] La búsqueda **solo** puntúa candidatos del índice.
- [ ] Resultados ordenados, en `MinimalSource`, y con el recorte de 2000.
- [ ] `uv run pytest` y `uv run make lint` en verde.

## 8. Tiempo estimado

**≈ 45–60 minutos.**
