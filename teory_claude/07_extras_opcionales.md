# Parte 7 — Ideas para ir más allá (extras opcionales)

Esta parte es opcional: reúne los conceptos nuevos que aparecen en los extras del proyecto. Solo tiene sentido abordarla cuando lo esencial (Partes 0 a 6) esté claro. Aquí solo hay teoría; no hay nada que construir todavía.

---

## 1. Conceptos nuevos — la versión sencilla

**Embedding (vector de significado)**
Un modelo especial convierte un texto en **una lista de números** (un vector) de forma que textos con **significado parecido** quedan con números parecidos. Imagina un mapa donde cada texto es un punto: "lanzar el servidor" y "start the service" caen en el mismo barrio aunque no compartan ni una palabra. Es lo que la búsqueda léxica no puede hacer.

**Similitud entre vectores (coseno)**
Para saber qué tan cerca están dos puntos del mapa se mide el **ángulo** entre sus flechas: ángulo pequeño = mismo sentido = significado parecido. El resultado va de -1 a 1; cuanto más alto, más parecidos.

**Búsqueda híbrida**
Combinar el ranking léxico (palabras) y el semántico (significado) en **una sola lista**. Cada uno acierta donde el otro falla: el léxico clava los nombres literales; el semántico entiende las paráfrasis.

**Fusión por rangos (RRF)**
Una forma sencilla de mezclar dos rankings: cada resultado suma puntos según **su posición** en cada lista (los primeros dan más), y gana quien más suma. Es como dos jueces que entregan su clasificación y se suman los puestos. Su ventaja: no importa que las puntuaciones de ambos buscadores estén en escalas distintas, porque solo se usan posiciones.

**Huella (hash) de un archivo**
Un "resumen" corto del contenido de un archivo, calculado de forma que **si el archivo cambia aunque sea un carácter, la huella cambia**. Sirve para saber si un archivo se ha modificado sin tener que comparar todo su contenido.

**Indexación incremental**
En lugar de rehacer toda la biblioteca cuando cambia un libro, **solo reindexas ese libro**. Para saber cuál cambió, guardas un **registro** (manifiesto) con la huella de cada archivo y los chunks que produjo.

**Caché**
Una **libreta de resultados ya calculados**. Si te hacen la misma pregunta dos veces, no repites el trabajo: miras la libreta. Una caché tiene un riesgo clásico: que el resultado guardado esté **desactualizado** (*invalidación*).

**API HTTP local**
Una forma de que **otros programas** (no solo una persona escribiendo órdenes) hablen con tu sistema. Es un "mostrador de atención" abierto en tu ordenador: el cliente envía una petición a una dirección concreta (*endpoint*), y recibe una respuesta, normalmente en JSON. "Local" significa que el mostrador solo es accesible desde tu propia máquina.

---

## 2. Profundizando

**Lo que debes llevarte de aquí:** (1) entender **qué problema concreto resuelve cada extra** (qué limitación del sistema base ataca); (2) saber cuál es su **coste** (tiempo, memoria, complejidad); (3) reconocer la regla común: un extra solo suma si lo base es sólido.

### Por qué existe cada extra

| Extra | Limitación que ataca | Coste |
|---|---|---|
| Embeddings | La búsqueda léxica no entiende sinónimos ni paráfrasis | Calcular vectores de todos los chunks tarda; ocupan memoria |
| Híbrido | Ni léxico ni semántico aciertan solos en todo | Mantener dos índices y decidir cómo mezclar |
| Incremental | Reindexar todo por un cambio pequeño es lento | Hay que llevar un registro y recalcular algunas estadísticas |
| Caché | Repetir cálculos idénticos | Riesgo de resultados obsoletos |
| API HTTP | Solo se puede usar a mano | Gestionar entradas, errores y estado compartido |

### Embeddings y búsqueda semántica

El proceso es paralelo al léxico: al indexar, calculas un vector por chunk y lo guardas; al buscar, conviertes la pregunta en vector y localizas **los vectores más cercanos**. Dos matices:

- Los modelos de embeddings **ligeros** (los que caben en una CPU normal) son rápidos pero menos finos que los grandes; sirven para ganar recall en preguntas parafraseadas.
- Calcular vectores para miles de chunks **tarda de verdad**, y se paga al indexar. Es un coste a planificar, no un detalle.

### Híbrido: cómo se mezcla

Dos estrategias habituales:

- **RRF** (por posiciones): cada resultado suma `1 / (c + posición)` por cada lista en la que aparece, con una constante `c` (se suele usar un valor alrededor de 60) que suaviza la ventaja de los primeros puestos.
- **Suma ponderada** de puntuaciones: `α · léxico + (1 − α) · semántico`; exige normalizar antes las puntuaciones (porque las escalas son distintas) y elegir `α`.

Se evalúa como cualquier cambio (Parte 5): línea base, un cambio, medir docs y code por separado. Lo esperable es que el híbrido ayude sobre todo en **documentación parafraseada**.

### Incremental: la dificultad escondida

Añadir o quitar un archivo parece local, pero la puntuación BM25 depende de **estadísticas globales** (número total de chunks, largo medio, IDF de cada palabra). Cuando cambia un archivo, esos números cambian para **todos**. Por eso un índice incremental debe **recalcular las estadísticas globales** a partir de lo almacenado, sin releer todo el corpus. Las tres situaciones a gestionar: archivo **nuevo** (añadir), **modificado** (quitar sus chunks viejos y añadir los nuevos) y **borrado** (quitar sus chunks).

### Caché: la pregunta clave es "¿cuándo deja de valer?"

Una caché de consultas guarda `(pregunta, k) → resultados`. Pero si el índice cambia, los resultados guardados dejan de ser válidos. La solución conceptual: que la **clave** de la caché incluya una marca de la **versión del índice**; si el índice cambia, las entradas viejas ya no coinciden. También conviene **acotar su tamaño** para que no crezca sin límite.

Hay dos "cachés" distintas que conviene no mezclar: la de **cargar el índice** (que acelera el arranque) y la de **resultados de consultas** (que acelera las repeticiones).

### API HTTP: ideas mínimas

- **Cliente y servidor**: el servidor espera peticiones; el cliente las envía.
- **Endpoint**: cada "mostrador" tiene una dirección y una función (uno para buscar, otro para responder).
- **Entrada/salida en JSON**: aprovechas los mismos formularios (modelos) de la Parte 2.
- **Códigos de estado**: el servidor responde con un número que indica qué pasó: éxito, petición incorrecta (error del cliente), fallo interno (error del servidor). Una entrada rara debe producir un error **claro del cliente**, no un fallo interno.
- **Coste de arranque**: cargar índice y modelo es caro; se hace **una vez al arrancar**, no en cada petición.

### Regla común a todos los extras

Un extra solo cuenta si funciona de verdad (no basta con describirlo) y solo se valora si lo obligatorio es sólido. Si tuvieras que elegir por valor y coste, lo más rentable suele ser lo que **ataca una limitación medida** en tu sistema, no lo que suena más sofisticado.

---

## 3. Diez preguntas que responder antes de programar

1. ¿Qué es un embedding y qué ventaja tiene sobre contar palabras?
2. ¿Qué mide la similitud coseno entre dos vectores?
3. ¿Qué problema resuelve combinar ranking léxico y semántico?
4. ¿Cómo funciona RRF y por qué no necesita que las puntuaciones estén en la misma escala?
5. ¿Qué es una huella de archivo y qué permite hacer en la indexación incremental?
6. ¿Por qué cambiar un solo archivo obliga a recalcular estadísticas globales de BM25?
7. ¿Qué tres situaciones debe gestionar una indexación incremental?
8. ¿Qué riesgo tiene una caché de consultas y cómo se evita conceptualmente?
9. ¿Qué significa que una API sea "local" y qué es un endpoint?
10. ¿Por qué el índice y el modelo deben cargarse una sola vez al arrancar la API y no en cada petición?

<details><summary>Respuestas rápidas (autoevaluación)</summary>

1. Un vector que representa el significado de un texto; permite encontrar textos parecidos aunque no compartan palabras.
2. Cuánto se parecen en dirección (significado); cuanto más cerca de 1, más parecidos.
3. Que cada método acierta donde el otro falla (nombres literales frente a paráfrasis).
4. Cada resultado suma puntos según su posición en cada lista; como solo usa posiciones, las escalas de puntuación no importan.
5. Un resumen del contenido que cambia si el archivo cambia; sirve para detectar qué archivos se modificaron sin comparar todo el texto.
6. Porque el número de chunks, el largo medio y los IDF dependen de todo el corpus y cambian al añadir o quitar chunks.
7. Archivo nuevo, modificado y borrado.
8. Devolver resultados obsoletos tras cambiar el índice; se evita incluyendo la versión del índice en la clave de la caché (y limitando su tamaño).
9. Que solo se accede desde tu propia máquina; el endpoint es la dirección concreta a la que se envía una petición para una función concreta.
10. Porque cargarlos es caro; hacerlo en cada petición haría la API lentísima e inviable.
</details>

---

## 4. Vocabulario que ya puedes usar a partir de aquí

Embedding y similitud coseno · búsqueda híbrida y RRF · huella (hash) y manifiesto · indexación incremental · caché e invalidación · API HTTP, endpoint, cliente/servidor, código de estado.
