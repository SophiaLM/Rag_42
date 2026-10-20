# 08b — Modelo y generación

El prompt está listo (`08a`). Ahora cargas el modelo **una sola vez** y le pides que **continúe** el texto: esa continuación es la respuesta. Con esto el ciclo de RAG queda cerrado — **recuperar → aumentar → generar** (teoría `01`).

Usamos `Qwen/Qwen3-0.6B`: 600 millones de parámetros corren bien en CPU. Es pequeño y tiene los límites de la teoría `08` (se pierde con contextos largos, puede divagar, escribe "borradores de pensamiento"), así que las decisiones de **decodificación** importan tanto como el prompt.

---

## 1. Qué vas a construir

Dos funciones en `src/generator.py`:

- `load_model(model_name)` — carga tokenizador y modelo, **una vez** por ejecución.
- `generate_answer(question, blocks, model, tokenizer, ...)` — arma el prompt final, lo recorta si no cabe y genera.

**Dónde vive cada cosa:**

| Símbolo | Ubicación | Por qué ahí |
|---|---|---|
| `load_model` | `generator.py` | Carga del modelo: conocimiento de la fase de generación |
| `generate_answer` | `generator.py` | El puente prompt → texto |

---

## 2. Las piezas que necesitas

Firmas (con docstring). **La lógica**, debajo.

```python
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


def load_model(model_name: str = "Qwen/Qwen3-0.6B") -> tuple[Any, Any]:
    """Carga tokenizador y modelo (una vez); devuelve (model, tokenizer)."""


def generate_answer(question: str, blocks: list[tuple[str, str]],
                    model: Any, tokenizer: Any, max_new_tokens: int = 256,
                    token_budget: int = 8000) -> str:
    """Genera la respuesta a `question` apoyada en `blocks`."""
```

### La lógica detrás de cada una

**`load_model`** — tres pasos:

1. `AutoTokenizer.from_pretrained(model_name)` y `AutoModelForCausalLM.from_pretrained(model_name, torch_dtype="auto")`.
2. `model.eval()` — modo inferencia (desactiva el *dropout*, necesario para que la salida sea estable).
3. Devolver `(model, tokenizer)`.

**Nota de tipado:** el subject exige `--disallow-untyped-defs` (`V.1`); anotar `model`/`tokenizer` como `Any` es **correcto** y evita pelearte con `mypy`. **`torch_dtype`, no `dtype`:** el alias `dtype` solo existe en versiones muy recientes de `transformers`; `torch_dtype="auto"` funciona en el rango que fijamos. **Sobre usar otro modelo:** el subject (V.4) permite otros modelos **solo si todo sigue funcionando con `Qwen/Qwen3-0.6B`**; el nombre del modelo es un parámetro (`model_name`) con ese default, así que puedes probar alternativas sin romper el contrato.

**`generate_answer`** — el "generar", en orden. Lo importante es el **bucle de presupuesto**:

```text
mientras blocks:
    prompt = aplicar plantilla de chat a build_messages(question, blocks)
    si el prompt cabe en token_budget: romper
    blocks = blocks[:-1]          # suelta el menos relevante (el último)
si blocks se vació:  devolver el texto honesto (inglés, p. ej. "I could not find relevant context to answer the question.")
generar (greedy) y decodificar SOLO los tokens nuevos
```

1. **Aplicar la plantilla de conversación.** El modelo no quiere texto suelto: quiere mensajes con roles envueltos en **marcas especiales suyas** (teoría `08`). `tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)` las pone por ti.
2. **Recortar si no cabe.** La ventana de contexto se mide en **tokens, no en caracteres** (teoría `08`). Cuentas los tokens del prompt y, si exceden `token_budget`, **sueltas el último bloque** (el menos relevante) y rearmas — hasta que quepa o no queden bloques. Si te quedas sin bloques, devuelves una respuesta **honesta** en inglés (p. ej. "I could not find relevant context to answer the question.") en vez de dejar al modelo inventar (teoría `08`, casos degenerados). Mantén el texto en inglés para que case con `SYSTEM` (`08a`) y con el test de `test_no_context_is_honest`.
3. **Generar solo los tokens nuevos.** Tokenizas el prompt (`return_tensors="pt"`), llamas a `model.generate(...)` dentro de `with torch.no_grad()` (sin gradientes: la inferencia no los necesita) y decodificas **únicamente** los tokens **después** de la longitud del prompt. **Por qué recortar el prompt de la salida:** `generate` devuelve prompt + continuación; sin cortar, la respuesta repetiría todo el contexto.

**Las decisiones de decodificación** (teoría `08`: en una tarea factual, estabilidad y concisión, no creatividad):

| Decisión | Elección | Por qué |
|---|---|---|
| Cómo elegir el siguiente token | **Greedy** (`do_sample=False`) | Determinista y reproducible |
| Cuánto puede extenderse | `max_new_tokens=256` | Acota la divagación y el tiempo |
| Token de relleno | `pad_token_id = pad or eos` | Evita avisos/errores si no hay `pad_token` |
| Razonamiento interno | `enable_thinking=False` | El "borrador de pensamiento" gasta tokens y ensucia la salida (teoría `08`) |

> Si tu versión de `transformers` no acepta `enable_thinking`, no lo pases y **limpia** el bloque ` thinking...</think>` de la salida decodificada. Cualquiera de las dos vías cumple la teoría `08`.
>
> Y no lo olvides: `generate_answer` **solo produce texto**. Envolverlo en `MinimalAnswer` lo hace **tu código** (`08c`). Un modelo de 0.6B falla produciendo JSON válido; es más robusto pedirle texto y encajarlo tú (teoría `08`).

---

## 3. Reglas que este paso debe respetar

| Regla (teoría `08`) | Implementación |
|---|---|
| Determinista en tareas factuales | Greedy (`do_sample=False`) |
| Acotar la longitud de la respuesta | `max_new_tokens` |
| Presupuesto medido en **tokens** | Se cuenta el prompt y se recorta si excede `token_budget` |
| Contexto largo → recortar, no petar | El bucle suelta el bloque menos relevante |
| Razonamiento interno controlado | `enable_thinking=False` (o limpiar ` thinking`) |
| **Solo texto**, sin JSON | La estructura la arma `08c` |

---

## 4. Caso de uso mínimo

```python
from src.generator import build_context, generate_answer, load_model
from src.index import InvertedIndex, search
from src.corpus import project_root

root = project_root()
idx = InvertedIndex.load(root / "data/processed")
model, tokenizer = load_model()                       # UNA vez por ejecución

q = "How to dynamically load a LoRA adapter?"
blocks = build_context(search(idx, q, k=5), root)
print(generate_answer(q, blocks, model, tokenizer))
```

---

## 5. Comprobación

`tests/test_generator.py`, los tests que **cargan el modelo** (lentos; dilo en el README). Qué demuestra cada uno:

| Test | Qué demuestra |
|---|---|
| `test_prompt_fits_budget` | El prompt armado con la plantilla no supera `token_budget`; si un contexto no cabe, el bucle suelta bloques hasta que quepa |
| `test_no_context_is_honest` | Sin contexto, la respuesta contiene "could not find" — no alucina |

```python
def test_no_context_is_honest() -> None:
    from src.generator import generate_answer, load_model
    model, tokenizer = load_model()
    answer = generate_answer("anything", [], model, tokenizer)
    assert "could not find" in answer.lower()
```

El segundo es el que protege el requisito de *grounding*: un sistema RAG honesto **admite** cuando no sabe.

---

## 6. Qué NO cubre esta parte

- **Responder un dataset entero** (`answer`, `answer_dataset`) y la CLI → `08c`.
- **Mejorar la calidad del prompt**: cambia `SYSTEM` (`08a`) y vuelve a medir; esta función no lo decide.

## 7. Checklist

- [ ] `Qwen/Qwen3-0.6B` cargado **una vez** por ejecución.
- [ ] Decodificación determinista con límite de tokens nuevos.
- [ ] Presupuesto medido en **tokens** y recortado si no cabe.
- [ ] Sin contexto, respuesta honesta.
- [ ] `uv run pytest` y `uv run make lint` en verde.

## 8. Tiempo estimado

**≈ 1–1.5 h** (la primera descarga del modelo es lo que más tarda).
