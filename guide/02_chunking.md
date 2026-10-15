# 02 — Chunking (Python + Markdown/texto)

Partes el corpus sin dejar huecos ni superar 2000 caracteres.

## 1. Código

`src/chunking.py`:
```python
from dataclasses import dataclass
import ast
import re


@dataclass(frozen=True)
class Chunk:
    file_path: str
    start: int
    end: int

    @property
    def length(self) -> int:
        return self.end - self.start


HEADING = re.compile(r"(?m)^#{1,6}\s")


def line_start_offsets(text: str) -> list[int]:
    offsets = [0]
    for line in text.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    return offsets


def python_segments(text: str) -> list[tuple[int, int]]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return [(0, len(text))]
    starts = line_start_offsets(text)
    nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
    spans: list[tuple[int, int]] = []
    for node in nodes:
        node_start = min([d.lineno for d in node.decorator_list] + [node.lineno])
        spans.append((starts[node_start - 1], starts[node.end_lineno]))
    segments: list[tuple[int, int]] = []
    cursor = 0
    for s, e in sorted(spans):
        if s > cursor:
            segments.append((cursor, s))
        segments.append((s, e))
        cursor = e
    if cursor < len(text):
        segments.append((cursor, len(text)))
    return segments


def markdown_segments(text: str) -> list[tuple[int, int]]:
    starts = [0] + [m.start() for m in HEADING.finditer(text)]
    bounds = sorted(set(starts + [len(text)]))
    return [(bounds[i], bounds[i + 1]) for i in range(len(bounds) - 1)]


def split_large(text: str, start: int, end: int, max_chunk_size: int) -> list[tuple[int, int]]:
    parts: list[tuple[int, int]] = []
    cursor = start
    while end - cursor > max_chunk_size:
        limit = cursor + max_chunk_size
        cut = text.rfind("\n\n", cursor, limit)
        if cut == -1 or cut <= cursor:
            cut = limit
        else:
            cut = cut + 1
        parts.append((cursor, cut))
        cursor = cut
    if cursor < end:
        parts.append((cursor, end))
    return parts


def pack_segments(segments: list[tuple[int, int]], text: str,
                  max_chunk_size: int, overlap: int = 0) -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    cur_start: int | None = None
    cur_end = 0
    for start, end in segments:
        if end - start > max_chunk_size:
            if cur_start is not None:
                result.append((cur_start, cur_end))
                cur_start = None
            result.extend(split_large(text, start, end, max_chunk_size))
            continue
        if cur_start is None:
            cur_start, cur_end = start, end
        elif end - cur_start <= max_chunk_size:
            cur_end = end
        else:
            result.append((cur_start, cur_end))
            cur_start = max(cur_end - overlap, start) if overlap else start
            cur_end = end
    if cur_start is not None:
        result.append((cur_start, cur_end))
    return result


def chunk_file(file_path: str, text: str, max_chunk_size: int,
               overlap: int = 0) -> list[Chunk]:
    if file_path.endswith(".py"):
        segments = python_segments(text)
    else:
        segments = markdown_segments(text)
    spans = pack_segments(segments, text, max_chunk_size, overlap)
    return [Chunk(file_path, s, e) for s, e in spans]
```

## 2. Testers

`tests/test_chunking.py`:
```python
from src.chunking import chunk_file, Chunk
from src.corpus import project_root, read_text, to_corpus_path, iter_corpus_files


ROOT = project_root()


def _covered(chunks: list[Chunk], length: int) -> bool:
    if not chunks:
        return length == 0
    if chunks[0].start != 0 or chunks[-1].end != length:
        return False
    return all(chunks[i].end == chunks[i + 1].start for i in range(len(chunks) - 1))


def test_every_file_is_fully_covered() -> None:
    corpus = ROOT / "data/raw/vllm-0.10.1"
    for path in iter_corpus_files(corpus):
        text = read_text(path)
        rel = to_corpus_path(path, ROOT)
        chunks = chunk_file(rel, text, 2000)
        assert _covered(chunks, len(text)), rel


def test_no_chunk_exceeds_max_size() -> None:
    corpus = ROOT / "data/raw/vllm-0.10.1"
    for path in iter_corpus_files(corpus):
        text = read_text(path)
        rel = to_corpus_path(path, ROOT)
        for c in chunk_file(rel, text, 2000):
            assert 0 < c.length <= 2000, rel


def test_small_definitions_stay_whole() -> None:
    src = "def a():\n    return 1\n\n\ndef b():\n    return 2\n"
    chunks = chunk_file("m.py", src, 2000)
    assert len(chunks) == 1


def test_huge_definition_is_split() -> None:
    src = "def big():\n" + "    x = 1\n" * 2000
    chunks = chunk_file("m.py", src, 2000)
    assert len(chunks) > 1
    assert all(c.length <= 2000 for c in chunks)
```

## 3. Checklist

- [ ] `src/chunking.py` implementado.
- [ ] Tests pasan.
- [ ] `make lint` pasa.

## 4. Tiempo estimado

**≈ 1h.**
