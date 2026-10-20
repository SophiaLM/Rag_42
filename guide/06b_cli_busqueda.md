# 06b — CLI de búsqueda

Ya tienes `search` (`05b`) y `search_dataset` (`06a`), pero solo son llamables **desde Python**. El evaluador las invoca **desde la terminal**, con entradas que puede torcer (query vacía, `k=0`, ficheros ausentes, JSON roto). Esta etapa las **expone como comandos** y las **blinda**: ningún camino de entrada puede terminar en `Traceback` (subject VI.6).

Recuerda el contrato de invocación fijado en `00b`:

```bash
uv run python -m src search <query> --k <int>
uv run python -m src search_dataset --dataset_path <path> --k <int> --save_directory <dir>
```

---

## 1. Qué vas a construir

Añades a `src/cli.py` un helper y **dos comandos**, y actualizas el mapa de `src/__main__.py`:

- `_load_index(index_directory)` — carga el índice **o avisa** si no se puede.
- `search(query, k, index_directory)` — el comando de búsqueda individual.
- `search_dataset(dataset_path, k, save_directory, index_directory)` — el comando de lote.

**Dónde vive cada cosa:**

| Símbolo | Ubicación | Por qué ahí |
|---|---|---|
| `_load_index` | `cli.py` | Carga del índice con aviso: la comparten `search` y `search_dataset` |
| `search` / `search_dataset` | `cli.py` | Comandos de la CLI (capa de traducción argumentos → lógica) |
| el mapa `{"search": ...}` | `__main__.py` | Cableado de la entrada (crece una línea) |

**La colisión de nombres, y cómo se resuelve.** Fire usa el **nombre de la función** como subcomando, así que la función pública debe llamarse `search`. Pero en `index.py` ya existe una función `search` (`05b`) y necesitas usarla desde dentro. Solución: importarla **con alias** (`from src.index import search as run_search`). Mismo patrón para `search_dataset`.

---

## 2. Las piezas que necesitas

Firmas (con docstring). **La lógica**, debajo.

```python
from pathlib import Path
import json

from src.corpus import project_root
from src.index import InvertedIndex
from src.index import search as run_search
from src.io_utils import load_dataset, save_model
from src.retriever import search_dataset as run_search_dataset


def _load_index(index_directory: str) -> InvertedIndex | None:
    """Carga el índice de `index_directory`; None (con aviso) si no puede."""


def search(query: str, k: int = 10,
           index_directory: str = "data/processed") -> None:
    """Imprime las `k` mejores fuentes de `query`."""


def search_dataset(dataset_path: str, k: int = 10,
                   save_directory: str = "data/output/search_results",
                   index_directory: str = "data/processed") -> None:
    """Busca todo un dataset y guarda el StudentSearchResults JSON."""
```

### La lógica detrás de cada una

**`_load_index(index_directory)`** — el punto de carga con manejo de errores. En orden:

1. Resolver la ruta desde la raíz del proyecto (`project_root()`, `01`) — nunca depende del directorio actual.
2. Comprobar que existen `index.json` y `chunks.json`; si no, **imprimir un aviso** ("no hay índice; corre `index` primero") y devolver `None`.
3. Si existen, `InvertedIndex.load(path)`; si la carga falla (JSON corrupto, campos que faltan), capturar `(FileNotFoundError, json.JSONDecodeError, ValueError, KeyError)`, avisar y devolver `None`.

**Por qué un `None` en vez de lanzar:** el comando debe **informar**, no reventar. Los comandos que lo llaman comprueban `if idx is None: return`. Así, "sin índice" y "índice corrupto" tienen el mismo trato: un mensaje claro y salida limpia.

**`search(query, k, index_directory)`** —

1. Cargar el índice con `_load_index`; si es `None`, salir.
2. `run_search(idx, str(query), k)` (`05b`).
3. Imprimir cada fuente. Detalle: `str(query)` convierte la entrada a texto por seguridad (evita reventar si Fire entrega algo raro).
4. Con `k=0` o query vacía, `search` ya devuelve `[]` (`05b`), así que el bucle simplemente no imprime nada — sin caso especial.

**`search_dataset(...)`** — el lote con escritura a disco:

1. Cargar el índice (`_load_index`).
2. Cargar el dataset con `load_dataset` (`03`), **capturando** `FileNotFoundError`/`OSError` (fichero ausente) y `ValueError` (JSON mal formado) → mensaje claro y salida.
3. `run_search_dataset(idx, ds, k)` (`06a`).
4. Construir la carpeta destino usando **`save_directory` tal cual lo pasó quien invoca** y crearla con `mkdir(parents=True, exist_ok=True)`.
5. Guardar con `save_model` en `save_directory/<nombre original del dataset>.json` e informar de la ruta.

**Por qué el nombre original del fichero, y por qué el scope lo aporta quien llama.** El evaluador espera el resultado en `data/output/search_results/<Scope>/dataset_...json`, con **el mismo nombre** que el dataset de entrada (VI.7.2). El `<Scope>` **no lo añade el comando**: lo aporta quien invoca, pasando un `--save_directory` **ya scopeado** (`.../search_results/UnansweredQuestions`). El subject lo pide así porque los datasets públicos comparten nombre de fichero (`dataset_docs_public.json`), y es responsabilidad del llamante separarlos. **No** añadas tú la subcarpeta: si el `--save_directory` ya viene scopeado, duplicarías el nivel y el fichero quedaría donde el evaluador no lo busca.

**Las rutas son argumentos, nunca constantes.** `--dataset_path`, `--save_directory` e `--index_directory` son parámetros con default pero **configurables**: el subject lo exige (VI.7.1). El evaluador apunta `--save_directory` a sus propios directorios.

---

## 3. Reglas que este paso debe respetar

| Regla (subject VI.6) | Implementación |
|---|---|
| Comandos vía Fire | `search`/`search_dataset` + entradas en el mapa |
| Rutas **configurables**, no *hardcodeadas* | `--dataset_path`, `--save_directory`, `--index_directory` |
| `--save_directory` debe quedar scopeado por dataset | Lo aporta **quien invoca** (pasa la carpeta ya scopeada); el comando **no** añade subcarpetas |
| **Ningún** traceback | `_load_index` avisa; `FileNotFoundError`, `OSError`, `ValueError` capturadas |
| Degenerados no revientan | Query vacía y `k=0` → `[]`; JSON roto → mensaje |

**Entradas que el subject prueba, y qué las cubre:**

| Entrada | Resultado esperado | ¿Dónde se resuelve? |
|---|---|---|
| Query vacía | salida vacía | `search` (`05b`) |
| Query absurda | lista vacía | `search` (`05b`) |
| `k=0` | lista vacía | `search` (`05b`) |
| Dataset que falta | mensaje claro | `search_dataset` (aquí) |
| JSON mal formado | mensaje claro | `search_dataset` (aquí) |
| Índice ausente | mensaje claro | `_load_index` (aquí) |

---

## 4. Caso de uso mínimo

```bash
# búsqueda individual
uv run python -m src search "How to dynamically load a LoRA adapter?" --k 5

# búsqueda en lote (el índice se carga una vez; el scope lo aporta el llamante)
uv run python -m src search_dataset \
    --dataset_path data/datasets/UnansweredQuestions/dataset_docs_public.json \
    --k 10 --save_directory data/output/search_results/UnansweredQuestions

# datos degenerados: ninguno debe imprimir Traceback
uv run python -m src search "" --k 5
uv run python -m src search "cache" --k 0
uv run python -m src search_dataset --dataset_path no/existe.json --k 5 --save_directory /tmp/o
```

---

## 5. Comprobación

No hay `pytest` aquí: **esto se prueba como lo prueba el evaluador**, con comandos reales.

```bash
printf '{not json' > /tmp/bad.json
uv run python -m src search_dataset --dataset_path /tmp/bad.json --k 5 --save_directory /tmp/o
uv run python -m src search_dataset --dataset_path no/existe.json --k 5 --save_directory /tmp/o
echo "Si no aparece Traceback, esta parte esta bien."
```

Y el tiempo del lote (lo que mide el presupuesto de `06a`):

```bash
time uv run python -m src search_dataset \
    --dataset_path data/datasets/UnansweredQuestions/dataset_docs_public.json \
    --k 10 --save_directory data/output/search_results/UnansweredQuestions
```

La única aserción es siempre la misma: **"no veo `Traceback`"**. Es literalmente lo que exige el subject.

---

## 6. Qué NO cubre esta parte

- **Medir** lo recuperado (recall@k, IoU) → `07`.
- **Generar respuestas** (`answer`, `answer_dataset`) → `08c`.
- **El comando `evaluate`** → `07`.

## 7. Checklist

- [ ] `search` y `search_dataset` conectados en el mapa de la CLI.
- [ ] Rutas configurables por argumento (sin *hardcode*).
- [ ] `--save_directory` se usa **tal cual** (el scope lo aporta quien llama, no el comando).
- [ ] Ninguna entrada degenerada produce `Traceback` (índice ausente, fichero ausente, JSON roto, `k=0`, query vacía).
- [ ] `uv run make lint` en verde.

## 8. Tiempo estimado

**≈ 15–30 minutos.**
