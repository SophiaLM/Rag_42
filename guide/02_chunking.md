# 02 — Chunking (Python + Markdown/texto)

En `01` aprendiste a leer el corpus sin mover un offset y a señalar cualquier región con `(file_path, start, end)`. Aquí decides **cómo partir ese texto en fragmentos**: los *chunks*. Es la etapa que más determina la calidad de la búsqueda, porque decide **qué "piezas de respuesta" van a existir**. Si la pieza correcta no existe, ningún algoritmo la encontrará después.

Esta etapa viene directa de `03_el_chunking.md`. Recuerda sus tres ideas, que aquí se vuelven código:

- **Corte estructural, no ciego:** `.py` se corta por definiciones; `.md` por títulos.
- **Cobertura:** la unión de los chunks debe cubrir el archivo entero; no dejar huecos.
- **Techo de tamaño:** ningún chunk puede superar `max_chunk_size` (por defecto 2000).

---

## 1. Qué vas a construir, y por qué así

Un módulo `src/chunking.py` que, dado `(file_path, text, max_chunk_size)`, devuelve **una lista de chunks**. Cada chunk es una **ubicación**, no un texto: solo guarda de qué archivo sale y qué rango ocupa. El texto no se copia a ningún lado; se recalcula después con `extract_span` cuando haga falta (esa es la decisión de la etapa `01`, y aquí se respeta).

El flujo interno es una **cadena de tres pasos**, y conviene tenerlos separados en la cabeza:

```text
texto ──► SEGMENTAR ──► EMPAQUETAR ──► trocear los gigantes ──► list[Chunk]
          (juntas        (agrupar
           naturales)     vecinos pequeños
                          sin pasar el techo)
```

1. **Segmentar**: encontrar las *juntas naturales* del formato (funciones/clases en `.py`, secciones en `.md`). Cada segmento es un rango `(start, end)`.
2. **Empaquetar**: fundir segmentos vecinos mientras quepan, para no generar cientos de chunks minúsculos (teoría `03`: las piezas pequeñas se agrupan).
3. **Partir los gigantes**: un segmento que por sí solo supera el techo se corta en trozos válidos (teoría `03`: las piezas gigantes se parten).

**Por qué funciones libres y un contenedor, en vez de una clase:** el chunking no tiene estado ni ciclo de vida; es una **transformación** de texto a lista. Igual que en `ejemplo2` ("el algoritmo no es un método de `Zone`"), aquí no hay objeto del dominio que "sepa" cortarse a sí mismo. Lo único que merece ser una estructura es el resultado: `Chunk`.

---

## 2. Dónde vive cada cosa

Todo en `src/chunking.py`. Este es el reparto, y es fijo:

| Símbolo | Decide | Quién lo usa |
|---|---|---|
| `Chunk(file_path, start, end)` | cómo se representa una pieza (solo ubicación) | el índice (`05a`) |
| `line_start_offsets(text)` | traducir **línea** → **offset** | `python_segments` |
| `python_segments(text)` | dónde cortar un `.py` | `chunk_file` |
| `markdown_segments(text)` | dónde cortar un `.md`/texto | `chunk_file` |
| `split_large(...)` | cómo partir un segmento gigante | `pack_segments` |
| `pack_segments(...)` | cómo agrupar segmentos en chunks | `chunk_file` |
| `chunk_file(...)` | elige estrategia y orquesta | el indexado (`05c`) |

`chunk_file` es **la única función que se llama desde fuera**; las demás son piezas internas. Esto importa: si algún día cambias cómo se corta el código, solo tocas `python_segments`, y nadie más se entera.

---

## 3. Las piezas que necesitas

Firmas (con su docstring, obligatorio por V.1). **Los cuerpos los escribes tú**; la lógica va explicada después de cada firma.

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    """Una pieza del corpus: solo su ubicación, no su texto."""
    file_path: str
    start: int
    end: int

    @property
    def length(self) -> int:
        """Número de caracteres que ocupa el chunk."""


def line_start_offsets(text: str) -> list[int]:
    """Offsets donde empieza cada línea; el índice i es la línea i+1."""


def python_segments(text: str) -> list[tuple[int, int]]:
    """Rangos de las definiciones top-level y de los huecos entre ellas."""


def markdown_segments(text: str) -> list[tuple[int, int]]:
    """Rangos de las secciones delimitadas por títulos (y el preámbulo)."""


def split_large(text: str, start: int, end: int,
                max_chunk_size: int) -> list[tuple[int, int]]:
    """Parte un rango que supera el techo en trozos válidos."""


def pack_segments(segments: list[tuple[int, int]], text: str,
                  max_chunk_size: int, overlap: int = 0) -> list[tuple[int, int]]:
    """Agrupa segmentos vecinos en chunks sin pasar el techo."""


def chunk_file(file_path: str, text: str, max_chunk_size: int,
               overlap: int = 0) -> list[Chunk]:
    """Punto de entrada: devuelve los chunks de un archivo."""
```

### La lógica detrás de cada una

**`Chunk`** — un `dataclass(frozen=True)`: un chunk es un dato **inmutable**; no "se edita" una ubicación, se crea otra. `length` es una `@property` (derivada de `end - start`), no un campo, para que no puedan contradecirse. Es el tipo que el índice guardará (`05a`).

> ¿Por qué `dataclass` y no `pydantic`? El subject (V.4) exige pydantic para los **modelos que se intercambian entre etapas o se serializan**; `Chunk` es una estructura **interna** del indexado. (Al persistir se convierte, no se valida contra el grader.)

**`line_start_offsets`** — devuelve, para cada línea, el offset donde empieza. Se construye acumulando la longitud de cada línea, incluyendo su salto (`splitlines(keepends=True)`). **Por qué hace falta:** el analizador de Python (`ast`) reporta posiciones en **números de línea**, pero todo el sistema habla en **offsets** (teoría `02`: línea ≠ offset). Esta función es el traductor entre ambos mundos, y debe incluir el `\n` para que las longitudes sumen exactamente.

**`python_segments`** — corta un `.py` por sus **definiciones top-level**:

- `ast.parse(text)`: el propio lenguaje te dice dónde empieza y acaba cada `FunctionDef`, `AsyncFunctionDef` y `ClassDef` (teoría `03`: el código se puede *analizar*, no adivinar).
- Si el archivo **no parsea** (`SyntaxError`), no lo pierdes: se devuelve el archivo entero como un único segmento. Un `.py` roto sigue siendo parte del corpus.
- De cada definición se toma desde su primera línea **decorador** hasta su `end_lineno`, y se traducen líneas a offsets con `line_start_offsets`.
- **Los huecos importan:** entre definición y definición hay código de módulo (docstring, `import`, constantes). Esos tramos entre el final de una definición y el inicio de la siguiente se emiten **también** como segmentos. Si los saltaras, dejarías huecos → cobertura rota (regla de oro de la teoría `03`).

**`markdown_segments`** — corta la documentación por **títulos**: se buscan las posiciones que cumplen `^#{1,6}\s` (de `h1` a `h6` al inicio de línea) y se usan como fronteras. El tramo **antes del primer título** (el preámbulo) también es una sección. **Por qué por títulos:** son las juntas naturales de un documento; respetarlas evita partir una idea a la mitad.

**`split_large`** — cuando un único segmento supera `max_chunk_size`, se emiten ventanas de tamaño máximo. El detalle fino: antes de cortar en el límite duro, se busca el último **doble salto de línea** (`\n\n`) dentro de la ventana; si existe, se corta ahí (frontera de párrafo, más natural). Si no, se corta en el límite exacto. Avanza el cursor hasta el final del rango. **Por qué cortar por `\n\n`:** mantiene los párrafos enteros cuando se puede; el techo se respeta siempre.

**`pack_segments`** — recorre los segmentos **en orden** y va acumulando:

- Si el segmento actual es válido (no supera el techo) y **cabe** en el chunk en curso, se extiende.
- Si **no cabe**, se cierra el chunk y se abre otro; `overlap` decide cuántos caracteres del final se repiten al principio del nuevo (por defecto `0`, la teoría `03` lo describe como palanca a probar, no obligación).
- Si el segmento **es más grande que el techo**, se cierra el chunk en curso y se delega en `split_large`.

**Por qué agrupar:** sin este paso, veinte funciones de tres líneas generarían veinte chunks pobres y sin contexto (teoría `03`). Agruparlas produce uno solo, con significado completo.

**`chunk_file`** — el orquestador: elige `python_segments` si el archivo termina en `.py`, `markdown_segments` en cualquier otro caso; pasa los segmentos por `pack_segments`; y convierte los rangos resultantes en `Chunk`. No contiene lógica de corte: solo une las piezas.

---

## 4. Reglas que este paso debe respetar

| Regla (teoría `03` / subject) | Implementación |
|---|---|
| Ningún chunk supera `max_chunk_size` | `pack_segments` nunca excede; `split_large` corta lo que por sí solo se pasa |
| Cobertura total (sin huecos) | `python_segments` rellena los tramos entre definiciones; los rangos se emiten contiguos |
| Corte **estructural** según formato | `.py` → AST; `.md`/texto → títulos |
| Piezas gigantes se parten | `split_large`, prefiriendo `\n\n` |
| Piezas minúsculas se agrupan | `pack_segments` funde vecinos hasta el techo |
| El chunk es una **ubicación**, no texto | `Chunk` guarda `file_path/start/end`; el texto se recalcula con `extract_span` |

> Trampa: contar el `\n` de cada línea o no al construir `line_start_offsets` desplaza **todos** los offsets siguientes. Es el mismo error de la teoría `02` (una lectura inconsistente), solo que escondido en la traducción línea → offset.

---

## 5. Caso de uso mínimo

```python
from src.chunking import chunk_file

src = "def a():\n    return 1\n\n\ndef b():\n    return 2\n"
chunks = chunk_file("m.py", src, max_chunk_size=2000)
# dos funciones pequeñas caben juntas -> un solo chunk que cubre todo el archivo

text = read_text(path)                         # la lectura de 01, siempre la misma
rel = to_corpus_path(path, root)               # la ruta canónica
for chunk in chunk_file(rel, text, 2000):
    print(chunk.file_path, chunk.start, chunk.end, chunk.length)
```

Cada `Chunk` de la salida es ya una `MinimalSource` en potencia: mismo `file_path` y mismos offset. Solo le faltará pasar por la validación de `03`.

---

## 6. Comprobación

`tests/test_chunking.py`. Lo que hay que verificar —y **qué demuestra** cada cosa—:

| Test | Qué demuestra |
|---|---|
| `test_every_file_is_fully_covered` | Sobre **todo el corpus**: los chunks empiezan en `0`, terminan en `len(text)` y son contiguos (sin huecos). Es el test de la regla de cobertura. |
| `test_no_chunk_exceeds_max_size` | Ningún chunk mide más de `2000` (ni mide `0`). Es el techo duro. |
| `test_small_definitions_stay_whole` | Dos funciones diminutas se **agrupan** en un solo chunk (no uno por función). |
| `test_huge_definition_is_split` | Una función gigantesca se **parte** en varios chunks, todos ≤ 2000. |

El helper de cobertura, que es la idea del primer test:

```python
def _covered(chunks: list[Chunk], length: int) -> bool:
    if chunks[0].start != 0 or chunks[-1].end != length:
        return False
    return all(chunks[i].end == chunks[i + 1].start for i in range(len(chunks) - 1))
# chunks contiguos ⇒ sin huecos y sin solapes "accidentales"
```

## 7. Qué NO cubre esta parte

- **Convertir el texto del chunk en términos** (mayúsculas, identificadores, stopwords) → `04`.
- **Construir el índice** → `05a`; aquí solo se producen las piezas.
- **Ajustar el solape** para subir recall → es una palanca del bucle de mejora (`07`).

## 8. Checklist

- [ ] `src/chunking.py` con `Chunk` y las seis funciones.
- [ ] Cobertura total y techo de tamaño verificados sobre el corpus real.
- [ ] `uv run pytest` y `uv run make lint` en verde.

## 9. Tiempo estimado

**≈ 1 h.**
