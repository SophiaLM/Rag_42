# 00b — CLI mínimo

Añades **solo** la interfaz necesaria para que el paquete arranque. Por ahora, solo un stub de `index`. Los demás comandos aparecerán cuando su etapa lo requiera.

## 1. Archivos

### `src/cli.py`
```python
"""Command-line interface exposed with Python Fire."""


def index(max_chunk_size: int = 2000) -> None:
    """Ingest data/raw/ and build the index under data/processed/."""
    print(f"[stub] index max_chunk_size={max_chunk_size}")
```

### `src/__main__.py`
```python
"""Entry point: `uv run python -m src <command> [options]`."""
import fire

from src import cli

if __name__ == "__main__":
    fire.Fire({
        "index": cli.index,
    })
```

## 2. Comprobación

```bash
uv run python -m src --help
uv run python -m src index --max_chunk_size 2000
```

Ninguno debe lanzar `Traceback`.

## 3. Checklist

- [ ] `src/cli.py` y `src/__main__.py` existen con mapa explícito de comandos.
- [ ] `uv run python -m src index` funciona sin traceback.

## 4. Tiempo estimado

**≈ 5–10 minutos.**
