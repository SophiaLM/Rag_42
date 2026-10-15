# 01 — Corpus y offsets

Te centras solo en **leer correctamente el corpus** y trabajar con coordenadas.

## 1. Objetivo

Crear `src/corpus.py` con:
- `project_root() -> Path`
- `read_text(path: Path) -> str` (UTF-8, sin traducción de saltos; fallback ante bytes inválidos)
- `to_corpus_path(path: Path, root: Path) -> str`
- `resolve_corpus_path(corpus_path: str, root: Path) -> Path`
- `extract_span(text: str, start: int, end: int) -> str`
- `iter_corpus_files(root: Path, extensions: tuple[str, ...] = (".py", ".md", ".txt")) -> Iterator[Path]`

Usa convención **exclusiva** `[start, end)`.

> **`file_path` se compara *verbatim*.** El grader compara tu ruta con la de referencia carácter a carácter. Por eso `to_corpus_path` debe producir exactamente `data/raw/vllm-0.10.1/...` (sin `./` delante, con `/`, relativa a la raíz del proyecto). Un prefijo distinto **nunca** coincide.

## 2. Código

`src/corpus.py`:
```python
from collections.abc import Iterator
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_text(path: Path) -> str:
    try:
        return path.read_bytes().decode("utf-8")
    except UnicodeError:
        return path.read_bytes().decode("utf-8", errors="replace")


def to_corpus_path(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def resolve_corpus_path(corpus_path: str, root: Path) -> Path:
    return root / corpus_path


def extract_span(text: str, start: int, end: int) -> str:
    return text[start:end]


def iter_corpus_files(root: Path,
                      extensions: tuple[str, ...] = (".py", ".md", ".txt")) -> Iterator[Path]:
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix in extensions:
            yield path
```

> Incluye `.txt` (hay referencias a CMakeLists.txt). Puedes ampliar tras medir.

## 3. Testers

`tests/test_corpus.py`:
```python
from pathlib import Path

from src.corpus import (
    extract_span,
    project_root,
    read_text,
    to_corpus_path,
)


ROOT = project_root()


def test_extract_matches_reference_span() -> None:
    rel = "data/raw/vllm-0.10.1/docs/features/lora.md"
    text = read_text(ROOT / rel)
    span = extract_span(text, 4695, 6098)
    assert span.startswith("### Using API Endpoints")
    assert len(span) == 6098 - 4695


def test_offsets_are_characters_not_bytes() -> None:
    text = "ábc"
    assert len(text) == 3
    assert extract_span(text, 0, 3) == "ábc"


def test_corpus_path_is_posix_and_relative() -> None:
    p = ROOT / "data/raw/vllm-0.10.1/docs/features/lora.md"
    out = to_corpus_path(p, ROOT)
    assert out == "data/raw/vllm-0.10.1/docs/features/lora.md"
    assert not out.startswith("./")
    assert "\\" not in out


def test_reading_is_stable() -> None:
    rel = "data/raw/vllm-0.10.1/docs/features/lora.md"
    a = read_text(ROOT / rel)
    b = read_text(ROOT / rel)
    assert a == b
```

## 4. Checklist

- [ ] `src/corpus.py` implementado.
- [ ] Tests pasan.
- [ ] `make lint` pasa.

## 5. Tiempo estimado

**≈ 30 minutos.**
