# Uso del prototipo

Ejecutar los comandos en PowerShell desde la raíz del clon. Preparar el entorno con `uv sync --locked` o con el procedimiento pip del README. No se modificaron las versiones fijadas de las dependencias.

## Preparar una toma

Usar cámara fija, vista lateral, manga de un animal de ancho, iluminación estable y espacio visible antes de A y después de B. Colocar tomas locales en `assets/`; esa carpeta, los resultados y los modelos no se versionan. Evitar personas dentro de la ROI.

El primer segundo aproximadamente (`warmup_frames=30`) debe mostrar la manga vacía para aprender el fondo. Un animal presente durante esa preparación puede quedar absorbido por el fondo. El video debe mantener el mismo tamaño y encuadre durante toda la sesión.

## Calibrar líneas y altura

El archivo `config/example.json` permite ejecutar una primera prueba sin medidas físicas. Para ajustar solo la ROI y las líneas:

```powershell
.\.venv\Scripts\python.exe -m conteo_bovino --source assets\corral.mp4 --calibrate --save-config config\local.json
```

Seleccionar el rectángulo de la manga y presionar Enter. Después hacer clic en A (entrada) y B (salida). Se deduce el sentido de avance. Las líneas deben estar dentro del rectángulo. Escape cancela sin guardar.

Para habilitar clasificación automática se requiere una referencia visible de altura conocida, colocada en el mismo plano de paso. Elegir el umbral adulto/becerro con ejemplos del ganadero. Los siguientes números son **ilustrativos**, no un umbral validado:

```powershell
.\.venv\Scripts\python.exe -m conteo_bovino --source assets\corral.mp4 --calibrate --reference-height-cm 100 --adult-threshold-cm 110 --uncertainty-cm 10 --save-config config\local.json
```

Después de seleccionar ROI, A y B, hacer clic en el suelo de la referencia y en su cima. Ambos puntos deben quedar dentro de la ROI. Usar la altura real de esa referencia en el comando. La escala asume el mismo plano y un suelo aproximadamente horizontal; cambiar cámara, perspectiva o suelo requiere recalibrar. Una calibración nueva de geometría invalida la anterior de altura. También se puede editar JSON: las coordenadas están normalizadas respecto al fotograma completo.

## Procesar y revisar

```powershell
.\.venv\Scripts\python.exe -m conteo_bovino --source assets\corral.mp4 --config config\local.json --output-video
```

| Control | Acción |
| --- | --- |
| Espacio | Pausar/reanudar un video grabado. La cámara en vivo sigue capturando. |
| `[` / `]` | Seleccionar el evento anterior/siguiente, sin cambiar el conteo. |
| A | Marcar el evento seleccionado como adulto. |
| B | Marcarlo como becerro. |
| P | Dejarlo pendiente. |
| Q / Escape / cerrar ventana | Guardar resultados y salir. |

El primer evento queda seleccionado automáticamente. Los eventos nuevos no mueven la selección. Una corrección conserva el total y la categoría automática original.

Sin ventanas, para procesar un archivo completo:

```powershell
.\.venv\Scripts\python.exe -m conteo_bovino --source assets\corral.mp4 --config config\local.json --no-display --output-video --output runs\evaluacion01
```

`--max-frames 300` limita una prueba corta. La carpeta de resultados debe estar vacía o no existir; se rechaza sobrescribir una sesión anterior. En un archivo se termina al llegar al final. En cámara, Q o Ctrl+C termina la sesión; una lectura fallida se registra como captura interrumpida.

Para seleccionar una parte de una grabación sin recortar el original, usar `--start-seconds 7.2` y, opcionalmente, `--end-seconds 13`. El intervalo debe comenzar con la ROI vacía durante la preparación del fondo. Los instantes del CSV conservan los segundos del archivo original. Estas opciones solo se admiten para archivos; el video anotado contiene únicamente el tramo procesado. Véase la [demostración con video público](pruebas-internet-2026-11-27.md).

## Cabeza y lomo por bovino

El modo `pose` registra solo el total de bovinos que completan el cruce. En la demostración, Espacio inicia o pausa, R repite y Q cierra. La configuración `config/farmquip-pose.json` amplía la región de paso en una segunda pasada para recuperar algunos animales parcialmente tapados.

El modo `--detector pose` usa modelos animales ONNX para detectar vacas individuales y dibujar un círculo en el hocico y una línea entre cuello y base de cola. Cada ID conserva sus colores y suma al completar A → B. Se puede iniciar con animales en pantalla. Preparar los pesos con `.\.venv\Scripts\python.exe -m scripts.download_pose_models`. La [guía del modo animal](pose-animal.md) incluye la toma del usuario, los comandos y los límites observados.

Se conserva `--detector motion` como valor por defecto para reproducir las pruebas anteriores. MediaPipe Hands se usa para la mano del operador; la anatomía de las vacas se estima con RTMPose, y los puntos todavía pueden ser imprecisos con oclusiones.

## Gestos con MediaPipe Hands

Descargar una vez el modelo oficial:

```powershell
.\.venv\Scripts\python.exe scripts\download_hand_model.py
```

El script descarga la revisión 1 del modelo float16 de Google, registra URL y SHA256 y conserva el archivo local. No se descarga nada durante el conteo. Usa [MediaPipe Hand Landmarker Tasks](https://developers.google.com/edge/api/mediapipe/python/mp/tasks/vision/HandLandmarker), con modo VIDEO y marcas de tiempo crecientes.

Usar una cámara independiente que vea al operador. Si la cámara del corral es 0, por ejemplo:

```powershell
.\.venv\Scripts\python.exe -m conteo_bovino --source 0 --config config\local.json --gesture-camera 1
```

Para revisar una grabación puede usarse `--source assets\corral.mp4 --gesture-camera 0`. Se abren la vista del conteo y la del operador. Los índices concretos dependen de las cámaras conectadas.

| Mano | Orden sobre el evento seleccionado |
| --- | --- |
| Solo índice extendido | Adulto |
| Índice y medio extendidos | Becerro |
| Cuatro dedos extendidos, palma abierta | Pendiente |

Mantener el gesto 0.7 segundos. Retirar o relajar la mano al menos 0.4 segundos antes de otra orden. El pulgar no participa. Mostrar dos manos invalida la orden. Las reglas de dedos son heurísticas sobre los 21 puntos de Hands; deben probarse con el operador y su iluminación. La revisión por gestos requiere ventanas para ver el evento objetivo; no se admite con `--no-display`.

## Resultados y correcciones posteriores

Cada ejecución crea `runs/<fecha-hora>/` salvo que se indique `--output`:

- `session.json`: configuración, fuente, FPS, estado final, eventos e historial de correcciones. Se reemplaza mediante un archivo temporal al contar, corregir y terminar.
- `events.csv`: una fila por cruce, con ID, ID del seguimiento, instante, categoría final, categoría automática, altura estimada, motivo y marca de revisión. Codificación UTF-8 con BOM para Excel.
- `annotated.mp4`: opcional, con cajas, líneas y totales en cada fotograma procesado. Refleja el estado durante el procesamiento; las correcciones posteriores se consultan en CSV/JSON.

Los instantes de evento son segundos desde el inicio de la grabación (o captura). Los instantes de revisión son segundos Unix del reloj del equipo. CSV y JSON se actualizan individualmente; si se interrumpe el equipo entre ambos, JSON es la fuente principal. No se implementó reanudación del seguimiento de una captura interrumpida.

Para corregir una sesión ya guardada, sin volver a contar:

```powershell
.\.venv\Scripts\python.exe -m conteo_bovino --review-session runs\evaluacion01\session.json --event 1 --category adulto
```

Este comando actualiza el JSON y el CSV en esa carpeta. Revisar una categoría no permite reparar una omisión o falso cruce: esas discrepancias deben registrarse en la validación manual.

## Demostración y pruebas

Para ver la prueba pública en una ventana que comienza en pausa y permanece abierta al terminar:

```powershell
.\.venv\Scripts\python.exe -m scripts.show_demo
```

Espacio inicia o pausa. R repite desde el inicio del tramo y reinicia el contador. Q sale. Se reutilizan `MotionDetector`, `Counter`, el dibujo y las revisiones del prototipo sobre el video original, sin reproducir un resultado pregrabado. Cada repetición guarda su sesión por separado en `runs/demostracion-en-vivo/`. Se requiere haber descargado el conjunto de prueba indicado en el [informe](pruebas-internet-2026-11-27.md).

```powershell
.\.venv\Scripts\python.exe scripts\create_demo.py
.\.venv\Scripts\python.exe -m conteo_bovino --source assets\demo_sintetico.avi --output-video
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

La demo usa rectángulos que pasan por una manga simulada. Hay dos cruces completos, una pausa de 2 segundos y un intento cancelado por retroceso; sin calibración deben resultar 2 pendientes. El generador rechaza sobrescribir el video si ya existe. Los tests crean sus propios videos temporales y comprueban también clasificación con una escala artificial. La precisión real sigue sin medirse.
