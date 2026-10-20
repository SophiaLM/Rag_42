# 08a — Contexto y prompt

Llegaste al final del pipeline: tienes las fuentes correctas. Pero **no traen el texto** — recuerda (`03`, `05c`) que una fuente es solo una **ubicación**: `file_path` + dos offsets. Antes de generar hay que **releer** cada archivo, extraer su fragmento y **armar el prompt**. Esta es la etapa de **aumentar (augmentation)** de RAG (teoría `08`): convertir ubicaciones en contexto que el modelo pueda leer.

Es el momento de añadir las dependencias del modelo. En `00a` las dejamos fuera a propósito ("no cargues el modelo hasta que lo necesites"); ese "ahora" es ahora.

---

## 1. Qué vas a construir

Las dependencias en `pyproject.toml` y la **parte sin modelo** de `src/generator.py`:

- `SYSTEM` — el string de rol y reglas (el *grounding*).
- `build_context(sources, root)` — relee y prepara los fragmentos.
- `build_messages(question, blocks)` — arma los mensajes con el formato de conversación.

**Por qué un módulo `generator.py`:** generar (**augment + generar**) es una fase distinta de buscar. `index.py` puntúa; `generator.py` reconstruye texto y habla con el modelo. Separarlos mantiene `index.py` libre de `torch`.

**Dónde vive cada cosa:**

| Símbolo | Ubicación | Por qué ahí |
|---|---|---|
| `SYSTEM` | `generator.py` | Las reglas del prompt: pieza de la fase de generación |
| `build_context` | `generator.py` | Relectura + selección + dedup de fragmentos |
| `build_messages` | `generator.py` | Formato del prompt |

---

## 2. Dependencias (solo ahora)

Añade a `pyproject.toml`:

```toml
dependencies = [
    "pydantic>=2",
    "fire",
    "tqdm",
    "transformers>=4.51",
    "torch",
]
```

> `torch` + los pesos suman varios GB; descárgalos desde una ubicación con espacio. El modelo se **cachea**: la primera ejecución tarda, las siguientes no. `uv sync` es lo único que corre el evaluador, así que estas dependencias deben estar aquí, no instaladas a mano.

---

## 3. Las piezas que necesitas

Firmas (con docstring) y la constante del prompt. **La lógica**, debajo.

```python
from pathlib import Path

from src.corpus import extract_span, read_text, resolve_corpus_path
from src.models import MinimalSource

SYSTEM = (
    "You answer questions about a codebase. Use ONLY the provided context. "
    "If the context does not contain the answer, say you do not know. "
    "Answer in 2-4 sentences and mention the relevant file or function."
)


def build_context(sources: list[MinimalSource],
                  root: Path) -> list[tuple[str, str]]:
    """Relee cada fuente, la recorta y deduplica; devuelve pares (etiqueta, texto)."""


def build_messages(question: str,
                   blocks: list[tuple[str, str]]) -> list[dict]:
    """Arma los mensajes [system, user] con el contexto etiquetado y la pregunta al final."""
```

### La lógica detrás de cada una

**`SYSTEM`** — las reglas del *grounding* (teoría `08`): *usa solo el contexto*, *si no está, dilo*, *sé breve, cita el archivo o la función*. Es la instrucción que más reduce las alucinaciones y **no cuesta tocar el modelo**: cambiarla es una palanca de la fase de mejora. El subject exige documentar la estrategia de prompt, y este string **es** esa estrategia.

**`build_context(sources, root)`** — de ubicaciones a texto, con tres pasos que importan:

1. Resolver la ruta real con `resolve_corpus_path(source.file_path, root)` (`01`) y **releer** con `read_text` (`01`).
2. **Releer con la misma función que al indexar.** Esta es la condición de oro de la teoría `08`: si al generar usas otra forma de leer (otra codificación, traducción de saltos de línea), los offsets **se desplazan** y extraes un fragmento que no es el que encontraste. Por eso `read_text`, no un `open().read()`.
3. Recortar con `extract_span(text, first, last)` (`01`) y **deduplicar**: dos fuentes pueden caer en el mismo texto; repetirlo no aporta y gasta contexto.

**Manejo de fuentes muertas:** si el archivo ya no existe (`FileNotFoundError`) o no decodifica (`UnicodeDecodeError`), **se salta** esa fuente y se sigue. Con un fragmento que falta **mejor una respuesta pobre que un `Traceback`** (teoría `08`, casos degenerados).

**La forma de la salida — `(etiqueta, texto)`** — y **por qué etiqueta**: cada fragmento se marca con **su** `file_path`, para que el modelo pueda citar un origen concreto y tú puedas trazar de dónde salió cada respuesta (teoría `08`: etiquetar cada fragmento).

**`build_messages(question, blocks)`** — arma la conversación respetando el orden que pide la teoría `08`:

- El **contexto etiquetado** (`[1] ruta\n texto`), con cada fragmento numerado.
- La **pregunta al final**. **Por qué al final:** los modelos pequeños atienden mejor al **principio y al final** del prompt, y lo último que ven antes de escribir es la pregunta.
- Un mensaje `system` con `SYSTEM` y un mensaje `user` con contexto+pregunta. **No** se aplica aquí el *chat template* — eso es cosa del tokenizador en `08b`.

> Aún **no** hay recorte por presupuesto de tokens: `build_messages` solo arma el texto. Recortar si no cabe es responsabilidad de `08b`, que sí tiene el tokenizador para contar.

---

## 4. Reglas que este paso debe respetar

| Regla (teoría `08`) | Implementación |
|---|---|
| La respuesta se ancla en el contexto (*grounding*) | `SYSTEM` prohíbe inventar y admite "no lo sé" |
| Releer con la **misma** política que al indexar | `build_context` usa `read_text` (`01`) |
| Etiquetar cada fragmento con su origen | Bloques `(file_path, texto)` numerados |
| La pregunta, **al final** | `build_messages` la pone tras el contexto |
| Limpiar y **deduplicar** | El mismo texto no entra dos veces |
| Una fuente muerta no rompe nada | `FileNotFoundError`/`UnicodeDecodeError` → se salta |

---

## 5. Caso de uso mínimo

```python
from src.corpus import project_root
from src.generator import build_context, build_messages
from src.models import MinimalSource

s = MinimalSource(file_path="data/raw/vllm-0.10.1/docs/features/lora.md",
                  first_character_index=4695, last_character_index=6098)
blocks = build_context([s, s], project_root())   # la duplicada se descarta -> 1 bloque
label, text = blocks[0]
text.startswith("### Using API Endpoints")       # True
messages = build_messages("How do I load a LoRA adapter?", blocks)
# messages[0]["role"] == "system"; la pregunta queda al final del user
```

---

## 6. Comprobación

`tests/test_generator.py` — **rápido, sin cargar el modelo**. Qué demuestra:

| Test | Qué demuestra |
|---|---|
| `test_context_labels_and_dedup` | Dos fuentes idénticas producen **un** bloque; la etiqueta termina en `lora.md` y el texto empieza por `### Using API Endpoints` |

```python
def test_context_labels_and_dedup() -> None:
    s = MinimalSource(file_path="data/raw/vllm-0.10.1/docs/features/lora.md",
                      first_character_index=4695, last_character_index=6098)
    blocks = build_context([s, s], ROOT)
    assert len(blocks) == 1
    label, text = blocks[0]
    assert label.endswith("lora.md")
    assert text.startswith("### Using API Endpoints")
```

Este test es valioso porque cubre a la vez **el dedup**, **la etiqueta** y —sobre todo— que **releer de nuevo con los offsets guardados reconstruye el fragmento correcto**. Si `read_text` cambiara de política, este test caería.

---

## 7. Qué NO cubre esta parte

- **Cargar el modelo y generar** texto → `08b`.
- **Recortar por tokens** si el contexto no cabe → `08b` (tiene el tokenizador).
- **Responder un dataset entero y la CLI** → `08c`.

## 8. Checklist

- [ ] Dependencias `transformers` y `torch` añadidas a `pyproject.toml`.
- [ ] `build_context` relee con `read_text`, recorta y **deduplica**; salta fuentes muertas.
- [ ] `build_messages` etiqueta el contexto y deja la pregunta **al final**.
- [ ] `uv run pytest` y `uv run make lint` en verde.

## 9. Tiempo estimado

**≈ 30 minutos.**
