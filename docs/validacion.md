# Validación con video del corral

## Preparación

1. Grabar pasadas con cámara fija e identificar cada video y su sentido de avance. Incluir pausas, retrocesos, animales muy juntos y casos de tamaño similar entre categorías.
2. Pedir al ganadero que anote el instante de cada cruce completo y la categoría de cada bovino. Conservar esa lista como referencia manual.
3. Reservar videos distintos para calibrar la altura y para evaluar el resultado. Registrar la posición de las líneas y los umbrales utilizados.

## Comparación

Emparejar los eventos del sistema y los manuales por instante y orden de paso. Un total coincidente puede ocultar una omisión compensada por un duplicado.

| Aspecto | Qué registrar |
| --- | --- |
| Conteo | Pasos manuales, pasos detectados, omisiones, duplicados y detecciones sin cruce real. |
| Clasificación automática | Por cada categoría manual, cuántos cruces emparejados se asignaron a adulto, becerro o pendiente antes de la revisión. |
| Revisión por gestos | Evento seleccionado, categoría antes y después del gesto y total antes y después. Comprobar qué ocurre al mantener el gesto varios fotogramas. |

Para cada diferencia, anotar el video, el instante y la observación que permita reproducirla. Los objetivos de precisión se acordarán con el ganadero. Aún no se han registrado pruebas de campo.

## Comprobaciones disponibles

El [informe de implementación](implementacion.md) registra las pruebas automatizadas y la demostración sintética del 27 de noviembre de 2026. Comprueban reglas y funcionamiento de la tubería; no sustituyen la comparación con bovinos reales. Cada sesión guarda la configuración, el instante del cruce, la categoría automática y el historial de correcciones para permitir esa comparación.

La [prueba posterior con video público](pruebas-internet-2026-11-27.md) incluye dos cruces reales emparejados con una referencia manual en un tramo controlado y dos ejecuciones fallidas sobre la toma completa. Se documentan los ajustes y la selección del tramo; no se considera una evaluación independiente ni de campo.

La [prueba del modo de anatomía animal](pose-animal.md) compara dos eventos visuales del video Farmquip con los cruces del sistema y vuelve a probar Toros7 completo. Añade casos de dos entidades simultáneas y solapadas a las pruebas automatizadas. La evaluación de hacinamiento y oclusión completa sigue pendiente; no se debe extrapolar el resultado a todos los planos del video.
