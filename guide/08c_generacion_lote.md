# 08c — Generación en lote

Tienes la búsqueda en lote (`06a`) y la generación de una respuesta (`08b`). Falta **encadenarlas** sobre todo un dataset y producir un `StudentSearchResultsAndAnswer` válido. Es la última pieza del pipeline: **recuperar → aumentar → generar**, a escala.

Hay un detalle de diseño que ordena toda esta etapa: **la estructura la construye tu código, no el modelo** (teoría `08`). Al modelo se le pide **solo el texto**; envolverlo en `MinimalAnswer` y `StudentSearchResultsAndAnswer` es trabajo tuyo.

---

## 1. Qué vas a construir

Una función más en `generator.py` y **dos comandos** en `cli.py`:

- `answer_dataset(search_results, model, tokenizer, root)` — recorre los resultados, genera y reensambla.
- `answer(query, k, index_directory)` — una pregunta: busca y responde (por consola).
- `answer_dataset(student_search_results_path, save_directory)` — un lote: responde y **guarda** el JSON.

**Dónde vive cada cosa:**

| Símbolo | Ubicación | Por qué ahí |
|---|---|---|
| `answer_dataset` (lógica) | `generator.py` | Orquestar generación sobre un lote es la fase de generación |
| `answer` / `answer_dataset` (comandos) | `cli.py` | Traducción argumentos ↔ lógica de negocio |
| mapa de Fire (una entrada más) | `__main__.py` | Cableado de la entrada |

**La diferencia clave entre los dos comandos**, y por qué existe:

- `answer_dataset` **no necesita el índice**: trabaja sobre fuentes **ya recuperadas** (que vienen dentro del `StudentSearchResults`).
- `answer` **sí reconstruye la búsqueda** desde el índice, porque parte de una pregunta nueva, no de un resultado guardado.

---

## 2. Las piezas que necesitas

Firmas (con docstring). El **mapa de Fire** sí lo muestras entero (es el cableado, el entregable de la etapa). La lógica, debajo.

```python
from pathlib import Path
from typing import Any

from tqdm import tqdm

from src.models import (MinimalAnswer, StudentSearchResults,
                        StudentSearchResultsAndAnswer)


def answer_dataset(search_results: StudentSearchResults, model: Any,
                   tokenizer: Any, root: Path) -> StudentSearchResultsAndAnswer:
    """Responde cada pregunta y devuelve el StudentSearchResultsAndAnswer."""
```

Los comandos en `src/cli.py`:

```python
def answer(query: str, k: int = 10,
           index_directory: str = "data/processed") -> None:
    """Busca `query` y responde (imprime la respuesta)."""


def answer_dataset(student_search_results_path: str,
                   save_directory: str = "data/output/search_results_and_answer") -> None:
    """Responde todo un StudentSearchResults y guarda el JSON de salida."""
```

El mapa en `src/__main__.py` (aquí sí importa el orden final):

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

> **La colisión de nombres, igual que en `06b`.** Fire usa el nombre de la función como subcomando, así que el comando debe llamarse `answer_dataset`; pero la lógica de `generator.py` también se llama `answer_dataset`. Impórtala **con alias** (`from src.generator import answer_dataset as run_answer_dataset`) y llama a `run_answer_dataset(...)` desde el comando. (`answer` no colisiona con `generator.py`, y reutiliza el alias `search as run_search` que ya dejaste en `06b`.)

### La lógica detrás de cada una

**`answer_dataset`** — el bucle de generación:

1. Recorrer `search_results.search_results` **con una barra `tqdm`** (subject: operaciones largas). Para cada `item`:
   - `build_context(item.retrieved_sources, root)` (`08a`) — de ubicaciones a texto.
   - `generate_answer(item.question, blocks, model, tokenizer)` (`08b`) — el texto de la respuesta.
   - Envolver en `MinimalAnswer(question_id, question, retrieved_sources, answer)`, **copiando** id, pregunta y fuentes **tal cual** del `item`. El grader empareja por `question_id` (`06a`).
2. Devolver `StudentSearchResultsAndAnswer(search_results=answers, k=search_results.k)` — propagando el mismo `k`.

**Por qué copias id/pregunta/fuentes en vez de reconstruirlos:** son la entrada del grader para medir **recall**; alterarlos rompería la evaluación. La generación **solo añade** el campo `answer`.

**`answer` (comando)** —

1. Cargar el índice con `_load_index` (`06b`); si es `None`, salir.
2. `load_model()` **una vez** (`08b`).
3. Buscar (`search`, `05b`), `build_context` (`08a`), `generate_answer` (`08b`).
4. **Imprimir** la respuesta.

**`answer_dataset` (comando)** — el mismo esqueleto de escritura que `search_dataset` (`06b`):

1. Cargar los resultados con `load_search_results` (`03`), **capturando** `FileNotFoundError`/`OSError`/`ValueError` → aviso sin `Traceback`.
2. `load_model()` una vez.
3. `answer_dataset(...)` (la función de arriba).
4. `mkdir(parents=True, exist_ok=True)` sobre **`save_directory` tal cual lo pasó quien invoca** + `save_model` en `save_directory/<nombre original>.json`.

**Por qué el `--save_directory` se usa tal cual:** igual que en la búsqueda (`06b`), los datasets públicos **comparten nombre de fichero**; el subject pide que **quien invoca** pase una carpeta **ya scopeada** (`.../search_results_and_answer/UnansweredQuestions`). El comando **no** añade la subcarpeta: si el `--save_directory` ya viene scopeado, duplicarlo dejaría el fichero donde el evaluador no lo busca.

---

## 3. Reglas que este paso debe respetar

| Regla (subject VI.6 / teoría `08`) | Implementación |
|---|---|
| La estructura la arma **tu código** | Se envuelve el texto del modelo en los modelos de `03` |
| Ruta de salida **configurable** y scopeada | `--save_directory` usado tal cual (el scope lo aporta quien llama) |
| El JSON de salida **valida** | `model_dump_json` de `StudentSearchResultsAndAnswer` |
| Ninguna entrada degenerada revienta | `FileNotFoundError`/`OSError`/`ValueError` capturadas |
| `question_id`/fuentes se preservan | Se copian **verbatim** del `StudentSearchResults` |

**Casos degenerados, y que la salida siga siendo válida** (teoría `08`):

| Situación | Comportamiento |
|---|---|
| Búsqueda sin fuentes | `build_context` devuelve `[]` → respuesta honesta, sin alucinar |
| Fuente que apunta a archivo inexistente | `build_context` la **salta** (`08a`) |
| Contexto que no cabe | `generate_answer` **recorta** (`08b`) |

En los tres, el `StudentSearchResultsAndAnswer` sigue validando contra el modelo.

---

## 4. Caso de uso mínimo

```bash
# una pregunta: busca y responde
uv run python -m src answer "How to dynamically load a LoRA adapter?" --k 5

# un lote: parte de los resultados de búsqueda ya guardados
uv run python -m src answer_dataset \
    --student_search_results_path data/output/search_results/UnansweredQuestions/dataset_docs_public.json \
    --save_directory data/output/search_results_and_answer/UnansweredQuestions
```

---

## 5. Comprobación

Integración (lenta: carga el modelo). Qué demuestra:

| Comprobación | Qué demuestra |
|---|---|
| `test_answer_dataset_output_is_valid` | Buscar un dataset → responderlo → guardar y **validar** con `model_validate_json` |
| Los dos comandos de arriba | End-to-end real: `answer` puntual y `answer_dataset` en lote, sin `Traceback` |

```python
def test_answer_dataset_output_is_valid(tmp_path) -> None:
    from src.generator import answer_dataset, load_model
    from src.index import InvertedIndex
    from src.io_utils import load_dataset, save_model
    from src.models import StudentSearchResultsAndAnswer
    from src.retriever import search_dataset

    idx = InvertedIndex.load(ROOT / "data/processed")
    ds = load_dataset("data/datasets/UnansweredQuestions/dataset_docs_public.json")
    sr = search_dataset(idx, ds, k=3)          # 06a
    model, tokenizer = load_model()            # 08b
    out = answer_dataset(sr, model, tokenizer, ROOT)
    dest = tmp_path / "ans.json"
    save_model(out, dest)
    StudentSearchResultsAndAnswer.model_validate_json(dest.read_text())   # valida
```

La aserción final es la que importa: **la salida generada valida contra el modelo del grader**. Si el modelo pequeño escribiera cualquier cosa, verías un error antes de entregar nada.

---

## 6. Qué NO cubre esta parte

- **Medir** la calidad (recall) → `07`; aquí solo se **genera**.
- **Robustez global de la CLI** y la entrega final → `09`.
- **Mejorar** las respuestas: la palanca está en `SYSTEM` (`08a`) y en el contexto que le das (`05b`,`02`), no en esta orquestación.

## 7. Checklist

- [ ] `answer` y `answer_dataset` conectados en el mapa de la CLI.
- [ ] La salida escribe `save_directory/<nombre>.json` (scopeado por quien llama) y **valida**.
- [ ] La estructura la construye **tu código**, no el modelo.
- [ ] Sin fichero o JSON mal formado, avisa sin `Traceback`.
- [ ] `uv run pytest` y `uv run make lint` en verde.

## 8. Tiempo estimado

**≈ 30–45 minutos.**
