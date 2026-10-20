# 03 — Modelos de datos

Las etapas del pipeline no se pasan **texto suelto**: se pasan **estructuras con una forma fija**. Esta etapa las define, tal como las describe `04_los_modelos_de_datos.md`. Sin ellas, cada módulo inventaría su propio "formato" y todo se rompería al conectar una etapa con la siguiente.

El subject es explícito (V.4): los modelos que se **intercambian entre etapas** deben ser **pydantic** (validación y tipado). Es la primera obligación no negociable del proyecto, y por eso tiene su propio archivo.

---

## 1. Qué vas a construir

Dos módulos con responsabilidades muy distintas:

- **`src/models.py`** — las **formas** de los datos: qué campos, de qué tipo, cuáles obligatorios y qué reglas deben cumplir. Puro "esquema".
- **`src/io_utils.py`** — los **verbos** de entrada/salida: convertir esas formas a/desde JSON para leerlas de disco y escribirlas. Teoría `04`: *serializar* / *deserializar*.

Se separan porque responden a preguntas distintas: `models.py` dice *"qué es un dato válido"*; `io_utils.py` dice *"cómo se guarda y se recupera"*. Cambiar el formato de guardado no debería tocar los modelos, y añadir un modelo no debería tocar el IO.

---

## 2. El árbol de estructuras

Este es el vocabulario que usará **todo** el resto del proyecto (teoría `04`). Léelo como un viaje: entra un dataset, sale un `StudentSearchResults`, y de ahí un `StudentSearchResultsAndAnswer`.

```text
MinimalSource      ── file_path, first_character_index, last_character_index

UnansweredQuestion ── question_id, question
   └─ AnsweredQuestion  = lo anterior + sources (list[MinimalSource]) + answer

RagDataset         ── rag_questions: list[AnsweredQuestion | UnansweredQuestion]

MinimalSearchResults       ── question_id, question, retrieved_sources: list[MinimalSource]
   └─ MinimalAnswer        = lo anterior + answer

StudentSearchResults           ── search_results: list[MinimalSearchResults], k
StudentSearchResultsAndAnswer  ── search_results: list[MinimalAnswer],        k
```

**Dónde vive cada cosa** (fijo):

| Símbolo | Ubicación | Por qué ahí |
|---|---|---|
| `MinimalSource` | `models.py` | Pieza fundamental: la ubicación de una fuente |
| `UnansweredQuestion` / `AnsweredQuestion` | `models.py` | Herencia: la respondida *es* la no respondida + `sources` + `answer` |
| `RagDataset` | `models.py` | Contenedor de preguntas (admitidas en ambos estados) |
| `MinimalSearchResults` / `MinimalAnswer` | `models.py` | Resultado de búsqueda de **una** pregunta (con o sin respuesta) |
| `StudentSearchResults` / `StudentSearchResultsAndAnswer` | `models.py` | Resultado de buscar/responder **todo** un dataset |
| `load_dataset` / `load_search_results` / `save_model` | `io_utils.py` | Los únicos puntos que tocan disco |

---

## 3. Las piezas que necesitas

`src/models.py` — declaraciones de campos. Fíjate en los **tipos**, los **defaults** y la **herencia**; la lógica viva está en el validador, explicado abajo.

```python
import uuid
from typing import Union

from pydantic import BaseModel, Field, model_validator


class MinimalSource(BaseModel):
    file_path: str
    first_character_index: int = Field(ge=0)
    last_character_index: int

    @model_validator(mode="after")
    def _check_range(self) -> "MinimalSource":
        """Rechaza rangos vacíos o invertidos (last <= first)."""


class UnansweredQuestion(BaseModel):
    question_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str


class AnsweredQuestion(UnansweredQuestion):
    sources: list[MinimalSource]
    answer: str


class RagDataset(BaseModel):
    rag_questions: list[Union[AnsweredQuestion, UnansweredQuestion]]


class MinimalSearchResults(BaseModel):
    question_id: str
    question: str
    retrieved_sources: list[MinimalSource]


class MinimalAnswer(MinimalSearchResults):
    answer: str


class StudentSearchResults(BaseModel):
    search_results: list[MinimalSearchResults]
    k: int


class StudentSearchResultsAndAnswer(BaseModel):
    search_results: list[MinimalAnswer]
    k: int
```

`src/io_utils.py` — firmas:

```python
from pathlib import Path

from pydantic import BaseModel

from src.models import RagDataset, StudentSearchResults


def load_dataset(path: str | Path) -> RagDataset:
    """Lee un dataset desde JSON y lo valida como RagDataset."""


def save_model(model: BaseModel, path: str | Path) -> None:
    """Escribe `model` como JSON, creando el directorio destino si no existe."""


def load_search_results(path: str | Path) -> StudentSearchResults:
    """Lee unos resultados de búsqueda desde JSON y los valida."""
```

### La lógica detrás de cada pieza

**`MinimalSource`** — la ubicación de un trozo: archivo + dos offsets (teoría `02`/`04`). Dos decisiones de validación **en el propio modelo**:

- `first_character_index` con `Field(ge=0)`: un offset no puede ser negativo.
- el validador `_check_range` exige `last > first`: un rango vacío o invertido es inválido.

**Por qué validar aquí:** el error salta **al crear** la fuente, no veinte pasos después cuando el grader mire el JSON. Encontrar el fallo en el origen ahorra horas.

**`UnansweredQuestion`** — el estado "antes de trabajar": `question_id` (UUID) y `question`. `question_id` se genera con `default_factory=lambda: str(uuid.uuid4())`: único, aleatorio y **sin coordinación** (teoría `04`). Cuando lees un dataset, el id ya viene en el JSON; el default solo aplica si creas preguntas tú.

**`AnsweredQuestion`** — la ejecución de la **herencia**: *es* una `UnansweredQuestion` (hereda `question_id` y `question`) **más** `sources` (las fuentes correctas) y `answer`. Es el patrón con el que se mide la búsqueda.

**`RagDataset`** — un contenedor con una única lista `rag_questions`, cuyos elementos son `AnsweredQuestion | UnansweredQuestion`. Admite los dos tipos porque el **mismo** formato sirve para "pregúntame" y para "aquí está lo correcto".

**Los resultados** — `MinimalSearchResults` (una pregunta: id, pregunta, `retrieved_sources`) y `MinimalAnswer` (= anterior + `answer`). `StudentSearchResults` y `StudentSearchResultsAndAnswer` son sus versiones **a nivel de dataset**, más el campo `k` (cuántas fuentes se pidieron por pregunta). Así, buscar sobre 100 preguntas produce **un** JSON con 100 entradas.

**`io_utils`** — los tres helpers. `load_*` leen el fichero y lo **validan** con `model_validate_json` (si el JSON está mal formado, pydantic lanza `ValueError` → los comandos lo capturarán en `06b`). `save_model` **crea el directorio destino** (`parents=True, exist_ok=True`) y escribe con `model_dump_json(indent=2)` para que el JSON sea legible. Centralizarlos evita que cada comando invente su forma de guardar.

---

## 4. Reglas que este paso debe respetar

| Regla (subject VI.4 / teoría `04`) | Implementación |
|---|---|
| Los modelos son **pydantic** | `BaseModel` para todos los intercambiados entre etapas |
| Nombres y campos **exactos** del subject | `file_path`, `first_character_index`, `last_character_index`, `rag_questions`, `retrieved_sources`, `search_results`, `k`… |
| `question_id` único | `uuid4` como `default_factory` |
| No construir fuentes inválidas | `Field(ge=0)` + validador `last > first` |
| Se puede **ampliar**, pero sin romper | Añade campos **opcionales** (p. ej. un `score`) si los necesitas |

> Trampas: (1) un nombre de campo con una letra distinta (`retrieved_sources` vs `sources`) hace que el JSON **no** valide contra el modelo del grader; (2) no valides `last > first` en el modelo "porque ya lo hago al buscar": entonces el error aparece tarde y confuso.

---

## 5. Caso de uso mínimo

```python
from src.io_utils import load_dataset, save_model
from src.models import MinimalSource

ds = load_dataset("data/datasets/UnansweredQuestions/dataset_docs_public.json")
# 100 UnansweredQuestion listas para buscar (04a/b las llenará)

src = MinimalSource(file_path="data/raw/vllm-0.10.1/docs/features/lora.md",
                    first_character_index=4695, last_character_index=6098)
save_model(ds, "/tmp/copia.json")   # escribe y crea el directorio si hace falta
```

---

## 6. Comprobación

`tests/test_models.py`. Qué demuestra cada test:

| Test | Qué demuestra |
|---|---|
| `test_unanswered_dataset_loads` | El dataset de entrada valida y tiene 100 preguntas |
| `test_answered_dataset_loads` | El dataset ground truth valida (100 preguntas en `AnsweredQuestions/dataset_docs_public.json`) |
| `test_roundtrip` | `save_model` + `load_dataset` devuelve **exactamente** el mismo objeto |
| `test_invalid_range_raises` | `last == first` lanza `ValidationError` |
| `test_negative_index_raises` | Un offset negativo lanza `ValidationError` |
| `test_uuid_is_generated_unique` | Dos preguntas sin id reciben ids **distintos** |

Reparto de responsabilidades: los tres primeros prueban **IO** (y el roundtrip), los tres últimos prueban **la validación** de los modelos.

---

## 7. Qué NO cubre esta parte

- **Rellenar** los modelos con resultados reales (buscar, generar) → `05b`–`08c`.
- **Convertir texto a términos** → `04`.
- **La CLI** que carga y guarda estos JSON → `06b`/`08c`.

## 8. Checklist

- [ ] `src/models.py` y `src/io_utils.py` creados, con los nombres exactos del subject.
- [ ] Roundtrip serializar→deserializar idéntico.
- [ ] Validación de rangos probada (negativo y `last <= first` fallan).
- [ ] `uv run pytest` y `uv run make lint` en verde.

## 9. Tiempo estimado

**≈ 30 minutos.**
