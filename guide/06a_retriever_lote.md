# 06a — Recuperación en lote

En `05b` resolviste **una** pregunta. Pero el evaluador no pregunta de una en una: lanza **todo un dataset** y mide el tiempo (subject VI.2). Aquí conviertes la búsqueda individual en un **lote**: recorrer las preguntas, buscar cada una y producir **un** JSON `StudentSearchResults` con todas las respuestas. Es la etapa de *recuperación* de RAG (teoría `01`) aplicada a escala.

El presupuesto es duro: **200 preguntas en ≤ 90 s** (≈ 0,45 s por pregunta). Casi todo el riesgo de rendimiento se concentra en una decisión: **cuándo cargas el índice**.

---

## 1. Qué vas a construir

Un módulo nuevo `src/retriever.py` con **una** función, `search_dataset`. **Por qué un módulo aparte de `index.py`:** el índice sabe *cómo se puntúa* (un verbo por documento, `05b`); el retriever sabe *cómo se recorre un dataset de preguntas* (una capa de orquestación por encima). Son dos preocupaciones distintas, y mezclarlas difumina la responsabilidad.

`search_dataset` **no escribe nada**: recibe el índice y el dataset, y devuelve el `StudentSearchResults` en memoria. **Dónde guardar** ese JSON es decisión de quien llama (el comando `search_dataset` de `06b`), y ahí entra el *scopeado* (ver §3).

**Dónde vive cada cosa:**

| Símbolo | Ubicación | Por qué ahí |
|---|---|---|
| `search_dataset` | `retriever.py` | Recorre el dataset y agrupa resultados; no es lógica del índice |

---

## 2. Las piezas que necesitas

Firma (con docstring). **La lógica**, debajo.

```python
from tqdm import tqdm

from src.index import InvertedIndex, search
from src.models import MinimalSearchResults, RagDataset, StudentSearchResults


def search_dataset(index: InvertedIndex, dataset: RagDataset,
                   k: int) -> StudentSearchResults:
    """Busca cada pregunta del dataset y devuelve el StudentSearchResults."""
```

### La lógica detrás de la función

Un bucle, con una sola idea importante:

1. Recorrer `dataset.rag_questions` **con una barra `tqdm`** (subject: operaciones largas).
2. Por cada pregunta, llamar a `search(index, question.question, k)` (`05b`) para obtener sus fuentes.
3. Envolver el resultado en un `MinimalSearchResults(question_id, question, retrieved_sources)`.
4. Devolver un **único** `StudentSearchResults(search_results=[...], k=k)`.

Recuerda el modelo (`03`): buscar sobre 100 preguntas produce **un** JSON con 100 entradas, no 100 ficheros. El `question_id` y el `question` se copian **verbatim** de la pregunta: el grader empareja por `question_id`.

---

## 3. Reglas que este paso debe respetar

| Regla (subject VI.2 / teoría `01`) | Implementación |
|---|---|
| Devolver un `StudentSearchResults` válido | `search_dataset` rellena `search_results` y `k` |
| 200 preguntas en **≤ 90 s** | El índice se carga **una vez**; nada se reconstruye por pregunta |
| `question_id` emparejable | Se copia tal cual de la pregunta |
| Reutilizar la búsqueda single | Se llama a `search` (`05b`), no se duplica lógica |

> **Rendimiento — las dos reglas que deciden si entras en el presupuesto:**
> 1. **Carga el índice una sola vez**, fuera del bucle. Cargar decenas de MB 200 veces revienta los 90 s.
> 2. **No releas el corpus al buscar.** El índice ya tiene los offsets; el texto se relee solo al **generar** (`08`). Buscar es puntuar términos, no leer archivos.

> **Sobre el scopeado de la salida.** Los datasets públicos **comparten nombre de fichero** (`dataset_docs_public.json`), así que el subject (VI.7.2) pide que **quien invoca** el comando apunte `--save_directory` a una carpeta **ya scopeada** por dataset (`.../search_results/UnansweredQuestions`). Esa es una decisión de la CLI (`06b`), no del retriever: por eso `search_dataset` aquí solo devuelve el objeto y no toca rutas. **Ojo:** no añadas el scope *dentro* del comando a un `--save_directory` que ya lo lleva, o acabarás con `.../UnansweredQuestions/UnansweredQuestions/`.

---

## 4. Caso de uso mínimo

```python
from src.corpus import project_root
from src.index import InvertedIndex
from src.io_utils import load_dataset
from src.retriever import search_dataset

idx = InvertedIndex.load(project_root() / "data/processed")   # UNA sola vez
ds = load_dataset("data/datasets/UnansweredQuestions/dataset_docs_public.json")
out = search_dataset(idx, ds, k=10)
print(len(out.search_results), "preguntas resueltas")   # 100
```

Ese `out` es el objeto que `06b` guardará como `StudentSearchResults` JSON.

---

## 5. Comprobación

`tests/test_retriever.py`. Qué demuestra el test:

| Test | Qué demuestra |
|---|---|
| `test_search_dataset_shape` | El resultado tiene **una** entrada por pregunta (`len(ds.rag_questions)`), `k` se propaga y ninguna pregunta trae más de `k` fuentes |

```python
def test_search_dataset_shape() -> None:
    idx = InvertedIndex.load(ROOT / "data/processed")
    ds = load_dataset("data/datasets/UnansweredQuestions/dataset_docs_public.json")
    out = search_dataset(idx, ds, k=10)
    assert len(out.search_results) == len(ds.rag_questions)
    assert out.k == 10
    assert all(len(r.retrieved_sources) <= 10 for r in out.search_results)
```

Es un test de **forma**: la búsqueda en lote no debe perder preguntas ni devolver más fuentes de las pedidas.

---

## 6. Qué NO cubre esta parte

- **Escribir el JSON y scopeado de la salida** (y blindar errores) → `06b`.
- **Generar respuestas** con esas fuentes → `08`.
- **Medir** el recall de lo recuperado → `07`.

## 7. Checklist

- [ ] `search_dataset` implementado y devuelve un `StudentSearchResults` válido.
- [ ] Índice cargado **una vez** por batch.
- [ ] El resultado tiene una entrada por pregunta y respeta `k`.
- [ ] `uv run pytest` y `uv run make lint` en verde.

## 8. Tiempo estimado

**≈ 30 minutos.**
