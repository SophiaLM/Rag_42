# 06 — La búsqueda léxica: TF-IDF y BM25

Ya sabemos partir el corpus en chunks (03) y convertir texto en términos (05). Falta lo esencial: **dado un conjunto de términos de la pregunta, decidir qué chunks son los más relevantes y ordenarlos**. Eso es la búsqueda *léxica*, y sus dos métodos clásicos son **TF-IDF** y **BM25**.

**Lo que te llevas:** entenderás qué es un índice invertido, qué miden TF e IDF, cómo se combinan, y por qué BM25 mejora a TF-IDF. Reconocerás `k1` y `b` cuando los veas, sin que sean fórmulas mágicas.

---

## 1. Los conceptos, con palabras sencillas

**Búsqueda léxica vs búsqueda semántica.**
- **Léxica**: busca por **palabras literales**. Si la pregunta cita `max_model_len` y el texto lo contiene, acierta. Pero si pregunta "arrancar el servicio" y el texto dice "launch the server", no comparten ni una palabra y la búsqueda falla.
- **Semántica**: busca por **significado** (usa vectores, "embeddings"). Encontraría "launch the server" a partir de "arrancar el servicio". Es otra tecnología; aquí nos centramos en la léxica, que es la base y la que exige el proyecto.

**Índice invertido.**
Es el **índice alfabético** de un libro, pero al revés: en vez de "página → palabras", guarda **"palabra → en qué chunks aparece"**. Para buscar `scheduler`, el sistema no recorre los miles de chunks: mira la entrada de esa palabra y va directamente a los pocos chunks que la contienen. Esa estructura es la que hace la búsqueda **rápida**, y es la razón de que el trabajo pesado se haga una vez al indexar (archivo 01).

**TF (frecuencia del término).**
Cuántas veces aparece una palabra **dentro de este chunk**. Si `cache` aparece ocho veces, es probable que el chunk hable de caché.

**IDF (rareza global).**
Cuán **poco frecuente** es la palabra en **todo el corpus**. `the` aparece en casi todos los chunks, así que no informa; un identificador raro aparece en pocos y es una pista valiosa. Comparación policial: "el sospechoso lleva zapatos" no ayuda (todos llevan); "el sospechoso tiene un loro verde" sí.

**TF-IDF = TF × IDF.**
La idea clave: una palabra es importante para un chunk cuando es **frecuente ahí** y **rara en el resto**. El producto de TF e IDF captura exactamente eso.

**BM25.**
El hermano mayor de TF-IDF, con dos correcciones de sentido común:
- **Saturación**: repetir una palabra cincuenta veces no la hace cincuenta veces más relevante que repetirla cinco. El peso "se aplana".
- **Normalización por longitud**: un chunk largo tiene más oportunidades de contener una palabra por puro azar, así que se le penaliza un poco.

---

## 2. Profundizando

### Cómo se puntúa, paso a paso

1. La pregunta se tokeniza (archivo 05) en términos.
2. El índice invertido dice **qué chunks contienen** algún término de la pregunta. Solo esos son candidatos.
3. Para cada candidato se calcula una **puntuación de relevancia** combinando los términos de la pregunta que contiene.
4. Se seleccionan los **`k` mejores** (el top-k, archivo 01).

El índice invertido no solo acelera: garantiza que **solo miras lo relevante** en vez de puntuar los miles de chunks en cada consulta.

### La fórmula de TF-IDF (intuición, no memorización)

```
peso(término, chunk) = tf(término, chunk) × idf(término)
idf(término)          = ln( nº de chunks / nº de chunks que contienen el término )
```

- El **TF** crece con las apariciones dentro del chunk.
- El **IDF** es grande para términos raros y casi cero para los comunes (`the` aparece en casi todos → `idf ≈ 0`).
- El producto premia "frecuente aquí y raro fuera".

Existen variantes con suavizados (sumar 1 para evitar divisiones por cero y logaritmos de cero) y formas de evitar que los chunks muy largos se beneficien por tamaño. No necesitas memorizarlas: necesitas entender **qué premia** la fórmula.

### La fórmula de BM25 (y sus dos mandos)

BM25 cambia el TF por una versión que **satura** y añade una penalización por longitud:

```
score(pregunta, chunk) = Σ  idf(t) × [ tf(t) × (k1 + 1) ] / [ tf(t) + k1 × (1 − b + b × |chunk| / media_longitud) ]
                        t en la pregunta
```

Los dos parámetros se comportan como **mandos de una consola**:

| Parámetro | Qué controla | Valores típicos |
|---|---|---|
| **`k1`** | Cuánta importancia se da a **repetir** un término (saturación). `k1 = 0` → solo importa si aparece o no. | 1.2 – 2.0 |
| **`b`** | Cuánto se **penaliza la longitud** del chunk. `b = 0` → la ignora; `b = 1` → la normaliza del todo. | 0.75 (entre 0 y 1) |

No son números sagrados: se **ajustan probando** con datos. Lo que hay que poder explicar es **qué hace cada uno**.

### TF-IDF frente a BM25

| | TF-IDF | BM25 |
|---|---|---|
| Repetición del término | Crece sin freno (o con logaritmo) | **Satisface** gracias a `k1` |
| Longitud del chunk | Se compensa de otra forma | **Parámetro propio** (`b`) |
| Parámetros a ajustar | Casi ninguno | `k1`, `b` |
| Dificultad | Muy simple | Simple (una fórmula más) |
| Rendimiento típico en texto | Bueno | **Suele ser mejor** |

### Por qué el mismo tokenizador en los dos lados

Esto ya se dijo en el archivo 05, pero aquí se entiende *por qué*: la puntuación compara **términos**. Si el chunk guardó `server` y la pregunta se tokenizó a `Server`, el índice nunca encontrará el match. La coherencia del tokenizador es una condición de correctitud, no un detalle de estilo.

### El efecto del tamaño del chunk (que ya conoces del 03)

BM25 y TF-IDF puntúan **chunks**. Un chunk grande contiene más términos por azar, y `b` intenta compensarlo. Esto conecta con el dilema del archivo 03: **el tamaño del chunk y el método de puntuación están acoplados**. Por eso el tamaño es una palanca que se mide, no un valor que se fija de una vez.

---

## 3. Preguntas para comprobar que lo entiendes

1. ¿Qué diferencia hay entre búsqueda léxica y semántica? Da una pregunta donde gane la léxica y otra donde pierda.
2. ¿Qué es un índice invertido y por qué acelera tanto la búsqueda?
3. ¿Qué mide TF y qué mide IDF? ¿Por qué se multiplican?
4. ¿Por qué `the` tiene un IDF cercano a cero y un identificador raro lo tiene alto?
5. ¿Qué problema resuelve la **saturación** de BM25?
6. ¿Qué controla el parámetro `b`? ¿Qué pasaría con `b = 0`?
7. ¿Por qué BM25 suele rendir mejor que TF-IDF?
8. ¿Por qué es indispensable usar el mismo tokenizador para chunks y preguntas?
9. Explica con tus palabras por qué el tamaño del chunk y el método de puntuación están relacionados.

<details><summary>Respuestas rápidas</summary>

1. Léxica = palabras literales; semántica = significado. Gana la léxica: `max_model_len`. Pierde: "arrancar el servicio" frente a "launch the server".
2. Estructura que mapea "palabra → chunks que la contienen"; solo se visitan los chunks relevantes en vez de todos.
3. TF: frecuencia en el chunk. IDF: rareza en el corpus. Se multiplican para premiar lo frecuente aquí y raro fuera.
4. Aparece en casi todos los chunks (idf ≈ 0); el raro aparece en pocos y discrimina mucho.
5. Evita que repetir una palabra muchas veces domine el ranking de forma desproporcionada.
6. La penalización por longitud. Con `b = 0`, los chunks largos no se penalizan por ser largos.
7. Porque satura la repetición y normaliza por longitud con un parámetro explícito.
8. Porque la puntuación compara términos: si se tokenizan distinto, los mismos términos no coinciden.
9. Chunks grandes acumulan términos por azar y "ganan" por tamaño; por eso la puntuación necesita una normalización por longitud y el tamaño es una palanca de calidad.
</details>
