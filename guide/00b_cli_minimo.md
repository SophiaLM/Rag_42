# 00b — CLI mínimo

Al terminar `00a` tienes un **paquete** (`src/` con `__init__.py`) que pasa el lint… pero que no hace nada y no se puede *invocar*. Esta etapa añade la **puerta de entrada**: la interfaz por la que el evaluador (y tú) usaréis absolutamente todo lo que venga después.

El subject (VI.6) fija una forma única de invocar el programa:

```bash
uv run python -m src <command> [options]
```

De esa lista de comandos (`index`, `search`, `search_dataset`, `answer`, `answer_dataset`, `evaluate`) aquí montamos **solo `index`**, y **solo como esqueleto**: la lógica de indexar no existe todavía (llega en `05c`). La misión de esta etapa no es indexar nada, es **demostrar que el camino de invocación funciona de extremo a extremo** antes de que haya algo que pueda romperse.

---

## 1. Cómo se invoca un paquete en Python

`python -m src` le dice a Python: "trata `src` como un módulo ejecutable". Cuando `src` es un **paquete**, Python ejecuta su archivo llamado **exactamente** `__main__.py`. Ese nombre no es una convención nuestra: es el nombre fijo que Python busca para `-m <paquete>`. Por eso el fichero se llama así y no `main.py`.

- **Por qué no `python src/cli.py`:** ejecutar un archivo dentro del paquete rompe la identidad del paquete (los imports `from src...` dejan de resolver igual, y `sys.path` cambia). El subject ya fija `python -m src`: lo respetamos.
- **Por qué delante va `uv run`:** es el gestor obligatorio (V.4); prepara el entorno del proyecto y ejecuta el comando dentro de él. Por eso, al probar a mano, lo escribes igual que en los scripts de referencia.

---

## 2. Por qué Python Fire

El subject (V.4) exige que la CLI se construya con **`Fire`**. Fire hace una cosa muy concreta y nos ahorra `argparse`: le das una función y la **convierte en un subcomando**, donde cada parámetro de la función pasa a ser una opción con `--`.

```text
def index(max_chunk_size: int = 2000)   →   index --max_chunk_size 2000
        └── nombre de la función               └── nombre del parámetro
```

Los type hints hacen el trabajo: como `max_chunk_size` es `int`, Fire convierte el `"2000"` de la línea de comandos en el número `2000`.

### El mapa explícito, no la lista automática

Fire admite `fire.Fire(cli)` (exponer todo el módulo), pero aquí usamos un **diccionario explícito**. Es la decisión de diseño de esta etapa, y tiene dos motivos:

- **El mapa es el catálogo público.** Solo se expone lo que aparece en el diccionario; las funciones auxiliares de `cli.py` (las que empiezan por `_`, o las internas de cada comando) quedan fuera. Con `fire.Fire(cli)` expondrías por accidente cualquier función pública.
- **El mapa se compara con el subject.** VI.6 lista los comandos requeridos; tenerlos todos en una sola línea del `__main__.py` te deja ver de un vistazo qué falta. Crece **una línea por etapa**.

---

## 3. Qué vas a crear

Dos piezas, con roles muy distintos: una **cablea** (sin lógica de negocio) y la otra **expone los comandos** (la capa que traduce argumentos en llamadas). *Dónde vive cada cosa* es fijo, no "depende":

| Símbolo | Ubicación | Por qué ahí |
|---|---|---|
| el mapa `{"index": ...}` | `src/__main__.py` | Puro cableado de la entrada: no debe contener lógica |
| `index(max_chunk_size)` | `src/cli.py` | Cada comando es una función aquí; el mapa la referencia |
| `__init__.py` | `src/` | Ya existe (`00a`): sin él no habría paquete que ejecutar |

### `src/__main__.py` — el cableado

Este fichero no "hace" nada: conecta la línea de comandos con las funciones de `cli.py`. Es configuración, por eso lo mostramos completo — pero cada línea tiene su porqué:

```python
"""Entry point: `uv run python -m src <command> [options]`."""
import fire

from src import cli

if __name__ == "__main__":
    fire.Fire({
        "index": cli.index,
    })
```

- **`from src import cli`** (import absoluto, no `import cli`): el programa se ejecuta como paquete `src`, desde la raíz; el import absoluto es lo que esperan tanto Python como `mypy`/`pythonpath`.
- **`if __name__ == "__main__":`** → cuando corres `python -m src`, este fichero se ejecuta **como** `__main__`, así que la condición es verdadera. El guard evita que el despacho de Fire se dispare si alguien importara el módulo por error.
- **`fire.Fire({...})`** → entrega el **mapa** comando→función. La clave (`"index"`) es lo que tecleas; el valor (`cli.index`) es lo que se llama.

### `src/cli.py` — la capa de comandos

`cli.py` no contiene el "cómo": su único trabajo es **traducir argumentos de la CLI en llamadas al resto de `src/`**, y devolver/avisar. La lógica de indexar vivirá en `index.py`; aquí solo se orquesta. Por eso el comando de esta etapa es una **firma**, no una implementación:

`index(max_chunk_size: int = 2000) -> None`

` Decide: ingerir data/raw/ y construir el índice bajo data/processed/ (lo implementa 05c) `

` Por qué aquí: es el comando que el mapa expone; un comando = una función pública `

` Por qué max_chunk_size: int = 2000: el subject (VI.1) fija el default en 2000 y prohíbe superarlo (el moulinette rechaza fuentes de más de 2000 caracteres) `

` Por qué -> None: no retorna nada; su efecto es escribir el índice y reportar por consola `

En esta etapa el **cuerpo** es un marcador de posición: basta con que imprima lo que recibió, para comprobar que el comando llega y que Fire le pasó bien el parámetro. No te damos el cuerpo porque aún no hay lógica que aprender — lo único que se está verificando es el *plumbing*:

```python
def index(max_chunk_size: int = 2000) -> None:
    """Ingest data/raw/ and build the index under data/processed/."""
```

Cuando llegues a `05c`, ese cuerpo se sustituye por la llamada real (`build_and_save(...)` + un mensaje de cuántos chunks se indexaron). La firma —que es el **contrato** que Fire y el evaluador ven— no cambia.

> Recuerda V.1: el docstring no es opcional. Los tres puntos (`...`) no valen como cuerpo: pon al menos la línea de `print` del marcador, o `pass`.

---

## 4. Comprobación

```bash
uv run python -m src --help
uv run python -m src index --help
uv run python -m src index --max_chunk_size 2000
```

Qué debe pasar, y **por qué** cada uno:

- `--help` → Fire lista **exactamente un** comando, `index`. Si aparece más de uno, el mapa tiene entradas de más; si aparece cero, no se ejecutó `__main__.py`. Esto prueba que el mapa y el import funcionan.
- `index --help` → Fire muestra la opción `--max_chunk_size` **con su default (2000)**. Eso demuestra que Fire leyó la firma y su type hint; no hiciste nada más que declararla.
- `index --max_chunk_size 2000` → imprime la confirmación del marcador y **no lanza `Traceback`**. Ese "sin traceback" es la única aserción real de esta etapa: significa que `python -m src` → `__main__.py` → mapa → `cli.index` está conectado.

---

## 5. Qué NO cubre esta parte

- **La lógica de `index`** (leer, cortar, indexar, persistir) → `05c`.
- **Los demás comandos** (`search`, `search_dataset`, `answer`, `answer_dataset`, `evaluate`) → cada uno se añade a `cli.py` **y una línea al mapa** en su etapa (`06b`, `08c`, `07`). El mapa está pensado para crecer así.
- **Las barras `tqdm`** → cuando existan operaciones largas que mostrar (`05c`).
- **La robustez ante entradas raras** (query vacía, `k=0`, JSON mal formado, ficheros ausentes) → es un requisito transversal que se blinda en `06b`; aquí no hay nada que pueda recibir esas entradas todavía.

---

## 6. Checklist

- [ ] `src/__main__.py` con el mapa explícito de comandos (solo `index` por ahora).
- [ ] `src/cli.py` con la firma `index(max_chunk_size: int = 2000) -> None` y su docstring.
- [ ] `uv run python -m src --help` lista `index`.
- [ ] `uv run python -m src index --max_chunk_size 2000` no lanza `Traceback`.
- [ ] `uv run make lint` sigue en verde.

## 7. Tiempo estimado

**≈ 5–10 minutos.**
