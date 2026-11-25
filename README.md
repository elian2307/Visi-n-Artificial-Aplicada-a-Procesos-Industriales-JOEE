# Conteo de bovinos en la manga de manejo

El objetivo es desarrollar un prototipo de visión artificial que cuente los bovinos al pasar de uno en uno por la manga de manejo (*chutis*) y registre cuántos son adultos y cuántos son becerros. El sistema busca asistir al personal del corral en una tarea repetitiva de la industria ganadera regional.

## Alcance del prototipo

Una cámara fija observará de lado un tramo recto a la salida del embudo. Cada cruce completo en el sentido de avance sumará un paso al total. El prototipo estimará la categoría del bovino a partir de la altura aparente del lomo en un punto de referencia. Si la evidencia es insuficiente, registrará el paso como **pendiente de revisión**. Al resolver la categoría se conservará el total.

## Requisitos técnicos

| Herramienta | Requisito del proyecto | Aplicación prevista |
| --- | --- | --- |
| OpenCV | Al menos dos técnicas | Delimitar el pasillo con una región de interés (ROI) y detectar movimiento por sustracción de fondo. |
| MediaPipe | Al menos una función | Usar el seguimiento de manos (Hands) para que el operador confirme o corrija una categoría mediante un gesto. |

## Estado y entorno

El proyecto está en fase de diseño. El entorno local de Windows se creó con `uv` en la raíz del repositorio y ya se verificó la importación de OpenCV y MediaPipe. El conteo, la clasificación y la revisión por gestos están pendientes de implementación y validación con video del corral.

### Instalación para colaboradores

Con Python 3.15 de 64 bits instalado en Windows, abre PowerShell en la raíz del repositorio clonado. Crea el entorno una vez e instala las dependencias con pip:

```powershell
py -3.15 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Cuando cambie `requirements.txt`, vuelve a ejecutar el segundo comando. Puedes comprobar la instalación con `.\.venv\Scripts\python.exe -c "import cv2, mediapipe, numpy; print(cv2.__version__, mediapipe.__version__, numpy.__version__)"`.

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
