# 02 — El texto y sus coordenadas (offsets)

Antes de hablar de chunks, modelos de datos o búsqueda, hay que entender **cómo tratamos el texto** y **cómo señalamos una parte concreta dentro de un archivo**. Esa forma de señalar —el *offset*— es el vocabulario base de todo el sistema. Aquí se explica por primera vez, para poder usarla después sin ambigüedad.

---

## 1. Los conceptos, con palabras sencillas

**Corpus.**
Llamamos *corpus* al conjunto de archivos que el sistema va a poder consultar. En un proyecto real es un repositorio de código: por un lado archivos de **código** (por ejemplo `.py`) y por otro **documentación** (por ejemplo `.md`). Un archivo de código y una página de documentación se comportan muy distinto, y eso tendrá consecuencias más adelante.

**El texto es una secuencia de caracteres.**
Cuando leemos un archivo, obtenemos una cadena de texto: una fila de **caracteres** en un orden concreto. El primer carácter es el número `0`, el segundo el `1`, el tercero el `2`… como las casillas de una cinta larguísima.

**Offset (posición en caracteres).**
Un **offset** es el número de casilla de un carácter: *cuántos caracteres hay desde el principio hasta él*. Es la coordenada que usamos para decir "esta parte empieza aquí y termina allá". Un **rango** es un par de offsets: `[inicio, fin]`.

**Ruta del archivo (`file_path`).**
Para localizar algo dentro del corpus hacen falta **dos** datos, no uno: **el archivo** y **el rango dentro de él**. Es como decir "tomo la página 12 de *este* libro, desde la línea 3 hasta la 8". Si cambias el libro, el rango ya no significa nada. Por eso la ruta debe ser **exacta** (lo veremos abajo).

---

## 2. Profundizando

### Caracteres frente a bytes: el error clásico

Un archivo en disco es una secuencia de **bytes** (números de 0 a 255), no de caracteres. Y muchos caracteres ocupan **más de un byte**:

- `a` ocupa 1 byte.
- `á`, `ñ`, `ü` ocupan 2 bytes en la codificación habitual.
- Un emoji puede ocupar 3 o 4 bytes.

Cuando el archivo se **decodifica** (por ejemplo como **UTF-8**, la codificación universal), esos bytes se convierten en caracteres. Los offsets de este proyecto se cuentan en **caracteres**, no en bytes. Si por error cuentas bytes, cada carácter multibyte "empuja" todas las posiciones siguientes y tus rangos quedan corridos: apuntarías a trozos que no existen o a texto equivocado.

### Los saltos de línea también mueven los offsets

En los archivos, el fin de línea puede guardarse como `\n` (un carácter) o como `\r\n` (dos caracteres). Algunos lenguajes, al leer en "modo texto", **traducen** `\r\n` a `\n` automáticamente. Es cómodo para leer, pero **acorta** el texto y desplaza los offsets. La regla de oro:

> Lee el corpus **siempre de la misma manera**. Si indexas contando los caracteres de una forma y luego relees el archivo contando de otra, los rangos dejan de cuadrar.

Esta consistencia es no negociable: el momento en que guardas un rango y el momento en que lo usas para volver a extraer el texto deben dar exactamente el mismo resultado.

### Por qué la ruta debe ser exacta

El sistema compara rutas de archivo **carácter a carácter** contra las de referencia. Dos cadenas que se refieren al mismo archivo, pero escritas distinto, son para el comparador **archivos diferentes**:

- `data/raw/vllm-0.10.1/docs/features/lora.md` ✅ (tal como está en el corpus)
- `./data/raw/vllm-0.10.1/docs/features/lora.md` ❌ (prefijo `./` de más)
- `/home/tu_usuario/.../lora.md` ❌ (ruta absoluta)
- `data\\raw\\vllm-0.10.1\\...` ❌ (barras invertidas)

Moraleja: la ruta se construye **de una única forma**, en un único lugar del sistema, y se reutiliza tal cual. Nunca la "arregles" a mano en cada sitio.

### Una coordenada, tres usos

El mismo par `(file_path, inicio, fin)` sirve para tres cosas, y por eso hay que tratarlo con cuidado:

1. **Describir** un resultado de búsqueda: "la respuesta está en este archivo, entre estas posiciones".
2. **Guardar** un chunk: recordar qué trozo del corpus es.
3. **Reconstruir** el texto: más adelante, cuando solo tengamos la ruta y el rango (sin el texto), podremos releer exactamente ese fragmento.

Un offset mal calculado rompe los tres a la vez.

### Offset no es número de línea

No confundas "carácter número 4000" con "línea 120". Son dos formas distintas de contar. La línea es cómoda para los humanos y para analizar código; el offset es lo que necesitas para apuntar con precisión a **cualquier** posición, incluso en mitad de una línea. Más adelante habrá que **traducir** de línea a offset; aquí basta con que retengas que son unidades distintas.

---

## 3. Preguntas para comprobar que lo entiendes

1. Define *offset* con tus palabras. ¿En qué unidad se cuenta en este proyecto: caracteres o bytes?
2. ¿Por qué un archivo con emojis o tildes puede corromper tus offsets si los cuentas mal?
3. ¿Qué efecto tiene traducir `\r\n` a `\n` al leer un archivo? ¿Por qué exige usar la misma lectura en todo el sistema?
4. ¿Por qué decimos que para localizar algo hacen falta *dos* datos (archivo + rango) y no solo el rango?
5. Da dos ejemplos de cómo escribir una ruta de forma "equivocada" aunque apunte al mismo archivo, y explica por qué fallan.
6. ¿Cuál es la diferencia entre "línea 120" y "offset 4000"? ¿Cuándo usarías cada uno?
7. Nombra los tres usos del par (ruta, inicio, fin) y di qué pasa si uno de los offsets es incorrecto.

<details><summary>Respuestas rápidas</summary>

1. Es la posición (número de casilla) de un carácter dentro del archivo; se cuentan caracteres, no bytes.
2. Porque los caracteres multibyte ocupan varios bytes: al contar bytes, todas las posiciones posteriores quedan desplazadas.
3. Convierte dos caracteres de fin de línea en uno, acortando el texto; si unas veces traduces y otras no, los rangos no coinciden entre indexar y releer.
4. Porque el rango solo tiene sentido dentro de un archivo concreto; el mismo rango en otro archivo apunta a texto distinto.
5. Poner `./` delante, usar ruta absoluta, mezclar `/` y `\`: el comparador las ve como archivos distintos aunque el contenido coincida.
6. Línea es para lectura humana/estructura; offset es para apuntar con precisión a un carácter. Habrá que traducir entre ambos.
7. Describir resultados, guardar chunks y reconstruir texto; un offset malo rompe las tres cosas a la vez.
</details>
