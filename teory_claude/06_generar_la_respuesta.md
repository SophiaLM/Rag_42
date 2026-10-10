# Parte 6 — Generar la respuesta: aumentar y generar

La búsqueda ya trajo las fichas correctas. Ahora el "estudiante" (el modelo) las lee y redacta. Esta parte explica **cómo prepararle la mesa** (aumentar) y **cómo se comporta al escribir** (generar). Recuerda que el modelo del proyecto es pequeño: tu trabajo no es pedirle milagros, es **ponérselo fácil**.

---

## 1. Conceptos nuevos — la versión sencilla

**Modelo pequeño**
El modelo del proyecto (Qwen3-0.6B) tiene unos 600 millones de parámetros, que es poco comparado con los grandes. Puede ejecutarse en un ordenador normal, pero tiene límites: se pierde con textos largos, mezcla datos y sigue peor las instrucciones complicadas. Es un estudiante aplicado pero con poca memoria de trabajo.

**Prompt**
La **hoja de examen** que le entregas: contiene las instrucciones, los apuntes y la pregunta. Todo el comportamiento del modelo depende de cómo la redactes.

**Rol de mensaje (plantilla de chat)**
Los modelos conversacionales esperan el texto organizado en mensajes con **roles** (por ejemplo, "sistema": las reglas generales; "usuario": la pregunta). Cada modelo tiene su propio formato interno, con marcas especiales; la **plantilla de chat** es la receta que convierte tus mensajes en ese formato exacto. Es como rellenar un formulario con las casillas que el modelo reconoce.

**Aumentar (augment)**
La etapa en la que decides **qué páginas pones sobre la mesa y cómo**: cuáles de las recuperadas, en qué orden, cuánto texto de cada una, y cómo las presentas.

**Presupuesto de contexto**
Como la mesa (ventana de contexto, Parte 0) es limitada, decides de antemano **cuánto espacio dedicas a los apuntes**, dejando sitio para las instrucciones, la pregunta y la respuesta.

**Decodificación determinista frente a muestreo**
Al escribir, el modelo calcula qué pieza viene después con ciertas probabilidades. Puede elegir **siempre la más probable** (determinista: mismo prompt, misma respuesta) o **sortear** entre las probables (muestreo: más variedad y más azar). La *temperatura* regula cuánto azar.

**Modo "thinking" (pensamiento)**
Algunos modelos, entre ellos Qwen3, pueden escribir primero un "borrador de razonamiento" entre marcas especiales y después la respuesta. Útil para problemas difíciles; en un modelo pequeño y lento, suele gastar tiempo y espacio y puede ensuciar la salida.

---

## 2. Profundizando

**Lo que debes llevarte de aquí:** (1) que el modelo **no recibe texto de la búsqueda, sino direcciones**, y por tanto hay un paso intermedio de reconstrucción; (2) los criterios para **elegir y ordenar** los apuntes; (3) cómo se estructura un prompt y por qué cada parte existe; (4) los comportamientos del modelo que debes conocer (alucinación, determinismo, pensamiento) para anticipar sus fallos.

### El paso intermedio: de direcciones a texto

Recuerda la Parte 2: los resultados de búsqueda guardan fuentes (archivo + rango), **no texto**. Antes de preparar la mesa hay que **volver al archivo y leer ese rango** para recuperar el texto. Y aquí reaparece la regla de la Parte 1: ese texto solo es el correcto si el archivo se lee **exactamente igual** que cuando se calcularon las coordenadas. Si no, el modelo recibiría un trozo desplazado.

```
fuentes (archivo + rango) ──► releer el rango en el archivo ──► texto de cada fragmento
                                                                      │
                  instrucciones + fragmentos + pregunta ──► PROMPT ──► modelo ──► respuesta
```

### Aumentar: cómo preparar bien la mesa

No se trata de "meter todo lo recuperado". Cuatro decisiones, todas con la idea de **reducir ruido**:

1. **Cuántos fragmentos usar.** Puedes recuperar k = 10 y usar solo los 3–5 mejores. Más apuntes aumentan la probabilidad de incluir la respuesta, pero también el ruido y el tiempo.
2. **En qué orden.** Los modelos pequeños suelen prestar más atención a lo que está **al principio y al final** del texto, y menos a lo del medio. Lo más relevante va primero; la pregunta, lo más cerca posible del punto donde el modelo empieza a escribir (al final).
3. **Cuánto texto de cada uno.** Si el contexto total excede tu presupuesto, **recortas** (mejor un fragmento recortado limpiamente que un prompt desbordado). El presupuesto se mide en tokens, no en caracteres, porque la ventana se mide en tokens.
4. **Cómo se presentan.** Etiquetar cada fragmento con su origen (por ejemplo, el archivo) ayuda al modelo a distinguirlos y a apoyarse en ellos. Si dos fragmentos se solapan, no repitas el texto común.

### Anatomía de un buen prompt

| Parte | Para qué sirve | Idea clave |
|---|---|---|
| **Reglas** | Dicen qué papel juega y qué no puede hacer | Cortas y directas; un modelo pequeño se pierde con instrucciones largas |
| **Restricción de anclaje** | "Usa solo el contexto; si no está, dilo" | Reduce la alucinación (Parte 0: respuesta anclada) |
| **Apuntes** | La evidencia | Etiquetados y ordenados por relevancia |
| **Pregunta** | Lo que debe contestar | Al final del prompt |
| **Formato deseado** | Longitud y estilo de la respuesta | "Responde en 2–4 frases" evita divagaciones |

Elegir bien estas piezas es lo que el subject llama **estrategia de prompt**: parte de la nota se basa en que puedas explicar *por qué* tu prompt es como es.

### Qué hace el modelo cuando escribe

- **Predice el siguiente fragmento de texto, uno detrás de otro.** No "consulta" los apuntes como un buscador; los usa como contexto que influye en lo que predice. Por eso funciona mejor si el prompt deja muy claro qué debe hacer con ellos.
- **Alucina con facilidad si los apuntes no contienen la respuesta.** Ante un contexto vacío o irrelevante, un modelo suele inventar. Es preferible detectar ese caso y devolver una respuesta honesta ("no se encontró contexto relevante") antes que dejar que escriba algo plausible pero falso.
- **Determinista (sin azar) para tareas factuales.** Si quieres respuestas estables y comparables entre experimentos, evita el muestreo aleatorio; si el modelo es creativo, se desvía de los apuntes.
- **Longitud limitada.** Se fija un máximo de texto a generar: respuestas más cortas, más rápidas y con menos oportunidad de desvariar.
- **Pensamiento en voz alta.** Si el modo "thinking" está activo, la salida puede contener el borrador además de la respuesta; hay que desactivarlo o limpiarlo para quedarte solo con la respuesta.

### Por qué se genera solo el texto y no el JSON final

La respuesta final del proyecto tiene una estructura (el modelo `MinimalAnswer` de la Parte 2). Un modelo de 0.6B tiene dificultades para producir estructuras correctas de forma fiable. La división sensata es: **el modelo escribe solo el texto de la respuesta**, y **tu propio código** lo coloca dentro de la estructura junto al id, la pregunta y las fuentes. Así la parte frágil (la redacción) queda separada de la parte que debe ser exacta (la estructura).

### Criterios de una buena respuesta

El subject los define: **coherente** (se entiende), **anclada** (se apoya en los fragmentos, sin grandes invenciones) y **al grano** (responde lo que se preguntó). Y recuerda la jerarquía: no es una prueba de perfección, es una prueba de que tu sistema **le da buena evidencia y buenas instrucciones** a un modelo con limitaciones.

### Un límite que conviene aceptar

Si la búsqueda trajo fragmentos incorrectos, no hay prompt que lo arregle: el modelo solo puede escribir sobre lo que ve. Este es el motivo por el que el esfuerzo principal está en la búsqueda (Partes 3 a 5), y la generación es la última capa de pulido.

---

## 3. Diez preguntas que responder antes de programar

1. ¿Por qué hay que "volver al archivo" antes de construir el prompt?
2. ¿Qué condición debe cumplirse al releer para que el texto recuperado sea el correcto?
3. ¿Por qué usar menos fragmentos de los recuperados puede mejorar la respuesta?
4. ¿Por qué importa el orden de los fragmentos y la posición de la pregunta en un modelo pequeño?
5. ¿Por qué el presupuesto de contexto se mide en tokens y no en caracteres?
6. ¿Qué cinco partes tiene un buen prompt y para qué sirve la restricción de anclaje?
7. ¿Qué haces cuando los fragmentos entregados no contienen la respuesta?
8. ¿Por qué se prefiere la generación determinista en este proyecto?
9. ¿Por qué se le pide al modelo solo el texto y no el JSON completo?
10. Si la respuesta es mala, ¿cómo decides si mejorar el prompt o mejorar la búsqueda?

<details><summary>Respuestas rápidas (autoevaluación)</summary>

1. Porque los resultados de búsqueda solo guardan archivo y rango; el texto hay que reconstruirlo leyendo ese rango.
2. Que el archivo se lea exactamente igual que cuando se calcularon las coordenadas (mismo tratamiento de caracteres y saltos de línea).
3. Menos ruido y más espacio libre; un modelo pequeño aprovecha mejor pocos fragmentos buenos que muchos mezclados.
4. Atienden mejor al principio y al final del prompt; lo más relevante primero y la pregunta cerca del punto en que empieza a escribir.
5. Porque la ventana de contexto está definida en tokens; los caracteres no se corresponden con ellos uno a uno.
6. Reglas, restricción de anclaje, apuntes, pregunta y formato. El anclaje ("usa solo el contexto; si no está, dilo") reduce la alucinación.
7. Devuelves una respuesta honesta de "no se encontró contexto relevante" en lugar de dejar que invente.
8. Resultados estables y comparables entre experimentos, y menos desvíos respecto a los apuntes.
9. Un modelo pequeño falla con estructuras exactas; es más fiable que escriba texto y que tu código lo coloque en la estructura.
10. Mirando los fragmentos entregados: si contienen la respuesta y el modelo falla, el prompt; si no la contienen, la búsqueda.
</details>

---

## 4. Vocabulario que ya puedes usar a partir de aquí

Modelo pequeño · prompt y plantilla de chat · aumentar y presupuesto de contexto · decodificación determinista / muestreo · modo thinking · reconstrucción del texto desde coordenadas · respuesta anclada · estrategia de prompt.
