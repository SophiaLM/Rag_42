# Parte 2 — Los datos del proyecto: qué entra, qué sale y qué significa cada pieza

Tu sistema recibe "formularios" y entrega "formularios". Esta parte explica **qué representa cada uno y por qué existe**, para que cuando los veas en el subject no sean nombres sueltos, sino piezas de una historia. (Asumo que ya sabes que son modelos de pydantic, es decir, formularios con campos y tipos; aquí nos centramos en su *significado*.)

---

## 1. Conceptos nuevos — la versión sencilla

**Pregunta con identificador (`question_id`)**
Cada pregunta lleva un número de DNI (el `question_id`) además de su texto. El DNI sirve para que, al final, nadie confunda tu respuesta a la pregunta A con la respuesta a la B.

**UUID (y `uuid4`)**
Un UUID es un identificador larguísimo, como `3f2b8c1e-9d4a-4e7b-a1c5-0b6f2d8e7a43`, que se genera **al azar** y tiene una probabilidad prácticamente nula de repetirse. `uuid4` es el tipo que se genera aleatoriamente (existen otros tipos que se calculan a partir de datos). La gracia: puedes dar un DNI único a cada pregunta **sin que nadie tenga que coordinarse** ni llevar una lista de los números ya usados.

**Valor por defecto generado (`default_factory`)**
En el modelo de pregunta, el DNI se rellena solo si no lo proporcionas: *cada vez* que se crea una pregunta nueva, se llama a una pequeña receta que fabrica un uuid4 nuevo. (Por eso se usa una "fábrica" y no un valor fijo: un valor fijo daría el mismo DNI a todas las preguntas.)

**Pregunta sin responder (`UnansweredQuestion`)**
Solo trae lo mínimo: `question_id` y `question`. Es lo que **tu sistema recibe**: un examen en blanco.

**Pregunta respondida (`AnsweredQuestion`)**
Es una pregunta sin responder **más** dos campos: `sources` (las fuentes correctas, es decir, dónde está realmente la respuesta) y `answer` (una respuesta de referencia). Es el **solucionario**: lo que el corrector usa para comprobar tu trabajo. Hereda los campos de la anterior, como una ficha de empleado hereda los datos de la ficha de candidato y añade otros.

**Dataset (`RagDataset`)**
La **caja** que contiene muchas preguntas. Una caja puede contener preguntas respondidas, sin responder, o mezcla (esa es la razón del símbolo `|` en `AnsweredQuestion | UnansweredQuestion`: "cada elemento puede ser de uno u otro tipo").

**Fuente mínima (`MinimalSource`)**
La dirección que ya conoces de la Parte 1, en forma de formulario: `file_path` (qué archivo), `first_character_index` (dónde empieza el rango) y `last_character_index` (dónde termina).

**Resultados de búsqueda y respuestas**
- `MinimalSearchResults`: *"para esta pregunta, estas son las fuentes que recuperé"* (`question_id`, `question`, `retrieved_sources`).
- `MinimalAnswer`: lo mismo **más** el texto de la respuesta generada.
- `StudentSearchResults` y `StudentSearchResultsAndAnswer`: la **caja** con todos esos resultados y el `k` usado. Se llaman "Student" simplemente porque son *tu* entrega, en contraste con el solucionario.

---

## 2. Profundizando

**Lo que debes llevarte de aquí:** (1) ver los modelos como un **viaje de información** en tres momentos; (2) entender por qué `first_character_index` y `last_character_index` son el corazón de todo y no simples "datos extra"; (3) saber por qué el `question_id` nunca debe cambiar.

### El viaje de la información

```
  EXAMEN EN BLANCO                TU BÚSQUEDA                  TU GENERACIÓN
 (dataset sin responder) ──►  StudentSearchResults  ──►  StudentSearchResultsAndAnswer
 preguntas: id + texto         id + texto +                  id + texto + fuentes
                               fuentes recuperadas           + respuesta redactada
                                      │
                                      ▼
                 SOLUCIONARIO (dataset respondido): id + texto + fuentes correctas + respuesta
                          el corrector compara tus fuentes con las del solucionario
```

El mismo nombre de archivo existe en las dos carpetas de datasets: la versión "sin responder" es la que recibes; la "respondida" es la que usa el corrector. Se emparejan **por `question_id`**. Si tú cambiaras un id, tu respuesta quedaría sin pareja y sería como si no hubieras contestado.

### Por qué `first_character_index` y `last_character_index` son tan importantes

No son "metadatos": son las coordenadas que la Parte 1 explicó, y se usan en **tres sitios** distintos:

1. **El corrector las compara** con las del solucionario (mediante IoU) para decidir si acertaste. Sin ellas, tu búsqueda no se puede puntuar.
2. **El generador las usa para reconstruir el texto.** Fíjate: los resultados de búsqueda guardan *direcciones*, no texto. Para redactar la respuesta, el sistema tiene que volver al archivo y leer justo ese rango. (Por eso importa que indexar y releer lean el archivo igual.)
3. **Imponen un límite.** El corrector rechaza cualquier fuente que mida más de 2000 caracteres, y la medida sale precisamente de la resta entre ambos índices. Una sola fuente demasiado larga invalida toda la entrega.

### Por qué la ruta `file_path` es delicada

Es una cadena de texto que se compara **al pie de la letra**. Dos rutas que "apuntan al mismo archivo" pero se escriben distinto (con `./` delante, absoluta en lugar de relativa) son, para el corrector, archivos diferentes, y el acierto es imposible. Es una identidad, no una referencia flexible.

### El identificador: el hilo que une todo

El `question_id` viaja intacto desde el dataset hasta tu salida. Es lo que permite que, entre 100 preguntas, el corrector sepa cuál es cuál. Puede ser un uuid4 o un texto sencillo como `"q1"`; lo que importa es que **lo conserves tal cual**.

### El campo `k` dentro de los resultados

Los resultados incluyen el `k` con el que se hicieron. Es una constancia: "con estas reglas busqué". El corrector lo necesita para saber hasta qué posición mirar tu lista.

### La unión de tipos y la herencia, sin misterio

- **Herencia** (`AnsweredQuestion` hereda de `UnansweredQuestion`): lo común se escribe una vez; lo propio, aparte.
- **Unión** (`A | B`): una lista que acepta elementos de varios tipos. Es lo que permite que **la misma caja** sirva para cargar preguntas con o sin solución. Tu código de búsqueda solo debe depender de lo que ambas comparten (`question_id` y `question`).

### Los modelos son un mínimo, no un máximo

El subject permite añadir campos o modelos nuevos (por ejemplo, una puntuación en cada resultado). Pero lo que ya está **no se toca**: es el contrato mínimo que el corrector espera.

### Resumen de piezas

| Modelo | Qué representa | Quién lo produce / lee |
|---|---|---|
| `UnansweredQuestion` | Pregunta del examen | Se lee (entrada) |
| `AnsweredQuestion` | Pregunta + fuentes correctas + respuesta de referencia | Se lee (solucionario) |
| `RagDataset` | Caja de preguntas | Se lee |
| `MinimalSource` | Dirección: archivo + rango | Tu búsqueda la produce |
| `MinimalSearchResults` | Pregunta + fuentes que recuperaste | Tu búsqueda |
| `MinimalAnswer` | Lo anterior + respuesta redactada | Tu generación |
| `StudentSearchResults(AndAnswer)` | Caja con todos los resultados + `k` | Tu entrega |

---

## 3. Diez preguntas que responder antes de programar

1. ¿Para qué sirve un uuid4 y por qué se puede generar sin una lista central de números usados?
2. ¿Por qué el identificador de la pregunta usa una "fábrica" en lugar de un valor fijo?
3. ¿Qué campos tiene `UnansweredQuestion` y cuáles añade `AnsweredQuestion`?
4. ¿Qué es un `RagDataset` y por qué su lista admite `AnsweredQuestion | UnansweredQuestion`?
5. ¿Cuál de los dos tipos de dataset recibe tu sistema como entrada y cuál usa el corrector como solucionario?
6. ¿Qué tres usos tienen `first_character_index` y `last_character_index`?
7. ¿Por qué los resultados de búsqueda no incluyen el texto de los fragmentos?
8. ¿Qué ocurriría si cambias el `question_id` de una pregunta en tu salida?
9. ¿Por qué `file_path` debe ser idéntico al del corpus y no "equivalente"?
10. ¿Qué diferencia hay entre `StudentSearchResults` y `StudentSearchResultsAndAnswer`?

<details><summary>Respuestas rápidas (autoevaluación)</summary>

1. Para dar un identificador único a cada elemento; al ser aleatorio y larguísimo, la probabilidad de repetición es despreciable, así que no hace falta coordinarse.
2. Para que cada pregunta nueva reciba un uuid distinto; un valor fijo daría el mismo a todas.
3. `question_id` y `question`; `AnsweredQuestion` añade `sources` y `answer`.
4. La caja que contiene muchas preguntas; acepta ambos tipos porque la misma estructura se usa para cargar preguntas con y sin solución.
5. Entrada: el dataset sin responder; solucionario: el respondido.
6. Que el corrector compare (IoU), que el generador relea el texto de ese rango, y medir/limitar la longitud de la fuente.
7. Porque guardan direcciones; el texto se reconstruye leyendo el archivo en ese rango cuando hace falta.
8. Tu resultado no tendría pareja en el solucionario: contaría como pregunta sin contestar.
9. Porque se compara como texto literal; una ruta escrita distinto es otro archivo para el corrector.
10. El segundo añade la respuesta redactada a cada resultado.
</details>

---

## 4. Vocabulario que ya puedes usar a partir de aquí

`question_id` y uuid4 · pregunta sin responder / respondida (solucionario) · dataset (`RagDataset`) · `MinimalSource` y sus tres campos · resultados de búsqueda frente a resultados con respuesta · "Student" = tu entrega.
