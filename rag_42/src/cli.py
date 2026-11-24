import sys

from src.corpus import project_root
from src.index import MAX_SOURCE_LEN, build_and_save


def index(max_chunk_size: int = 2000) -> None:
    """Ingest data/raw/ and build the index under data/processed/."""
    if max_chunk_size > MAX_SOURCE_LEN:
        print(
            f"Aviso: max_chunk_size={max_chunk_size} supera el límite de "
            f"{MAX_SOURCE_LEN}; se recortará a {MAX_SOURCE_LEN}.",
            file=sys.stderr,
        )

    root = project_root()
    index_obj = build_and_save(
        root / "data/raw/vllm-0.10.1",
        max_chunk_size,
        root / "data/processed",
    )
    print(f"Indexed {index_obj.n_docs} chunks")
