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

## 3. Los modelos (`src/models.py`)

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

### La lógica detrás de cada modelo

**`MinimalSource`** — la ubicación de un trozo: archivo + dos offsets (teoría `02`/`04`). Dos decisiones de validación **en el propio modelo**:

- `first_character_index` con `Field(ge=0)`: un offset no puede ser negativo.
- el validador `_check_range` exige `last > first`: un rango vacío o invertido es inválido.

**Por qué validar aquí:** el error salta **al crear** la fuente, no veinte pasos después cuando el grader mire el JSON. Encontrar el fallo en el origen ahorra horas.

**`UnansweredQuestion`** — el estado "antes de trabajar": `question_id` (UUID) y `question`. `question_id` se genera con `default_factory=lambda: str(uuid.uuid4())`: único, aleatorio y **sin coordinación** (teoría `04`). Cuando lees un dataset, el id ya viene en el JSON; el default solo aplica si creas preguntas tú.

**`AnsweredQuestion`** — la ejecución de la **herencia**: *es* una `UnansweredQuestion` (hereda `question_id` y `question`) **más** `sources` (las fuentes correctas) y `answer`. Es el patrón con el que se mide la búsqueda.

**`RagDataset`** — un contenedor con una única lista `rag_questions`, cuyos elementos son `AnsweredQuestion | UnansweredQuestion`. Admite los dos tipos porque el **mismo** formato sirve para "pregúntame" y para "aquí está lo correcto".

**Los resultados** — `MinimalSearchResults` (una pregunta: id, pregunta, `retrieved_sources`) y `MinimalAnswer` (= anterior + `answer`). `StudentSearchResults` y `StudentSearchResultsAndAnswer` son sus versiones **a nivel de dataset**, más el campo `k` (cuántas fuentes se pidieron por pregunta). Así, buscar sobre 100 preguntas produce **un** JSON con 100 entradas.

---

## 4. La entrada/salida (`src/io_utils.py`)

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

Lo que decía la guía sobre este módulo, tal cual:

**`io_utils`** — los tres helpers. `load_*` leen el fichero y lo **validan** con `model_validate_json` (si el JSON está mal formado, pydantic lanza `ValueError` → los comandos lo capturarán en `06b`). `save_model` **crea el directorio destino** (`parents=True, exist_ok=True`) y escribe con `model_dump_json(indent=2)` para que el JSON sea legible. Centralizarlos evita que cada comando invente su forma de guardar.

Las secciones siguientes explican **por qué** funciona así y cómo se conecta con el resto del pipeline. No cambian ninguna decisión de arriba (firmas, nombres, comportamiento): solo las desarrollan.

### 4.1 Qué problema resuelve

Los modelos de la sección 3 viven **en memoria**: cuando el programa termina, desaparecen. Pero el pipeline no es un único programa: son **comandos separados** (`search_dataset`, después `answer_dataset`, después `evaluate`…), y cada uno arranca de cero. La única forma de pasar datos de un comando al siguiente es **un archivo**. `io_utils` es ese puente.

Hay una segunda razón: los archivos que escribes los **lee otro programa** (la moulinette), así que su formato no es una elección libre, sino parte del contrato con el subject.

### 4.2 Las tres capas: objeto, texto y archivo

Entre un dato en memoria y un archivo en disco hay **dos saltos distintos**:

> objeto (`RagDataset`)  ⇄  texto JSON  ⇄  archivo en disco

- **Primer salto, objeto ⇄ texto.** Es lo que la teoría `04` llama *serializar* (objeto a JSON) y *deserializar* (JSON a objeto). **Lo hace pydantic**: `model_dump_json` serializa y `model_validate_json` deserializa y valida. No hay que escribir esa lógica.
- **Segundo salto, texto ⇄ archivo.** Abrir el archivo, leer o escribir el texto y cerrarlo. **Esto es lo único que añaden tus funciones**, con `pathlib`.

Por eso la parte conceptual de `io_utils` parece pequeña: la lógica pesada ya está en pydantic y en los modelos de la sección 3. Lo que aporta `io_utils` es **un único sitio** donde ocurre el segundo salto, con las mismas decisiones para todos los comandos.

### 4.3 Cómo encaja cada función

| Función | Qué recibe | Paso de disco | Paso de formato | Qué devuelve |
|---|---|---|---|---|
| `load_dataset` | una ruta (`str` o `Path`) | **leer** el texto del archivo | **deserializar y validar** como `RagDataset` | un `RagDataset` |
| `load_search_results` | una ruta (`str` o `Path`) | **leer** el texto del archivo | **deserializar y validar** como `StudentSearchResults` | un `StudentSearchResults` |
| `save_model` | cualquier modelo pydantic y una ruta | crear la carpeta y **escribir** el texto | **serializar** con `indent=2` | nada (`None`): su efecto es el archivo |

Hay dos `load_*` y no una función genérica porque cada una **devuelve un tipo distinto**: así `mypy` (y quien lee el código) sabe exactamente qué obtiene. `save_model` sí es genérica porque recibe cualquier `BaseModel`: para escribir da igual qué modelo sea.

### 4.4 Qué significa «deserializar y validar» a la vez

`model_validate_json` no se limita a convertir texto en objetos: reconstruye el objeto **comprobando todo lo que declaraste en los modelos**. Con un dataset, en este orden:

1. El texto es **JSON bien formado** (si no, error).
2. Existe el campo raíz (`rag_questions`) y es una lista.
3. Cada elemento encaja con `AnsweredQuestion` o con `UnansweredQuestion` (campos obligatorios y tipos).
4. Dentro de cada pregunta, **cada fuente** pasa por las reglas de `MinimalSource`: `Field(ge=0)` y el validador `_check_range`.
5. Solo si todo lo anterior pasa, se entrega el objeto construido.

Es la razón por la que la sección 3 insiste en validar **dentro** de los modelos: al leer un dataset de disco, cada fuente de cada pregunta se comprueba automáticamente, sin que `load_dataset` haga nada extra. Y si algo falla, falla **en el punto de entrada**, con un error de pydantic que dice qué campo es el problema, y no veinte pasos después.

La alternativa —leer el JSON a un diccionario y construir el modelo a mano— son más pasos, y los errores quedan repartidos entre dos sitios. Con `model_validate_json` es una sola llamada.

### 4.5 De dónde salen los datos que devuelven los `load_*`

Las funciones `load_*` **no inventan datos**: leen archivos que ya existen. Lo importante es saber **quién creó cada archivo**. Hay tres cosas distintas que no conviene mezclar:

| Qué es | Dónde está | Quién lo crea | Quién lo lee |
|---|---|---|---|
| **El corpus**: el código de vLLM, el material donde se busca | `data/raw/vllm-0.10.1/` | te lo dan | `corpus.py` |
| **Los datasets**: las preguntas, en JSON | `data/datasets/UnansweredQuestions/` y `AnsweredQuestions/` | te los dan | `load_dataset` |
| **Tus resultados**: lo que produce tu sistema | `data/output/...` | tus comandos, con `save_model` | `load_search_results` y la moulinette |

Dos consecuencias:

- **Las preguntas no salen del corpus.** Los datasets son archivos aparte. Lo que los une al corpus es que cada fuente de un dataset con respuestas **apunta** a un trozo del corpus con `file_path` y dos offsets.
- **`load_search_results` lee lo que escribió un comando anterior.** El `search_dataset` (etapa `06b`) carga las preguntas con `load_dataset`, busca en el índice, agrupa el resultado en un `StudentSearchResults` y lo guarda con `save_model`. Más tarde, `answer_dataset` (o `evaluate`) abre ese mismo archivo con `load_search_results`. Es una **cadena**: lo que `save_model` escribe en un paso lo lee `load_search_results` en el siguiente, quizá desde otra ejecución del programa.

### 4.6 La carpeta que crea `save_model`

- **Cuál es.** `save_model` no tiene una carpeta fija: crea **la carpeta que contiene el archivo** que le pides escribir (la ruta completa la monta cada comando). Por ejemplo, el subject muestra que `search_dataset` guarda en `data/output/search_results/UnansweredQuestions/dataset_docs_public.json`; esa carpeta es la que hay que crear.
- **Por qué hay que crearla.** No existe en un repo recién clonado: `data/` está en el `.gitignore`, así que nunca viaja con el código. Escribir un archivo en una carpeta inexistente da `FileNotFoundError`. Si `save_model` no la creara, el primer `search_dataset` del evaluador fallaría. La guía `00a` ya lo anticipa: las carpetas de salida no se crean a mano, **cada comando las crea** con `mkdir(parents=True, exist_ok=True)`.
- **Qué significan las dos opciones.** `parents=True` crea también las carpetas intermedias (`output/`, `search_results/`, `UnansweredQuestions/`). `exist_ok=True` evita el error cuando la carpeta ya existe, que es lo normal a partir de la segunda ejecución.
- **Qué lo exige.** El layout del subject (VI.7.1), que fija `data/output/search_results/<DatasetScope>/` y `data/output/search_results_and_answer/<DatasetScope>/`; el argumento `--save_directory`, que **el evaluador** apunta a sus propias carpetas de salida; y la separación por dataset (`<DatasetScope>`), porque los datasets públicos comparten nombre de archivo y una ejecución pisaría a la otra.
- **Qué uso tiene.** Es donde quedan los JSON que otros leen después: el de `search_results/` lo lee la moulinette (para calcular el recall) y `answer_dataset`; el de `search_results_and_answer/` es el resultado final con respuestas.

### 4.7 Qué errores pueden salir y de dónde vienen

Hay **dos familias**, según el salto en el que ocurran:

| Situación | Error | Quién lo lanza |
|---|---|---|
| El archivo no existe | `FileNotFoundError` | la **lectura** (segundo salto) |
| No hay permiso para leer o escribir | `PermissionError` | la **lectura** o la **escritura** (segundo salto) |
| JSON roto, o con otra forma | `ValidationError` (es un tipo de `ValueError`) | pydantic (primer salto) |
| Una fuente con rango inválido | `ValidationError` | el validador `_check_range` de `MinimalSource` |

Los dos primeros son tipos de `OSError`; los otros, de `ValueError`. `io_utils` **no captura ninguno**: los deja subir. Los comandos (etapas `06b` y `08c`) tendrán que capturar **ambas familias**, porque el subject prohíbe que la CLI termine con un `Traceback`.

### 4.8 Las decisiones de cada función, y por qué

- **Aceptar `str | Path`.** La firma lo promete; lo primero que hace cada función es convertir la ruta a un `Path`, con el que ya puede trabajar igual venga como venga.
- **UTF-8 explícito.** Las preguntas llevan tildes y signos (`¿`). La codificación no se deja a lo que decida el sistema: es la misma razón por la que `corpus.py` decodifica a mano.
- **Crear la carpeta antes de escribir**, y no después ni «por si acaso» en cada comando: así ningún comando puede olvidarlo.
- **Leer y escribir con los métodos de `Path`.** Abren y cierran el archivo solos, así que cumplen la regla del subject de no dejar recursos sin liberar (V.1), sin escribir un bloque `with` aparte.
- **`indent=2`.** Solo por legibilidad: el JSON es igual de válido sin indentar, pero así se puede abrir y revisar a ojo.
- **Los nombres del JSON salen de los modelos.** `save_model` no decide ningún nombre de campo: los toma de los modelos de la sección 3. Por eso el subject insiste en nombres exactos: si un campo se llamara distinto, la moulinette no podría leer tu salida.

### 4.9 Qué comando usa qué

| Comando | Lee | Escribe |
|---|---|---|
| `index` | el corpus, con `corpus.py` | el índice en `data/processed/` (etapa `05c`, con su propio código: el índice no es un modelo pydantic) |
| `search` / `answer` | el índice (y el corpus, en `answer`) | nada: imprimen por pantalla |
| `search_dataset` | `load_dataset(--dataset_path)` | `save_model` de un `StudentSearchResults` en `--save_directory` |
| `answer_dataset` | `load_search_results(--student_search_results_path)` | `save_model` de un `StudentSearchResultsAndAnswer` en `--save_directory` |
| `evaluate` | `load_search_results` y `load_dataset` (el ground truth) | nada: imprime el recall |

### 4.10 Lo que `io_utils` no hace

- **No lee el corpus.** Eso es de `corpus.py`, que es el único módulo que lee archivos del corpus y cuida los offsets. Los JSON se leen aquí con los métodos de `Path`, no con el `read_text` de `corpus.py`.
- **No decide el nombre del archivo ni la carpeta.** Los monta cada comando a partir de `--save_directory` y del nombre del dataset; `save_model` solo recibe la ruta final.
- **No comprueba `k` ni preguntas vacías.** Esas reglas son del CLI (`06b`), donde se puede dar un mensaje claro.
- **No captura errores.** Los deja subir a los comandos (ver 4.7).
- **No guarda el índice.** Eso es de la etapa `05c`.

---

## 5. Reglas que este paso debe respetar

| Regla (subject VI.4 / teoría `04`) | Implementación |
|---|---|
| Los modelos son **pydantic** | `BaseModel` para todos los intercambiados entre etapas |
| Nombres y campos **exactos** del subject | `file_path`, `first_character_index`, `last_character_index`, `rag_questions`, `retrieved_sources`, `search_results`, `k`… |
| `question_id` único | `uuid4` como `default_factory` |
| No construir fuentes inválidas | `Field(ge=0)` + validador `last > first` |
| Se puede **ampliar**, pero sin romper | Añade campos **opcionales** (p. ej. un `score`) si los necesitas |

> Trampas: (1) un nombre de campo con una letra distinta (`retrieved_sources` vs `sources`) hace que el JSON **no** valide contra el modelo del grader; (2) no valides `last > first` en el modelo "porque ya lo hago al buscar": entonces el error aparece tarde y confuso.

---

## 6. Caso de uso mínimo

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

## 7. Comprobación

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

## 8. Preguntas de repaso — Modelos de datos

### Preguntas

#### 1. ¿Por qué se separan las responsabilidades en dos módulos (`src/models.py` y `src/io_utils.py`)?
#### 2. ¿Qué ventaja ofrece usar Pydantic frente a diccionarios o `dataclass` nativas para las estructuras intercambiadas?
#### 3. ¿Cómo valida `MinimalSource` que sus coordenadas corresponden a un rango válido y no negativo?
#### 4. ¿Por qué `question_id` en `UnansweredQuestion` utiliza `Field(default_factory=lambda: str(uuid.uuid4()))`?
#### 5. ¿Cómo se aprovecha la herencia de clases en `AnsweredQuestion` respecto a `UnansweredQuestion`?
#### 6. ¿Cuál es el rol de `RagDataset` y qué tipos de elementos admite dentro de `rag_questions`?
#### 7. ¿Cuál es la diferencia de nivel entre `MinimalSearchResults` y `StudentSearchResults`?
#### 8. ¿Qué dos saltos conceptuales ocurren durante la serialización/deserialización al guardar o cargar un archivo JSON?
#### 9. ¿Por qué `save_model` ejecuta `parent.mkdir(parents=True, exist_ok=True)` antes de escribir en disco?
#### 10. ¿Por qué es crítico respetar los nombres de campo exactos especificados por el subject (ej. `retrieved_sources`)?

---

## Respuestas

<details>
<summary><strong>Respuesta 1 — Separación de responsabilidades (`models.py` vs `io_utils.py`)</strong></summary>

Se separan porque responden a dos preguntas distintas:
- `src/models.py` define **qué es un dato válido** (el esquema, tipos, campos obligatorios y reglas de validación).
- `src/io_utils.py` define **cómo se lee y guarda ese dato en disco** (los verbos de entrada/salida y la serialización JSON).

Esta separación permite modificar la forma en que se escriben los archivos sin alterar las estructuras de datos, y viceversa.

</details>

<details>
<summary><strong>Respuesta 2 — Ventajas de Pydantic</strong></summary>

Pydantic valida automáticamente los tipos y reglas de datos durante la instanciación y deserialización desde JSON. Si un dato no coincide con la definición, Pydantic lanza una `ValidationError` explicativa inmediatamente en el punto de entrada. Con diccionarios o `dataclass` estándar, los errores pasarían desapercibidos hasta causar fallos difíciles de depurar en etapas avanzadas.

</details>

<details>
<summary><strong>Respuesta 3 — Validación de rangos en `MinimalSource`</strong></summary>

Utiliza dos mecanismos de validación:
1. `first_character_index: int = Field(ge=0)` asegura que el offset de inicio nunca sea negativo.
2. El validador `@model_validator(mode="after")` mediante `_check_range` verifica que `last_character_index > first_character_index`. 

Esto rechaza rangos vacíos o invertidos en el momento de creación.

</details>

<details>
<summary><strong>Respuesta 4 — Identificadores únicos (`uuid4`)</strong></summary>

`default_factory=lambda: str(uuid.uuid4())` garantiza que si se instancian preguntas sin id explícito, cada una reciba un identificador único global (UUIDv4) generado dinámicamente. Se usa `default_factory` para que la función se ejecute al crear cada objeto nuevo y no una sola vez al definir la clase.

</details>

<details>
<summary><strong>Respuesta 5 — Herencia de `AnsweredQuestion`</strong></summary>

`AnsweredQuestion` hereda directamente de `UnansweredQuestion`. Esto significa que reutiliza los campos `question_id` y `question`, y añade los campos obligatorios de una pregunta respondida: `sources` y `answer`. Evita duplicar código y mantiene la consistencia de los identificadores.

</details>

<details>
<summary><strong>Respuesta 6 — Rol y contenido de `RagDataset`</strong></summary>

`RagDataset` es la estructura contenedora que representa un conjunto de datos completo. Su campo `rag_questions` contiene una lista de elementos que pueden ser `AnsweredQuestion` o `UnansweredQuestion` (`Union[...]`), permitiendo servir tanto para entradas sin respuesta como para ground truth.

</details>

<details>
<summary><strong>Respuesta 7 — Nivel individual vs Nivel Dataset</strong></summary>

- `MinimalSearchResults` representa el resultado de búsqueda para **una sola pregunta** (`question_id`, `question`, `retrieved_sources`).
- `StudentSearchResults` representa el resultado acumulado para **todo un dataset** de preguntas, conteniendo la lista de resultados y el parámetro `k`.

</details>

<details>
<summary><strong>Respuesta 8 — Saltos en serialización y deserialización</strong></summary>

Existen dos saltos conceptuales entre el objeto en memoria y el archivo en disco:
1. **Objeto ⇄ Texto JSON:** Pydantic lo maneja con `model_dump_json()` y `model_validate_json()`.
2. **Texto JSON ⇄ Archivo:** `pathlib.Path` maneja la lectura y escritura física en disco.

</details>

<details>
<summary><strong>Respuesta 9 — Creación preventiva de directorios (`mkdir`)</strong></summary>

`data/` y sus subcarpetas están excluidas de Git por el `.gitignore`, por lo que no existen en un repositorio recién clonado. Escribir un archivo en una ruta cuya carpeta no existe causa un `FileNotFoundError`. Ejecutar `parent.mkdir(parents=True, exist_ok=True)` asegura que las carpetas intermedias se creen automáticamente.

</details>

<details>
<summary><strong>Respuesta 10 — Nombres de campo exactos</strong></summary>

La moulinette / evaluador automático espera encontrar en los JSON una estructura de claves fija e inalterable definida en el subject. Si un campo se nombra de manera diferente (ej. `sources` en lugar de `retrieved_sources`), la deserialización del evaluador fallará y la comprobación se marcará como incorrecta.

</details>

---

## 9. Checklist

- [ ] `src/models.py` y `src/io_utils.py` creados, con los nombres exactos del subject.
- [ ] Roundtrip serializar→deserializar idéntico.
- [ ] Validación de rangos probada (negativo y `last <= first` fallan).
- [ ] `uv run pytest` y `uv run make lint` en verde.

## 10. Tiempo estimado

**≈ 2:30 horas.**