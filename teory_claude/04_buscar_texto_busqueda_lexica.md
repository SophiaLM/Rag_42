# Parte 4 — Buscar texto: búsqueda léxica, TF-IDF y BM25

Tienes miles de chunks. Dada una pregunta, ¿cómo decides cuáles son los más relevantes? Esta parte explica la **lógica de puntuación** que usan los buscadores clásicos. Es matemática sencilla, pero con mucha intuición detrás.

---

## 1. Conceptos nuevos — la versión sencilla

**Búsqueda léxica**
Busca por **palabras literales**. No entiende significados: si preguntas por "arrancar el servidor" y el texto dice "launch the server", no hay ninguna palabra en común y no lo encuentra. Pero si preguntas por `max_model_len` y ese nombre aparece escrito en un chunk, lo encuentra al instante. Es un bibliotecario muy literal.

**Búsqueda semántica**
La alternativa: busca por **significado**, no por palabras (se verá como extra en la Parte 7). Aquí nos centramos en la léxica.

**Término**
Cada "palabra" que el buscador reconoce. Ojo con la palabra *token*: ya conoces los tokens del modelo de lenguaje; aquí los "términos" de búsqueda son **unidades que defines tú** (normalmente palabras normalizadas), y no tienen nada que ver con los del modelo, aunque a veces se llamen igual.

**Tokenización (de búsqueda)**
Convertir un texto en una lista de términos normalizados: pasar a minúsculas, separar por signos y espacios. `"How to Configure the Server?"` → `how, to, configure, the, server`.

**Palabras vacías (stopwords)**
Palabras tan comunes ("the", "is", "how") que aparecen en casi todo y no ayudan a distinguir un chunk de otro. Son como el ruido de fondo de una conversación.

**Raíz (stemming)**
Reducir palabras de la misma familia a una base común: "configure", "configuring" y "configuration" → algo como "configur". Así una pregunta con una forma encuentra textos con otra.

**Índice invertido**
El **índice alfabético del final de un libro**. En lugar de "página → palabras que contiene", guarda **"palabra → páginas donde aparece"**. Para buscar `scheduler` no lees el libro entero: vas a esa entrada y ves la lista de páginas. Es la estructura que hace la búsqueda rápida.

**TF (frecuencia del término)**
Cuántas veces aparece una palabra **en este chunk**. Si "cache" aparece 8 veces, el chunk probablemente habla de caché.

**IDF (rareza global)**
Cuán **poco común** es una palabra en **todo el corpus**. "the" aparece en todas partes y no informa; `kv_cache_dtype` aparece en tres chunks y es una pista valiosísima. Como en un caso policial: "el culpable lleva zapatos" no ayuda; "el culpable tiene un loro verde" sí.

**TF-IDF**
TF multiplicado por IDF: una palabra importa mucho si es **frecuente aquí y rara en el resto**.

**BM25**
Un TF-IDF mejorado con dos ideas de sentido común: (1) repetir una palabra mucho tiene **rendimientos decrecientes** (saturación); (2) los chunks largos tienen más oportunidades de contener una palabra por casualidad, así que se les **penaliza un poco** (normalización por longitud).

**Ranking y top-k**
Puntuar todos los chunks candidatos, ordenarlos de mayor a menor puntuación y quedarte con los **k** primeros (el `k` de la Parte 0).

---

## 2. Profundizando

**Lo que debes llevarte de aquí:** (1) la intuición de **por qué** TF e IDF puntúan bien (frecuente aquí, raro fuera); (2) qué problema resuelve cada ajuste de BM25 (saturación y longitud); (3) que la **calidad de la tokenización** pesa tanto como la fórmula, sobre todo en código; (4) cómo el índice invertido hace posible buscar en milisegundos.

### El flujo de una búsqueda léxica

```
INDEXAR (una vez):  chunks ──► tokenizar ──► índice invertido + estadísticas
BUSCAR (cada vez):  pregunta ──► tokenizar igual ──► puntuar candidatos ──► ranking ──► top-k
```

Regla importante: **la pregunta y los chunks deben tokenizarse exactamente igual**. Si no, la misma palabra se escribiría de dos formas y nunca coincidiría.

### Por qué TF-IDF tiene sentido

Piensa en dos preguntas al azar sobre el repositorio. Las palabras que más nos acercan a la respuesta correcta son las que cumplen **dos condiciones a la vez**: aparecen mucho en el chunk bueno (TF alto) y casi no aparecen en los demás (IDF alto). Una palabra muy frecuente en todas partes (IDF ≈ 0) no ayuda aunque aparezca mil veces; una palabra rara que aparece una vez en el chunk correcto puede ser decisiva. Multiplicar ambas captura esa idea.

El IDF se suele escribir así (N = número total de chunks; df = en cuántos aparece el término):

```
idf(t) = ln( N / df(t) )      (con pequeños suavizados en la práctica)
```

Si el término aparece en *todos* los chunks, `N/df = 1` y `ln(1) = 0`: no aporta nada.

### BM25: la fórmula y qué hace cada pieza

```
score(consulta, chunk) = Σ  idf(t) × [ tf × (k1 + 1) ] / [ tf + k1 × (1 − b + b × largo/largo_medio) ]
                         t ∈ consulta
```

No hace falta memorizarla; sí entender sus tres mandos:

| Pieza | Qué controla | Metáfora |
|---|---|---|
| `idf(t)` | Cuánto vale la palabra por ser rara | El valor de la pista |
| `k1` | Saturación: cuánto sube la nota al repetir la palabra | Un aplauso más fuerte no vale el doble |
| `b` | Cuánto penaliza que el chunk sea más largo que la media (0 = nada, 1 = del todo) | Un discurso largo tiene más ocasiones de decir "casualidades" |

Ejemplo de saturación: pasar de 1 a 2 apariciones de una palabra sube bastante la nota; pasar de 20 a 21 casi nada. Sin saturación, un chunk que repite "cache" 200 veces dominaría injustamente.

### TF-IDF frente a BM25

| | TF-IDF | BM25 |
|---|---|---|
| Repetición de un término | Crece sin tope (o con log) | **Satura** |
| Longitud del chunk | Se compensa con otra técnica (normalizar vectores) | **Parámetro propio** (`b`) |
| Parámetros a ajustar | Casi ninguno | `k1` y `b` |
| Complejidad | Muy simple | Algo más, pero asequible |

Ambos son legítimos; lo importante es que sepas **explicar uno de ellos por dentro**.

### La tokenización en código: donde se gana o se pierde

Una pregunta puede hacerse de dos formas, y el buscador debe sobrevivir a ambas:
- **Citando un identificador literal**: `max_model_len`. Aquí gana quien conserve ese identificador entero en el índice.
- **Parafraseando la idea**: "longitud máxima del modelo". Aquí gana quien haya troceado el identificador en sus partes (`max`, `model`, `len`).

Solución habitual: **guardar ambas cosas**, el identificador completo y sus partes. Reglas típicas para trocear: separar por guion bajo (`snake_case`) y por cambios de mayúscula (`camelCase`).

Otras decisiones con efecto real:
- **Stopwords**: quitarlas ahorra ruido, pero ten cuidado: en código, palabras como `self` o `return` aparecen en todos lados y se comportan como stopwords por sí solas (su IDF ya es bajo).
- **Stemming**: ayuda cuando la pregunta usa otra forma de la palabra (típico en documentación); puede estorbar en código, donde los nombres exactos importan.
- **Pares de palabras**: tratar "kv cache" como unidad captura frases hechas.

### Texto original frente a texto indexable

Lo que se **muestra al modelo** (el texto real del chunk) y lo que se **usa para buscar** no tienen por qué ser idénticos. Puedes enriquecer el texto de búsqueda con información que ayuda a encontrarlo pero que no vive dentro del chunk: por ejemplo, las palabras de la **ruta del archivo** (`entrypoints/openai/api_server.py`) o el **título** de la sección. Las preguntas suelen hablar de *temas*, y los nombres de carpeta y archivo son temas. El texto original se mantiene intacto: las coordenadas no cambian.

### Por qué el índice invertido hace rápida la búsqueda

Sin él, para cada pregunta tendrías que mirar los miles de chunks uno por uno. Con él, solo miras los chunks que contienen **algún término de la pregunta**. Además, las partes caras del cálculo (el IDF, el largo medio) se calculan **una sola vez al indexar**, no en cada búsqueda. Este reparto "trabajo pesado una vez, consulta ligera muchas veces" es la razón de que existan la etapa de indexar y la de recuperar por separado.

### Quedarse con los k mejores

No hace falta ordenar los miles de chunks puntuados: basta con ir manteniendo un pequeño grupo con los k mejores vistos hasta ahora (la misma idea de una cola de prioridad que ya conoces de otros proyectos). Un detalle conceptual: cuando dos chunks empatan en puntuación, hace falta un **criterio fijo de desempate**; si no, el orden podría cambiar entre ejecuciones y los resultados dejarían de ser reproducibles.

### Los límites de lo léxico

Un buscador léxico no ve sinónimos ("arrancar" ≠ "launch") ni relaciones de significado. Es un límite **de diseño**, no un fallo tuyo. Las mejoras de tokenización lo suavizan; las técnicas semánticas lo resuelven de otra forma (Parte 7).

---

## 3. Diez preguntas que responder antes de programar

1. ¿Qué diferencia hay entre búsqueda léxica y semántica? Pon un ejemplo donde la léxica acierte y otro donde falle.
2. ¿Qué es un índice invertido y por qué acelera tanto las búsquedas?
3. ¿Qué mide TF y qué mide IDF? ¿Por qué se multiplican?
4. ¿Por qué una palabra presente en *todos* los chunks tiene un IDF igual a 0?
5. ¿Qué problema resuelve la saturación (`k1`) en BM25?
6. ¿Qué hace `b` y qué ocurre cuando vale 0?
7. ¿Por qué hay que tokenizar igual la pregunta y los chunks?
8. ¿Por qué conviene guardar tanto el identificador completo como sus partes?
9. ¿Qué ventaja tiene añadir las palabras de la ruta del archivo al texto de búsqueda? ¿Cambia eso las coordenadas del chunk?
10. ¿Por qué hace falta un criterio de desempate al elegir el top-k?

<details><summary>Respuestas rápidas (autoevaluación)</summary>

1. Léxica = coincidencia de palabras; semántica = coincidencia de significado. Acierta con `max_model_len`; falla con "arrancar el servidor" frente a un texto que dice "launch the server".
2. Una tabla "palabra → chunks donde aparece"; solo se visitan los chunks que contienen términos de la pregunta.
3. TF: veces que aparece en el chunk. IDF: rareza en el corpus. El producto premia lo frecuente aquí y raro fuera.
4. `N/df = 1` y `ln(1) = 0`: no distingue ningún chunk de otro.
5. Evita que repetir una palabra cientos de veces domine el ranking.
6. Controla cuánto se penaliza un chunk largo; con 0, la longitud no influye.
7. Si se tokenizaran distinto, la misma palabra no coincidiría con la del índice.
8. Porque la pregunta puede citar el identificador entero o parafrasear sus partes.
9. Ayuda porque las preguntas hablan de temas reflejados en nombres de carpetas/archivos; no cambia las coordenadas, porque el texto original queda intacto.
10. Sin él, empates se resolverían de forma arbitraria y los resultados no serían reproducibles.
</details>

---

## 4. Vocabulario que ya puedes usar a partir de aquí

Búsqueda léxica / semántica · término y tokenización de búsqueda · stopwords · stemming · índice invertido · TF, IDF, TF-IDF · BM25 (`k1`, `b`) · texto original frente a texto indexable · ranking y desempate.
