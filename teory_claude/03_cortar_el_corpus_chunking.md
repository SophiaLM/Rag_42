# Parte 3 — Cortar el corpus: la teoría del chunking

Ya sabes qué es un chunk y cómo se describe (archivo + rango). Ahora toca la pregunta de fondo: **¿por dónde y en qué tamaño se corta?** Es una decisión pequeña en apariencia, pero marca el techo de calidad de todo lo que viene después.

---

## 1. Conceptos nuevos — la versión sencilla

**Chunking**
El acto de trocear un archivo en chunks. Es como convertir una enciclopedia en fichas: cuanto mejor cortes, más útil será cada ficha.

**Corte ciego**
Cortar cada N caracteres sin mirar qué hay. Como cortar un pan con un cuchillo cada 3 cm sin fijarte en dónde están las rebanadas: a veces partes una función por la mitad o dejas una frase colgando.

**Corte estructural**
Cortar por las "juntas naturales" del texto: entre funciones y clases en código, entre secciones y párrafos en documentación. Como separar el pan por sus rebanadas.

**Árbol de sintaxis (AST)**
Cuando Python lee un archivo de código, lo convierte en un **árbol**: el módulo contiene clases, las clases contienen métodos, los métodos contienen instrucciones. Cada nodo del árbol "sabe" en qué línea empieza y en cuál acaba. Es como tener el plano de un edificio en lugar de solo ver la fachada: sabes dónde acaba cada habitación.

**Solape entre chunks (repetición)**
Hacer que chunks vecinos **compartan** un pequeño trozo en la frontera, para que una idea que cae justo en el corte no quede partida sin remedio. Como cortar una pizza dejando que cada porción se pase un poquito de la anterior. *(No lo confundas con el "solapar" de la Parte 1: aquel era una comparación entre rangos para puntuar; este es una decisión de cómo cortar.)*

**Empaquetado voraz (greedy packing)**
Cuando tienes muchas piezas diminutas seguidas (por ejemplo, diez funciones de tres líneas), las vas metiendo en la misma maleta **mientras quepan**; cuando no caben más, abres otra maleta. Evita fichas minúsculas sin contexto.

**Cobertura**
Que todo el archivo pertenezca a algún chunk. Si dejas huecos sin cubrir, cualquier respuesta que viva en un hueco **no se podrá encontrar jamás**.

---

## 2. Profundizando

**Lo que debes llevarte de aquí:** (1) el chunk es la **unidad mínima que tu búsqueda puede devolver**, así que si el chunk correcto no existe, no hay algoritmo que lo encuentre; (2) el tamaño del chunk es una palanca con **dos efectos opuestos** (contexto frente a precisión), y puedes razonarlo con el IoU; (3) cortar por estructura casi siempre supera a cortar a ciegas, y por qué.

### Por qué el chunk limita todo lo demás

La búsqueda no puede devolver nada más pequeño ni más grande que un chunk. Si la respuesta está partida entre dos chunks, ninguno de los dos la contiene entera. Si el chunk es enorme, la respuesta queda diluida entre mucho texto irrelevante. El resto del sistema (puntuar, ordenar, generar) trabaja sobre lo que el chunking le sirve en bandeja.

### El tamaño: dos fuerzas opuestas

Lo que debes aprender aquí es a **razonar el equilibrio**, no a memorizar un número:

| Si el chunk es grande… | Si el chunk es pequeño… |
|---|---|
| ✔ Una idea suele caber entera (más contexto) | ✘ Una idea puede quedar partida |
| ✘ El IoU contra una fuente pequeña se diluye | ✔ El IoU contra una fuente pequeña es mejor |
| ✘ Más texto irrelevante al entregarlo al modelo | ✔ Entrega más limpia |
| ✔ Menos chunks que gestionar | ✘ Muchos chunks casi iguales pueden llenar el top-k |

**Cómo se conecta con el IoU (ejemplo guiado).** Supón que la fuente correcta mide 100 caracteres y tu chunk la contiene entera:
- Chunk de 2000 → IoU = 100/2000 = **0.05** → justo en el límite del umbral.
- Chunk de 1000 → IoU = 0.10 → cómodo.
- Chunk de 400 → IoU = 0.25 → muy cómodo.

Y la otra cara: si el chunk es *tan* pequeño que parte la idea, el contenido útil queda repartido en varios chunks y cada uno por separado puede ser demasiado pobre para puntuar bien. Por eso no existe un tamaño "correcto" universal: se **mide** probando varios y viendo cuál funciona mejor con tus datos (ese es el tipo de experimento que se espera que hagas).

### El techo máximo

El proyecto impone un tamaño máximo (por defecto 2000 caracteres): ningún chunk devuelto puede superarlo. Es un **techo**, no un objetivo. Se puede cortar más pequeño; no más grande.

### Cortar por estructura: la teoría

**En código Python.** La unidad natural es la *definición*: una función, una clase, un método. El árbol de sintaxis te dice dónde empieza y acaba cada una, y de ahí sacas las coordenadas. Detalles conceptuales que conviene entender:
- El árbol da **líneas**, pero tú necesitas **caracteres**: hay que traducir "línea 42" al offset del primer carácter de esa línea.
- Hay texto que el árbol no asigna a ninguna definición (comentarios previos, líneas en blanco, decoradores): si no decides a quién pertenece, aparecen huecos.
- Una clase muy grande se "abre" y se corta por sus métodos; una función muy grande no tiene juntas internas fáciles y se corta por tramos.
- Si el archivo no se puede leer como Python válido, hay que tener un **plan B** (corte por tramos).

**En Markdown y texto de documentación.** La unidad natural es la *sección* (lo que cuelga de un título) y dentro de ella, el *párrafo*. Un matiz importante: dentro de un bloque de código incrustado en el Markdown, un símbolo `#` es un comentario, no un título; hay que saber cuándo estás "dentro" de uno. Otro: un párrafo suelto sin su título pierde su tema, así que el título es información valiosa que no conviene separar del contenido.

**Plan B común.** Cuando la estructura falla, se corta por tramos de tamaño fijo, pero **buscando una frontera razonable** (salto de línea, espacio) cercana, en vez de partir una palabra por la mitad.

### Por qué importa "empaquetar" piezas pequeñas

Un chunk de 30 caracteres (por ejemplo, solo un `import`) casi no contiene información: puntúa raro, ocupa un puesto del top-k y aporta ruido. Agrupar piezas pequeñas vecinas hasta un tamaño razonable produce fichas con sentido.

### Solape entre chunks: ¿útil o peligroso?

A favor: reduce el riesgo de partir una idea en la frontera. En contra: genera chunks casi duplicados; si dos vecinos casi idénticos ocupan los puestos 1 y 2 del top-k, desperdicias un puesto que podría servir a otra fuente. No es ni bueno ni malo: es otra palanca que se prueba.

### Cobertura y qué excluir

Que un trozo no esté en ningún chunk lo hace invisible. Excluir cosas es legítimo, pero debe ser una **decisión consciente** (por ejemplo, ignorar binarios o archivos generados), no un efecto secundario de cómo cortas. Del mismo modo, qué *tipos* de archivo indexas decide qué preguntas podrás contestar: si una pregunta se responde con un archivo de configuración y no lo indexaste, no hay forma de acertar.

### Cómo se razona una decisión de chunking

1. ¿Qué tipo de contenido es? (código, documentación, otro) → qué junturas naturales tiene.
2. ¿Qué tamaño de fuente correcta espero? → qué tamaño de chunk mantiene el IoU sano.
3. ¿Qué pasa en el peor caso? (línea gigante, archivo sin estructura) → plan B.
4. ¿Cómo lo comprobaré? → comparar con el corte ciego usando una métrica (Parte 5).

---

## 3. Diez preguntas que responder antes de programar

1. ¿Por qué el chunk limita la calidad máxima de toda la búsqueda?
2. ¿Qué problema concreto tiene el corte ciego?
3. ¿Qué información te da el árbol de sintaxis de cada nodo y para qué te sirve?
4. ¿Por qué hay que traducir "líneas" a "caracteres" al usar el árbol?
5. Una fuente correcta mide 80 caracteres. Calcula el IoU si tu chunk de 1600 la contiene entera. ¿Pasa el umbral de 0.05?
6. ¿Por qué un chunk demasiado pequeño también perjudica?
7. ¿Qué es el empaquetado voraz y qué problema resuelve?
8. ¿Qué es el solape entre chunks y qué riesgo trae para el top-k?
9. ¿Qué pasa con una respuesta que vive en un hueco que ningún chunk cubre?
10. En Markdown, ¿por qué no basta con "cortar en cada `#`"?

<details><summary>Respuestas rápidas (autoevaluación)</summary>

1. Porque la búsqueda solo puede devolver chunks; si el chunk adecuado no existe (partido o diluido), nadie puede encontrarlo.
2. Parte funciones o ideas por la mitad, dejando la respuesta repartida en fichas incompletas.
3. Dónde empieza y acaba (líneas) cada definición; sirve para cortar por funciones/clases completas.
4. Porque las fuentes se expresan en posición de carácter, no en número de línea.
5. 80/1600 = 0.05 → justo en el umbral (límite exacto; arriesgado: un chunk algo menor da más margen).
6. Parte las ideas y deja cada chunk con poca información para puntuar bien; además llena el top-k de fichas similares.
7. Agrupa piezas pequeñas contiguas hasta un tamaño razonable; evita fichas minúsculas sin contexto.
8. Zona repetida entre vecinos; puede llenar los primeros puestos con casi lo mismo y desperdiciar posiciones.
9. No se puede recuperar nunca: ningún resultado la contiene.
10. Porque dentro de bloques de código incrustados un `#` es un comentario, no un título; hay que saber si estás "dentro" de uno.
</details>

---

## 4. Vocabulario que ya puedes usar a partir de aquí

Chunking · corte ciego frente a estructural · AST (árbol de sintaxis) · solape entre chunks · empaquetado voraz · cobertura · techo de tamaño · el equilibrio contexto/precisión del tamaño.
