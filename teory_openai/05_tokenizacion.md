# 05 — Tokenización para la búsqueda

Para poder buscar texto por palabras, primero hay que decidir **qué cuenta como "palabra"**. Esa operación se llama **tokenizar**, y es una de las palancas que más afecta a si encuentras o no la respuesta correcta.

**Lo que te llevas:** entenderás por qué antes de comparar hay que *normalizar* y *trocear* el texto, y qué decisiones concretas (mayúsculas, signos, identificadores de código, palabras vacías) mejoran o empeoran la búsqueda.

---

## 1. Los conceptos, con palabras sencillas

**Buscar "por palabras".**
La forma más directa de decidir si dos textos se parecen es ver **qué palabras comparten**. Si la pregunta dice `cache` y un fragmento también dice `cache`, hay coincidencia. Pero para comparar palabras hay que definirlas de forma estable.

**Tokenización (aquí).**
Es el proceso de convertir un texto en una **lista de términos** normalizados. `"How to Configure the Server?"` se convierte en algo como `["how", "to", "configure", "the", "server"]`. Es pasar el texto por un colador que quita mayúsculas y signos, y lo deja en piezas comparables.

> **Ojo, no confundir dos "tokens".** Los *tokens del LLM* son las unidades con las que el modelo trocea el texto para procesarlo (las viste en el archivo 00). Los *tokens de búsqueda* de los que hablamos aquí son las **palabras normalizadas** con las que comparamos fragmentos. Son conceptos distintos: uno es para que el modelo lea, el otro para que el índice encuentre.

**Normalizar.**
Dejar todas las variantes de un término con la **misma forma**, para que coincidan. Lo más básico: pasar a **minúsculas** (`Server` y `server` deben ser lo mismo) y separar por signos de puntuación.

**Palabras vacías (stopwords).**
Palabras como `the`, `is`, `of`, `to` aparecen en casi todas partes y por sí solas **no informan** de nada. A menudo se descartan al buscar, porque meterían ruido.

---

## 2. Profundizando

### Un pipeline típico de tokenización

1. **Minúsculas**: `Configure` → `configure`.
2. **Separar** por todo lo que no sea letra, dígito o guion bajo: los signos de puntuación dejan de estorbar.
3. **Trocear identificadores** (esto es clave en un corpus de **código**). Un identificador escrito junto suele estar formado por varias palabras:
   - `snake_case` → `snake` + `case`.
   - `CamelCase` → `camel` + `case`.
   - `max_model_len` → `max` + `model` + `len`.
4. **Conservar también el identificador completo**, además de sus partes. ¿Por qué? Porque una consulta puede **citar** el identificador literal (`max_model_len`, coincidencia exacta) o **parafrasear** sus partes ("model length", coincidencia por trozos). Guardando ambos, cubres los dos casos.
5. **Quitar palabras vacías** (con criterio).
6. **Stemming** (opcional): reducir palabras a una raíz común, para que `configuring`, `configuration` y `configure` se traten como la misma. Ayuda cuando la pregunta **parafrasea**; a veces estorba en código. Es una palanca que se prueba.
7. **N-gramas** (opcional): agrupar pares de palabras ("kv cache") para capturar frases hechas.

### La regla de oro: el mismo colador en los dos lados

Los **fragmentos** y las **preguntas** deben tokenizarse **exactamente igual**. Si un lado convierte `Server` en `server` y el otro no, los mismos términos no coincidirán y la búsqueda fallará aunque el texto sea el mismo. Es como si dos personas buscaran en la misma biblioteca pero una usara el índice en mayúsculas y otra en minúsculas.

### Enriquecer el texto indexable

Truco importante: lo que guardas para buscar no tiene por qué ser **solo** el texto literal del chunk. Puedes **añadirle** información que ayude a encontrarlo:

- **La ruta del archivo**: `vllm/entrypoints/openai/api_server.py` aporta las palabras `entrypoints`, `openai`, `api`, `server`.
- **El título de la sección** (en documentación): un párrafo suelto que dice "see below" no dice de qué habla; con su título ("Features › LoRA"), sí.

¿Por qué funciona? Porque las preguntas suelen hablar de **temas**, y los temas suelen estar reflejados en los nombres de archivo y en los títulos, que a veces **no aparecen** dentro del texto del chunk. Es una de las mejoras más rentables.

### Cuidado con pasarse de "limpieza"

Quitar demasiado puede borrar señal. En un corpus de **código**, palabras como `self`, `def` o `return` casi no informan, pero un identificador raro sí. La regla: quita solo lo que **no distingue**; conserva lo que **discrimina**.

---

## 3. Preguntas para comprobar que lo entiendes

1. ¿En qué se diferencian los "tokens de búsqueda" de los "tokens del LLM"?
2. ¿Por qué necesitamos normalizar el texto antes de compararlo? Da un ejemplo donde sin normalizar fallaría.
3. ¿Por qué es clave trocear identificadores en un corpus de código? Pon un ejemplo de `CamelCase` y de `snake_case`.
4. ¿Por qué conviene guardar **tanto** el identificador completo como sus partes troceadas?
5. ¿Qué son las palabras vacías y por qué se descartan?
6. ¿Por qué es obligatorio tokenizar igual los fragmentos y las preguntas?
7. ¿Qué mejora puede aportar añadir la ruta del archivo al texto que se indexa?
8. ¿Qué riesgo hay en "limpiar" el texto de más?

<details><summary>Respuestas rápidas</summary>

1. Los de búsqueda son las palabras normalizadas con las que comparamos fragmentos; los del LLM son las unidades con las que el modelo trocea el texto para procesarlo.
2. Para que las variantes coincidan. Sin normalizar, `Server` ≠ `server` y no habría match aunque el texto sea el mismo.
3. Porque un identificador comprimido contiene varias palabras útiles. `maxModelLen` → `max`+`model`+`len`; `max_model_len` → `max`+`model`+`len`.
4. Para cubrir consultas que lo citan literal y consultas que parafrasean sus partes.
5. Palabras muy frecuentes que apenas informan (`the`, `to`); se quitan para reducir ruido.
6. Porque si se tokenizan distinto, los mismos términos no coinciden en el índice.
7. Las preguntas hablan de temas que a menudo se reflejan en nombres de carpeta/archivo, y esos nombres no están dentro del texto del chunk.
8. Borrar señal discriminante: quitar términos que sí ayudaban a distinguir, sobre todo en código.
</details>
