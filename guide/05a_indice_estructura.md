# 05a — Índice invertido: estructura y construcción

Tienes las piezas (`Chunk`, etapa `02`) y los términos de cada pieza (etapa `04`). Ahora construyes la **estructura que hace la búsqueda rápida**: el *índice invertido*. Sin él, cada pregunta tendría que recorrer los miles de chunks comparando palabras; con él, se salta directamente a los pocos chunks que contienen un término. Es la idea central de `06_la_busqueda_lexica.md`.

Esta etapa hace **solo** la estructura y su construcción. **Sin** puntuar y ordenar (eso es `05b`) y **sin** guardar a disco (eso es `05c`). Es importante separarlo: primero el "almacén", luego los "verbos".

---

## 1. Qué vas a construir, y por qué ahora sí una clase

`src/index.py` con una clase `InvertedIndex` y una función `build_index`.

**Por qué aquí una clase y en `02` no.** El chunking era una *transformación* sin estado: entra texto, sale una lista. El índice es distinto: **guarda estado** (los datos indexados), **vive más allá de una llamada** y sobre él actúan varios "verbos" (puntuar en `05b`, guardar/cargar en `05c`). Cuando hay estado + comportamiento sobre él, eso *es* un objeto de dominio — justo el caso en el que la OOP del subject tiene sentido.

La estructura clave, traducida de la teoría `06`:

```text
"índice alfabético al revés"
   palabra "cache"  ──► {doc 0: 2 veces, doc 7: 1 vez, ...}
   palabra "server" ──► {doc 1: 1 vez, ...}
```

Es decir: **de cada término a los documentos que lo contienen** (y cuántas veces).

---

## 2. Dónde vive cada cosa

Todo en `src/index.py`:

| Símbolo | Decide | Quién lo usa |
|---|---|---|
| `InvertedIndex` | qué se guarda del corpus indexado | `05b` (puntuar), `05c` (persistir) |
| `.postings` | término → `{doc_id: frecuencia}` | `bm25_score` |
| `.doc_lengths` | longitud de cada documento | `bm25_score` (la necesita `b`) |
| `.chunks` | **qué** es cada `doc_id` (su ubicación) | `search` (para devolver `MinimalSource`) |
| `.k1`, `.b` | parámetros de BM25 (con default) | `bm25_score` |
| `build_index(entries)` | cómo pasar de `(Chunk, términos)` a índice | el comando `index` (`05c`) |

---

## 3. Las piezas que necesitas

Firmas: campos del `dataclass` (la **estructura** es el entregable aquí) y la firma de `build_index`. La lógica va explicada debajo.

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
        """Número de documentos indexados."""

    @property
    def avg_doc_len(self) -> float:
        """Longitud media de los documentos (0 si no hay ninguno)."""

    def doc_freq(self, term: str) -> int:
        """En cuántos documentos aparece `term` (df de BM25)."""


def build_index(entries: Iterable[tuple[Chunk, list[str]]],
                k1: float = 1.5, b: float = 0.75) -> InvertedIndex:
    """Construye el índice a partir de pares (chunk, términos)."""
```

### La lógica detrás de cada pieza

**Los cuatro campos, y por qué cada uno:**

- `chunks: list[Chunk]` — la lista de documentos **en orden**. Su posición es el `doc_id`: el chunk `i` de esta lista es el documento `i` del índice. Es la única fuente de verdad de *qué* es cada documento; `postings` guarda números, no rutas.
- `postings: dict[str, dict[int, int]]` — el corazón del índice invertido: para cada término, un diccionario `doc_id → frecuencia (TF)`. La clave externa es la palabra; la interna, el documento, y su valor, cuántas veces aparece (teoría `06`: TF).
- `doc_lengths: list[int]` — la longitud de cada documento (número de términos). **Por qué guardarla:** BM25 penaliza por longitud con el mando `b` (teoría `06`); para ello necesita la longitud de cada documento y su media, y recalcularlas en cada consulta sería absurdo.
- `k1` y `b` — los parámetros de BM25 **con sus valores por defecto** (1.5 y 0.75, los típicos de la teoría `06`). Viven **dentro** del índice para que `05b` los encuentre ahí y `05c` los persista: el índice debe recordar con qué configuración se construyó.

**Las tres consultas derivadas** (todas `@property`/métodos de solo lectura, no campos, para que no se contradigan):

- `n_docs` — cuántos documentos hay (el `N` de la fórmula IDF).
- `avg_doc_len` — la media de `doc_lengths`, con el cuidado de no dividir por cero cuando no hay documentos.
- `doc_freq(term)` — cuántos documentos contienen un término: la `df` de `idf`. Se lee del `postings`; si la palabra no aparece, es `0`.

**`build_index(entries)`** — el constructor. Recibe un **iterable** de `(Chunk, list[str])` (el chunk y sus términos ya tokenizados) y hace, para cada uno, con `doc_id` = su posición:

1. `Counter(terms)` → frecuencia de cada término en **este** documento (el TF).
2. Guardar el chunk en `chunks` y su longitud (`sum` de las frecuencias) en `doc_lengths`.
3. Para cada término, escribir su frecuencia en `postings[term][doc_id]`.

**Por qué `Iterable` y no list:** el indexado (`05c`) puede generar los pares sobre la marcha, sin materializarlos todos. El índice no necesita tenerlos en memoria de golpe.

> Ojo con dos cosas: (1) `postings` guarda **frecuencias**, no posiciones; la posición se guarda en `chunks` — no las mezcles. (2) `doc_lengths` cuenta términos **después** de tokenizar, no caracteres; es lo que BM25 espera.

---

## 4. Reglas que este paso debe respetar

| Regla (teoría `06`) | Implementación |
|---|---|
| Solo se puntúan documentos que contienen algún término | Es lo que **posibilita** `postings`: "palabra → documentos" |
| TF = veces en el documento | El entero de `postings[term][doc_id]` |
| df = en cuántos documentos aparece | `doc_freq` = tamaño del diccionario interno de `postings` |
| BM25 necesita longitudes y su media | `doc_lengths` + `avg_doc_len` |
| El índice recuerda su configuración | `k1` y `b` guardados en el propio índice |

## 5. Caso de uso mínimo

```python
from src.chunking import Chunk
from src.index import build_index

entries = [
    (Chunk("a.py", 0, 10), ["cache", "kv", "cache"]),
    (Chunk("b.py", 0, 10), ["server", "launch", "http"]),
]
idx = build_index(entries)

idx.n_docs                 # 2
idx.doc_lengths            # [3, 3]
idx.postings["cache"]      # {0: 2}   -> el término "cache" aparece 2 veces en el doc 0
idx.doc_freq("cache")      # 1       -> en 1 documento de 2
idx.chunks[1].file_path    # "b.py"  -> qué es el doc 1
```

Esta `idx` es exactamente lo que `05b` puntuará y `05c` escribirá en `data/processed/`.

---

## 6. Comprobación

`tests/test_index.py` (parte 1). Qué demuestra el test:

| Test | Qué demuestra |
|---|---|
| `test_postings_and_lengths` | Con dos chunks conocidos: `n_docs == 2`, `doc_lengths == [3, 3]`, `postings["cache"] == {0: 2}` y `doc_freq("cache") == 1` |

Es decir, comprueba a la vez las tres cosas que el índice debe saber: **cuántos** documentos hay, **cómo de largos** son y **dónde** está cada término (con su frecuencia).

> El test usa un helper `make_index()` con dos documentos de juguete; `05b` y `05c` lo reutilizan. Un índice **pequeño y conocido** es la mejor herramienta para razonar sobre puntuaciones.

---

## 7. Qué NO cubre esta parte

- **Puntuar y ordenar** (BM25, top-k) → `05b`.
- **Guardar/cargar** el índice y conectarlo al comando `index` → `05c`.
- **Escribir tu propio código**: aquí **construyes** el índice con `build_index`, pero quien lo llama con el corpus real es `05c`.

## 8. Checklist

- [ ] `InvertedIndex` con `postings`, `doc_lengths`, `chunks`, `k1`, `b`.
- [ ] `n_docs`, `avg_doc_len` y `doc_freq` coherentes con los datos.
- [ ] `build_index` construye el índice desde `(chunk, términos)`.
- [ ] `uv run pytest` y `uv run make lint` en verde.

## 9. Tiempo estimado

**≈ 45–60 minutos.**
