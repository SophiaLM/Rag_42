"""Divide archivos del corpus en chunks con cobertura total y tamaño acotado.

Cada chunk guarda solo su ubicación ``(file_path, start, end)`` dentro de un
archivo, no una copia del texto. Los archivos ``.py`` se cortan por
definiciones y los demás por títulos de Markdown; después se agrupan los
segmentos pequeños y se parten los que superan ``max_chunk_size``.
"""
import ast
import io
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    """Representa un fragmento del corpus mediante su ubicación.

    Attributes:
        file_path: Ruta canónica del archivo de origen.
        start: Offset del primer carácter incluido.
        end: Offset del primer carácter excluido.
    """
    file_path: str
    start: int
    end: int

    @property
    def length(self) -> int:
        """Devuelve cuántos caracteres ocupa el chunk."""
        return self.end - self.start


def line_start_offsets(text: str) -> list[int]:
    """Devuelve el offset donde empieza cada línea de `text`.

    El índice ``i`` de la lista corresponde a la línea ``i + 1``, que es el
    número de línea que usa `ast`. Los saltos de línea se conservan para que
    los offsets sumen exactamente la longitud del texto.

    Args:
        text: Texto completo.

    Returns:
        Lista de offsets de inicio, uno por línea. Si `text` está vacío,
        devuelve una lista vacía.
    """
    lines = io.StringIO(text, newline="").readlines()
    offsets = []
    current_offset = 0

    for line in lines:
        offsets.append(current_offset)
        current_offset += len(line)
    return offsets


def python_segments(text: str) -> list[tuple[int, int]]:
    """Divide el código Python en segmentos según sus definiciones top-level.

    Cada función, función asíncrona o clase forma un segmento; también se
    incluyen los tramos de código de módulo que quedan entre ellas. Los
    decoradores se incorporan a la definición. Si el texto no se puede
    analizar, se devuelve el archivo completo como un único segmento.

    Args:
        text: Código fuente Python.

    Returns:
        Lista de rangos ``(start, end)`` contiguos que cubren todo el texto.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return [(0, len(text))]

    offsets = line_start_offsets(text)
    segments = []
    cursor = 0

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.decorator_list:
                start_line = node.decorator_list[0].lineno
            else:
                start_line = node.lineno

            start_offset = offsets[start_line - 1]
            end_line = node.end_lineno or node.lineno

            if end_line < len(offsets):
                end_offset = offsets[end_line]
            else:
                end_offset = len(text)

            if cursor < start_offset:
                segments.append((cursor, start_offset))

            segments.append((start_offset, end_offset))
            cursor = end_offset

    if cursor < len(text):
        segments.append((cursor, len(text)))

    if not segments and text:
        segments.append((0, len(text)))

    return segments


def markdown_segments(text: str) -> list[tuple[int, int]]:
    """Divide un documento Markdown en secciones según sus títulos.

    El texto anterior al primer título se devuelve como un segmento propio. Si
    no hay títulos, el documento entero forma un único segmento.

    Args:
        text: Contenido Markdown o texto plano.

    Returns:
        Lista de rangos ``(start, end)`` contiguos que cubren todo el texto.
    """
    matches = list(re.finditer(r"^#{1,6}\s", text, re.MULTILINE))

    if not matches:
        return [(0, len(text))] if text else []

    segments = []
    first_start = matches[0].start()

    if first_start > 0:
        segments.append((0, first_start))

    for i, match in enumerate(matches):
        start = match.start()
        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(text)
        segments.append((start, end))

    return segments


def split_large(
    text: str,
    start: int,
    end: int,
    max_chunk_size: int
) -> list[tuple[int, int]]:
    """Parte un rango grande en trozos que no superan `max_chunk_size`.

    Antes de cortar por el límite duro, intenta terminar en el último párrafo
    (``\\n\\n``) que quepa en la ventana.

    Args:
        text: Texto completo.
        start: Offset donde empieza el rango.
        end: Offset donde termina el rango (excluido).
        max_chunk_size: Tamaño máximo de cada trozo.

    Returns:
        Lista de rangos ``(start, end)`` contiguos que cubren ``[start, end)``.
    """
    segments = []
    cursor = start

    while cursor < end:
        limit = min(cursor + max_chunk_size, end)
        if limit == end:
            cut = end
        else:
            cut = text.rfind("\n\n", cursor, limit)
            if cut != -1:
                cut += 2
            else:
                cut = limit
        segments.append((cursor, cut))
        cursor = cut

    return segments


def pack_segments(
    segments: list[tuple[int, int]],
    text: str,
    max_chunk_size: int, overlap: int = 0
) -> list[tuple[int, int]]:
    """Agrupa segmentos vecinos en chunks sin superar `max_chunk_size`.

    Los segmentos que caben se funden en orden; los que por sí solos superan
    el techo se parten con `split_large`. El valor de `overlap` permite repetir
    caracteres del final de un chunk al principio del siguiente.

    Args:
        segments: Rangos ``(start, end)`` ordenados.
        text: Texto completo.
        max_chunk_size: Tamaño máximo de cada chunk.
        overlap: Número de caracteres que se solapan entre chunks consecutivos.

    Returns:
        Lista de rangos ``(start, end)`` en el mismo orden de entrada.
    """
    chunks = []
    current_start = None
    current_end = 0  # solo se lee si current_start no es None

    for start, end in segments:
        segment_size = end - start

        if segment_size > max_chunk_size:
            if current_start is not None:
                chunks.append((current_start, current_end))
                current_start = None
                current_end = 0

            chunks.extend(split_large(text, start, end, max_chunk_size))
            continue

        if current_start is None:
            current_start = start
            current_end = end

        elif end - current_start <= max_chunk_size:
            current_end = end

        else:
            chunks.append((current_start, current_end))

            current_start = max(
                current_start,
                start - overlap,
                end - max_chunk_size
            )
            current_end = end

    if current_start is not None:
        chunks.append((current_start, current_end))

    return chunks


def chunk_file(
    file_path: str,
    text: str,
    max_chunk_size: int,
    overlap: int = 0
) -> list[Chunk]:
    """Devuelve los chunks de un archivo según su formato y tamaño.

    Los archivos ``.py`` se segmentan por definiciones y el resto por títulos
    de Markdown; después se agrupan y se parten para respetar
    `max_chunk_size`.

    Args:
        file_path: Ruta canónica del archivo.
        text: Contenido completo del archivo.
        max_chunk_size: Tamaño máximo de cada chunk.
        overlap: Número de caracteres que se solapan entre chunks consecutivos.

    Returns:
        Lista de `Chunk` que cubre todo el texto en orden.

    Raises:
        ValueError: Si `max_chunk_size` es menor que 1.
    """
    if max_chunk_size < 1:
        raise ValueError(f"max_chunk_size must be >= 1, got {max_chunk_size}")

    if file_path.endswith(".py"):
        segments = python_segments(text)
    else:
        segments = markdown_segments(text)

    ranges = pack_segments(
        segments,
        text,
        max_chunk_size,
        overlap
    )

    chunks = [
        Chunk(file_path, start, end)
        for start, end in ranges
    ]

    return chunks
