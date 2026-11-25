# Guía para agentes de IA

Antes de modificar el prototipo, consulta el [objetivo y estado del proyecto](../README.md). Usa el [diseño](diseno.md) para interpretar los eventos de paso y el [protocolo de validación](validacion.md) para comparar resultados con el registro del ganadero.

## Cómo mantener la documentación

Todo agente debe dejar en `docs/` un registro de los cambios, implementaciones y hechos importantes antes de cerrar la tarea, según las [instrucciones del repositorio](../AGENTS.md).

- Si cambia una regla de conteo o clasificación, actualiza el diseño e indica qué observación o decisión motivó el cambio.
- Al realizar una prueba, registra en Markdown el identificador del video, la configuración, el conteo manual, el resultado del sistema y los casos en que difieren. Enlaza el informe desde el protocolo de validación.
- Distingue las propuestas, las funciones implementadas y los resultados medidos. Actualiza el estado del README al verificar un avance.
- Para trabajar en un clon, sigue la instalación con pip o con uv del [README](../README.md). Las dependencias directas se declaran en `pyproject.toml`. Cuando cambien, actualiza `uv.lock` con `uv lock` y regenera `requirements.txt` con el comando de su cabecera. Versiona los tres archivos juntos para que ambos métodos instalen las mismas versiones.

## Verificación del entorno

Se probó una instalación limpia en Windows con una copia de ambos archivos y Python 3.15.2. La sincronización instaló 19 paquetes y se verificaron las importaciones de OpenCV 5.1.0, MediaPipe 1.2.3 y NumPy 2.5.5.

También se creó un entorno limpio con el módulo estándar `venv` y se instalaron las dependencias con `python -m pip install -r requirements.txt`. La comprobación con `pip check` pasó y los tres módulos se importaron con las mismas versiones.
