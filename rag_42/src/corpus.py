"""Lectura y direccionamiento de los archivos del corpus.

Este módulo es el único punto del proyecto que lee archivos del corpus y que
decide cómo se nombran. Mantener ambas decisiones en un solo sitio garantiza
que los offsets calculados al indexar coincidan con el texto que se recorta
después, y que `file_path` se escriba siempre igual.

Un fragmento del corpus se identifica con la terna
``(file_path, first_character_index, last_character_index)``:

* ``file_path`` es la ruta de corpus canónica (POSIX, relativa a la raíz del
  repositorio, p. ej. ``data/raw/vllm-0.10.1/docs/features/lora.md``).
* Los índices son offsets en **caracteres** (no en bytes) y definen el rango
  semiabierto ``[start, end)``.
"""
from collections.abc import Iterator
from pathlib import Path


def project_root() -> Path:
    """Devuelve la raíz del repositorio (el directorio que contiene `src/`).

    Returns:
        Ruta absoluta de la raíz del repositorio.
    """
    return Path(__file__).resolve().parents[1]


def to_corpus_path(path: Path, root: Path) -> str:
    """Devuelve la ruta de corpus canónica de `path` (POSIX, relativa a `root`).

    Args:
        path: Ruta del archivo, absoluta o relativa.
        root: Raíz del repositorio.

    Returns:
        Ruta de corpus, p. ej. ``data/raw/vllm-0.10.1/docs/features/lora.md``.

    Raises:
        ValueError: Si `path` no está dentro de `root`.
    """
    return (
        path.resolve()
        .relative_to(root.resolve())
        .as_posix()
    )


def read_text(path: Path) -> str:
    """Lee un archivo como texto UTF-8, sin traducir saltos de línea.

    Args:
        path: Ruta del archivo a leer.

    Returns:
        Contenido del archivo. Los bytes inválidos se sustituyen por `�`.

    Raises:
        OSError: Si el archivo no existe o no se puede leer.
    """
    data = path.read_bytes()
    try:
        return data.decode("utf-8")
    except UnicodeError:
        return data.decode("utf-8", errors="replace")


def extract_span(text: str, start: int, end: int) -> str:
    """Devuelve el fragmento de `text` en el rango ``[start, end)``.

    Args:
        text: Texto completo.
        start: Posición del primer carácter (incluido).
        end: Posición donde termina el fragmento (excluido).

    Returns:
        El fragmento ``text[start:end]``.

    Raises:
        ValueError: Si el rango no cumple ``0 <= start <= end <= len(text)``.

    Example:
        >>> extract_span("abcdef", 1, 3)
        'bc'
    """
    if not 0 <= start <= end <= len(text):
        raise ValueError(
            f"Invalid span [{start}, {end}) for text of length {len(text)}"
        )
    return text[start:end]


def resolve_corpus_path(corpus_path: str, root: Path) -> Path:
    """Devuelve la ruta real en disco de una ruta de corpus guardada.

    Args:
        corpus_path: Ruta de corpus, relativa a `root`.
        root: Raíz del repositorio.

    Returns:
        Ruta de `corpus_path` unida a `root`.
    """
    return root / corpus_path


def iter_corpus_files(
    root: Path,
    extensions: tuple[str, ...] = (".py", ".md", ".txt"),
) -> Iterator[Path]:
    """Entrega los archivos del corpus bajo `root`, en orden estable.

    Args:
        root: Carpeta del corpus donde buscar (no la raíz del proyecto).
        extensions: Extensiones aceptadas, con el punto inicial.

    Yields:
        Ruta de cada archivo del corpus, ordenadas.
    """
    files = [
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix in extensions
    ]
    yield from sorted(files)
