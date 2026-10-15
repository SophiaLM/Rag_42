# 04 — Tokenización

Mismo tokenizador para chunks y preguntas.

## 1. Código

`src/tokenizer.py`:
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
    parts: list[str] = []
    for piece in token.split("_"):
        if piece:
            parts.extend(_CAMEL.sub(" ", piece).split())
    return [p.lower() for p in parts]


def tokenize(text: str) -> list[str]:
    terms: list[str] = []
    for raw in _WORD.findall(text):
        token = raw.lower()
        terms.append(token)
        parts = split_identifier(raw)
        if parts != [token]:
            terms.extend(parts)
    return [t for t in terms if t]


def tokenize_source(text: str, file_path: str) -> list[str]:
    p = Path(file_path)
    parts = list(p.parts)
    while len(parts) > 3 and parts[0] in ("data", "raw"):
        parts = parts[1:]
    rel_parts = parts or list(p.parts)
    return tokenize(text) + tokenize("/".join(rel_parts))


def remove_stopwords(terms: list[str], stopwords: frozenset[str] = STOPWORDS) -> list[str]:
    return [t for t in terms if t not in stopwords]
```

## 2. Testers

`tests/test_tokenizer.py`:
```python
from src.tokenizer import tokenize, tokenize_source


def test_basic_normalization() -> None:
    assert tokenize("How to Configure the Server?") == [
        "how", "to", "configure", "the", "server",
    ]


def test_snake_case_is_split() -> None:
    assert tokenize("max_model_len") == ["max_model_len", "max", "model", "len"]


def test_camel_case_is_split() -> None:
    assert tokenize("MaxModelLen") == ["maxmodellen", "max", "model", "len"]


def test_same_terms_for_equal_text() -> None:
    assert tokenize("Server") == tokenize("server")
    assert tokenize("KV_Cache") == tokenize("kv_cache")


def test_path_terms_are_added() -> None:
    terms = tokenize_source("see below", "data/raw/vllm-0.10.1/docs/features/lora.md")
    assert "lora" in terms
    assert "features" in terms
    assert "see" in terms


def test_full_identifier_is_kept() -> None:
    assert "max_model_len" in tokenize("call max_model_len here")
```

## 3. Checklist

- [ ] `src/tokenizer.py` creado.
- [ ] Testers pasan.
- [ ] `make lint` pasa.

## 4. Tiempo estimado

**≈ 30 minutos.**
