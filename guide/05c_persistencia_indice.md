# 05c — Persistencia del índice

Tienes el índice en memoria (`05a`) y sabes puntuar con él (`05b`). Pero ahora mismo **no sobrevive** al final del comando: cada vez que buscaras habría que reconstruirlo. Eso choca de frente con la asimetría central de RAG (teoría `01`): **indexar es caro y se hace una vez; recuperar es ligero y se hace en cada pregunta**.

Esta etapa resuelve eso: **persistir** el índice en `data/processed/` y conectar de verdad el comando `index` (el que dejaste como esqueleto en `00b`). Con esto, el subject (VI.1) queda satisfecho: indexar una vez, en **≤ 5 min**, y que la búsqueda lo cargue de disco en milisegundos.

---

## 1. Qué vas a construir

Tres piezas, con roles claros:

- `InvertedIndex.save(dir)` / `InvertedIndex.load(dir)` — serializar y deserializar el índice (la *persistencia*).
- `build_and_save(corpus_root, max_chunk_size, processed_dir)` — el **orquestador**: recorre el corpus, corta, tokeniza, construye y guarda.
- El **cuerpo real** de `cli.index` (el esqueleto de `00b`).

**Dónde vive cada cosa:**

| Símbolo | Ubicación | Por qué ahí |
|---|---|---|
| `save` / `load` | `index.py` (métodos de `InvertedIndex`) | Guardar/cargar **es** conocimiento del índice |
| `build_and_save` | `index.py` | Orquesta el indexado completo en un sitio |
| `index(max_chunk_size)` | `cli.py` | Comando de la CLI: traduce argumentos y llama a `build_and_save` |

**Por qué `save`/`load` son métodos y no funciones sueltas:** igual que en `05b`, persistir es un verbo **sobre el índice**. Una función libre que recibiera el índice sería "OOP de fachada"; el índice es quien sabe cómo serializarse.

---

## 2. Las piezas que necesitas

Firmas (con docstring). **La lógica**, debajo.

```python
import json
from dataclasses import asdict
from pathlib import Path

from tqdm import tqdm

from src.chunking import chunk_file
from src.corpus import (extract_span, iter_corpus_files, project_root, read_text,
                        to_corpus_path)
from src.tokenizer import tokenize_source


# --- métodos dentro de InvertedIndex ---

    def save(self, directory: Path) -> None:
        """Escribe el índice en `directory` (lo crea si no existe)."""

    @classmethod
    def load(cls, directory: Path) -> "InvertedIndex":
        """Reconstruye el índice guardado en `directory`."""


# --- orquestador ---

def build_and_save(corpus_root: Path, max_chunk_size: int,
                   processed_dir: Path) -> InvertedIndex:
    """Indexa el corpus y persiste el índice; devuelve el índice construido."""
```

### La lógica detrás de cada una

**`save(directory)`** — dos ficheros, por comodidad:

- `chunks.json`: la lista de `Chunk` serializada con `dataclasses.asdict` (un `Chunk` es un dataclass, `02`).
- `index.json`: los `postings`, los `doc_lengths`, `k1` y `b`.

El detalle que sorprende: **las claves JSON solo pueden ser strings**, pero en `postings` la clave interna es el `doc_id`, que es un **entero**. Así que al guardar hay que convertir `doc_id` → `str`, y al cargar, `str` → `int`. Si olvidas la conversión en algún lado, `postings["cache"][0]` no coincidirá con `postings["cache"]["0"]`.

Empieza con `directory.mkdir(parents=True, exist_ok=True)`: así `data/processed/` (que no existe todavía, `01`) se crea sola. Es el mismo patrón que verás en cada comando que escribe.

**`load(directory)`** — la operación inversa, como `@classmethod` (devuelve un `InvertedIndex` nuevo, no modifica nada). Reconstruye cada `Chunk(**campos)` y **vuelve a convertir las claves de `postings` a `int`**. Que sea `@classmethod` y no función libre permite escribir `InvertedIndex.load(path)`, que se lee como lo que es: "el índice sabe cargarse".

**`build_and_save(corpus_root, max_chunk_size, processed_dir)`** — el pipeline de indexado, en orden:

1. `project_root()` para tener la raíz (los corpora paths deben ser relativos a ella, `01`).
2. Recorrer `iter_corpus_files(corpus_root)` **con una barra `tqdm`** (el subject lo exige para operaciones largas).
3. Por cada archivo: `read_text` (siempre la misma lectura, `01`) y `to_corpus_path` (la ruta canónica).
4. Partir con `chunk_file(rel, text, max_chunk_size)` (`02`).
5. Por cada chunk, tokenizar **solo el texto de su rango** con `tokenize_source(extract_span(text, chunk.start, chunk.end), rel)` (`04`), acumulando pares `(Chunk, términos)`. Recorta con `extract_span` (`01`), **no** con slicing directo: es la única función que fija la convención `[start, end)`.
6. `build_index(...)` (`05a`) y `index.save(processed_dir)` (`05c`). Devolver el índice.

**Por qué tokenizar el span del chunk y no el archivo entero:** cada documento del índice es **un chunk**, no un archivo (teoría `03`). Sus términos son los de su trozo de texto, más los de la ruta.

**El cuerpo de `cli.index`** — completa el esqueleto de `00b` **sin cambiar su firma**:

- Llama a `build_and_save(root / "data/raw/vllm-0.10.1", max_chunk_size, root / "data/processed")`.
- Imprime un mensaje de éxito (p. ej. cuántos chunks se indexaron).

Recuerda: `max_chunk_size` ya viene como `int` con default `2000` desde `00b`; Fire y el subject fijan ese contrato, y aquí solo se consume.

> **El techo de 2000 es duro (VI.1).** El subject prohíbe superarlo: una sola fuente de más de 2000 caracteres invalida **toda** la salida. El default ya es 2000, pero si alguien pasa `--max_chunk_size 5000`, es prudente **acotar** el valor efectivo a `min(max_chunk_size, 2000)` antes de cortar. Es la primera de las dos redes: la segunda está en `search` (`05b`), que recorta cada fuente al devolverla.

---

## 3. Reglas que este paso debe respetar

| Regla (subject VI.1 / teoría `01`) | Implementación |
|---|---|
| Indexar **una sola vez**; el índice queda en disco | `save` escribe en `data/processed/` |
| Indexado completo en **≤ 5 min** | Recorrido único + barra `tqdm`; sin reconstruir en cada consulta |
| Ningún chunk supera `max_chunk_size` (techo 2000) | Se acota a `min(max_chunk_size, 2000)` y se corta con `chunk_file` (`02`) |
| Todo lo guardado puede **releerse idéntico** | `save`/`load` simétricos; roundtrip probado |
| `data/` no se versiona | Está en `.gitignore` (`00a`); el evaluador regenera el índice |

> Trampa clásica: guardar `postings` con claves `int` a un JSON y leerlas sin reconvertir. El código "funciona" al construir pero **falla al recargar** (claves `str` vs `int`). El `test_save_and_load` de abajo lo caza.

---

## 4. Caso de uso mínimo

```python
from src.corpus import project_root
from src.index import build_and_save

root = project_root()
index_obj = build_and_save(
    root / "data/raw/vllm-0.10.1", 2000, root / "data/processed")
print(f"Indexed {index_obj.n_docs} chunks")
```

Y como comando (esto es lo que corre el evaluador):

```bash
time uv run python -m src index --max_chunk_size 2000
ls -lh data/processed/         # chunks.json e index.json
```

---

## 5. Comprobación

`tests/test_index.py` (parte 3) y un comando real.

| Comprobación | Qué demuestra |
|---|---|
| `test_save_and_load` | `save` + `load` devuelve un índice **idéntico**: `chunks`, `postings` y `doc_lengths` iguales. Es el test del roundtrip (incluida la conversión de claves). |
| `test_real_index_respects_max_len` | Cargando el índice real de `data/processed`, **todos** los chunks miden ≤ 2000. Verifica el techo sobre datos reales. |
| `time uv run python -m src index --max_chunk_size 2000` | El indexado completo entra en **≤ 5 min** (presupuesto VI.1). |

```python
def test_save_and_load(tmp_path: Path) -> None:
    idx = make_index()                 # el índice de juguete de 05a
    idx.save(tmp_path)
    loaded = InvertedIndex.load(tmp_path)
    assert loaded.postings == idx.postings      # claves int reconvertidas
    assert loaded.doc_lengths == idx.doc_lengths
```

---

## 6. Qué NO cubre esta parte

- **Buscar** sobre el índice cargado (single y batch) → `05b` ya da `search`, `06a`/`06b` lo llevan al dataset y a la CLI.
- **Robustez de la CLI** (índice ausente, JSON roto) → `06b`.
- **Indexado incremental** (re-indexar solo un archivo cambiado) → es un **bonus**, no parte del obligatorio.

## 7. Checklist

- [ ] Índice persistido en `data/processed/` y recargado **idéntico**.
- [ ] `index` conectado en la CLI (cuerpo real; misma firma que `00b`).
- [ ] Índice completo en **≤ 5 min**.
- [ ] `uv run pytest` y `uv run make lint` en verde.

## 8. Tiempo estimado

**≈ 30 minutos.**
