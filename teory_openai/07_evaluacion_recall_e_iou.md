# 07 — Evaluar la búsqueda: recall@k e IoU

Un sistema de búsqueda sin forma de medirlo es una caja negra: puedes cambiar cosas, pero no sabes si mejoras. Este archivo explica **cómo se mide la calidad de la recuperación** con dos ideas: **recall@k** (cuánto encontramos) e **IoU** (cómo de bien solapa lo que devolvimos con lo correcto).

**Lo que te llevas:** sabrás calcular de forma intuitiva si una búsqueda "acertó", entenderás qué es el solape por IoU y por qué no hace falta clavar el rango exacto.

---

## 1. Los conceptos, con palabras sencillas

**Verificación (ground truth).**
Para medir necesitamos saber **cuáles eran las fuentes correctas**. En un dataset "con respuestas", cada pregunta trae su lista de `sources` correctas (los `MinimalSource` del archivo 04). Eso es el **patrón de referencia**.

**Recall (cobertura de lo correcto).**
El *recall* responde: **de todas las fuentes correctas, ¿cuántas encontré?** Si una pregunta tiene dos fuentes correctas y tú recuperaste una, tu recall en esa pregunta es `1/2 = 0.5`.

**`k` y recall@k.**
Aquí vuelve `k` (archivo 01). El sistema no devuelve todo lo que cree relevante, devuelve el **top-k**. Así que la pregunta fina es: **de las fuentes correctas, ¿cuántas aparecen entre mis k primeros resultados?** Eso es el **recall@k**. Con `k = 5` hablamos de recall@5; con `k = 10`, recall@10.

**IoU (Intersection over Union).**
Vamos por partes, porque este término se usa a veces sin explicarse.

- Lo que se solapa son **dos rangos de caracteres sobre el mismo archivo**: el rango que **devolviste** y el rango **correcto**.
- La **intersección** es la parte que ambos rangos comparten (donde se pisan).
- La **unión** es toda la zona que cubren entre los dos.
- El **IoU** es el cociente entre ambas: `intersección / unión`. Va de `0` (no se tocan) a `1` (coinciden exactamente).

Dicho con una imagen: son dos subrayados sobre la misma línea. El IoU mide **qué tanto se pisan** en proporción a lo que cubren juntos. No mide *cuánto texto* hay, sino **cuánto se superponen**.

---

## 2. Profundizando

### Un acierto = mismo archivo + solape suficiente

Una fuente de referencia cuenta como **encontrada** cuando existe, entre tus primeros `k` resultados, una fuente que cumpla **dos condiciones**:

1. **Mismo `file_path`** (recordatorio del archivo 02: se compara carácter a carácter; un prefijo distinto es otro archivo).
2. **Solape suficiente**: que el IoU entre tu rango y el rango correcto supere un umbral bajo.

¿Por qué un requisito y no exigir el rango exacto? Porque **es casi imposible** reproducir un offset exacto: depende de cómo partiste los chunks. Exigir coincidencia perfecta castigaría a todo el mundo. En vez de eso, se pide que hayas traído la **región correcta** del archivo correcto. Por eso decimos que devolver un chunk que **cubre** la zona correcta ya cuenta.

**El umbral es bajo**: basta un solapamiento pequeño. Pero no es cero, y tiene una consecuencia importante que ya intuías del archivo 03: **un chunk gigante que "contiene" la respuesta puede solapar poco porcentualmente** si la fuente de referencia es pequeña. La precisión del chunking se nota justo aquí.

### Cómo se calcula el recall, paso a paso

Para cada pregunta:

1. Toma sus fuentes correctas `R` y tus resultados `S` (los primeros `k`).
2. Para **cada** fuente correcta, pregunta: ¿hay algún resultado en `S` que sea del **mismo archivo** y que **solape** lo suficiente?
3. `recall(pregunta) = (número de fuentes correctas encontradas) / (número total de fuentes correctas)`.
4. El **recall@k del sistema** es la **media** de esos valores sobre todas las preguntas.

Un detalle que se escapa a veces: si una pregunta tiene **varias** fuentes correctas, hay que encontrar cada una por separado. Dos resultados que cubren el mismo sitio no valen por dos fuentes distintas.

### La fórmula del IoU, con números

Dados dos rangos `[a1, b1]` y `[a2, b2]`:

```
intersección = max(0, min(b1, b2) − max(a1, a2))
unión        = (b1 − a1) + (b2 − a2) − intersección
IoU          = intersección / unión        (0 si la unión es 0)
```

Ejemplo: rango devuelto `[100, 300]` (200 de ancho) y rango correcto `[250, 350]` (100 de ancho).
- Intersección = `min(300,350) − max(100,250) = 300 − 250 = 50`.
- Unión = `200 + 100 − 50 = 250`.
- IoU = `50 / 250 = 0.2`. Con un umbral bajo, **cuenta como acierto**.

Si los rangos no se tocaran, la intersección sería 0 y el IoU, 0.

### Docs y código: dos perfiles, se miden aparte

Las preguntas sobre **documentación** y sobre **código** se comportan distinto y conviene medirlas **por separado**:

| | Preguntas de docs | Preguntas de código |
|---|---|---|
| Estilo | Parafrasean en lenguaje natural | Más técnicas, a veces citan identificadores |
| Fuente típica | Una sección de un `.md` | Un trozo de un `.py` |
| Qué ayuda | Stemming, ruta y títulos en lo que se indexa | Trocear identificadores, conservar el literal |
| Dificultad | Media | Suele ser más difícil (por los identificadores) |

Si mezclas ambos en una sola cifra, una mejora en uno puede tapar un empeoramiento en el otro. Mídelos aparte.

### El bucle de mejora, en concepto

Medir no es un trámite del final: es **el motor del desarrollo**. El método:

1. **Línea base**: el sistema mínimo que funcione (chunking simple + puntuación básica). Anota sus números.
2. **Análisis de fallos**: coge las preguntas que fallan y **clasifica la causa**:
   - *Archivo equivocado* (el vocabulario de la pregunta no está en el chunk) → tokenización, stemming, enriquecer el texto indexable.
   - *Archivo correcto pero rango que solapa poco* → chunk demasiado grande o mal cortado.
   - *Archivo no indexado* → una extensión que excluiste sin darte cuenta.
   - *Correcta pero fuera del top-k* → ajustar el ranking (`k1`, `b`, deduplicar resultados casi iguales).
3. **Un cambio cada vez** y volver a medir: así sabes a qué se debe la mejora.
4. **Cuidado con el sobreajuste**: si afinas demasiado sobre las preguntas que ves, puedes fallar con preguntas nuevas. Prefiere mejoras **generales** (mejor tokenización) a trucos específicos.

---

## 3. Preguntas para comprobar que lo entiendes

1. ¿Qué mide el recall y qué **no** mide?
2. Si una pregunta tiene 4 fuentes correctas y tus 5 primeros resultados contienen 3 de ellas, ¿cuál es su recall@5?
3. ¿Cómo se combina el recall de cada pregunta para obtener la cifra del sistema?
4. ¿Qué es el IoU? Explica qué son la intersección y la unión de dos rangos.
5. Calcula el IoU de `[100, 300]` frente a `[250, 350]`. ¿Cuenta con un umbral bajo?
6. ¿Por qué un acierto exige el **mismo archivo** además del solape?
7. ¿Por qué NO se exige que el rango coincida exactamente? ¿Y qué consecuencia tiene para chunks grandes?
8. ¿Por qué conviene medir docs y código por separado?
9. En el bucle de mejora, ¿por qué cambiar **una sola cosa** por experimento?

<details><summary>Respuestas rápidas</summary>

1. Qué fracción de las fuentes correctas aparece en los k primeros resultados; no mide si el resto es ruido ni la calidad de la respuesta final.
2. 3/4 = 0.75.
3. Es la media del recall de cada pregunta sobre todas las preguntas.
4. Intersección = zona que comparten; unión = zona que cubren entre los dos; IoU = intersección / unión (0 a 1).
5. Intersección 50, unión 250, IoU = 0.2 → sí, con un umbral bajo.
6. Porque una fuente es una ubicación en un archivo concreto; solapar rangos de otro archivo no significa nada.
7. Porque reproducir offsets exactos es casi imposible; se pide cubrir la región correcta. Un chunk gigante puede solapar poco porcentualmente y no contar.
8. Porque se comportan distinto y una sola cifra puede ocultar que uno mejora y el otro no.
9. Para poder atribuir la mejora (o el empeoramiento) a ese cambio concreto.
</details>
