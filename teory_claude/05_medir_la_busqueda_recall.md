# Parte 5 — Medir la búsqueda: recall@k

Puedes construir el mejor buscador del mundo, pero sin una forma de **medirlo** no sabrás si mejora o empeora cuando cambies algo. Esta parte explica la métrica que usa el proyecto y, sobre todo, **cómo pensar con ella**.

---

## 1. Conceptos nuevos — la versión sencilla

**Verdad de referencia (ground truth)**
Las respuestas "correctas" contra las que se compara tu trabajo. Ya las conoces: es el **solucionario** de la Parte 2 (el dataset con `sources` correctas para cada pregunta).

**Acierto (hit)**
Una fuente correcta del solucionario se considera **encontrada** cuando alguno de tus resultados cumple **dos condiciones a la vez**: está en **el mismo archivo** y su **IoU** con la fuente correcta alcanza el umbral de 0.05 (Parte 1). Ambas, no una sola.

**Recall (cobertura)**
Imagina que hay **tesoros enterrados** (las fuentes correctas de una pregunta) y tú cavas unos cuantos hoyos (tus resultados). El recall responde a: *¿qué fracción de los tesoros has encontrado?* Si hay 4 tesoros y encuentras 3, tu recall es 3/4 = 0.75.

**Recall@k**
El mismo recall, pero **contando solo tus k primeros hoyos**. Es "la fracción de fuentes correctas que aparecen entre tus k primeros resultados". Con `k = 5` solo importan los cinco primeros de tu lista; lo que quede en el puesto 6 en adelante no existe.

**Recall final del sistema**
Se calcula el recall@k de **cada pregunta** y se hace la **media** de todas. Un 0.80 significa que, de media, encuentras el 80 % de las fuentes correctas.

**Precisión**
La otra cara: de los k resultados que entregaste, ¿qué fracción eran buenos? Si cavas 5 hoyos y solo 1 tenía tesoro, tu precisión es baja aunque hayas encontrado el único tesoro.

---

## 2. Profundizando

**Lo que debes llevarte de aquí:** (1) saber **calcular recall@k a mano** con un ejemplo; (2) entender por qué recall@k **no puede bajar** al subir k, y por qué eso no significa que "más k sea mejor"; (3) aprender el **método de diagnóstico**: cuando falla una pregunta, saber clasificar *por qué* falló; (4) entender el riesgo de ajustar demasiado el sistema a los datos que ves.

### Cálculo paso a paso (ejemplo)

Pregunta con **3 fuentes correctas**: A, B y C. Tu sistema devuelve (en orden) estos resultados:

| Puesto | Tu resultado | ¿Acierta alguna fuente? |
|---|---|---|
| 1 | otro archivo | No |
| 2 | archivo de A, buen solape | **Sí: A** |
| 3 | archivo de B, IoU = 0.01 | No (solape insuficiente) |
| 4 | otro archivo | No |
| 5 | archivo de C, IoU = 0.30 | **Sí: C** |
| 6 | archivo de B, IoU = 0.40 | **Sí: B** (pero ya fuera del top-5) |

- **recall@1** = 0/3 = 0
- **recall@3** = 1/3 ≈ 0.33 (solo A)
- **recall@5** = 2/3 ≈ 0.67 (A y C)
- **recall@6** = 3/3 = 1.0

El recall final sería la media de este número sobre **todas** las preguntas del dataset.

### Recall@k nunca baja al aumentar k

Al ampliar k solo *añades* resultados a mirar; nunca quitas ninguno. Por tanto recall@1 ≤ recall@3 ≤ recall@5 ≤ recall@10. Esto no significa que k grande sea siempre mejor: **más k aumenta la probabilidad de cubrir la respuesta, pero a costa de precisión** (más resultados inútiles) y, al generar, de ruido en la ventana de contexto (Parte 0). La métrica que te piden (recall@5) mide el equilibrio: "¿está en los 5 primeros?".

### Por qué el IoU y no "coincidencia exacta"

Exigir coordenadas exactas castigaría a cualquier sistema que cortara distinto que el solucionario, aunque trajera exactamente la información correcta. El IoU permite flexibilidad: tu chunk no tiene que ser idéntico, solo tiene que cubrir una parte **significativa** de la zona correcta. Pero, como viste, sigue exigiendo que el chunk no sea tan grande que la zona correcta se diluya.

### Docs frente a code: dos tipos de pregunta, dos umbrales

| | Preguntas de documentación | Preguntas de código |
|---|---|---|
| Estilo | Lenguaje natural, a menudo parafraseado | Más técnicas, a veces con nombres literales |
| Dónde suele estar la respuesta | Una sección de un `.md` | Una función o clase de un `.py` |
| Qué lo favorece | Buena tokenización de raíces, rutas y títulos en la búsqueda | Troceo y conservación de identificadores, chunks por definición |

Como son estilos distintos, se miden **por separado**: un sistema puede ir muy bien en uno y flojo en el otro, y la media escondería el problema.

### El método de diagnóstico: por qué falla una pregunta

Cuando una pregunta no se acierta, no sirve "mejorar el buscador" en abstracto. Se clasifica la causa:

| Causa | Cómo se reconoce | Dirección del arreglo |
|---|---|---|
| **El archivo ni siquiera estaba indexado** | La fuente correcta está en un tipo de archivo que excluiste | Ampliar qué se indexa |
| **Archivo equivocado** | Las palabras de la pregunta no coinciden con las del chunk correcto | Mejorar tokenización, texto de búsqueda ampliado; o recurrir a lo semántico |
| **Archivo correcto, rango equivocado** | Devuelves el archivo, pero otro trozo, o un chunk demasiado grande (IoU bajo) | Revisar tamaño y forma de cortar |
| **Está, pero fuera del top-k** | La fuente correcta aparece en el puesto 8 | Ajustar la puntuación (`k1`, `b`), reducir casi-duplicados |

Esta clasificación convierte "no funciona" en "falla por esto, así que ataco aquello".

### Experimentar con método

Para mejorar de forma fiable, el proceso es: **línea base → un solo cambio → medir → conservar o descartar**. Si cambias tres cosas a la vez y mejora, no sabes cuál ayudó; si empeora, tampoco sabes cuál estorbó. El resultado es una pequeña **tabla de experimentos**: "cambio → recall@5 en docs → recall@5 en code".

### Dos trampas conceptuales

- **Sobreajuste (overfitting).** Si afinas el sistema mirando las mismas preguntas una y otra vez, acabas optimizando para *esas* preguntas y no para las preguntas en general. Puede subir tu cifra sin que el sistema sea realmente mejor, y fallar en datasets nuevos. Preferible: mejoras **generales** (mejor tokenización) frente a trucos para casos concretos; y, si hay suficientes preguntas, reservar algunas sin tocar como comprobación.
- **Ruido estadístico.** Con 100 preguntas, un punto de recall equivale a una o dos preguntas. Variaciones de ±1 % pueden ser azar; no conviene sacar conclusiones de ellas.

### Tu medida y la oficial

Tu cálculo propio es un **termómetro casero** para iterar. La cifra que cuenta la calcula el corrector. Si discrepan, la oficial manda, y la discrepancia suele delatar un detalle de interpretación (por ejemplo, la convención del último índice o si el umbral es "mayor" o "mayor o igual").

---

## 3. Diez preguntas que responder antes de programar

1. ¿Qué dos condiciones debe cumplir un resultado tuyo para considerarse acierto de una fuente correcta?
2. Una pregunta tiene 5 fuentes correctas y tu top-5 contiene 2. ¿Cuál es su recall@5?
3. ¿Cómo se obtiene el recall final del sistema a partir de los recalls individuales?
4. ¿Por qué recall@10 nunca puede ser menor que recall@5?
5. Si recall@5 y recall@10 coinciden en tu sistema, ¿qué te dice eso?
6. ¿Qué diferencia hay entre recall y precisión? ¿Cuál mide el proyecto?
7. ¿Por qué se miden docs y code por separado en lugar de una sola media?
8. Una fuente correcta está en `ruta/a.md`; tu chunk de `ruta/b.md` la cubre perfectamente en rango. ¿Es acierto?
9. Tu sistema sube de 78 % a 79 % en recall@5 tras un cambio. ¿Por qué no deberías celebrarlo sin más?
10. ¿Qué es el sobreajuste en este contexto y cómo lo mitigas?

<details><summary>Respuestas rápidas (autoevaluación)</summary>

1. Estar en el mismo archivo y tener un IoU con la fuente correcta de al menos 0.05.
2. 2/5 = 0.40.
3. Calculando el recall@k de cada pregunta y haciendo la media.
4. Porque k mayor solo añade resultados a considerar; nunca elimina ninguno.
5. Que las fuentes correctas que te faltan no están dentro de tus 10 primeros: el problema no es el orden, sino que **ni aparecen** (falla la recuperación en sí o el chunking).
6. Recall: fracción de fuentes correctas halladas. Precisión: fracción de tus resultados que eran correctos. El proyecto mide recall.
7. Porque tienen estilos de pregunta distintos y umbrales distintos; una media escondería un punto débil.
8. No: el archivo es distinto; el IoU entre archivos distintos es 0.
9. Con pocas preguntas, un punto puede ser una o dos preguntas: podría ser puro azar.
10. Ajustar tanto el sistema a las preguntas que ves que pierde generalidad; se mitiga con mejoras generales y reservando preguntas sin tocar para comprobar.
</details>

---

## 4. Vocabulario que ya puedes usar a partir de aquí

Verdad de referencia · acierto (mismo archivo + IoU) · recall, recall@k y su media · precisión · diagnóstico de fallos (cuatro causas) · línea base y experimentos de un solo cambio · sobreajuste.
