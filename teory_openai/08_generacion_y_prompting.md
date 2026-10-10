# 08 — Generar la respuesta: contexto y prompt

La búsqueda ya trajo los fragmentos correctos. Ahora el modelo debe **leerlos y redactar** la respuesta. Aquí se cierra el ciclo de RAG: entenderás cómo se prepara el contexto (la etapa de *aumentar*) y cómo se le pide al modelo que responda sin inventar.

**Lo que te llevas:** sabrás por qué "cómo le presentas la información al modelo" importa tanto como "qué información le das", y qué palancas tienes para que la respuesta sea coherente, anclada y al grano.

---

## 1. Los conceptos, con palabras sencillas

**Generar.**
Generar es lo que vimos al principio (archivo 00): el modelo **continúa texto** prediciendo el siguiente token una y otra vez. No "consulta" nada: lo único que tiene delante es el **prompt** que le escribiste.

**Aumentar (augmentation).**
Es la etapa intermedia de RAG: tomar los fragmentos recuperados y **prepararlos** para meterlos en el prompt. No basta con pegarlos: hay que **seleccionar**, **etiquetar** y **ordenar** para que el modelo los aproveche.

**Prompt.**
La "hoja de instrucciones" que le entregas al modelo: qué papel juega, qué reglas sigue, qué **contexto** (los fragmentos) tiene delante y cuál es la **pregunta**. Un buen prompt reduce las respuestas malas sin tocar el modelo.

**Plantilla de conversación (chat template).**
El modelo no espera texto suelto: espera mensajes con roles ("sistema", "usuario") envueltos en unas **marcas especiales** propias de cada modelo. La librería aplica esas marcas por ti. Piensa en rellenar un formulario con las casillas exactas que el modelo reconoce: si no usas el formato correcto, rinde peor.

**Grounding, otra vez.**
Volvemos al anclaje (archivo 01): la respuesta debe apoyarse en el contexto recuperado. La instrucción principal del prompt va justo en esa dirección: *"usa solo lo que está en el contexto; si no está, dilo"*.

---

## 2. Profundizando

### La entrada de esta etapa no trae texto

Un punto que confunde al principio: cuando el sistema **busca para todo un dataset**, guarda las fuentes como lo que son: **ubicaciones** (`file_path` + offsets, `MinimalSource`, archivo 04). No guarda el texto. Para generar hay que **volver a leer** cada archivo y extraer el fragmento `[inicio:fin]`.

Consecuencia de oro: la lectura al **generar** debe usar **exactamente la misma forma de leer** que al **indexar** (archivo 02). Si no, los offsets no cuadran y el "fragmento" que extraes no es el que encontraste.

### Preparar el contexto: las decisiones que importan

1. **Seleccionar cuántos fragmentos usar.** No tienes por qué usar los `k` completos. Más contexto = más ruido y más tiempo. A menudo los mejores 3–5 bastan.
2. **Etiquetar cada fragmento con su origen** (por ejemplo `[1] ruta/del/archivo`) para que el modelo pueda apoyarse en algo concreto y tú puedas trazar de dónde salió.
3. **Ordenar.** Los modelos (sobre todo los pequeños) atienden mejor al **principio y al final** del prompt. Coloca lo más relevante primero y la **pregunta al final**, cerca de donde el modelo empieza a escribir.
4. **Respetar el presupuesto de la ventana de contexto.** La ventana (archivo 00) es finita y se mide en **tokens**, no en caracteres. Hay que contar los tokens del contexto y **recortar** si te pasas. Más aún en un modelo pequeño en CPU: cada token cuesta tiempo y el exceso lo distrae.
5. **Limpiar y deduplicar.** Quita líneas en blanco repetidas, cabeceras de licencia irrelevantes y fragmentos que solapan casi por completo. Repetir el mismo texto no aporta y quita espacio.

### Estrategia de prompt (esto se documenta)

Una estructura habitual y sencilla:

- **Rol y reglas** (breves): *"Responde preguntas sobre este corpus. Usa SOLO el contexto. Si el contexto no contiene la respuesta, di que no lo sabes."*
- **Contexto**, etiquetado.
- **Pregunta**.
- **Formato esperado**: *"Responde en 2–4 frases"*, *"menciona el archivo o función relevante"*.

Lo que conviene **probar** (cambiando una cosa cada vez): en qué idioma van las instrucciones, cuántos fragmentos incluyes, cuánto pides que se extienda la respuesta, si pides citar la fuente. Anota qué cambió y qué efecto tuvo.

### Decodificación: cómo el modelo produce el texto

"Decodificar" es elegir, paso a paso, el siguiente token. Las decisiones que más afectan:

| Decisión | Qué hace | Criterio práctico |
|---|---|---|
| **Elegir siempre el más probable** (greedy) vs **muestrear** | Determinista vs aleatorio | Para respuestas factuales y reproducibles, mejor **determinista** |
| **Temperatura** | Grado de "creatividad" cuando se muestrea | Baja, si se usa |
| **Límite de tokens nuevos** | Cuánto puede extenderse la respuesta | Acótalo: menos divagación y menos tiempo |
| **Penalización de repetición** | Evita bucles tipo "repite y repite" | A veces necesaria en modelos pequeños |
| **Token de fin** | Marca natural de "he terminado" | El modelo lo emite solo |

La idea general: en una tarea **factual**, quieres estabilidad y concisión, no creatividad.

### Los límites del modelo pequeño

Un modelo de 600 millones de parámetros (muy pequeño comparado con los gigantes) corre bien en CPU, y por eso se usa, pero tiene límites esperables:

- Se pierde con contextos largos.
- Puede mezclar información de fragmentos distintos.
- Le cuesta seguir instrucciones largas y complejas.
- Puede escribir razonamiento "interno" de más antes de responder (por ejemplo, un borrador de pensamiento marcado con etiquetas especiales). Ese borrador gasta tiempo y tokens y puede ensuciar la salida; conviene **controlarlo o limpiarlo**, no dejarlo pasar al resultado.

Por eso, con un modelo pequeño, **el mejor contexto vale más que la mejor redacción**: ayúdalo a no equivocarse, no le pidas milagros.

### Casos degenerados (respuestas que no se caen)

El sistema debe seguir siendo válido aunque algo falte:

- **La búsqueda no devolvió ninguna fuente**: mejor una respuesta **honesta** ("no encontré contexto relevante") que dejar al modelo inventar.
- **Una fuente apunta a un archivo que ya no existe**: avisar y continuar.
- **Pregunta rarísima o con caracteres extraños**: no romperse; responder con lo que haya.

En todos los casos, la salida estructurada (los modelos del archivo 04) debe seguir siendo **válida**.

### La salida estructurada la construye tu código, no el modelo

Detalle importante: al modelo se le pide **solo el texto de la respuesta**. La estructura (envolverla en `MinimalAnswer`, `StudentSearchResultsAndAnswer`, etc.) la construye **tu programa**. Un modelo tan pequeño falla con facilidad si le pides que produzca JSON perfecto; es más robusto pedirle texto y encajarlo tú.

---

## 3. Preguntas para comprobar que lo entiendes

1. ¿Qué es exactamente "generar" para un LLM? ¿Consulta algo mientras responde?
2. ¿Qué hace la etapa de aumentar y en qué se diferencia de recuperar?
3. ¿Por qué la entrada de la generación (los resultados de búsqueda) no trae el texto y hay que releerlo?
4. ¿Por qué la relectura del corpus al generar debe usar la misma política de lectura que al indexar?
5. Enumera tres decisiones al preparar el contexto y explica por qué importan.
6. ¿Por qué se mide el presupuesto de contexto en tokens y no en caracteres?
7. ¿Qué le pide la instrucción de grounding al modelo y por qué es la instrucción clave?
8. ¿Qué significa elegir la palabra más probable en cada paso y por qué conviene en tareas factuales?
9. ¿Qué es el "borrador de pensamiento" de algunos modelos y por qué puede ser un problema en uno pequeño?
10. ¿Por qué se le pide al modelo solo el texto de la respuesta y no el JSON final?

<details><summary>Respuestas rápidas</summary>

1. Continúa el texto prediciendo el siguiente token; no consulta nada, solo tiene el prompt.
2. Toma los fragmentos recuperados y los prepara (seleccionar, etiquetar, ordenar, recortar) para el prompt; recuperar era encontrarlos.
3. Porque la búsqueda guarda ubicaciones (archivo + offsets), no texto; hay que reconstruir el fragmento leyéndolo de nuevo.
4. Para que los offsets signifiquen lo mismo y el fragmento extraído sea el que se encontró.
5. P. ej.: cuántos fragmentos usar (ruido/tiempo), orden (los pequeños atienden al principio y al final), presupuesto de tokens (que quepa). Importan porque condicionan qué ve el modelo.
6. Porque la ventana del modelo se mide en tokens y caracteres y tokens no se corresponden uno a uno.
7. Que use solo el contexto y admita cuando no lo sabe; evita que invente (alucine).
8. Es la decodificación "greedy"; da respuestas estables y reproducibles, deseable en tareas factuales.
9. Un razonamiento previo entre etiquetas especiales; gasta tiempo/tokens y puede ensuciar la salida, más aún en un modelo pequeño.
10. Porque el modelo pequeño falla produciendo JSON válido; es más robusto que tu código envuelva el texto en la estructura.
</details>
