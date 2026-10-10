# 00 — El LLM y la ventana de contexto

Esta guía es **solo teoría**: explica los conceptos que necesitas entender *antes* de escribir la primera línea. No monta proyectos, no enseña herramientas que ya usas en cualquier proyecto (entornos, linters, Makefile, git) y no reproduce el subject. Aquí nos hacemos una pregunta: **¿qué necesito entender para construir un sistema de recuperación sobre un corpus?**

Empezamos por la pieza central: el modelo de lenguaje y su límite más importante.

---

## 1. Los conceptos, con palabras sencillas

**Qué es un LLM (modelo de lenguaje).**
Un LLM es, en el fondo, una máquina que **continúa texto**. Le das un texto y devuelve cuál es la continuación más probable. Repite ese paso una y otra vez —elige un trozo, añádelo, vuelve a empezar— y así "escribe" párrafos enteros. No consulta nada, no busca en internet y no razona como una persona: es un autocompletado gigantesco y muy afinado.

**Conocimiento congelado.**
Todo lo que el modelo "sabe" quedó fijado el día en que terminó su entrenamiento. Si le preguntas por algo posterior a esa fecha, por tu código privado o por un documento que él nunca vio, no lo sabe. Y como fue entrenado para producir texto **verosímil**, ante una pregunta que no puede responder no se calla: **inventa una respuesta que suena bien**. A eso lo llamamos **alucinación**.

**El prompt.**
Llamamos *prompt* al texto que le entregamos al modelo para que continúe. Es toda la información de la que dispone en ese momento: si algo no está en el prompt, para el modelo no existe.

**La ventana de contexto.**
El modelo no puede "ver" un texto arbitrariamente largo. La **ventana de contexto** es el número máximo de tokens (las unidades mínimas en que el modelo trocea el texto; concepto que ya conoces de otros proyectos) que puede atender **de una sola vez**, sumando el prompt que recibe *y* el texto que va generando. Piensa en ella como el **tamaño de la mesa de trabajo**: todo lo que el modelo está "pensando" en ese momento tiene que caber encima. Lo que no cabe en la mesa, no lo ve.

Esta ventana es la **restricción que da sentido a todo el proyecto**. El corpus (la colección de archivos que queremos consultar) es enorme —miles de archivos, cientos de miles de líneas—, así que no cabe en la mesa. La idea del sistema que vas a estudiar es precisamente esa: **elegir los pocos fragmentos que importan y subirlos a la mesa**, en vez de intentar meterlo todo.

---

## 2. Profundizando

### Dos tipos de "conocimiento": en los pesos y en el contexto

Conviene separar dos cosas que a veces se confunden:

| | Conocimiento **en los pesos** | Conocimiento **en el contexto** |
|---|---|---|
| Dónde vive | Dentro del modelo, fijado al entrenar | En el prompt que le escribes ahora |
| Cuándo cambia | Nunca (hasta que se reentrena) | En cada consulta, lo eliges tú |
| Coste de cambiarlo | Altísimo (reentrenar) | Casi nulo (redactar un prompt) |
| Frescura | La del entrenamiento | La que tú decidas |

El modelo **combina** ambos: usa lo que aprendió para entender el idioma y razonar, y usa lo que le pones en el contexto para responder sobre hechos concretos. La frase clave es: *si el dato correcto está en la mesa, el modelo puede apoyarse en él; si no está, completará con lo más probable (y probable ≠ verdadero).*

### Por qué no basta con meterlo todo

La tentación es: "si el problema es que no sabe de mi corpus, le paso el corpus entero". Falla por tres motivos:

1. **No cabe.** La ventana de contexto es finita y el corpus la desborda por órdenes de magnitud.
2. **Es caro y lento.** Más texto en la entrada = más tiempo de proceso por respuesta (especialmente en un modelo pequeño y en CPU).
3. **Distrae.** Un modelo —sobre todo uno pequeño— se atonta con prompts largos: si le das 200 páginas y solo una contiene la respuesta, es más fácil que se pierda o mezcle información. Es el problema de *la aguja en el pajar*: demasiada paja esconde la aguja.

De ahí la pregunta que vertebra todo: **¿cómo encontrar, entre miles de fragmentos, los dos o tres que de verdad responden la pregunta?**

### Las tres formas de darle conocimiento nuevo a un modelo

- **Reentrenar** (meter el conocimiento en los pesos): carísimo y lento; cada cambio del mundo exigiría otro entrenamiento. Absurdo para datos que cambian.
- **Ajuste fino / fine-tuning** (especializar los pesos con ejemplos): sigue siendo estático; no sirve para consultar un corpus que cambia cada día.
- **Contexto** (poner el conocimiento en el prompt): barato, inmediato y dinámico. Es la vía que exploraremos.

### Qué implica "ventana" para el diseño

La ventana de contexto aparece en dos momentos distintos y conviene tenerlos separados en la cabeza:

- **Al recuperar**: elegimos cuántos fragmentos (y de qué tamaño) vamos a considerar. `k` (lo verás enseguida) es cuántos.
- **Al generar**: metemos esos fragmentos en el prompt y comprobamos que **todo quepa**. Si no cabe, hay que recortar.

Un detalle que sorprende a quien empieza: el modelo **no recuerda** la conversación anterior ni el prompt de la vez pasada. Cada llamada empieza con la mesa vacía. Toda la información necesaria debe ir *otra vez* en ese prompt.

---

## 3. Preguntas para comprobar que lo entiendes

1. Explica con tus palabras por qué se dice que un LLM "está congelado en el tiempo".
2. ¿Qué es una alucinación y por qué ocurre, si el modelo está entrenado para "responder bien"?
3. ¿Qué mide la ventana de contexto: cuántas palabras sabe el modelo, o cuánto texto puede atender a la vez? ¿Por qué se mide en tokens y no en metros?
4. ¿Por qué no se le pasa el corpus entero al modelo en cada pregunta?
5. Diferencia entre conocimiento en los pesos y conocimiento en el contexto. ¿Cuál puedes cambiar sin reentrenar?
6. Si dos preguntas distintas comparten la misma conversación con el modelo, ¿recuerda la segunda lo que se le puso en el prompt de la primera? Justifica.

<details><summary>Respuestas rápidas</summary>

1. Porque todo lo que "conoce" quedó fijado al terminar su entrenamiento; no aprende nada nuevo por usarlo.
2. Es inventar una respuesta verosímil cuando no tiene el dato. Ocurre porque su objetivo es producir texto plausible, no decir la verdad.
3. Cuánto texto puede atender de golpe (entrada + salida). Se mide en tokens porque es la unidad con la que el modelo trocea y procesa el texto.
4. Porque no cabe, encarece y ralentiza cada respuesta, y distrae: demasiado texto irrelevante esconde el relevante.
5. En los pesos: fijo hasta reentrenar. En el contexto: lo eliges en cada prompt, sin tocar el modelo.
6. No. Cada llamada empieza con la mesa vacía; toda la información necesaria debe volver a estar en el prompt de esa llamada.
</details>
