# Parte 1 — Los textos como coordenadas: corpus, offsets, fuentes e IoU

En este proyecto una "respuesta de búsqueda" no es un texto: es una **dirección**. Esta parte te da el lenguaje para hablar de direcciones dentro de archivos. Casi todo lo que viene después se apoya aquí.

---

## 1. Conceptos nuevos — la versión sencilla

**Corpus**
La biblioteca completa sobre la que se hacen las preguntas: aquí, todos los archivos del repositorio de vLLM. Es el conjunto de "libros" disponibles.

**Chunk (fragmento)**
Un libro entero es demasiado grande para entregarlo. Lo troceamos en **fichas**, y cada ficha es un chunk: un pedazo de un archivo. La búsqueda trabajará con fichas, no con libros.

**Posición de carácter (offset)**
Imagina un archivo como una **cinta larga de casillas**, una letra en cada casilla. Numeramos las casillas empezando por el **0**. Ese número es el *offset* (o posición) de cada carácter. Los espacios y los saltos de línea también ocupan casilla.

```
texto:    H  O  L  A     M  U  N  D  O
offset:   0  1  2  3  4  5  6  7  8  9
```

**Rango**
Un tramo de la cinta, descrito con dos números: dónde empieza y dónde termina. El rango `[5:10]` del texto de arriba es `MUNDO`. Aquí usamos la convención de Python: **el inicio cuenta, el final no** (llegas hasta justo antes del 10).

**Fuente (source)**
La dirección completa de un trozo de texto: **qué archivo** + **qué rango dentro de él**. Como una dirección postal: calle (archivo) y portales (del número X al número Y). Una búsqueda no te devuelve el texto, te devuelve *fuentes*.

**Solapar**
Dos rangos "se solapan" si **comparten alguna parte** de la cinta. El rango `[100:300]` y el `[250:350]` se solapan en la zona `[250:300]`. Si uno termina antes de que empiece el otro, no se solapan.

**IoU (Intersection over Union)**
Es un **número entre 0 y 1 que mide cuánto se parecen dos rangos**. Se calcula dividiendo la parte que **comparten** entre el total que **cubren entre los dos juntos**. Imagina dos subrayadores sobre la misma línea: si subrayan exactamente lo mismo, IoU = 1; si no se tocan, IoU = 0; si se tocan un poco, algo intermedio.

```
rango A:   ██████████████████            (100 → 300)
rango B:              ████████           (250 → 350)
                      ░░░░░              comparten 250 → 300  (50)
total cubierto por A o B: 100 → 350     (250)
IoU = 50 / 250 = 0.2
```

---

## 2. Profundizando

**Lo que debes llevarte de aquí:** (1) que todo el proyecto "habla en coordenadas" (archivo + rango); (2) que esas coordenadas se cuentan en **caracteres**, y cualquier descuido al leer el archivo las desplaza; (3) que el IoU es lo que decide si una fuente tuya cuenta como acierto.

### Por qué coordenadas y no solo "el archivo"

Un archivo puede tener miles de líneas y contener muchas respuestas distintas. Decir "la respuesta está en `api_server.py`" es como decir "el libro que buscas está en la biblioteca". La coordenada dice **en qué parte exacta**. Además, con una dirección en vez del texto, dos sistemas distintos (el tuyo y el corrector) pueden comparar sus resultados sin leer ni una palabra: basta comparar números.

### Carácter no es byte

El ordenador guarda cada carácter con uno o varios **bytes**. Una `a` ocupa 1 byte, una `é` ocupa 2, un emoji ocupa 4. Si cuentas bytes en lugar de caracteres, cada vez que aparece un carácter "ancho" tus posiciones se corren, y todo lo que viene detrás queda desplazado. Las coordenadas del proyecto son **en caracteres**.

### La forma de leer el archivo cambia las coordenadas

Hay un segundo origen de desajustes: los **saltos de línea**. En algunos archivos, un salto de línea son dos caracteres (`\r\n`). Algunos modos de lectura los convierten en uno solo. Si al construir el índice lees de una forma y luego, al generar la respuesta, relees de otra, tus coordenadas ya no apuntan al mismo sitio. Regla de oro: **quien guarda las coordenadas y quien las usa debe haber leído el archivo exactamente igual**.

### Rango: ¿incluye el último carácter o no?

Hay dos convenciones: **exclusiva** (el final no cuenta, como en Python) e **inclusiva** (el final sí cuenta). Para el IoU apenas importa, porque un error de un carácter casi no mueve la proporción. Pero sí importa para medir la **longitud**: un rango `[0:2000]` mide 2000 en la convención exclusiva y 2001 en la inclusiva. El subject no precisa cuál usa el corrector, así que es una duda abierta que tendrás que comprobar.

### El IoU en detalle

Fórmula, para dos rangos `[a1:b1]` y `[a2:b2]` **en el mismo archivo**:

```
compartido = lo que tienen en común   (0 si no se solapan)
total      = longitud(A) + longitud(B) − compartido
IoU        = compartido / total
```

Casos de referencia:

| Situación | IoU |
|---|---|
| Rangos idénticos | 1.0 |
| Rangos que no se tocan | 0 |
| `[100:300]` frente a `[250:350]` | 0.2 |
| Un rango de 2000 que contiene entero a otro de 200 | 200 / 2000 = 0.10 |
| Un rango de 2000 que contiene entero a otro de 50 | 50 / 2000 = 0.025 |

### Qué significa el umbral de 0.05

En este proyecto un acierto exige IoU de al menos **0.05**: muy permisivo. No hace falta clavar el rango exacto; basta con "pisar la zona correcta". Pero atención a dos matices:

- **Rozar no basta.** Si tu rango de 2000 caracteres solo comparte 1 carácter con una referencia de 200, el IoU es 1/2199 ≈ 0.0005. Ni de cerca.
- **Contener tampoco garantiza.** Mira la tabla: un rango grande que contiene por completo una referencia pequeña puede *fallar* (el último caso: 0.025). Cuanto más grande es tu rango frente a lo que buscas, más se diluye el IoU. Es la primera pista de por qué el tamaño de los chunks es una decisión importante (se desarrolla en la Parte 3).

### El archivo tiene que ser el mismo

Dos rangos solo se comparan si son del **mismo archivo**; en archivos distintos el IoU es 0 por definición. Y como el corrector compara la ruta como texto literal, la ruta que guardes tiene que escribirse **exactamente igual** que la del corpus: una ruta con un prefijo distinto es, para él, otro archivo.

### Fuente = identidad + posición

Resumiendo la idea: una fuente es una pareja `(archivo, rango)`. El archivo dice *dónde*, el rango dice *qué parte*, y el IoU dice *cuánto coincide* con otra fuente. Las tres piezas trabajan juntas.

---

## 3. Diez preguntas que responder antes de programar

1. ¿Qué es un chunk y por qué no entregamos archivos enteros?
2. En el texto `"HOLA MUNDO"`, ¿qué offset tiene la `U`? ¿Y qué texto da el rango `[0:4]`?
3. ¿Qué componentes tiene una fuente y por qué una búsqueda devuelve fuentes y no texto?
4. ¿Qué significa que dos rangos "se solapan"?
5. Calcula el IoU de `[0:100]` frente a `[50:150]`.
6. ¿Por qué un rango de 1500 caracteres que contiene por completo una referencia de 150 acierta, pero uno que contiene una de 40 no?
7. ¿Por qué contar bytes en lugar de caracteres desplaza las posiciones?
8. ¿Por qué da problemas leer el archivo de forma distinta al indexar y al releer?
9. Dos fuentes con rangos idénticos pero de archivos distintos: ¿qué IoU tienen?
10. ¿Por qué la duda "inclusivo/exclusivo" es casi irrelevante para el IoU pero sí relevante para un límite de longitud?

<details><summary>Respuestas rápidas (autoevaluación)</summary>

1. Un trozo de un archivo; el archivo entero es demasiado grande y poco específico para entregar o comparar.
2. `U` está en el offset 6. `[0:4]` da `HOLA`.
3. Archivo + rango (inicio y fin). Devolver direcciones permite comparar con el corrector sin mover texto y deja claro dónde está la información.
4. Que comparten alguna zona común dentro del mismo archivo.
5. Compartido = 50; total = 100 + 100 − 50 = 150; IoU = 50/150 ≈ 0.33.
6. 150/1500 = 0.10 (≥ 0.05, acierta); 40/1500 ≈ 0.027 (< 0.05, falla): el chunk grande diluye la proporción.
7. Un carácter puede ocupar varios bytes; cada uno de esos adelanta la cuenta y desplaza todo lo posterior.
8. Porque los saltos de línea pueden contar distinto, y las coordenadas dejarían de apuntar al mismo texto.
9. 0: archivos distintos nunca se comparan.
10. Un carácter de diferencia casi no mueve una proporción; pero 2000 frente a 2001 puede cruzar un límite estricto.
</details>

---

## 4. Vocabulario que ya puedes usar a partir de aquí

Corpus · chunk · offset (posición de carácter) · rango (inicio incluido, final excluido) · fuente (archivo + rango) · solapar · IoU y su umbral de 0.05.
