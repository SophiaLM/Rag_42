import json
import math

from collections import Counter
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path

from tqdm import tqdm

from src.chunk import Chunk, chunk_file
from src.corpus import (
    extract_span,
    iter_corpus_files,
    project_root,
    read_text,
    to_corpus_path,
)
from src.models import MinimalSource
from src.tokenizer import tokenize, tokenize_source

MAX_SOURCE_LEN = 2000


def _write_json(path: Path, data: object) -> None:
    """Escribe JSON en un temporal y lo renombra al terminar.

    Así un fallo a mitad de escritura no deja un fichero truncado con el
    nombre definitivo.
    """
    temp_path = path.with_name(path.name + ".tmp")
    with temp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    temp_path.replace(path)


@dataclass
class InvertedIndex:
    """Índice invertido para recuperación de información basado en BM25.

    Attributes:
        chunks (list[Chunk]): Lista de fragmentos (chunks) indexados.
        postings (dict[str, dict[int, int]]): Diccionario que mapea cada
            término a un diccionario de IDs de documento y sus frecuencias.
        doc_lengths (list[int]): Longitud (número de términos) de cada documento.
        k1 (float): Parámetro k1 de BM25: saturación de la frecuencia del término.
        b (float): Parámetro b de BM25: penalización por longitud del documento.
    """

    chunks: list[Chunk] = field(default_factory=list)
    postings: dict[str, dict[int, int]] = field(default_factory=dict)
    doc_lengths: list[int] = field(default_factory=list)
    k1: float = 1.5
    b: float = 0.75

    @property
    def n_docs(self) -> int:
        """Calcula el número total de documentos indexados.

        Returns:
            int: Cantidad de chunks en el índice.
        """
        return len(self.chunks)

    @property
    def avg_doc_len(self) -> float:
        """Calcula la longitud media de los documentos indexados.

        Returns:
            float: Longitud promedio de los documentos, o 0.0 si no hay ninguno.
        """
        if not self.doc_lengths:
            return 0.0

        return sum(self.doc_lengths) / len(self.doc_lengths)

    def doc_frequency(self, term: str) -> int:
        """Calcula en cuántos documentos aparece un término específico (df de BM25).

        Args:
            term (str): Término del que se quiere la frecuencia de documentos.

        Returns:
            int: Número de documentos que contienen el término.
        """
        return len(self.postings.get(term, {}))

    def save(self, directory: Path) -> None:
        """Escribe el índice en `chunks.json` e `index.json`.

        Args:
            directory: Directorio de destino; se crea si no existe.
        """
        directory.mkdir(parents=True, exist_ok=True)

        chunks_data = [asdict(chunk) for chunk in self.chunks]
        serialized_postings = {
            term: {str(doc_id): freq for doc_id, freq in doc_freqs.items()}
            for term, doc_freqs in self.postings.items()
        }
        index_data = {
            "postings": serialized_postings,
            "doc_lengths": self.doc_lengths,
            "k1": self.k1,
            "b": self.b,
        }

        _write_json(directory / "chunks.json", chunks_data)
        _write_json(directory / "index.json", index_data)

    @classmethod
    def load(cls, directory: Path) -> "InvertedIndex":
        """Reconstruye el índice guardado en `directory`.

        Args:
            directory: Directorio con `chunks.json` e `index.json`.

        Returns:
            InvertedIndex: Índice reconstruido, equivalente al guardado.

        Raises:
            OSError: Si no se pueden leer los ficheros.
            json.JSONDecodeError: Si alguno no contiene JSON válido.
            ValueError: Si los datos guardados no son coherentes con el
                esquema del índice.
            TypeError: Si la estructura de chunks o postings no es la esperada.
        """
        with (directory / "chunks.json").open("r", encoding="utf-8") as f:
            chunks_data = json.load(f)
        with (directory / "index.json").open("r", encoding="utf-8") as f:
            index_data = json.load(f)

        if not isinstance(chunks_data, list):
            raise ValueError("chunks.json debe contener una lista de chunks")
        if not isinstance(index_data, dict):
            raise ValueError("index.json debe contener un objeto JSON")

        required = {"postings", "doc_lengths", "k1", "b"}
        missing = required - index_data.keys()
        if missing:
            raise ValueError(
                f"index.json falta las claves: {sorted(missing)}"
            )

        chunks = [Chunk(**item) for item in chunks_data]

        doc_lengths = index_data["doc_lengths"]
        if not isinstance(doc_lengths, list) or not all(
            isinstance(length, int) for length in doc_lengths
        ):
            raise ValueError("doc_lengths debe ser una lista de enteros")
        if len(doc_lengths) != len(chunks):
            raise ValueError(
                "doc_lengths y chunks tienen longitudes distintas: "
                f"{len(doc_lengths)} != {len(chunks)}"
            )

        raw_postings = index_data["postings"]
        if not isinstance(raw_postings, dict):
            raise ValueError("postings debe ser un objeto JSON")

        postings: dict[str, dict[int, int]] = {}
        for term, doc_freqs in raw_postings.items():
            postings[term] = {
                int(doc_id): freq for doc_id, freq in doc_freqs.items()
            }

        k1 = index_data["k1"]
        b = index_data["b"]
        if not isinstance(k1, (int, float)) or not isinstance(b, (int, float)):
            raise ValueError("k1 y b deben ser números")

        return cls(
            chunks=chunks,
            postings=postings,
            doc_lengths=doc_lengths,
            k1=k1,
            b=b,
        )


def build_index(
    entries: Iterable[tuple[Chunk, list[str]]],
    k1: float = 1.5,
    b: float = 0.75
) -> InvertedIndex:
    """Construye un índice invertido a partir de chunks y sus términos.

    Args:
        entries (Iterable[tuple[Chunk, list[str]]]): Pares (Chunk, términos
            normalizados).
        k1 (float, optional): cuánto importa repetir una palabra.
        b (float, optional): cuánto penalizamos un documento largo.

    Returns:
        InvertedIndex: Índice poblado con los chunks, las frecuencias de
        términos y las longitudes de los documentos.
    """

    index = InvertedIndex(k1=k1, b=b)

    for doc_id, (chunk, terms) in enumerate(entries):
        term_counts = Counter(terms)
        index.chunks.append(chunk)
        index.doc_lengths.append(sum(term_counts.values()))
        for term, frequency in term_counts.items():
            if term not in index.postings:
                index.postings[term] = {}

            index.postings[term][doc_id] = frequency

    return index


def bm25_score(
    index: InvertedIndex,
    query_terms: list[str],
    doc_id: int,
    *,
    avg_dl: float | None = None,
) -> float:
    """Calcula la relevancia de un documento respecto a una consulta usando BM25.

    Tiene en cuenta la frecuencia de las palabras, su importancia dentro
    del conjunto de documentos y la longitud del documento.

    Args:
        index: Índice invertido con la información de los documentos.
        query_terms: Palabras de la consulta previamente tokenizadas.
        doc_id: Identificador del documento que se quiere evaluar.
        avg_dl: Longitud media de los documentos. Si no se proporciona,
            se utiliza la longitud media almacenada en el índice.

    Returns:
        Puntuación BM25 del documento. Cuanto mayor sea, más relevante
        será el documento para la consulta. Devuelve 0.0 si no hay datos
        suficientes o el documento no es válido.
    """
    n_docs = index.n_docs

    if n_docs == 0 or not query_terms:
        return 0.0

    if not (0 <= doc_id < n_docs):
        return 0.0

    effective_avg_dl = index.avg_doc_len if avg_dl is None else avg_dl
    if effective_avg_dl <= 0.0:
        effective_avg_dl = 1.0

    dl = index.doc_lengths[doc_id]
    k1 = index.k1
    b = index.b

    norm_factor = k1 * (1.0 - b + b * (dl / effective_avg_dl))
    score = 0.0

    for term in query_terms:
        term_postings = index.postings.get(term)
        if not term_postings:
            continue

        tf = term_postings.get(doc_id, 0)
        if tf <= 0:
            continue

        df = len(term_postings)
        if df <= 0 or df > n_docs:
            continue

        idf = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))

        denominator = tf + norm_factor
        if denominator <= 0.0:
            continue

        score += idf * (tf / denominator)

    return score * (k1 + 1.0)


def search(
    index: InvertedIndex,
    query: str,
    k: int,
    max_source_len: int = MAX_SOURCE_LEN,
) -> list[MinimalSource]:
    """Devuelve las ``k`` mejores fuentes para ``query`` como MinimalSource.

    Primero, busca los documentos que contienen alguna palabra de la consulta.
    Después, calcula su relevancia, los ordena y devuelve los mejores resultados.
    Los términos repetidos se cuentan una sola vez y, si varios documentos
    tienen la misma puntuación, se ordenan por su identificador.
    Cada fuente devuelta tiene una longitud máxima de 2000 caracteres.

    Args:
        index: Índice invertido ya construido o cargado.
        query: Texto de la consulta que se tokenizará.
        k: Número máximo de fuentes que se quieren devolver.
        max_source_len: Longitud máxima en caracteres de cada fuente.
            Se limita al techo de 2000 caracteres.

    Returns:
        Lista de MinimalSource ordenada por relevancia BM25.
        Puede estar vacía si no hay documentos, términos o candidatos válidos.
    """
    effective_max = min(max_source_len, MAX_SOURCE_LEN)

    if k <= 0 or effective_max <= 0 or index.n_docs == 0:
        return []

    query_terms = list(dict.fromkeys(tokenize(query)))
    if not query_terms:
        return []

    candidates: set[int] = set()
    for term in query_terms:
        candidates.update(index.postings.get(term, {}))

    if not candidates:
        return []

    avg_dl = index.avg_doc_len
    scored = [
        (bm25_score(index, query_terms, doc_id, avg_dl=avg_dl), doc_id)
        for doc_id in candidates
    ]

    scored.sort(key=lambda item: (-item[0], item[1]))
    sources: list[MinimalSource] = []

    for _, doc_id in scored:
        if len(sources) >= k:
            break
        if doc_id < 0 or doc_id >= index.n_docs or doc_id >= len(index.chunks):
            continue

        chunk = index.chunks[doc_id]

        if chunk.start < 0 or chunk.end <= chunk.start:
            continue

        bounded_end = min(chunk.end, chunk.start + effective_max)
        sources.append(
            MinimalSource(
                file_path=chunk.file_path,
                first_character_index=chunk.start,
                last_character_index=bounded_end,
            )
        )
    return sources


def build_and_save(
    corpus_root: Path,
    max_chunk_size: int,
    processed_dir: Path,
    k1: float = 1.5,
    b: float = 0.75,
) -> InvertedIndex:
    """Indexa el corpus y persiste el índice; devuelve el índice construido.

    Args:
        corpus_root: Directorio del corpus a indexar.
        max_chunk_size: Tamaño máximo de chunk; se acota a 2000.
        processed_dir: Directorio donde se guarda el índice.
        k1: Parámetro k1 de BM25.
        b: Parámetro b de BM25.

    Returns:
        InvertedIndex: Índice construido y guardado.

    Raises:
        OSError: Si no se puede leer algún fichero del corpus.
        ValueError: Si no hay ficheros o el tamaño de chunk no es válido.
    """
    effective_chunk_size = min(max_chunk_size, MAX_SOURCE_LEN)
    root = project_root()
    entries: list[tuple[Chunk, list[str]]] = []

    files = list(iter_corpus_files(corpus_root))
    if not files:
        raise ValueError(f"No se encontraron ficheros en {corpus_root}")

    for file_path in tqdm(files, desc="Indexando corpus"):
        text = read_text(file_path)

        rel_path = to_corpus_path(file_path, root)
        chunks = chunk_file(rel_path, text, effective_chunk_size)

        for chunk in chunks:
            span_text = extract_span(text, chunk.start, chunk.end)
            terms = tokenize_source(span_text, rel_path)
            entries.append((chunk, terms))

    index = build_index(entries, k1=k1, b=b)
    index.save(processed_dir)
    return index
