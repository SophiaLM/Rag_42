# 04 — Los modelos de datos (las estructuras)

Las etapas del pipeline no se intercambian texto suelto: se intercambian **estructuras con una forma fija**. Eso es lo que en este proyecto llamamos *modelos de datos*. Este archivo responde a tres preguntas que suelen quedar flotando: **¿qué es cada modelo?, ¿por qué los campos son esos?, ¿y por qué la posición (los offsets) es parte de la estructura?**

**Lo que te llevas:** sabrás leer el "árbol" de estructuras del sistema y entenderás el papel de `MinimalSource`, `UnansweredQuestion`, `AnsweredQuestion` y `RagDataset`, y de campos como `first_character_index` y `last_character_index`.

---

## 1. Los conceptos, con palabras sencillas

**Modelo de datos (o esquema).**
Un modelo de datos es la **forma** que debe tener un dato: qué campos tiene, de qué tipo es cada uno y cuáles son obligatorios. Piensa en un **formulario oficial**: si el campo "fecha" debe ser una fecha, no vale escribir "ayer". Un sistema que se pasa formularios entre etapas necesita que todos usen **el mismo formato**.

**Validación.**
Es la comprobación de que un dato encaja con su modelo. Si falta un campo obligatorio o un número es de un tipo equivocado, queremos que salte un **error claro en el punto de entrada**, y no un fallo misterioso tres pasos después.

**Serializar / deserializar.**
Serializar = convertir una estructura en **texto** (normalmente **JSON**) para guardarla o enviarla. Deserializar = leer ese texto y **reconstruir** la estructura. Es "guardar la partida" y "volver a cargarla", pero con datos: permite que el resultado de una etapa se guarde en un archivo y otra etapa lo lea después.

**uuid4.**
Un **UUID** ("identificador único universal") es un número enormemente grande (128 bits) que se genera de forma **aleatoria** y que en la práctica **nunca colisiona** con otro. `uuid4` es la variante basada en aleatoriedad. Se usa para dar a cada pregunta un `question_id` único **sin coordinarse con nadie**: dos personas generando ids por separado no producirán el mismo. Es como un número de ticket que se imprime solo y que nadie más va a repetir.

**Herencia de modelos.**
Un modelo puede **extenderse**: partir de otro y añadirle campos. Un `AnsweredQuestion` *es* una `UnansweredQuestion` más `sources` y `answer`. Como una ficha de candidato (datos personales) que se convierte en ficha de empleado (datos personales **+** sueldo y puesto).

---

## 2. Profundizando

### El árbol de estructuras

```
MinimalSource      ── file_path, first_character_index, last_character_index

UnansweredQuestion ── question_id, question
   └─ AnsweredQuestion  = lo anterior + sources (lista de MinimalSource) + answer

RagDataset         ── rag_questions: lista de AnsweredQuestion | UnansweredQuestion

MinimalSearchResults       ── question_id, question, retrieved_sources (lista de MinimalSource)
   └─ MinimalAnswer        = lo anterior + answer

StudentSearchResults           ── search_results: lista de MinimalSearchResults, + k
StudentSearchResultsAndAnswer  ── search_results: lista de MinimalAnswer,        + k
```

Léelo como un viaje: entra un **dataset** de preguntas (`RagDataset`); tu **búsqueda** produce `StudentSearchResults`; tu **generación** produce `StudentSearchResultsAndAnswer`.

### `MinimalSource`: la pieza fundamental

`MinimalSource` representa **una fuente de información**: un trozo de un archivo. Sus tres campos son:

| Campo | Qué es |
|---|---|
| `file_path` | La ruta **exacta** del archivo dentro del corpus (archivo 02). |
| `first_character_index` | El **offset** donde empieza el trozo (primer carácter incluido). |
| `last_character_index` | El **offset** donde termina. |

**¿Por qué estos campos son tan importantes?** Porque un resultado de búsqueda **no es un texto**, es una **ubicación**: "la respuesta está *aquí dentro*". Y localizar necesita las tres cosas: el archivo y las dos coordenadas. Recuerda del archivo 02 que encontrar la fuente exige **el mismo archivo** y un **rango que se solape** con el correcto. Por eso `MinimalSource` es la estructura con la que se compara todo: es la que permite decir "acerté" o "fallé".

**¿Son parte de una estructura?** Sí: `MinimalSource` no vive sola. Es el **tipo de los elementos de las listas** que aparecen dentro de las preguntas, de los datasets y de los resultados (mira el árbol: `sources` y `retrieved_sources` son listas de `MinimalSource`). Es la pieza que se repite en todas las estructuras grandes.

> Detalle práctico: `first_character_index` y `last_character_index` deben cumplir reglas básicas —`first >= 0`, `last > first`— y el trozo no debe superar el límite de tamaño. Validarlas en el propio modelo evita fabricar una fuente inválida "en el origen", en lugar de descubrirlo al final.

### `UnansweredQuestion` y `AnsweredQuestion`

- **`UnansweredQuestion`** representa una pregunta **sin respuesta**: solo tiene `question_id` (el UUID de arriba) y `question` (el texto de la pregunta). Es lo que hay antes de que el sistema trabaje.
- **`AnsweredQuestion`** es una `UnansweredQuestion` **con la respuesta añadida**: hereda `question_id` y `question`, y añade `sources` (las fuentes correctas, una lista de `MinimalSource`) y `answer` (el texto de la respuesta esperada). Es lo que hay en un dataset "con respuestas correctas".

La diferencia importa en la práctica: cuando el sistema **busca para todo un dataset**, solo puede contar con `question_id` y `question`, porque puede estar trabajando sobre preguntas **sin respuesta**. Las `sources` y el `answer` son el patrón de referencia con el que luego se mide si acertaste.

### `RagDataset`: el dataset completo

`RagDataset` es simplemente un **contenedor**: una lista de preguntas bajo el campo `rag_questions`. Cada elemento puede ser **una pregunta sin responder o una respondida** (`AnsweredQuestion | UnansweredQuestion`), porque un mismo tipo de dataset sirve para dos momentos: el de "aquí están las preguntas para que las busques" y el de "aquí están las preguntas con su respuesta correcta para comparar".

### Los resultados de tu sistema

- **`MinimalSearchResults`**: lo que produce la búsqueda para **una** pregunta. Tiene `question_id`, `question` y `retrieved_sources` (los `MinimalSource` que encontró tu sistema, ya ordenados).
- **`MinimalAnswer`**: igual que el anterior pero **+ `answer`**, el texto que generó el modelo.
- **`StudentSearchResults`**: el resultado de buscar en **todo** un dataset. Envuelve una lista de `MinimalSearchResults` más un campo `k` (recuerda: cuántas fuentes pediste por pregunta).
- **`StudentSearchResultsAndAnswer`**: lo mismo pero con la lista de `MinimalAnswer`.

Así, buscar sobre 100 preguntas produce **un** `StudentSearchResults` que contiene 100 `MinimalSearchResults`.

### Un ejemplo real, con los datasets del proyecto

Los datasets públicos vienen en dos sabores y encajan exactamente con los modelos:

- **`UnansweredQuestions`**: cada elemento tiene `question_id` y `question`. Es un `RagDataset` de `UnansweredQuestion`. Aquí no hay fuentes ni respuesta: el sistema debe encontrarlas.
- **`AnsweredQuestions`**: cada elemento añade `answer` y `sources` (la lista de `MinimalSource` correctos). Es un `RagDataset` de `AnsweredQuestion`. Este es el **patrón** contra el que se compara tu búsqueda.

Un elemento real de `AnsweredQuestions` (simplificado) se ve así:

```
question_id: "189c8b8a-..."          ← UUID único
question:    "What activation formats does ... return?"
answer:      "The fused batched MoE layer returns ..."
sources: [ { file_path: "data/raw/vllm-0.10.1/.../fused_batched_moe.py",
             first_character_index: 28416,
             last_character_index:  28975 } ]
```

Ese `sources` es lo que tu sistema tiene que **volver a encontrar** por sí solo.

### Modelos flexibles y campos extra

Los modelos se pueden **ampliar** (añadir campos, por ejemplo una puntuación de relevancia). La prudencia: los campos añadidos deben ser **opcionales**, para no romper la compatibilidad con quien espere el formato mínimo. Y cualquier estructura que se guarde o se lea en disco conviene tenerla **validada** por su modelo.

---

## 3. Preguntas para comprobar que lo entiendes

1. ¿Para qué sirve un modelo de datos? ¿Qué ventaja tiene frente a usar texto o listas sueltas?
2. ¿Qué es serializar y qué es deserializar? ¿Por qué hacen falta en este sistema?
3. ¿Qué es un `uuid4` y por qué `question_id` lo usa en lugar de un número fijo o un contador?
4. Nombra los tres campos de `MinimalSource` y explica qué significa cada uno.
5. ¿Por qué decimos que `MinimalSource` es "la pieza fundamental" y que forma parte de otras estructuras? Da dos sitios donde aparezca.
6. ¿Qué añade `AnsweredQuestion` respecto a `UnansweredQuestion`? ¿Qué campos hereda?
7. ¿Qué es `RagDataset` y por qué admite preguntas respondidas y sin responder a la vez?
8. Diferencia entre `MinimalSearchResults` y `MinimalAnswer`. ¿Y entre `StudentSearchResults` y `StudentSearchResultsAndAnswer`?
9. Si buscas en un dataset de 100 preguntas, ¿qué escribes: 100 archivos o uno? ¿Qué contiene?
10. ¿Por qué conviene validar `first_character_index` y `last_character_index` dentro del modelo?

<details><summary>Respuestas rápidas</summary>

1. Define la forma de los datos (campos, tipos, obligatorios) y los valida en la entrada, con errores claros.
2. Convertir estructura ↔ texto JSON para guardar/enviar y volver a leer. Permiten que las etapas se comuniquen por archivos.
3. Identificador único de 128 bits generado al azar; da a cada pregunta un id irrepetible sin coordinación.
4. `file_path` (ruta exacta), `first_character_index` (offset inicial) y `last_character_index` (offset final).
5. Porque es la ubicación de una fuente y aparece dentro de otras: en `sources` de `AnsweredQuestion` y en `retrieved_sources` de `MinimalSearchResults`.
6. Añade `sources` (lista de `MinimalSource`) y `answer`; hereda `question_id` y `question`.
7. Contenedor con la lista `rag_questions`; admite ambos tipos porque sirve tanto para preguntar como para comparar con las respuestas correctas.
8. `MinimalAnswer` añade `answer`. `StudentSearchResultsAndAnswer` es el equivalente a nivel de dataset (lista de `MinimalAnswer`); ambos llevan `k`.
9. Uno solo, `StudentSearchResults`, con una lista de 100 `MinimalSearchResults` y el campo `k`.
10. Para que sea imposible construir una fuente inválida: el error salta al crearla, no al final del pipeline.
</details>
