# Conteo de bovinos en la manga de manejo

El objetivo es desarrollar un prototipo de visión artificial que cuente los bovinos al pasar de uno en uno por la manga de manejo (*chutis*) y registre cuántos son adultos y cuántos son becerros. El sistema busca asistir al personal del corral en una tarea repetitiva de la industria ganadera regional...

## Alcance del prototipo

Una cámara fija observará de lado un tramo recto a la salida del embudo. Cada cruce completo en el sentido de avance sumará un paso al total. El prototipo estimará la categoría del bovino a partir de la altura aparente del lomo en un punto de referencia. Si la evidencia es insuficiente, registrará el paso como **pendiente de revisión**. Al resolver la categoría se conservará el total.

## Requisitos técnicos

| Herramienta | Requisito del proyecto | Aplicación prevista |
| --- | --- | --- |
| OpenCV | Al menos dos técnicas | Delimitar el pasillo con una región de interés (ROI) y detectar movimiento por sustracción de fondo. |
| MediaPipe | Al menos una función | Usar el seguimiento de manos (Hands) para que el operador confirme o corrija una categoría mediante un gesto. |

## Estado y entorno

El prototipo ya incluye captura de video o cámara, detección de movimiento con OpenCV, seguimiento, conteo A → B, clasificación por altura calibrada y revisión por teclado o MediaPipe Hands. Guarda eventos y correcciones en CSV y JSON, y opcionalmente video anotado. Las pruebas de reglas y video sintético se describen en el [informe de implementación](docs/implementacion.md). Sigue pendiente validar su precisión con bovinos reales y la cámara del corral.

También se ejecutó una [prueba con video público de bovinos](docs/pruebas-internet-2026-11-27.md): dos cruces correctos en un tramo preparado y fallos en la toma completa con fondo inicial ocupado. Hay 17 pruebas automatizadas aprobadas. Estos resultados no equivalen a una precisión general validada.

Actualización: ya está disponible el [modo de detección individual con cabeza y lomo](docs/pose-animal.md), mediante `--detector pose`. Usa YOLOX-s y RTMPose AP-10K con OpenCV, sin dependencias adicionales ni fondo vacío inicial. Se comprobaron 2 cruces en un tramo del video Farmquip propuesto por el usuario y 6 en Toros7 completo. La suite actual tiene **27 pruebas aprobadas**. Las oclusiones fuertes, los cambios de cámara y la precisión general siguen pendientes de validación.

El modo `pose` detecta bovinos individuales y registra un total de cruces, sin categorías de edad. Todavía puede omitir o confundir animales muy superpuestos. El modo `motion` identifica movimiento y deja los cruces pendientes si falta calibración de altura.

### Instalación para colaboradores

Con Python 3.15 de 64 bits instalado en Windows, abre PowerShell en la raíz del repositorio clonado. Crea el entorno una vez e instala las dependencias con pip:

```powershell
py -3.15 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Cuando cambie `requirements.txt`, vuelve a ejecutar el segundo comando. Puedes comprobar la instalación con `.\.venv\Scripts\python.exe -c "import cv2, mediapipe, numpy; print(cv2.__version__, mediapipe.__version__, numpy.__version__)"`.

Si tu instalación de Windows no tiene el lanzador `py`, usa `uv sync --locked` o ejecuta `python -m venv .venv` después de verificar con `python --version` que estás usando Python 3.15.

### Instalación opcional con uv

Si ya usas `uv`, puedes preparar el entorno desde la raíz del repositorio con:

```shell
uv sync --locked
```

El comando crea un entorno local en `.venv/` con Python 3.15 e instala las versiones registradas en `uv.lock`. Para comprobar la instalación desde esa misma terminal, ejecuta `uv run python -c "import cv2, mediapipe, numpy; print(cv2.__version__, mediapipe.__version__, numpy.__version__)"`.

## Documentación

- [Guía para agentes de IA](docs/README.md)
- [Diseño del conteo y la clasificación](docs/diseno.md)
- [Protocolo de validación en el corral](docs/validacion.md)
- [Uso, calibración y controles](docs/uso.md)
- [Implementación y resultados de pruebas](docs/implementacion.md)

## Ejecutar el prototipo

Desde la raíz del repositorio, después de instalar el entorno:

Para contar bovinos con detección individual, descarga los modelos una vez y coloca tu video en `assets\corral.mp4`:

```powershell
.\.venv\Scripts\python.exe -m scripts.download_pose_models
.\.venv\Scripts\python.exe -m conteo_bovino --detector pose --source assets\corral.mp4 --config config\example.json
```

El modo de pose suma un bovino cuando cruza A y B. Ajusta las líneas y la dirección al encuadre de tu video. La [guía de pose](docs/pose-animal.md) incluye el ejemplo de Farmquip y los comandos para exportar el video anotado. Los modelos, los videos y el entorno se guardan localmente.

Para usar el modo de movimiento:

```powershell
# Video grabado; sustituye la ruta por una toma del corral.
.\.venv\Scripts\python.exe -m conteo_bovino --source "assets\corral.mp4" --config config\example.json

# Cámara en vivo, manteniendo la manga vacía durante la preparación del fondo.
.\.venv\Scripts\python.exe -m conteo_bovino --source 0
```

Para probarlo sin cámara ni video del rancho:

```powershell
.\.venv\Scripts\python.exe scripts\create_demo.py
.\.venv\Scripts\python.exe -m conteo_bovino --source assets\demo_sintetico.avi --output-video
```

La demostración contiene dos cruces completos, una pausa y un intento con retroceso. En modo de movimiento sin calibración se esperan **2 pendientes**. Consulta [la guía de uso](docs/uso.md) para ajustar el encuadre, las líneas y el sentido de avance.
