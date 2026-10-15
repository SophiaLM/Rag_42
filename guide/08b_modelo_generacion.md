# 08b — Modelo y generación

Cargas `Qwen/Qwen3-0.6B` una vez y generas respuestas ancladas en el contexto.

## 1. Código

Añade a `src/generator.py`:

```python
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


def load_model(model_name: str = "Qwen/Qwen3-0.6B") -> tuple[Any, Any]:
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype="auto")
    model.eval()
    return model, tokenizer


def generate_answer(question: str, blocks: list[tuple[str, str]],
                    model: Any, tokenizer: Any, max_new_tokens: int = 256,
                    token_budget: int = 8000) -> str:
    while blocks:
        messages = build_messages(question, blocks)
        prompt = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True,
            enable_thinking=False,
        )
        input_ids = tokenizer(prompt, return_tensors="pt").input_ids
        if input_ids.shape[1] <= token_budget:
            break
        blocks = blocks[:-1]
    else:
        return "I could not find relevant context to answer this question."

    with torch.no_grad():
        output = model.generate(
            input_ids, max_new_tokens=max_new_tokens,
            do_sample=False, pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
        )
    new_tokens = output[0, input_ids.shape[1]:]
    return tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
```

> **`torch_dtype`, no `dtype`.** `torch_dtype="auto"` funciona en el rango que fijamos; el alias `dtype` solo existe en versiones muy recientes.
> **Tipado:** el subject exige `--disallow-untyped-defs`; usar `Any` para `model`/`tokenizer` es válido y evita peleas con `mypy`.
> **Greedy** (`do_sample=False`) = determinista. **`enable_thinking=False`**: si tu versión no lo soporta, limpia el bloque ` thinking...</think>`.
> El **presupuesto es en tokens**; si no cabe, suelta el menos relevante (el último).

## 2. Testers (lentos: cargan el modelo)

```python
def test_prompt_fits_budget() -> None:
    from src.generator import build_messages, load_model
    _, tokenizer = load_model()
    messages = build_messages("q", [("a.py", "x" * 100)])
    prompt = tokenizer.apply_chat_template(messages, tokenize=False,
                                           add_generation_prompt=True)
    ids = tokenizer(prompt).input_ids
    assert len(ids) < 32768


def test_no_context_is_honest() -> None:
    from src.generator import generate_answer, load_model
    model, tokenizer = load_model()
    answer = generate_answer("anything", [], model, tokenizer)
    assert "could not find" in answer.lower()
```

## 3. Checklist

- [ ] Modelo `Qwen/Qwen3-0.6B` cargado **una vez** por ejecución.
- [ ] Decodificación determinista con límite de tokens nuevos.
- [ ] Presupuesto medido en tokens y recortado si hace falta.
- [ ] Sin contexto, respuesta honesta.
- [ ] `make lint` pasa.

## 4. Tiempo estimado

**≈ 1–1.5 h** (la primera descarga del modelo es lo que más tarda).
