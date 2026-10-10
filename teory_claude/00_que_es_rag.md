# Parte 0 — Qué es RAG y por qué existe

Antes de cualquier detalle técnico necesitas tener clara una sola idea: **por qué no basta con preguntarle al modelo directamente**. Todo el proyecto es la respuesta a esa pregunta.

---

## 1. Conceptos nuevos — la versión sencilla

**LLM (modelo de lenguaje)**
Un programa que ha leído una cantidad enorme de texto y ha aprendido a **continuar frases de forma plausible**. Tú le das un texto y él escribe lo que "tocaría" a continuación, pieza a pieza. No consulta una base de datos ni busca en internet: solo usa lo que aprendió.

**Modelo "congelado"**
Su aprendizaje terminó un día concreto. Es un estudiante que estudió una biblioteca entera, se encerró en una habitación y ya no sale: lo que pasó después, o lo que nunca estuvo en esa biblioteca (tu código privado, la documentación de ayer), no existe para él.

**Alucinación**
Cuando al estudiante le preguntas algo que no sabe, no suele callarse: **inventa algo que suena bien**. Lo hace con seguridad total. A eso se le llama alucinación, y es el problema central que RAG intenta reducir.

**RAG (Retrieval-Augmented Generation)**
"Generación aumentada con recuperación". Es un examen **a libro abierto**: en lugar de exigirle al estudiante que lo recuerde todo, le dejas entrar con apuntes. Un ayudante (el sistema de búsqueda) corre a la biblioteca, saca las páginas que parecen relevantes y se las pone en la mesa. El estudiante responde **leyendo esas páginas**.

**Las cuatro etapas de RAG**
1. **Indexar**: preparar la biblioteca para poder buscar rápido (se hace una vez, antes de las preguntas).
2. **Recuperar**: dada una pregunta, encontrar los fragmentos de texto más relevantes.
3. **Aumentar**: elegir cuáles de esos fragmentos entregar y colocarlos junto a la pregunta.
4. **Generar**: el modelo lee todo eso y redacta la respuesta.

**k (cuántos resultados pides)**
Cuando el sistema recupera, no devuelve "la respuesta": devuelve una **lista ordenada** de fragmentos, del más prometedor al menos. `k` es simplemente **cuántos de esa lista te quedas**. Con `k = 5` te quedas con los cinco primeros. Es un número que decides tú, igual que decir "tráeme las 5 mejores páginas".

**Ventana de contexto**
Tiene su propia sección más abajo porque es el concepto que más cuesta y el que más se usa después.

---

## 2. Profundizando

**Lo que debes llevarte de aquí:** (1) por qué RAG existe y qué problema real resuelve; (2) por qué hay que *elegir* qué páginas entregar en vez de entregarlas todas; (3) que "buscar bien" y "redactar bien" son dos habilidades separadas.

### Por qué no reentrenar el modelo

Añadir conocimiento *dentro* del modelo exige reentrenarlo: carísimo y lento. RAG hace lo contrario: el modelo no cambia, solo cambia **lo que ve en el momento de responder**. Es la diferencia entre obligar al estudiante a memorizar un manual nuevo cada semana y dejarle abrir el manual en la página correcta.

### La ventana de contexto, explicada despacio

Imagina que el modelo trabaja sobre **una mesa de tamaño fijo**. Todo lo que quiere "tener delante" mientras responde tiene que caber en esa mesa:

```
┌──────────────────────── MESA (ventana de contexto) ────────────────────────┐
│ instrucciones  │  apuntes (fragmentos)  │  la pregunta  │  hueco para la    │
│ que le das     │  que le entregas       │               │  respuesta        │
└────────────────────────────────────────────────────────────────────────────┘
```

Lo importante, en cuatro ideas:

1. **Es un límite de tamaño medido en tokens** (las piezas en que el modelo trocea el texto). No es "cuántos archivos", ni "cuántas páginas": es una cantidad total de texto que cabe de golpe.
2. **Todo comparte la misma mesa**: instrucciones + apuntes + pregunta + *la propia respuesta que va escribiendo*. Si los apuntes ocupan toda la mesa, no queda sitio para responder.
3. **No hay memoria fuera de la mesa**. Lo que no está sobre la mesa en este momento, para el modelo no existe. Y al terminar una pregunta, la mesa se vacía: la siguiente empieza desde cero.
4. **"Cabe" no es lo mismo que "lo aprovecha bien"**. Un modelo pequeño con la mesa llena de texto se despista: pierde detalles, mezcla datos, se queda con lo del principio o el final. Menos apuntes pero muy buenos suelen funcionar mejor que muchos apuntes con ruido.

**Por qué esto justifica todo el proyecto:** el repositorio que vas a consultar tiene cientos de miles de líneas. Es muchísimo más grande que cualquier mesa. Aunque cupiera, sería inútil: el modelo se ahogaría. Por eso necesitas la etapa de **recuperar**: reducir una biblioteca entera a las pocas páginas que importan para *esta* pregunta, y que *esas* sí quepan cómodamente.

### El dilema de k

Pedir pocos resultados (k pequeño) es limpio pero arriesgado: si la página correcta es la sexta, la perdiste. Pedir muchos (k grande) hace más probable incluir la correcta, pero llenas la mesa de páginas inútiles. No hay un k perfecto: hay un **equilibrio** entre "no perderme la respuesta" y "no ahogar al modelo". Más adelante verás que medir la calidad de la búsqueda depende justo de este k.

### Dos calidades que no se mezclan

| Calidad | Pregunta que responde | Quién es responsable |
|---|---|---|
| **De recuperación** | ¿Trajo las páginas correctas? | El ayudante que busca |
| **De generación** | ¿Redactó bien usando esas páginas? | El estudiante (el modelo) |

La regla de oro: **si el ayudante trae páginas equivocadas, el mejor estudiante del mundo no puede acertar**. Por eso casi todo el esfuerzo se concentra en buscar bien, y por eso se mide la búsqueda por separado.

### Respuesta "anclada" (grounding)

Una respuesta está *anclada* cuando cada cosa que dice puede rastrearse hasta las páginas entregadas, y *no anclada* cuando el modelo añade datos de su cosecha. En RAG buscamos lo primero: el modelo no es una fuente de verdad, es un **redactor de los apuntes**.

---

## 3. Diez preguntas que responder antes de programar

1. ¿Por qué se dice que un LLM está "congelado" y qué consecuencia práctica tiene?
2. ¿Por qué un modelo, ante una pregunta que no sabe, tiende a inventar en lugar de decir "no lo sé"?
3. ¿En qué se diferencia dar conocimiento al modelo *reentrenándolo* de dárselo *en el momento de responder*?
4. Nombra las cuatro etapas de RAG y di cuál de ellas se hace *antes* de que llegue ninguna pregunta.
5. Si `k = 3`, ¿qué recibes exactamente del sistema de búsqueda?
6. ¿Qué cuatro cosas ocupan la ventana de contexto a la vez?
7. ¿Por qué no basta con entregarle al modelo el repositorio entero, aunque la ventana fuese enorme?
8. Tu prompt ocupa casi toda la ventana. ¿Qué problema te encuentras al generar la respuesta?
9. ¿Por qué un k muy grande puede empeorar la respuesta final aunque "incluya" la página correcta?
10. Si la respuesta final es mala, ¿cómo distingues si falló la búsqueda o la redacción?

<details><summary>Respuestas rápidas (autoevaluación)</summary>

1. Su aprendizaje terminó en una fecha; no conoce nada posterior ni nada que no estuviera en sus datos (tu código privado, novedades).
2. Está entrenado para producir texto plausible, no para detectar los límites de su propio conocimiento; completar con lo más probable es su comportamiento por defecto.
3. Reentrenar cambia el modelo (caro y lento); RAG deja el modelo igual y cambia lo que ve en el momento de responder.
4. Indexar, recuperar, aumentar, generar. Indexar se hace antes de las preguntas.
5. Una lista ordenada con los 3 fragmentos más relevantes.
6. Instrucciones, apuntes (fragmentos), pregunta y la propia respuesta que se va generando.
7. Es demasiado grande para caber; y aunque cupiera, un modelo pequeño con tanto ruido se despistaría ("cabe" ≠ "aprovecha bien").
8. No queda sitio para la respuesta (se corta o no se puede generar bien), además de que el exceso de texto lo despista.
9. Los fragmentos extra son ruido que compite con el correcto y consume espacio de la ventana.
10. Mirando si los fragmentos entregados contenían la respuesta: si no la contenían, falló la búsqueda; si la contenían y aun así respondió mal, falló la redacción.
</details>

---

## 4. Vocabulario que ya puedes usar a partir de aquí

LLM · alucinación · RAG · indexar / recuperar / aumentar / generar · `k` (top-k) · ventana de contexto · grounding (respuesta anclada).
