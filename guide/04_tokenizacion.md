# 04 — Tokenización

Ya tienes chunks (`02`) y sus formas (`03`). Para poder **buscar por palabras** falta decidir qué cuenta como "palabra": convertir el texto en una **lista de términos normalizados**. Eso es *tokenizar*, y es la etapa que conecta la lectura del corpus con la búsqueda léxica (`06_busqueda_lexica.md`).

> Cuidado con una confusión de nombre: estos **tokens de búsqueda** (palabras normalizadas para comparar) no son los **tokens del LLM** (las unidades con las que el modelo trocea el texto, `00`). Uno sirve para que el índice encuentre; el otro para que el modelo lea.

La regla que manda aquí (teoría `05`) es una condición de **correctitud**, no de estilo:

> **Los chunks y las preguntas se tokenizan exactamente igual.** Si un lado guarda `server` y el otro busca `Server`, el match nunca ocurre aunque el texto sea idéntico.

Por eso hay **un solo** tokenizador (`src/tokenizer.py`) y lo usan los dos lados: el indexado (`05c`) y la consulta (`05b`).

---

## 1. Qué vas a construir

Un módulo `src/tokenizer.py` que, dado un texto, devuelve la lista de términos con los que **se comparará**. Dos funciones de entrada según el lado:

- `tokenize(text)` → se usa en la **pregunta**.
- `tokenize_source(text, file_path)` → se usa en el **chunk**, y además inyecta los términos de la ruta (el truco de enriquecimiento de la teoría `05`).

Y dos piezas internas: `split_identifier` (trocear identificadores de código) y `remove_stopwords` (palanca opcional).

---

## 2. Dónde vive cada cosa

Todo en `src/tokenizer.py`:

| Símbolo | Decide | Quién lo usa |
|---|---|---|
| `tokenize(text)` | el colador común (minúsculas, signos, identificadores) | la consulta (`05b`) y `tokenize_source` |
| `split_identifier(token)` | cómo trocear `snake_case`/`CamelCase` | `tokenize` |
| `tokenize_source(text, file_path)` | qué texto indexable tiene un chunk (texto **+ ruta**) | el indexado (`05c`) |
| `remove_stopwords(terms, ...)` | qué palabras vacías descartar | **palanca opcional** (no conectada por defecto) |
| `STOPWORDS` | la lista de palabras vacías | `remove_stopwords` |

Por qué `tokenize` y `tokenize_source` son **dos** funciones y no una: el chunk se enriquece con su ruta, la pregunta no. Pero las dos desembocan en el **mismo** `tokenize`, que es lo que garantiza la regla de oro.

---

## 3. Las piezas que necesitas

Firmas (con docstring). **Los cuerpos los escribes tú**; la lógica va debajo.

```python
import re
from pathlib import Path

_WORD = re.compile(r"[A-Za-z0-9_]+")
_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")

STOPWORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "of", "to", "in",
    "on", "for", "and", "or", "with", "that", "this", "it", "as",
})


def split_identifier(token: str) -> list[str]:
    """Trocea un identificador en sus palabras (por '_' y por mayúsculas)."""


def tokenize(text: str) -> list[str]:
    """Lista de términos normalizados de `text`."""


def tokenize_source(text: str, file_path: str) -> list[str]:
    """Términos del chunk: los del texto más los de su ruta."""


def remove_stopwords(terms: list[str],
                     stopwords: frozenset[str] = STOPWORDS) -> list[str]:
    """Palanca: devuelve `terms` sin las palabras vacías."""
```

### La lógica detrás de cada una

**`_WORD`** (`[A-Za-z0-9_]+`) — el colador base: encuentra "palabras" formadas por letras, dígitos y guion bajo. Todo lo demás (signos de puntuación, espacios) separa. Nada de `á`/`ñ`: el corpus y las preguntas son en inglés; si algún día hiciera falta, sería una palanca más.

**`split_identifier(token)`** — de un identificador comprimido saca sus palabras. Primero parte por `_` (cubre `snake_case` y `SCREAMING_CASE`), y cada trozo lo vuelve a partir por `CamelCase` con la expresión `_CAMEL` (que detecta las fronteras `aB` y `ABCd`). Lo devuelve todo en minúsculas. Ejemplos: `max_model_len` → `max, model, len`; `MaxModelLen` → `max, model, len`.

**`tokenize(text)`** — el pipeline de la teoría `05`:

1. Encuentra cada palabra con `_WORD` y **la pasa a minúsculas** (normalización: `Server` = `server`).
2. **Conserva el identificador completo** y **añade sus partes** si aportan algo (`split_identifier`). Así se cubren los dos casos de la teoría `05`: una consulta que **cita** `max_model_len` literal, y una que **parafrasea** "model length".

Guardar el token entero **y** sus trozos es la clave en un corpus de código; es la mejora más rentable del tokenizador.

**`tokenize_source(text, file_path)`** — `tokenize(text)` **+** los términos de la **ruta**. Antes de tokenizar la ruta, se le quitan los prefijos comunes `data/` y `raw/` (con `Path.parts`): aparecen en **cada** archivo, así que no distinguen nada. **Por qué añadir la ruta:** las preguntas hablan de **temas** ("lora", "features") que muchas veces están en el nombre del archivo y **no** dentro del texto del chunk (teoría `05`). Ejemplo: `.../docs/features/lora.md` aporta `lora` y `features`.

**`remove_stopwords`** — devuelve la lista sin las palabras de `STOPWORDS`. Es una **palanca**, no parte del pipeline por defecto: en un corpus de código, limpiar de más borra señal (teoría `05`). Se deja disponible para **probarla** (misma disciplina que `07`: un cambio cada vez).

---

## 4. Reglas que este paso debe respetar

| Regla (teoría `05`) | Implementación |
|---|---|
| **Mismo tokenizador en los dos lados** | Chunk y pregunta acaban en `tokenize`; nadie más tokeniza |
| Normalizar a minúsculas | `raw.lower()` antes de guardar el término |
| Citar el identificador **y** parafrasear sus partes | Se añaden el token completo **y** las partes de `split_identifier` |
| Enriquecer lo indexable | `tokenize_source` inyecta los términos de la ruta (sin `data/raw/`) |
| No limpiar de más | Las stopwords son **opcionales**; el default las conserva |
| Señal discriminante se conserva | Identificadores raros (`max_model_len`) se mantienen enteros |

---

## 5. Caso de uso mínimo

```python
from src.tokenizer import tokenize, tokenize_source

tokenize("How to Configure the Server?")
# ["how", "to", "configure", "the", "server"]        (normalizado)

tokenize("call max_model_len here")
# [..., "max_model_len", "max", "model", "len", ...] (literal + partes)

tokenize_source("see below", "data/raw/vllm-0.10.1/docs/features/lora.md")
# ["see", "below", ..., "lora", "features", ...]     (texto + ruta)
```

La salida de `tokenize_source` es exactamente lo que el índice guardará por cada chunk (`05a`); la de `tokenize(query)` es lo que la búsqueda comparará contra él (`05b`).

---

## 6. Comprobación

`tests/test_tokenizer.py`. Qué demuestra cada test:

| Test | Qué demuestra |
|---|---|
| `test_basic_normalization` | Frase en lenguaje natural → términos en minúsculas, sin signos |
| `test_snake_case_is_split` | `max_model_len` produce el entero **y** sus partes |
| `test_camel_case_is_split` | `MaxModelLen` produce sus partes (fronteras de mayúsculas) |
| `test_same_terms_for_equal_text` | `Server`/`server` y `KV_Cache`/`kv_cache` dan los mismos términos |
| `test_path_terms_are_added` | La ruta aporta `lora` y `features` al chunk |
| `test_full_identifier_is_kept` | El identificador literal sobrevive en la lista |

El test que fija la regla de oro es `test_same_terms_for_equal_text`: si el chunk y la pregunta tokenizaran distinto, este fallo aparecería como "no encuentro nada" en la búsqueda.

---

## 7. Qué NO cubre esta parte

- **Ordenar y puntuar** los chunks (BM25) → `05b`.
- **Stemming y n-gramas** (teoría `05`, opcionales) → son palancas del bucle de mejora (`07`), no del tokenizador mínimo.
- **Aplicar stopwords por defecto** → aquí solo se deja la herramienta; probarla es decisión tuya.

## 8. Checklist

- [ ] `src/tokenizer.py` con `tokenize`, `split_identifier` y `tokenize_source`.
- [ ] El identificador completo **y** sus partes se indexan.
- [ ] Mismo tokenizador usado en chunks y preguntas.
- [ ] `uv run pytest` y `uv run make lint` en verde.

## 9. Tiempo estimado

**≈ 30 minutos.**
