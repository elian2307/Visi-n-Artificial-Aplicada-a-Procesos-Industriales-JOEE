# Prueba con video público de bovinos — 27 de noviembre de 2026

## Fuente y selección

Por petición del usuario se descargó material de internet para una demostración académica del proyecto. Se eligió [Counting cattle Dataset: Supporting livestock Multi Objetct Tracking, versión 1](https://data.mendeley.com/datasets/dk54zg67dd/1), DOI `10.17632/dk54zg67dd.1`, de Ernesto dos Santos, Bruna Guterrez y Ricardo Bedin, publicado el 28 de abril de 2025. Licencia indicada por los autores: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

La fuente contiene videos de bovinos Brangus de un rancho en Uruguay. Se prefirió a un video comercial porque tiene una descarga pública y documentación de investigación. El paquete se obtuvo mediante la API pública documentada de Mendeley, sin iniciar sesión. Contiene diez MP4 y un archivo de anotaciones MOT para `Toros.mp4`. Esas anotaciones **no corresponden a Toros7**, por lo que no se usaron como referencia del tramo elegido.

Descarga: [Dataset Files.zip](https://data.mendeley.com/public-files/datasets/dk54zg67dd/files/447679ea-783a-4702-bdd8-285dab542906/file_downloaded), 275,216,868 bytes. SHA256 verificado contra el manifiesto del proveedor: `1fcb101ac83eb917f492e00f10b8b67d912fbb1bc881e40b11713a078868e01b`.

Archivos locales, fuera de Git por tamaño:

- `assets/internet/mendeley-dk54zg67dd-v1/dataset.zip`: paquete original.
- `assets/internet/mendeley-dk54zg67dd-v1/manifest.json`: nombres, tamaños, hashes y enlaces originales.
- `assets/internet/mendeley-dk54zg67dd-v1/dataset/Videos/`: diez tomas originales.
- `runs/internet-inspeccion/`: metadatos, hojas de contacto y secuencias de inspección visual.

Se seleccionó `Toros7.mp4`: vista lateral en un corral, movimiento principalmente de izquierda a derecha, 848 × 480, 402 fotogramas, aproximadamente 30.0065 FPS y 13.397 s. La cámara presenta pequeños movimientos y los animales ya están pasando al inicio; la toma completa no cumple el requisito de preparar un fondo vacío. Su tramo final permite observar dos animales separados y una ROI vacía antes de su entrada. Es adecuado para una primera demostración controlada, no una toma ideal de cámara fija.

## Ejecuciones y resultado

| Prueba | Preparación | Resultado del contador | Interpretación |
| --- | --- | --- | --- |
| Archivo completo, configuración de ejemplo | `config/example.json`, 30 fotogramas iniciales | 1 cruce | Resultado insuficiente: hay múltiples pasadas visibles; fondo inicial ocupado, movimiento de cámara y fragmentación de siluetas. No se anotó cada instante del archivo completo, por lo que no se publica una precisión para esta ejecución. |
| Archivo completo, configuración ajustada | `config/internet-toros7.json`, 10 fotogramas iniciales | 0 cruces | Ajustar ROI, áreas y tiempos sin un fondo inicial válido no resuelve la toma completa. Se conserva esta ejecución fallida. |
| Tramo desde 7.2 s hasta fin | Misma configuración ajustada; fondo inicialmente vacío dentro de la ROI | **2 cruces, ambos pendientes** | Coinciden con los dos pasos revisados visualmente, sin falsos cruces ni duplicados en este tramo. |

Las dos ejecuciones completas fallidas se conservan en `runs/internet-toros7-base/` y `runs/internet-toros7-completo-ajustado/`. La prueba controlada está en `runs/internet-toros7-intervalo/`: JSON, CSV, video anotado, hoja de eventos y comparación con la referencia manual. No se borraron ni reemplazaron resultados para ocultar fallos.

## Referencia manual del tramo

Se revisó la secuencia original y el video anotado alrededor de cada cruce. La referencia [toros7-intervalo.csv](referencias/toros7-intervalo.csv) marca aproximadamente el centro del torso cruzando la línea B (`x=0.60` del ancho). Su resolución temporal manual es aproximada, de unas décimas de segundo; se usa una tolerancia de ±0.35 s para emparejar eventos uno a uno.

| Evento manual | Instante manual, s | Instante del sistema, s | Diferencia, s |
| --- | ---: | ---: | ---: |
| 1 | 9.1 | 9.064697 | -0.035303 |
| 2 | 13.0 | 12.997176 | -0.002824 |

Dentro de ese criterio: 2 emparejados, 0 omitidos y 0 adicionales. El total conservado es `2 = 0 adultos + 0 becerros + 2 pendientes`. No hay referencia física de altura ni etiquetas de edad fiables; no se inventó una escala ni se trató el nombre del archivo como una categoría. No se evaluó la precisión adulto/becerro ni gestos en esta prueba.

La ROI y los parámetros se ajustaron observando la misma toma. El tramo solo contiene dos pasos y fue elegido por permitir el arranque del fondo. **No es una evaluación independiente ni una estimación de precisión general**. Los movimientos de cámara todavía producen algunas cajas de fondo espurias, aunque no sumaron cruces adicionales en este tramo.

## Reproducir la demostración

Desde la raíz del clon, con el entorno existente y el paquete extraído en la ruta indicada:

```powershell
.\.venv\Scripts\python.exe -m conteo_bovino --source assets\internet\mendeley-dk54zg67dd-v1\dataset\Videos\Toros7.mp4 --config config\internet-toros7.json --start-seconds 7.2 --output-video
```

Para repetir sin ventanas y conservar una salida nueva:

```powershell
.\.venv\Scripts\python.exe -m conteo_bovino --source assets\internet\mendeley-dk54zg67dd-v1\dataset\Videos\Toros7.mp4 --config config\internet-toros7.json --start-seconds 7.2 --no-display --output-video --output runs\toros7-repeticion01
```

La carpeta de salida debe estar vacía o no existir. Los archivos originales no se recortaron ni recodificaron: se selecciona el inicio durante la lectura. Los eventos conservan los segundos del video original, aunque el MP4 anotado de salida empieza en el tramo elegido.

## Cambios para permitir la prueba

Se añadieron `--start-seconds` y `--end-seconds` a la CLI para seleccionar intervalos de archivos sin crear copias recortadas. Se valida que sean finitos, ordenados y no negativos, se rechazan para cámaras, se registra el fotograma inicial y se conservan los tiempos de la fuente. La selección se redondea hacia el siguiente fotograma: 7.2 s corresponde al fotograma 217, aproximadamente 7.232 s en este archivo. El tramo procesado tiene 185 fotogramas.

Se guardó `config/internet-toros7.json`: ROI `(0.25, 0.22, 0.64, 0.50)`, A `0.40`, B `0.60`, sentido derecha, 10 fotogramas de preparación, área mínima 0.025 de la ROI, área máxima 0.80, distancia máxima 0.10 del fotograma y expiración 0.4 s. La calibración física permanece vacía. Estos ajustes son propios de esta toma; no sustituyen la configuración genérica.

Se añadió una prueba integrada de selección de intervalo sobre el video sintético: procesa 180 fotogramas entre 14 y 20 s, obtiene un cruce y conserva su instante original de 18.3 s. También comprueba entradas de intervalo inválidas. Resultado final: **17 pruebas automatizadas aprobadas**. Las 16 pruebas anteriores siguen pasando.

## Demostración visible en el equipo del usuario

A petición del usuario se añadió `scripts/show_demo.py` y se ejecutó en su escritorio con el Python del entorno, sin abrir una consola adicional. El lanzador procesa el video original con las mismas clases `MotionDetector` y `Counter`; inicia en pausa, Espacio reproduce/pausa, R reinicia y Q cierra. Conserva la ventana al terminar para revisar el resultado. A/B/P y los selectores de evento siguen disponibles y cada repetición guarda sus archivos separados en `runs/demostracion-en-vivo/`.

Se comprobó la ventana nativa «Conteo bovino - Demostracion en vivo» con Computer Use, se inició mediante Espacio y se verificó que aparecían cajas e IDs durante el procesamiento. La sesión visible volvió a registrar 2 cruces pendientes. La ayuda del lanzador y `git diff --check` finalizaron correctamente. No se cambiaron las reglas del detector ni del contador para esta presentación.

Se dejó la ventana abierta para que el usuario pueda repetirla con R. El arranque de `pythonw` emitió `warning: Making stdin inheritable failed` en el log del lanzador; no impidió abrir la ventana ni procesar el video.

## Decisión para continuar

Esta toma permite presentar una demostración real corta y repetirla localmente. El archivo completo demuestra que todavía hace falta mejorar la inicialización y la resistencia al movimiento de cámara y a las siluetas juntas. Antes de afirmar que el sistema funciona en cualquier video, se deben evaluar tomas separadas con cámara fija y arranque vacío, o implementar y comprobar compensación de movimiento/inicialización más robusta. La condición no comercial no cambia lo que estas pruebas pueden demostrar técnicamente.
