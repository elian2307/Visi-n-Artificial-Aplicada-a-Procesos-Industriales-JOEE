# Diseño del conteo y la clasificación

## Qué constituye un paso

Se propone colocar dos líneas virtuales dentro de la región de interés. La línea A estará del lado de entrada y la B del lado de salida. El seguimiento deberá mantener una referencia estable del mismo animal, por ejemplo el centro del torso, durante el cruce de ambas líneas.

| Situación observada | Comportamiento previsto |
| --- | --- |
| El animal cruza A y después B en el sentido de avance | Registrar un paso al cruzar B. |
| Cruza A, se detiene y finalmente cruza B | Conservar el seguimiento durante la pausa y registrar un solo paso. |
| Cruza A y regresa por A antes de llegar a B | Cancelar ese intento. |
| Permanece sobre B después del registro | Conservar el evento registrado y evitar duplicados. |

El total representa pasos de avance. Si la operación exige reconocer al mismo bovino cuando sale de la vista y vuelve a entrar, habrá que acordar con el ganadero cómo identificarlo.

## Cómo asignar una categoría

La primera hipótesis es que la altura del lomo permite separar adultos y becerros en el punto de medición. Se propone colocar una referencia de altura conocida en el mismo plano de paso y medir el lomo en varios fotogramas cercanos. El umbral y el intervalo de duda se determinarán con ejemplos etiquetados por el ganadero. Un cambio de cámara o de encuadre requerirá revisar la calibración.

Si el lomo queda oculto o la altura cae en el intervalo de duda, el evento quedará pendiente. La revisión con MediaPipe Hands deberá asociar el gesto del operador a un solo evento. Una corrección cambiará su categoría una vez y mantendrá la relación **total = adultos + becerros + pendientes**.

## Decisiones abiertas

Falta confirmar la posición de la cámara, la visibilidad de la mano desde el puesto del operador y los gestos de revisión. Si los videos muestran que la altura resulta insuficiente, se evaluará un clasificador entrenado con imágenes del rancho.

## Implementación del prototipo (27 de noviembre de 2026)

Se implementaron las reglas anteriores en `conteo_bovino/core.py`. El centro de la caja de movimiento es la referencia de seguimiento. Las líneas son verticales y admiten avance hacia la derecha o la izquierda. Un seguimiento que aparece después de A no se arma hasta observar un cruce de A desde el lado de entrada. Al perderlo durante más de `max_missing_seconds` se descarta su intento; no se inventa un paso al reaparecer después de B. Un seguimiento contado conserva esa marca hasta desaparecer: si vuelve por A sin perder su ID no se suma otra vez.

OpenCV recorta la ROI, aplica MOG2, elimina sombras mediante umbral y limpia la máscara con apertura/cierre morfológico. Se asocian cajas por distancia uno a uno. El fondo se congela mientras haya seguimientos para conservar animales detenidos; se requieren fotogramas iniciales de manga vacía. No es un detector entrenado de bovinos. Personas, sombras fuertes y fragmentación pueden producir falsos objetos; un seguimiento perdido o animales juntos pueden causar omisiones, duplicados o intercambio de IDs.

La altura se aproxima con la mediana del borde superior en el tercio central de cada silueta, cerca de B. Se descartan cajas que tocan el borde de la ROI. Se transforma la medida a centímetros usando suelo, cima y altura real de una referencia en el plano del animal. La mediana de varias medidas se compara contra el umbral; los límites del intervalo de duda son inclusivos. Sin calibración o con pocas muestras queda pendiente. Esta aproximación requiere validación: una máscara fragmentada o el cuello pueden sesgar la medida aunque no toquen el borde.

La selección del evento se mantiene fija hasta que el operador la cambia con `[` o `]`. Nuevos cruces no cambian el objetivo de una revisión. Un dedo índice significa adulto, índice y medio becerro, y palma con los cuatro dedos extendidos pendiente. Se ignora el pulgar. El gesto debe mantenerse 0.7 s y soltarse 0.4 s antes de otra orden; cambiar de evento manteniendo la mano no aplica la orden al siguiente. Dos manos o poses no reconocidas no emiten órdenes. Son gestos propuestos, configurados en código, aún por confirmar con el operador.

La revisión puede repetirse intencionalmente si es necesario corregir una decisión. Una orden idéntica consecutiva no duplica el historial. Cada cambio conserva la categoría automática, la categoría anterior, el método y el total; nunca añade ni elimina cruces. En vivo no se pausa la captura para evitar perder pasos. Para revisar con calma se usa video grabado o el archivo de sesión al terminar.

Detalles de uso y límites: [guía de uso](uso.md). Evidencia y pendientes: [informe de implementación](implementacion.md).

## Propuesta del usuario: cabeza y lomo por animal

Actualización: el usuario autorizó la implementación. Ya existe el modo `--detector pose` con YOLOX-s y RTMPose AP-10K, círculos en hocico, eje cuello/cola, seguimiento global y supresión de cabezas duplicadas. La referencia de cruce permanece en el centro de la caja individual para evitar saltos de puntos anatómicos. Véase [implementación, fuentes y pruebas de pose](pose-animal.md). El resto de esta sección conserva el contexto de la propuesta inicial.

El 27 de noviembre de 2026 el usuario propuso representar cada bovino con un círculo en la cabeza y una línea a lo largo del lomo, de forma semejante a los puntos de manos, para distinguir entidades antes de aplicar las zonas de cruce. Esta alternativa se encuentra en evaluación conceptual; todavía no se ha implementado ni probado en el prototipo.

La representación podría usar cabeza, cruz y base de la cola, agrupadas por individuo, junto a un ID persistente. La separación depende de detectar y asociar correctamente esos puntos a cada animal; dibujar círculos y líneas sobre los contornos actuales no separa por sí mismo dos siluetas fusionadas. Los cruces A → B podrían seguir aplicándose a un punto estable del cuerpo de cada ID, en vez de depender únicamente del centro de una caja de movimiento.

La [documentación oficial de MediaPipe Pose](https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker?hl=en) describe un modelo de puntos del cuerpo humano, por lo que no constituye un modelo de anatomía bovina. La [documentación oficial del Model Zoo de DeepLabCut](https://github.com/DeepLabCut/DeepLabCut/blob/main/docs/ModelZoo.md) ofrece modelos SuperAnimal para cuadrúpedos: unos combinan detector individual y estimador de puntos, otros predicen puntos y los agrupan en individuos. Es una posible base que necesita comprobarse con estas tomas, no una integración ya disponible en este repositorio.

La dificultad principal sería la detección por individuo y conservar IDs cuando se ocultan, no el dibujo. Antes de sustituir el detector habría que verificar compatibilidad del entorno, pesos y rendimiento sobre imágenes laterales con dos bovinos juntos; si el modelo no generaliza, harían falta ejemplos anotados y ajuste. Una oclusión completa sigue sin aportar evidencia visual suficiente para garantizar dos detecciones independientes. No se ha fijado un modelo, una fecha ni una precisión esperada.
