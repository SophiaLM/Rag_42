# 01 — Corpus y offsets

Aquí empieza el **código de verdad**. Esta etapa no corta, no busca ni genera: establece el **vocabulario de coordenadas** que todas las etapas siguientes van a reutilizar. Si esto queda mal, el fallo se propaga a absolutamente todo (los resultados no cuadran, la reconstrucción del texto miente, el grader no reconoce ninguna ruta). Por eso es la primera, y por eso se explica antes de escribirla.

Hace exactamente **dos cosas**, que son las dos ideas centrales de `02_el_texto_y_sus_coordenadas.md`:

1. **Leer el corpus siempre de la misma manera** → bytes a texto, en UTF-8, sin traducir saltos de línea.
2. **Nombrar cada archivo de una única forma** → la ruta canónica `data/raw/vllm-0.10.1/...`, tal cual.

---

## 1. La regla que gobierna esta etapa: un único punto de entrada

Las dos ideas de arriba solo funcionan si se cumplen **en un sitio y en un solo sitio**:

- Si cada módulo leyera los archivos a su manera (uno con `open()`, otro con `read_text()` de `pathlib`, otro sin fijar la codificación), tendríamos varias "formas de leer". Un rango calculado al indexar no coincidiría con el texto extraído al mostrar → los offsets se desplazarían.
- Si cada módulo construyera la ruta a mano (`"./" + ...`, `str(path)`, rutas absolutas), aparecerían variantes que apuntan al mismo archivo pero que el comparador ve como **archivos distintos**.

Por eso todo esto vive en **un único módulo, `src/corpus.py`**, y el resto del sistema pasa por él: nunca vuelve a leer un archivo ni a construir una ruta por su cuenta. `corpus.py` es la capa más baja del proyecto; no depende de nada del dominio.

> Estas funciones son **funciones libres, no métodos**. Eso aquí es correcto: operan sobre primitivas (`Path`, `str`), no sobre ningún objeto del dominio — y en esta etapa el dominio todavía no existe. "OOP obligatorio" del subject aplica a las clases que representan *tu sistema*, no a helpers de E/S sin estado.

---

## 2. Dónde vive cada cosa

Todo `corpus.py`. *Qué decide* cada función, para no confundirlas entre sí:

| Símbolo | Decide | Quién lo usa (más adelante) |
|---|---|---|
| `project_root()` | dónde está la raíz del repositorio | todo el que construya rutas (`05c`, `06b`) |
| `read_text(path)` | cómo se convierten bytes en texto | indexado (`05c`), reconstrucción del contexto (`08a`) |
| `to_corpus_path(path, root)` | la forma **canónica** de nombrar un archivo | al guardar cada chunk (`05c`) |
| `resolve_corpus_path(corpus_path, root)` | la ruta real a partir de una guardada | al releer un `file_path` guardado (`08a`) |
| `extract_span(text, start, end)` | cómo se recorta un rango | indexado y reconstrucción |
| `iter_corpus_files(root, extensions)` | qué archivos forman el corpus y en qué orden | bucle de indexado (`05c`) |

---

## 3. Las funciones que necesitas

Firmas completas (con su docstring, que es obligatorio, V.1). **Los cuerpos los escribes tú**: la lógica va explicada debajo de cada una.

```python
from collections.abc import Iterator
from pathlib import Path


def project_root() -> Path:
    """Raíz del repositorio (el directorio que contiene `src/`)."""


def read_text(path: Path) -> str:
    """Texto de `path` en UTF-8, sin traducir saltos de línea."""


def to_corpus_path(path: Path, root: Path) -> str:
    """Ruta de corpus canónica (POSIX, relativa a la raíz) de `path`."""


def resolve_corpus_path(corpus_path: str, root: Path) -> Path:
    """Ruta real en disco a partir de una ruta de corpus guardada."""


def extract_span(text: str, start: int, end: int) -> str:
    """Devuelve el texto de `text` en el rango [start, end)."""


def iter_corpus_files(
    root: Path,
    extensions: tuple[str, ...] = (".py", ".md", ".txt"),
) -> Iterator[Path]:
    """Recorre el corpus y produce sus archivos, en orden estable."""
```

### La lógica detrás de cada una

**`project_root`** — sube desde la ubicación del propio archivo (`__file__`) hasta el directorio que contiene `src/`. `Path(__file__).resolve().parents[1]`: `corpus.py` está en `src/`, así que `parents[0]` es `src/` y `parents[1]` es la raíz. **Por qué no usar el directorio actual:** el evaluador lanza los comandos desde la raíz, pero tú puedes probar desde otro sitio; resolver la raíz a partir del archivo hace que funcione igual en ambos casos. Y el subject exige rutas relativas a la raíz del proyecto.

**`read_text`** — lee el archivo como **bytes** y lo **decodifica** como UTF-8. Es el punto delicado:

- Leer bytes (y no en "modo texto") evita la traducción automática `\r\n` → `\n`, que **acortaría el texto y desplazaría los offsets** (teoría `02`).
- Decodificar `"utf-8"` fija la codificación; nunca dejarla al azar del sistema.
- Si algún byte no es UTF-8 válido, `decode` lanza `UnicodeError`: se reintenta con `errors="replace"` para **no reventar** (regla V.1). Un archivo del corpus con un byte raro no puede tumbar el indexado.

**`to_corpus_path`** — produce la ruta canónica a partir de una ruta real. Tres pasos, cada uno con su motivo: `resolve()` (elimina `./`, `..` y simbólicos) → `relative_to(root)` (la deja relativa a la raíz, sin prefijo absoluto) → `as_posix()` (siempre `/`, nunca `\`). El resultado tiene que ser, literalmente, `data/raw/vllm-0.10.1/docs/features/lora.md`.

**`resolve_corpus_path`** — la operación inversa: une la raíz con una ruta guardada (`root / corpus_path`). Sirve para el momento en que *solo* tienes el `file_path` almacenado (sin el texto) y necesitas volver a abrir el archivo.

**`extract_span`** — devuelve `text[start:end]`. Es un simple slicing, y precisamente por eso existe como función: **fija la convención en un único lugar** en vez de repetir el `[:]` por todo el proyecto. La convención es `[start, end)`, **exclusiva** en `end`: `end` no se incluye. Así `end - start` es exactamente el número de caracteres del fragmento, un rango vacío es expresable (`start == end`) y coincide con el slicing de Python.

**`iter_corpus_files`** — recorre el árbol con `rglob("*")`, se queda con los archivos (`is_file()`) cuya extensión está en `extensions`, y los entrega **en orden** (`sorted(...)`). Por qué ordenar: un mismo corpus debe producir siempre el mismo índice (reproducibilidad; nada de depender del orden del sistema de archivos). Por qué es un `Iterator` y no una lista: se consume a medida que se indexa, sin cargar todas las rutas a la vez. Se incluye `".txt"` además de `.py`/`.md` porque el corpus tiene ficheros de texto relevantes (p. ej. `CMakeLists.txt`).

---

## 4. Reglas que este paso debe respetar

| Regla (teoría `02`) | Implementación |
|---|---|
| Los offsets se cuentan en **caracteres**, no en bytes | Se indexa sobre el `str` que devuelve `read_text`; nunca sobre `len(bytes)` |
| El corpus se lee **siempre igual** | Solo `read_text` abre archivos; ningún otro módulo usa `open`/`read_text` de `pathlib` |
| `file_path` se compara **verbatim** | La ruta se construye solo con `to_corpus_path` (relativa, POSIX, sin `./`) |
| El rango es **`[start, end)`** | Solo `extract_span` recorta, y siempre con slicing de Python |
| Ningún byte inválido puede tumbar el pipeline | `read_text` reintenta con `errors="replace"` ante `UnicodeError` |

> Ojo con dos trampas: (1) un `len()` sobre bytes en vez de sobre el `str` decodificado da offsets corridos en cuanto hay tildes o emojis; (2) abrir un archivo con `open(path).read()` "para el test rápido" trae la traducción de saltos de línea de vuelta y rompe la consistencia.

---

## 5. Caso de uso mínimo

Así se combinan (esto es, en esencia, el corazón del indexado de `05c`):

```python
root = project_root()

for path in iter_corpus_files(root / "data/raw/vllm-0.10.1"):
    rel = to_corpus_path(path, root)      # "data/raw/vllm-0.10.1/docs/features/lora.md"
    text = read_text(path)                # bytes -> str, mismo criterio siempre
    span = extract_span(text, 4695, 6098) # trozo reconstruido desde sus offsets
```

`rel` junto con `start`/`end` es **exactamente** la terna `(file_path, first_character_index, last_character_index)` de la teoría `02`: la misma que más tarde se guarda en un `MinimalSource` (`03`) y que el grader compara. Por eso las dos piezas —ruta y offsets— tienen que nacer bien aquí.

---

## 6. Comprobación

Crea `tests/test_corpus.py` y verifica **estas cinco cosas** (los nombres son orientativos; lo que importa es qué demuestra cada una):

| Test | Qué demuestra |
|---|---|
| `test_extract_matches_reference_span` | Recuperar `[4695, 6098)` de `docs/features/lora.md` **empieza por `### Using API Endpoints`** y mide `6098 - 4695`. Es la prueba de extremo a extremo de la convención. |
| `test_offsets_are_characters_not_bytes` | Con `"ábc"`, `len == 3` y `extract_span(text, 0, 3) == "ábc"`. Demuestra que **no** se cuentan bytes (`á` son 2 bytes). |
| `test_corpus_path_is_posix_and_relative` | `to_corpus_path(...)` devuelve la ruta exacta, **sin** `./` y **sin** `\`. |
| `test_reading_is_stable` | Leer dos veces el mismo archivo da el mismo texto (nada de traducción no determinista). |
| `test_iter_is_sorted` | `iter_corpus_files` produce rutas ordenadas (reproducibilidad del índice). |

Las dos aserciones que condensan el aprendizaje:

```python
text = "ábc"
assert len(text) == 3 and extract_span(text, 0, 3) == "ábc"       # caracteres, no bytes

out = to_corpus_path(ROOT / "data/raw/vllm-0.10.1/docs/features/lora.md", ROOT)
assert out == "data/raw/vllm-0.10.1/docs/features/lora.md"       # verbo a verbo
assert not out.startswith("./") and "\\" not in out
```

> El test de la referencia necesita el corpus en `data/raw/vllm-0.10.1/`. Si aún no lo has copiado allí, es el momento: `file_path` se compara contra esa ruta exacta, no contra `proyect/...`.

---

## 7. Qué NO cubre esta parte

- **Cortar el texto en chunks** (código vs markdown, solape, tamaño) → `02`.
- **Los modelos de datos** (`MinimalSource`, etc.) → `03`; aquí solo se produce la materia prima.
- **El indexado** (recorrer, tokenizar, guardar) → `05c`. Esta etapa deja las piezas listas; el bucle real las encadena.

---

## 8. Checklist

- [ ] `src/corpus.py` con las seis funciones y sus docstrings.
- [ ] Los cinco tests pasan (`uv run pytest`).
- [ ] `uv run make lint` pasa en verde.

## 9. Tiempo estimado

**≈ 30 minutos.**
