# 03 — El chunking

El *chunking* es la decisión de **cómo partir el corpus en fragmentos**. Es la etapa que más determina la calidad de la búsqueda, porque decide qué "piezas de respuesta" existirán en tu sistema. Si la pieza correcta no existe, ningún algoritmo la encontrará.

**Lo que te llevas de este archivo:** entenderás qué es un chunk, por qué partimos en vez de indexar archivos enteros, y cómo el **tamaño**, la **cobertura** y el **solape** de los chunks afectan a lo bien que podrás encontrar la respuesta.

---

## 1. Los conceptos, con palabras sencillas

**Chunk.**
Un chunk es un **trozo** de un archivo, junto con su ubicación (archivo + rango de caracteres, el vocabulario que ya conoces del archivo 02). En vez de indexar el archivo entero, lo cortamos en chunks y son ellos las "fichas" que el sistema buscará.

**¿Por qué no indexar archivos enteros?**
Por varias razones a la vez:
- Un archivo entero es **demasiado grande**: si lo usas como unidad, cuando lo recuperas le metes al modelo un montón de texto irrelevante en la ventana de contexto.
- **Diluye la relevancia**: la buena señal ("esto habla de caché") queda enterrada entre cientos de líneas que no vienen al caso.
- Hay un **límite de tamaño** que ninguna fuente puede superar (si lo supera, el resultado deja de ser válido).

Cortar en fragmentos permite que cada unidad sea **precisa y autocontenida**.

**Corte ciego frente a corte con sentido.**
La opción más simple es el **corte ciego**: cortar cada N caracteres sin mirar qué hay. Funciona, pero parte una función por la mitad o deja media tabla cortada. La alternativa es el **chunking estructural**: cortar por las **juntas naturales** del texto. Un archivo de código se corta entre funciones y clases; una página de documentación, entre secciones y párrafos. Como rebanar un pan por sus cortes en vez de a martillazos.

**Cobertura y solape.**
- **Cobertura**: que entre todos los chunks no queden **huecos**. Si dejas texto sin asignar a ningún chunk, cualquier respuesta que viva en ese hueco se vuelve inalcanzable.
- **Solape (overlap)**: que cada chunk **repita** un poquito del anterior, para no cortar una idea justo en la frontera. El precio es que aparecen chunks casi duplicados.

---

## 2. Profundizando

### El gran dilema: ¿cuán grande debe ser un chunk?

No hay una talla única. Hay un **compromiso** entre chunks grandes y pequeños:

| | Chunks **grandes** | Chunks **pequeños** |
|---|---|---|
| Contexto que llevan | Mucho: una idea suele caber entera | Poco: las ideas se parten |
| **Precisión** al localizar | Baja: el fragmento útil queda enterrado en mucho texto de relleno | Alta: cada chunk habla de menos cosas |
| Número de chunks | Pocos (búsqueda más ligera) | Muchos (más pesada) |
| Ruido que se le pasa al modelo | Mucho | Poco |
| Riesgo principal | Superar el límite de tamaño y diluir la señal | Cortar ideas y perder el hilo |

La idea que cuesta interiorizar: **un chunk grande que "contiene" la respuesta no es automáticamente un buen chunk**. Contiene la respuesta, sí, pero también cien líneas que no vienen al caso, y eso empobrece tanto la búsqueda como la respuesta final. La precisión importa.

**Conclusión de este apartado:** el tamaño del chunk no es un detalle; es una **palanca de calidad** que se ajusta probando y midiendo (más adelante verás cómo se mide).

### El techo duro de tamaño

Existe un **máximo** de tamaño por fragmento, y es un **techo, no un objetivo**. Significa:

- Tus chunks **pueden** ser más pequeños (de hecho, a menudo deben serlo) para ganar precisión.
- Ningún chunk **puede** superarlo. Si un solo resultado devuelto se pasa del límite, todo el resultado de esa consulta se invalida.

Por eso conviene diseñar con **margen** y con una "guardia" conceptual: que, pase lo que pase, nada supere el máximo. Un chunk distinto de tamaño según el contenido es lo normal.

### Cobertura: no dejar huecos

Imagina que decides ignorar los comentarios o las líneas en blanco al construir chunks. Cualquier respuesta que, por casualidad, viva en una de esas zonas **no se podrá recuperar jamás**, porque no pertenece a ningún chunk. La regla sana:

> La unión de todos los chunks de un archivo debería cubrir el archivo entero (o, como mínimo, todo lo que decidas excluir **conscientemente**).

Excluir con criterio (por ejemplo, un fichero de licencia) está bien; dejar huecos "por accidente" es lo que vuelve inalcanzables las respuestas que caen ahí.

### Solape: la palanca que sube el precio

Un solape del, digamos, 10–20 % del tamaño sirve para que una idea a caballo entre dos chunks no desaparezca. Pero tiene un coste: generas chunks que se parecen mucho entre sí y pueden **llenar el top-k con el mismo sitio**, dejando fuera otras partes relevantes. El solape es una palanca que **se prueba**, no una obligación.

### Cortar según el tipo de archivo

Un `.py` y un `.md` no se rompen igual:

- **Código**: las juntas naturales son las **definiciones** (funciones, clases). Ahí es donde una idea empieza y acaba. Además, el lenguaje de programación se puede **analizar** para saber exactamente dónde empieza y acaba cada definición, en lugar de adivinar.
- **Documentación**: las juntas naturales son los **títulos y párrafos**. Hay que respetar la jerarquía de secciones y no partir tablas o bloques de código.

Por eso se implementan **estrategias distintas** según el tipo de archivo. Lo verás con detalle cuando toque codificar; aquí basta con entender *por qué* son distintas: **cada formato tiene su estructura, y cortar por la estructura respeta el significado**.

### Piezas demasiado pequeñas y demasiado grandes

Dos casos que hay que resolver:
- **Piezas minúsculas** (una función de tres líneas, un párrafo de dos frases): generan muchísimos chunks pobres y sin contexto. La solución habitual es **agrupar piezas pequeñas vecinas** hasta acercarse al tamaño útil.
- **Piezas gigantes** (una función o una sección enorme): hay que **partirlas** en trozos válidos, cortando por el mejor límite natural disponible.

### Qué es un "buen chunk"

Un criterio práctico para reconocerlo:
- Contiene una **idea completa** (una función, una sección).
- Es **autoexplicativo**: se entiende sin depender de los chunks vecinos.
- Tiene un **tamaño razonable** (ni ridículo, ni al límite).
- Su rango de caracteres es **exacto** respecto al archivo original.

---

## 3. Preguntas para comprobar que lo entiendes

1. ¿Por qué no indexamos archivos enteros? Da al menos tres razones.
2. ¿Qué diferencia hay entre el "corte ciego" y el "chunking estructural"? ¿Por qué el segundo respeta mejor el significado?
3. Un chunk gigante que contiene la respuesta correcta, ¿es necesariamente un buen chunk? Explica por qué sí o por qué no.
4. ¿Por qué el tamaño máximo de un chunk se describe como un "techo" y no como un "objetivo"?
5. ¿Qué problema crea dejar un hueco (texto que no pertenece a ningún chunk)? Pon un ejemplo.
6. ¿Para qué sirve el solape entre chunks y qué precio tiene?
7. ¿Por qué el código y la documentación usan estrategias de corte distintas?
8. ¿Qué haces con veinte funciones diminutas seguidas? ¿Y con una sola función gigantesca?
9. Enumera las cuatro propiedades de un "buen chunk".

<details><summary>Respuestas rápidas</summary>

1. Un archivo entero es demasiado grande, diluye la relevancia del fragmento útil y puede superar el límite de tamaño permitido por fuente.
2. Ciego corta cada N caracteres sin mirar; estructural corta por las juntas naturales (funciones/clases, secciones/párrafos). El segundo respeta las unidades de significado.
3. No. Aunque contenga la respuesta, arrastra mucho texto irrelevante: baja la precisión y ensucia la búsqueda y la respuesta.
4. Porque es el máximo permitido: los chunks suelen ser más pequeños para ganar precisión, pero ninguno puede superarlo.
5. Cualquier respuesta situada en ese hueco se vuelve irrecuperable, porque no pertenece a ningún chunk. Ej.: ignorar los comentarios de un `def` deja inalcanzable lo que ahí se explique.
6. Evita cortar una idea justo en la frontera; el precio es que aparecen chunks casi duplicados que pueden acaparar puestos del top-k.
7. Porque su estructura es distinta: el código se organiza en definiciones analizables; la documentación, en títulos y párrafos.
8. Las diminutas se agrupan con sus vecinas hasta un tamaño útil; la gigante se parte en trozos válidos por el mejor límite natural.
9. Idea completa, autoexplicativo, tamaño razonable, rango exacto respecto al original.
</details>
