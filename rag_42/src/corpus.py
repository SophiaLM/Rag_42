from collections.abc import Iterator
from pathlib import Path


def project_root() -> Path:
    """Raíz del repositorio (el directorio que contiene `src/`)."""
    return Path(__file__).resolve().parents[1]


def read_text(path: Path) -> str:
    """Texto de `path` en UTF-8, sin traducir saltos de línea."""
    data = path.read_bytes()
    return data.decode("utf-8")


def to_corpus_path(path: Path, root: Path) -> str:
    """Ruta de corpus canónica (POSIX, relativa a la raíz) de `path`."""
    return (
        path.resolve()
        .relative_to(root.resolve())
        .as_posix()
    )


def resolve_corpus_path(corpus_path: str, root: Path) -> Path:
    """Ruta real en disco a partir de una ruta de corpus guardada."""


def extract_span(text: str, start: int, end: int) -> str:
    """Devuelve el texto de `text` en el rango [start, end)."""


def iter_corpus_files(
    root: Path,
    extensions: tuple[str, ...] = (".py", ".md", ".txt"),
) -> Iterator[Path]:
    """Recorre el corpus y produce sus archivos, en orden estable."""
