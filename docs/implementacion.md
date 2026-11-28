# Implementación y verificación — 27 de noviembre de 2026

## Contexto

La implementación inicial se realizó en el clon del proyecto, en la rama `main`.

## Implementación

- `conteo_bovino/config.py`: configuración JSON validada, ROI y líneas normalizadas, sentido de avance y escala física opcional.
- `conteo_bovino/core.py`: asociación por distancia, máquina de estados A → B, cancelación por retroceso, expiración del seguimiento, clasificación por mediana, registro e historial de revisión, bloqueo de gestos sostenidos.
- `conteo_bovino/vision.py`: ROI, MOG2, umbral que elimina las sombras de MOG2, apertura/cierre, contornos y estimación del borde superior central de la silueta. Congela la actualización del fondo durante el seguimiento.
- `conteo_bovino/gestures.py`: MediaPipe Tasks Hand Landmarker, una sola mano válida y reglas geométricas para índice, dos dedos y palma. El modelo se obtiene explícitamente desde Google con `scripts/download_hand_model.py`.
- `conteo_bovino/__main__.py`: cámara/video, calibración por clics, interfaz OpenCV, selección de un evento, revisión por teclado o cámara independiente, procesamiento sin ventanas, salida anotada y corrección de sesiones guardadas.
- `scripts/create_demo.py` y `tests/`: prueba sintética reproducible y pruebas de reglas, persistencia y gestos.

Los resultados van a `runs/`. CSV conserva la clasificación automática y la final; JSON añade configuración e historial. El total siempre se deriva del número de eventos y las categorías del mismo registro. Se rechaza usar una carpeta de resultados que ya contenga archivos.

No se añadieron dependencias: se creó `.venv` con `uv sync --locked` usando Python 3.15.2 y los 19 paquetes fijados. Importaciones comprobadas: OpenCV 5.1.0, MediaPipe 1.2.3 y NumPy 2.5.5. `py` no estaba disponible en PowerShell, por lo que se usó `uv` y después el ejecutable de `.venv`.

## Resultados de verificación

Comandos ejecutados desde la raíz del clon:

```powershell
uv sync --locked
uv pip check
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts\create_demo.py
.\.venv\Scripts\python.exe -m conteo_bovino --source assets\demo_sintetico.avi --config config\example.json --no-display --output-video --output runs\demo-verificacion
git diff --check
```

Resultado final: **16 pruebas aprobadas**. Cubren pausa y permanencia en B sin duplicados; retroceso y reintento; dirección inversa; aparición inicial después de A; avance hacia la izquierda; pérdida breve y expiración; dos seguimientos separados; calibración y límite de duda; mediana de alturas; configuración inválida; conservación del total y de la categoría automática; persistencia y corrección; bloqueo/liberación de gestos; cambio de selección; geometría de dedos rotada; y ejecución completa con video real codificado de contenido sintético.

La prueba integrada genera un AVI temporal, ejecuta el programa sin ventanas, lee los resultados y comprueba un MP4 anotado no vacío. Sin calibración obtuvo 2 pendientes; con una escala artificial obtuvo 1 adulto y 1 becerro. También corrigió un evento de una sesión persistida conservando el total y comprobó que se rechaza sobrescribir una carpeta de resultados no vacía. `uv pip check` confirmó compatibilidad de los 19 paquetes; la ayuda de la CLI y la comprobación de espacios del diff terminaron correctamente.

Se conservó la demo local `assets/demo_sintetico.avi`: 670 fotogramas, 640 × 360, 30 FPS, dos cruces completos, pausa de 2 s y un intento cancelado por retroceso. Con `config/example.json`, referencia manual sintética: 2 cruces; resultado: **2 cruces, 0 adultos, 0 becerros, 2 pendientes**. Los eventos están en 5.8333 s y 18.3 s, con IDs de seguimiento 1 y 3; el ID 2 correspondió al retroceso que no contó. No hubo omisiones ni duplicados en este escenario artificial. Salida retenida: `runs/demo-verificacion/` con `session.json`, `events.csv`, `annotated.mp4` y `preview.png`. Se inspeccionó visualmente la imagen extraída del fotograma 560: ROI, líneas A/B, ID, totales y selección visibles. No se probaron las ventanas interactivas de calibración ni sus clics mediante automatización.

## Incidencias resueltas

La primera ejecución de pruebas detectó que una altura de 110 cm calculada con coordenadas decimales podía exceder por redondeo el límite inclusivo de duda de 10 cm sobre un umbral de 100 cm. Se añadió tolerancia numérica en la comparación del borde; la prueba conserva ese caso como regresión.

La regla preexistente `/Scripts/` de `.gitignore` también ocultaba `scripts/` en este Git de Windows. Se añadieron excepciones limitadas a los dos scripts fuente nuevos para que queden disponibles a colaboradores, manteniendo ignorados los demás archivos de esa carpeta.

## Modelo de manos y diagnóstico

Se descargó la revisión 1 del [modelo oficial de Hand Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker?tab=Python). Archivo local: `models/hand_landmarker.task`; SHA256 `fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1`. La URL de descarga y el hash se guardaron en `models/hand_landmarker.metadata.json`; ambos archivos quedan fuera de Git.

La creación de HandLandmarker y dos inferencias VIDEO en fotogramas negros devolvieron ninguna mano y terminaron con código 0. LiteRT emitió mensajes informativos de XNNPACK y avisos de alineación de memoria/ROI; no impidieron inferir ni cerrar el modelo. Esto comprueba la integración y carga del modelo, no la precisión de los gestos con una persona.

## Pendientes de campo y límites

Actualización posterior de la misma fecha: se descargó y probó [video público de bovinos](pruebas-internet-2026-11-27.md), con referencia manual propia para un tramo de dos cruces. Ese informe conserva las ejecuciones fallidas y exitosas, los parámetros y los cambios posteriores de la CLI. El estado sin video real descrito a continuación corresponde al cierre de la implementación inicial; la validación de campo y de categorías sigue pendiente.

No hay video real del corral en el clon, referencia manual, umbral etiquetado ni calibración de la cámara real. No se midieron precisión, omisiones, duplicados ni calidad de categorías con ganado. Tampoco se usaron cámaras físicas ni se validaron gestos reales con el operador. Las pruebas sintéticas no justifican una cifra de precisión ganadera.

La sustracción de fondo no reconoce bovinos. Su rendimiento depende de un fondo vacío inicial, cámara fija, luz estable y animales separados. Superposiciones, fragmentación, oclusiones largas, desplazamientos rápidos y personas en la ROI pueden alterar IDs o conteos. La altura de una máscara es una aproximación y puede confundirse con cuello, cabeza o regiones incompletas. Se requiere aplicar el [protocolo de validación](validacion.md) antes de uso operativo.

El sistema cuenta cruces, no identidades individuales a largo plazo. No reanuda el seguimiento desde una sesión guardada ni repara automáticamente omisiones/falsos cruces mediante la revisión de categoría.
