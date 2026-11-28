# Detección individual, cabeza y lomo — 27 de noviembre de 2026

## Exportación fluida del 28 de noviembre de 2026

El usuario observó saltos en la demostración interactiva. El original de Farmquip tiene 50 FPS y la configuración analiza uno de cada cinco fotogramas. En la ejecución anterior, la CPU procesó 80 imágenes en 24.10 s, unas 3.3 inferencias por segundo de reloj. La ventana espera a cada inferencia antes de mostrar la siguiente imagen.

Para reproducir la prueba a la velocidad original, añadir `--smooth-output` al comando de exportación con `--output-video`. El MP4 conserva la resolución y todos los fotogramas del intervalo original. Las cajas y marcas se mantienen entre inferencias y el contador se actualiza con cada cruce observado por el detector. El archivo puede reproducirse a 50 FPS después de procesarlo. La demostración que analiza en el momento sigue dependiendo de la velocidad del modelo.

La exportación `runs/farmquip-fluido-50fps/annotated.mp4` se verificó con 400 fotogramas a 1280 × 720 y 50 FPS. Se comprobaron dos fotogramas consecutivos entre inferencias para verificar que conservan movimiento de la fuente. El contador analizó 80 fotogramas y guardó 2 cruces a 83.4 y 87.5 s. Pasaron las 28 pruebas automatizadas, incluida la comprobación del ritmo de salida y el límite del intervalo.

## Ajustes del 28 de noviembre de 2026

Por solicitud del usuario, el modo `pose` muestra únicamente el total de bovinos que completan A → B. Cada evento se guarda como bovino y el resumen contiene solo el total. La demostración de pose utiliza Espacio para iniciar o pausar, R para repetir y Q para cerrar. Las sesiones históricas y el modo de movimiento siguen siendo compatibles con la revisión anterior.

La configuración de Farmquip activa `pose_detail_pass`. El detector analiza el fotograma entero y después amplía la región de paso para recuperar candidatos con menor puntuación. Si una caja ampliada coincide estrechamente con una existente se descarta. Para aceptar una detección nueva en el recorte se requieren puntos fiables de hocico, cuello y base de cola. La supresión por cabeza compartida se aplica después de combinar ambas pasadas.

Comparación con el mismo tramo de Farmquip (81–89 s, 80 fotogramas analizados). El promedio de detecciones dentro de la región pasó de 4.04 a 4.74 por fotograma. Se revisaron los fotogramas de 81, 82, 84 y 87 s y se observaron marcas adicionales sobre bovinos parcialmente tapados. Los eventos de cruce siguieron siendo dos, a 83.4 y 87.5 s. El promedio mide detecciones en pantalla y todavía puede incluir errores de asociación con animales muy juntos. La comparación quedó en `runs/farmquip-refinado-prueba/comparacion.jpg`.

Pasaron 28 pruebas automatizadas, incluida una de guardado y reapertura de una sesión de conteo único. En la ventana de Windows se verificó el rótulo «Bovinos que cruzaron» y los controles sin categorías. Se dejó abierta en pausa inicial.

## Solicitud e implementación

El usuario autorizó implementar la propuesta de representar cada vaca con su cabeza y lomo para separar entidades y contar sus cruces. También dejó abierto en Brave un video para probarla. Se identificó mediante el título y la URL visibles del navegador: [Corral FQ 60A - Farmquip](https://www.youtube.com/watch?v=BzFWrCOscHM), del canal Farmquip Argentina. No se modificó el navegador ni se publicó contenido.

Se implementó un modo adicional `--detector pose`, conservando el modo anterior `motion` y los archivos previos. La alternativa inicial de DeepLabCut/SuperAnimal no se instaló: se eligieron exportaciones ONNX oficiales que ya funcionan con OpenCV DNN y el Python 3.15.2 existente, sin añadir dependencias al proyecto ni requerir entrenamiento inicial.

La cadena es:

1. YOLOX-s de OpenCV Zoo detecta cajas individuales y se conserva la clase COCO `cow` (índice 19). Se filtra por puntuación y NMS.
2. RTMPose-m AP-10K estima 17 puntos anatómicos dentro de cada caja, incluida nariz/hocico, cuello y base de cola.
3. Se dibuja un círculo centrado en el hocico y un eje entre cuello y base de cola. No es un contorno exacto de la cabeza ni una medición anatómica del borde del lomo. No se dibujan puntos que no superen el umbral configurado.
4. Cajas que se solapan y predicen prácticamente el mismo hocico y cuello se tratan como duplicados. Se conserva la que combina mejor puntuación de detección y anatomía. Cabezas distintas se conservan como entidades diferentes.
5. El seguimiento usa asignación global de coste mínimo y predicción corta de movimiento; compara también puntos anatómicos válidos. Se conserva un ID durante pérdidas breves, pero no se dibujan observaciones viejas como si fueran detecciones actuales.
6. El centro de la caja individual es la referencia estable que cruza A y B. Los puntos ayudan a distinguir/asociar entidades; no se usa el desplazamiento inestable de una predicción del lomo como referencia de conteo. Cada ID cuenta una vez.

El modo de movimiento sigue usando su asociación anterior y necesita fondo vacío. El modo de pose no necesita aprender un fondo vacío. Las dos opciones conservan la revisión por teclado/gestos y el registro de eventos.

## Fuentes de modelos y archivos

Documentación primaria consultada:

- [OpenCV Zoo: detector YOLOX y procesamiento oficial](https://github.com/opencv/opencv_zoo/tree/main/models/object_detection_yolox).
- [OpenMMLab: RTMPose, sección Animal 2d y exportación ONNX](https://github.com/open-mmlab/mmpose/tree/main/projects/rtmpose).
- [Definición oficial de puntos AP-10K](https://github.com/open-mmlab/mmpose/blob/main/configs/_base_/datasets/ap10k.py).

Los pesos se guardan en `models/animal_pose/`, fuera de Git, con sus URLs y hashes en `manifest.json`. `scripts/download_pose_models.py` descarga los dos paquetes, verifica los hashes fijados y extrae únicamente la red de pose. No ejecuta archivos del ZIP.

| Archivo | SHA256 |
| --- | --- |
| `yolox_s.onnx` | `c5c2d13e59ae883e6af3b45daea64af4833a4951c92d116ec270d9ddbe998063` |
| `rtmpose_ap10k.zip` | `2d75445331cf2f21d6e164430f96ffa765cd874872965ae1736932dda03987f0` |
| `rtmpose_ap10k.onnx` | `1cfd1c86e0d9e5d5f95178bcd95ee9a4e8386a624cd3c57519f27ff58cac7f28` |

El hash de YOLOX coincide con el publicado por su repositorio. El del paquete RTMPose se calculó al descargarlo desde OpenMMLab y se fijó para reproducir esta versión. La exportación devuelve dos tensores SimCC de 17 × 512; se usa entrada cuadrada 256 × 256, normalización RGB del modelo y transformación inversa de la caja ampliada 1.25. Los JSON SDK incluidos mezclan tamaños genéricos 192 × 256 con la configuración AP-10K 256 × 256; se comprobó la red real y se usó la configuración cuadrada de AP-10K. Las puntuaciones de puntos no son probabilidades calibradas y pueden superar 1.

No se modificaron `pyproject.toml`, `uv.lock` ni `requirements.txt`. Las inferencias se ejecutaron en CPU, aunque el equipo tiene una RTX 3060; no se configuró CUDA. La selección explícita de destino de OpenCV emitía un aviso del nuevo motor; se conservó el backend OpenCV y su destino CPU por defecto.

## Video del usuario

Se descargó localmente con `yt-dlp` mediante `uvx`, sin cookies, cuenta ni cambios en las dependencias del proyecto. El proveedor permitió obtener el formato 298: MP4 H.264, 1280 × 720, 50 FPS, 5,650 fotogramas, 113 s, sin audio. Los metadatos indican publicación el 18 de julio de 2023. Se mantiene el crédito de Farmquip en la imagen y en esta documentación.

Ruta: `assets/internet/farmquip/BzFWrCOscHM.mp4`; metadatos originales: `BzFWrCOscHM.info.json`. Hash del MP4: `e7f553c5a1d2e9bca8fe44f269e8e6f30466088f67c77ba5b89eb1da277f2820`. No se subió ni redistribuyó el video. La carpeta `assets/` sigue fuera de Git.

El video contiene tomas aéreas, desplazamientos y cambios de plano. Se eligió el intervalo **81–89 s**, donde los bovinos entran en una manga lateral. No se contó el video editado completo como una sola trayectoria. En tomas aéreas más lejanas, por ejemplo a 55 s, el detector llegó a devolver cero bovinos: no se garantiza funcionamiento en toda la grabación.

Configuración `config/farmquip-pose.json`: ROI `(0.20, 0.32, 0.79, 0.64)`, líneas A `0.46` y B `0.67`, sentido derecha, umbral del detector 0.35, puntos 0.30, distancia máxima 0.12 y pérdida máxima 0.6 s. Es una configuración para esa toma, no universal. Las líneas son coordenadas de la imagen, por lo que un paneo puede alterar su correspondencia con una posición física.

## Pruebas y resultados

Se ejecutaron **27 pruebas automatizadas**, todas aprobadas. Las nuevas comprueban dos entidades que cruzan simultáneamente, cajas parcialmente superpuestas, orden cambiante de detecciones, pérdida breve de un animal sin duplicar el otro, asignación global, supresión de una cabeza duplicada, conservación de dos cabezas diferentes, decodificación de puntos y error claro sin pesos. También se verificó que el muestreo de fotogramas conserva el tiempo original del evento y la duración del MP4 anotado. Las pruebas de entidades sintéticas verifican la lógica; no sustituyen las inferencias reales descritas a continuación.

| Ejecución real | Resultado | Salida |
| --- | --- | --- |
| Farmquip 81–89 s, cada 5 fotogramas | **2 cruces**, a 83.4 y 87.5 s; ambos pendientes de categoría | `runs/farmquip-pose-final/` |
| `Toros7.mp4` completo, cada 3 fotogramas, configuración de ejemplo | **6 cruces**; la pasada ya iniciada al comienzo no cumple un cruce completo observado A → B | `runs/toros7-pose-final/` |

La [referencia visual de Farmquip](referencias/farmquip-81-89.csv) contiene dos cruces aproximados a 83.5 y 87.5 s, con tolerancia de 0.4 s. Se revisaron sus imágenes alrededor de B para comprobar que corresponden a dos animales diferentes, no solamente a un total coincidente. En este tramo no se observaron omisiones ni eventos extra al comparar esos dos cruces. No se infiere una precisión general a partir de dos pasos.

En Toros7 se revisaron los seis eventos contra las secuencias de la fuente y sus imágenes de cruce. El video muestra una pasada parcial inicial y seis posteriores completas. El modo de movimiento anterior había registrado solo 1 en la toma completa; la nueva ejecución registra las seis completas sin necesitar fondo vacío. Los instantes del sistema son aproximadamente 2.300, 3.899, 4.599, 6.099, 9.198 y 13.297 s. Es una comprobación sobre material ya inspeccionado y usado durante el desarrollo, no una evaluación independiente.

Las carpetas de salida contienen `session.json`, `events.csv`, `annotated.mp4` y, en modo pose, `detections.jsonl` con cajas, puntos y asignaciones por fotograma procesado. Se conservan las ejecuciones anteriores y los ensayos fallidos; no se sobrescribieron.

## Incidencias corregidas durante el desarrollo

La primera versión usaba el punto medio cuello/cola para cruzar líneas y produjo saltos de posición al ocultarse un animal. Se cambió la referencia al centro de su caja. Además, dos cajas distintas podían localizar el mismo hocico/cuello y aparentar dos entidades; se añadió la supresión anatómica descrita arriba, con pruebas que evitan fusionar dos cabezas claramente distintas. En la toma Farmquip eso eliminó un evento adicional. La asociación global también mantuvo un paso que la asociación local perdía en Toros7.

Las primeras salidas `runs/farmquip-pose-81-89/` y `runs/toros7-pose-completo/` corresponden a esas versiones de desarrollo: 3 y 5 eventos, respectivamente. No deben citarse como resultados finales. Sus trazas se usaron para diagnosticar los cambios, por lo que los resultados finales no se presentan como una validación ciega.

## Ejecutar y ver la demostración

Preparar los pesos una vez desde la raíz del clon:

```powershell
.\.venv\Scripts\python.exe -m scripts.download_pose_models
```

Abrir la demostración interactiva, inicialmente en pausa:

```powershell
.\.venv\Scripts\python.exe -m scripts.show_demo --source assets\internet\farmquip\BzFWrCOscHM.mp4 --config config\farmquip-pose.json --detector pose --frame-stride 5 --start-seconds 81 --end-seconds 89
```

Espacio inicia/pausa, R reinicia y Q cierra. La ventana se llama **Conteo bovino - Cabeza y lomo** y permanece abierta al terminar. El lanzador procesa el archivo original con las clases del prototipo; no reproduce un MP4 ya anotado. Conserva sesiones por separado en `runs/demostracion-en-vivo/`.

En el equipo del usuario se inició la demostración con Espacio. Se comprobaron los círculos y las líneas durante la reproducción. La sesión terminó después de procesar 80 fotogramas y guardó dos cruces, a 83.4 y 87.5 s. Se dejó abierta la ventana final para repetir la demostración con R.

Procesar y exportar sin ventanas, usando una carpeta nueva:

```powershell
.\.venv\Scripts\python.exe -m conteo_bovino --source assets\internet\farmquip\BzFWrCOscHM.mp4 --config config\farmquip-pose.json --detector pose --frame-stride 5 --start-seconds 81 --end-seconds 89 --no-display --output-video --output runs\farmquip-repeticion01
```

`--frame-stride 5` analiza 10 fotogramas por segundo de una fuente de 50 FPS y escribe el MP4 a 10 FPS, conservando los 8 s del tramo. Los eventos conservan los segundos del original. En CPU el análisis interactivo puede avanzar más lento que el tiempo real; no se prometió 50 FPS. En modo de movimiento, `warmup_frames` cuenta fotogramas procesados y debe tenerse en cuenta si se usa muestreo.

## Límites y pendientes

Se ha implementado una separación por detección individual y anatomía, no identificación permanente de cada bovino. Permanecen riesgos de cajas fusionadas, puntos sobre otro animal, pérdidas prolongadas y cambio de IDs, especialmente con cercas y hacinamiento. Dos animales completamente superpuestos pueden seguir siendo indistinguibles. La supresión de cabezas compartidas es una heurística: requiere más pruebas cuando dos cabezas reales están muy cerca.

No se entrenó un modelo específico con etiquetas del rancho, no se midió precisión sobre videos nuevos reservados y no se validó adulto/becerro en este modo. La línea cuello/cola no se usa como una altura física; los eventos permanecen pendientes sin calibración. Los requisitos originales de MediaPipe Hands siguen disponibles para revisar categorías, pero MediaPipe no detecta la anatomía de las vacas.
