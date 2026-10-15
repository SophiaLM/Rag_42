# 08a — Contexto y prompt

Ya tienes las fuentes correctas. Antes de generar, reconstruyes el **texto** de esos fragmentos y armas el **prompt** con grounding.

## 1. Dependencias (solo ahora)

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

> `torch` + los pesos suman varios GB; descárgalos desde una ubicación con espacio. El modelo se cachea.

## 2. Código

`src/generator.py` (parte sin modelo):
```python
from pathlib import Path

from src.corpus import extract_span, read_text, resolve_corpus_path
from src.models import MinimalSource

SYSTEM = (
    "You answer questions about a codebase. Use ONLY the provided context. "
    "If the context does not contain the answer, say you do not know. "
    "Answer in 2-4 sentences and mention the relevant file or function."
)


def build_context(sources: list[MinimalSource], root: Path) -> list[tuple[str, str]]:
    seen: set[str] = set()
    blocks: list[tuple[str, str]] = []
    for source in sources:
        path = resolve_corpus_path(source.file_path, root)
        try:
            text = read_text(path)
        except (FileNotFoundError, UnicodeDecodeError):
            continue
        snippet = extract_span(text, source.first_character_index,
                               source.last_character_index)
        if snippet and snippet not in seen:
            seen.add(snippet)
            blocks.append((source.file_path, snippet))
    return blocks


def build_messages(question: str, blocks: list[tuple[str, str]]) -> list[dict]:
    context = "\n\n".join(f"[{i}] {label}\n{text}"
                          for i, (label, text) in enumerate(blocks, 1))
    user = f"Context:\n{context}\n\nQuestion: {question}"
    return [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": user}]
```

> Relee siempre con **`read_text`** (la misma lectura que al indexar). Etiqueta cada fragmento con su ruta y deja la pregunta **al final**.

## 3. Testers (rápidos, sin modelo)

`tests/test_generator.py`:
```python
from src.corpus import project_root
from src.generator import build_context
from src.models import MinimalSource

ROOT = project_root()


def test_context_labels_and_dedup() -> None:
    s = MinimalSource(file_path="data/raw/vllm-0.10.1/docs/features/lora.md",
                      first_character_index=4695, last_character_index=6098)
    blocks = build_context([s, s], ROOT)
    assert len(blocks) == 1
    label, text = blocks[0]
    assert label.endswith("lora.md")
    assert text.startswith("### Using API Endpoints")
```

## 4. Checklist

- [ ] Dependencias `transformers` y `torch` añadidas.
- [ ] `build_context` y `build_messages` implementados; dedup y rutas.
- [ ] `make lint` pasa.

## 5. Tiempo estimado

**≈ 30 minutos.**
