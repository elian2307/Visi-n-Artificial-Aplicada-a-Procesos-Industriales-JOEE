# Guía para agentes de IA

Antes de modificar el prototipo, consulta el [objetivo y estado del proyecto](../README.md). Usa el [diseño](diseno.md) para interpretar los eventos de paso y el [protocolo de validación](validacion.md) para comparar resultados con el registro del ganadero.

## Documentos del prototipo

- [Uso, calibración, gestos y archivos de resultados](uso.md).
- [Implementación, decisiones, diagnóstico y pruebas del 27 de noviembre de 2026](implementacion.md).
- [Prueba con video público: fuente, referencia manual, resultados y reproducción](pruebas-internet-2026-11-27.md).
- [Detección individual de cabeza/lomo y prueba con el video Farmquip del usuario](pose-animal.md).

## Cómo mantener la documentación

El 28 de noviembre de 2026 se ajustó `.gitignore` a una lista explícita. Los archivos compartidos incluyen el código Python del contador, los scripts para preparar y ejecutar la demostración, `requirements.txt`, los metadatos de dependencias, las configuraciones de ejemplo y la documentación con las referencias de validación. El entorno virtual, los pesos descargados, los videos, las salidas, los tests locales y las calibraciones personales quedan fuera. Cada colaborador instala las dependencias en su propio entorno. Los comandos de prueba de los informes corresponden a la copia de desarrollo que contiene `tests/`.

Todo agente debe dejar en `docs/` un registro de los cambios, implementaciones y hechos importantes antes de cerrar la tarea, según las [instrucciones del repositorio](../AGENTS.md).

- Si cambia una regla de conteo o clasificación, actualiza el diseño e indica qué observación o decisión motivó el cambio.
- Al realizar una prueba, registra en Markdown el identificador del video, la configuración, el conteo manual, el resultado del sistema y los casos en que difieren. Enlaza el informe desde el protocolo de validación.
- Distingue las propuestas, las funciones implementadas y los resultados medidos. Actualiza el estado del README al verificar un avance.
- Para trabajar en un clon, sigue la instalación con pip o con uv del [README](../README.md). Las dependencias directas se declaran en `pyproject.toml`. Cuando cambien, actualiza `uv.lock` con `uv lock` y regenera `requirements.txt` con el comando de su cabecera. Versiona los tres archivos juntos para que ambos métodos instalen las mismas versiones.

## Verificación del entorno

Antes de publicar el prototipo se probó una copia limpia de los archivos preparados para Git. Con Python 3.15.2 se instalaron las dependencias de `requirements.txt` y `pip check` confirmó su compatibilidad. La demo sintética registró dos cruces. El script de descarga verificó los pesos y el modo de pose registró dos cruces en 80 fotogramas analizados del tramo 81–89 s de Farmquip. El README explica cómo descargar los modelos y usar un video propio.

Se probó una instalación limpia en Windows con una copia de ambos archivos y Python 3.15.2. La sincronización instaló 19 paquetes y se verificaron las importaciones de OpenCV 5.1.0, MediaPipe 1.2.3 y NumPy 2.5.5.

También se creó un entorno limpio con el módulo estándar `venv` y se instalaron las dependencias con `python -m pip install -r requirements.txt`. La comprobación con `pip check` pasó y los tres módulos se importaron con las mismas versiones.
