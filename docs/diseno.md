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
