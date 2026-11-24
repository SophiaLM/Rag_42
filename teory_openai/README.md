# teory — teoría antes de tocar el teclado

Esta carpeta contiene **solo la teoría** necesaria para construir un sistema de recuperación (RAG) sobre un corpus de código. No explica el subject ni su interfaz, no monta el proyecto y no cubre tareas de entrega (README, defensa, bonus). La idea es que llegues a la parte práctica entendiendo los conceptos, sin memorizar conceptos que no usarás.

## Cómo está ordenada

El orden importa: **ningún concepto se usa antes de explicarse**. Si un archivo menciona algo "de antes", es porque se definió en un archivo anterior.

| Archivo | Concepto central |
|---|---|
| `00_llm_y_ventana_de_contexto.md` | El LLM, el conocimiento congelado, la alucinación y la ventana de contexto |
| `01_que_es_rag.md` | Qué es RAG, sus 4 etapas, `k` y el top-k, el grounding |
| `02_el_texto_y_sus_coordenadas.md` | Corpus, caracteres, codificación y **offsets** |
| `03_chunking.md` | Qué es un chunk y cómo afectan tamaño, cobertura y solape |
| `04_modelos_de_datos.md` | Las estructuras: `MinimalSource`, preguntas, `RagDataset`, `uuid4` |
| `05_tokenizacion.md` | Cómo se convierte el texto en términos para buscar |
| `06_busqueda_lexica.md` | Índice invertido, TF-IDF, BM25, `k1` y `b` |
| `07_evaluacion_recall_e_iou.md` | `recall@k` e **IoU** |
| `08_generacion_y_prompting.md` | Preparar el contexto, el prompt, la decodificación y el grounding |

Cada archivo termina con unas **preguntas de comprensión** con respuestas plegables. Si puedes responderlas con tus palabras, puedes pasar al siguiente.
