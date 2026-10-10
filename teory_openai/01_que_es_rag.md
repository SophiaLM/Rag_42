# 01 — Qué es RAG

En el archivo anterior vimos el problema: el modelo no sabe de tu corpus y su mesa (la ventana de contexto) es pequeña. La respuesta a ese problema tiene nombre: **RAG**. Aquí entenderás qué es, qué etapas tiene y por qué se dice que la calidad de la búsqueda lo es casi todo.

---

## 1. Los conceptos, con palabras sencillas

**RAG (Retrieval-Augmented Generation).**
"Generación aumentada por recuperación". En vez de meter el conocimiento *dentro* del modelo (reentrenar), le damos acceso a una **fuente externa** y le dejamos **tomar de ahí** lo que necesita para responder. La metáfora: no obligamos al estudiante a memorizar el manual entero; le dejamos **entrar con los apuntes** al examen.

**Las cuatro etapas de RAG.**
1. **Indexar (indexing)**: organizar el corpus para poder buscarlo rápido y sin releerlo entero cada vez.
2. **Recuperar (retrieval)**: dada una pregunta, encontrar los fragmentos del corpus más relevantes.
3. **Aumentar (augmentation)**: preparar esos fragmentos y colocarlos en el prompt del modelo.
4. **Generar (generation)**: el modelo lee ese contexto y redacta la respuesta.

Cada etapa alimenta a la siguiente; si la primera falla, las demás no pueden salvarla.

**Fragmento (chunk).**
Como el corpus es demasiado grande, no lo tratamos como archivos enteros, sino que lo **partimos en trozos** llamados *chunks*. Cada chunk guarda un fragmento de texto y **de dónde viene** (el archivo y la posición exacta que ocupa dentro del archivo). Los chunks son las "fichas" entre las que busca el sistema. En el archivo 03 estudiaremos en detalle cómo se parte.

**Recuperar y top-k (y qué es `k`).**
Recuperar es: dada una pregunta, devolver los fragmentos más relacionados con ella, **ordenados** de más a menos relevante. Casi nunca queremos "todos los que se parecen", sino **los `k` mejores**, donde `k` es simplemente un número que tú eliges (por ejemplo `k = 5`, `k = 10`). A ese conjunto se le llama los **top-k**. `k` es, entonces, "cuántos fragmentos voy a sacar en cada consulta".

**Grounding (anclaje).**
Que la respuesta se **apoye en las fuentes recuperadas** y no en la imaginación del modelo. Es el objetivo de todo RAG: que lo que el modelo diga esté respaldado por un fragmento real del corpus, en lugar de ser una alucinación plausible.

---

## 2. Profundizando

### El pipeline, de un vistazo

```
   CORPUS (los archivos)
        │
        ▼
   ┌──────────┐
   │ INDEXAR  │  partir en chunks + construir la estructura de búsqueda
   └──────────┘
        │  (esto se hace una vez; queda guardado)
        ▼
   ┌──────────┐
   │ RECUPERAR│  pregunta ──► top-k chunks más relevantes
   └──────────┘
        │
        ▼
   ┌──────────┐
   │ AUMENTAR │  esos chunks ──► contexto colocado en el prompt
   └──────────┘
        │
        ▼
   ┌──────────┐
   │ GENERAR  │  prompt ──► el LLM escribe la respuesta
   └──────────┘
        │
        ▼
     RESPUESTA (anclada en el corpus)
```

Fíjate en la asimetría: **indexar** es el trabajo pesado y se hace **una sola vez**; **recuperar** es ligero y se hace **en cada pregunta**. Esa separación es la que permite que el sistema responda en milisegundos en vez de releer el corpus entero cada vez.

### Dos calidades distintas (y por qué importa separarlas)

El sistema puede fallar en dos sitios diferentes:

| | Calidad de **recuperación** | Calidad de **generación** |
|---|---|---|
| Pregunta que responde | ¿Traje los fragmentos correctos? | ¿Redacté bien usando esos fragmentos? |
| Se mide con | Una métrica de recuperación (archivo 07) | Revisión de la respuesta (coherencia, anclaje, foco) |
| Arreglo si falla | Mejor chunking, mejor puntuación, mejor tokenización | Mejor prompt, mejor selección de contexto |

Son dos fallos **independientes**. Si el retriever no trae la página correcta, el mejor modelo del mundo no puede responder bien: le falta la evidencia. Por eso RAG mide la recuperación **aparte**, y por eso la calidad de la búsqueda es la base de todo.

### Por qué `k` no es "cuanto más, mejor"

`k` regula el compromiso entre **no quedarse corto** y **no ahogar al modelo**:

- `k` **demasiado pequeño**: si el fragmento correcto no entra en el top-k, se pierde (no encontrarás todas las fuentes correctas) y el modelo no tiene de dónde sacar la respuesta.
- `k` **demasiado grande**: metes ruido en el prompt, gastas contexto y tiempo, y confundes a un modelo pequeño. Además, con la métrica de recuperación, los puestos de más allá de un cierto k dejan de contar.

Elegir `k` es, por tanto, una **decisión de diseño** que probarás con datos.

### RAG no es magia: solo reduce el problema a dos subproblemas

RAG no convierte a un modelo pequeño en omnisciente. Lo que hace es transformar una tarea imposible ("que el modelo sepa todo el corpus") en dos tareas tratables:

1. **Encontrar** los fragmentos relevantes (un problema de búsqueda).
2. **Resumir/respnder** usando solo esos fragmentos (un problema de generación con contexto acotado).

Todo tu esfuerzo se reparte entre esas dos tareas. Y la primera es la que más controlas.

---

## 3. Preguntas para comprobar que lo entiendes

1. ¿Qué significa "aumentada por recuperación"? ¿Qué se aumenta y con qué?
2. Nombra las cuatro etapas de RAG en orden y di qué entra y qué sale de cada una.
3. ¿Por qué indexar se hace una vez y recuperar se hace muchas? ¿Qué se gana?
4. Define `k` con tus palabras. ¿Qué pasa si es demasiado pequeño? ¿Y si es demasiado grande?
5. ¿Qué es un chunk y qué información debe guardar además del texto?
6. ¿Qué es el grounding y por qué es el objetivo central de RAG?
7. Si un sistema da respuestas malas porque recuperó fragmentos equivocados, ¿es un problema de generación o de recuperación? ¿Por qué no se arregla "escribiendo un mejor prompt"?

<details><summary>Respuestas rápidas</summary>

1. Se aumenta la generación con información recuperada de una fuente externa: le pasamos al modelo los fragmentos relevantes del corpus.
2. Indexar (corpus → estructura de búsqueda) → Recuperar (pregunta → top-k fragmentos) → Aumentar (fragmentos → contexto en el prompt) → Generar (prompt → respuesta).
3. Indexar es caro y no cambia entre preguntas; recuperar debe ser ligero y frecuente. Se gana velocidad en cada consulta.
4. `k` es cuántos fragmentos devuelve la búsqueda. Pequeño: puedes dejar fuera el correcto. Grande: metes ruido, gastas contexto y tiempo.
5. Un trozo del corpus; debe guardar también de qué archivo sale y qué rango de posiciones ocupa.
6. Que la respuesta se apoye en las fuentes reales en vez de inventarse; es lo que distingue RAG de una alucinación.
7. De recuperación. Un prompt mejor no crea la evidencia que falta; si el fragmento correcto nunca se recuperó, no hay nada correcto que el modelo pueda citar.
</details>
