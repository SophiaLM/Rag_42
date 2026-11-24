"""Tokenización de búsqueda: convierte texto en términos normalizados.

Es el único tokenizador del proyecto: lo usan los chunks (al indexar) y las
preguntas (al buscar), porque ambos lados deben tokenizarse exactamente igual.
"""
import re
from pathlib import Path


_WORD = re.compile(r"\w+")
_PATH_PREFIXES = frozenset({"data", "raw"})

STOPWORDS_EN = frozenset({
    "a", "an", "the", "is", "are", "was", "were",
    "of", "and", "or", "with"
})

STOPWORDS_ES = frozenset({
    "el", "la", "los", "las", "un", "una",
    "de", "del", "que", "para", "con"
})

STOPWORDS = STOPWORDS_EN | STOPWORDS_ES


def split_identifier(token: str) -> list[str]:
    """Trocea un identificador en sus palabras, por ``_`` y por mayúsculas.

    Detecta las fronteras con ``islower``, ``isupper`` e ``isdigit`` en lugar
    de una expresión regular, así que reconoce las letras con mayúscula y
    minúscula de cualquier idioma (tildes, ñ...).

    Args:
        token: Identificador, p. ej. ``max_model_len``, ``MaxModelLen`` o
            ``XMLParser``.

    Returns:
        Sus partes en minúsculas, p. ej. ``["max", "model", "len"]``. Si
        `token` está vacío o solo tiene ``_``, devuelve una lista vacía.
    """
    parts: list[str] = []

    for section in token.split("_"):
        start = 0

        for i in range(1, len(section)):
            prev, char = section[i - 1], section[i]
            lower_to_upper = (prev.islower() or prev.isdigit()) and char.isupper()
            acronym_end = (
                prev.isupper()
                and char.isupper()
                and i + 1 < len(section)
                and section[i + 1].islower()
            )

            if lower_to_upper or acronym_end:
                parts.append(section[start:i])
                start = i

        if section:
            parts.append(section[start:])

    return [word.lower() for word in parts]


def tokenize(text: str) -> list[str]:
    """Convierte `text` en una lista de términos normalizados.

    Cada palabra se pasa a minúsculas y se conserva entera; si es un
    identificador compuesto, se añaden además sus partes.

    Args:
        text: Texto de un chunk o de una pregunta.

    Returns:
        Lista de términos en minúsculas: cada palabra entera y, si es un
        identificador compuesto, también sus partes.
    """
    terms: list[str] = []

    for raw in _WORD.findall(text):
        normalized = raw.lower()

        terms.append(normalized)

        if "_" in raw or raw != normalized:
            parts = split_identifier(raw)

            if parts != [normalized]:
                terms.extend(parts)

    return terms


def tokenize_source(text: str, file_path: str) -> list[str]:
    """Devuelve los términos de un chunk: los del texto más los de su ruta.

    Args:
        text: Texto del chunk.
        file_path: Ruta de corpus del archivo del que sale el chunk.

    Returns:
        Términos del texto seguidos de los términos de la ruta, sin los
        prefijos ``data/`` y ``raw/``.
    """
    terms = tokenize(text)

    path_parts = list(Path(file_path).parts)
    while path_parts and path_parts[0] in _PATH_PREFIXES:
        path_parts.pop(0)

    path_terms = tokenize(" ".join(path_parts))

    return terms + path_terms


def remove_stopwords(
    terms: list[str],
    stopwords: frozenset[str] = STOPWORDS,
) -> list[str]:
    """Quita de `terms` las palabras vacías (palanca opcional).

    Args:
        terms: Términos ya tokenizados.
        stopwords: Palabras a descartar. Por defecto, inglés y español.

    Returns:
        Los términos que no están en `stopwords`, en el mismo orden.
    """
    return [term for term in terms if term not in stopwords]
