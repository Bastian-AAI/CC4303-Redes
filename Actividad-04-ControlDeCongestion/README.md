# Control 02
## Actividad-04-ControlDeCongestión: Control de congestión

- Integrantes: Bastián Arias y Tomás León
- Repositorio: https://github.com/Bastian-AAI/CC4303-Redes/tree/C2/Actividad-04
- Archivo principal: Actividad-04-CongestionControl/SocketTCP.py
- Informe: Actividad-04-CongestionControl/README.md

## 1. Implementación

En esta actividad extendimos la clase `SocketTCP` para implementar la transferencia de datos utilizando el protocolo Go-Back N, reemplazando el antiguo modelo Stop & Wait por una ventana deslizante. Además, se integró un mecanismo de Control de Congestión basado en TCP Tahoe.

### 1.1. Preguntas Teóricas
**1. ¿Por qué le puede servir usar como base para Go Back-N el código de Stop & Wait de la sección anterior? ¿Qué similitud tiene Go Back-N con Stop & Wait?**
Stop & Wait es equivalente a un Go-Back N con una ventana de tamaño estricto de 1. Usar el código anterior sirve porque toda la fase de establecimiento de conexión (Handshake) y cierre de conexión es exactamente la misma. La única diferencia lógica radica en cómo se maneja la ráfaga de datos enviados en la función `send`.

**2. En la sección anterior solo se muestra la función send de Stop & Wait, ¿Qué ocurre con la función recv? ¿Esta función cambia con el uso de SocketUDP y SlidingWindowsCC?**
La función `recv` no cambia. En Go-Back N, el receptor se mantiene muy simple: solo acepta los paquetes que lleguen en el orden estricto esperado. Si llega un paquete desordenado, lo ignora y vuelve a enviar un ACK por el último paquete que recibió correctamente en orden. Esta es la misma lógica que ya utilizaba nuestro `recv` de Stop & Wait.

### 1.2. Control de Congestión (TCP Tahoe)
Creamos la clase independiente `CongestionControl` para manejar el tamaño de la ventana (`cwnd`) y el umbral (`ssthresh`):
- Comienza en el estado **Slow Start** con una ventana de 1 MSS (8 bytes). Por cada ACK recibido, la ventana crece en +1 MSS.
- Si la ventana supera el umbral, pasa a **Congestion Avoidance**, donde el crecimiento es más lento y fraccional.
- Si ocurre una pérdida (Timeout), el umbral se reduce a la mitad de la ventana actual, la ventana se reinicia a 1 MSS y vuelve al estado **Slow Start**.

### 1.3. Transición a Go-Back N con Ventana Deslizante
Modificamos `send` para soportar envío en ráfagas:
- El mensaje se fragmenta estrictamente en bloques de 8 bytes.
- El emisor inyecta a la red todos los paquetes que le permite el tamaño de su ventana actual sin esperar confirmación.
- Se utiliza un solo cronómetro (*timer*) asociado a la base de la ventana (el paquete más antiguo).
- Si llega un ACK válido, la ventana avanza. Si el cronómetro se agota, se retransmite toda la ventana actual desde la base.

---

## 2. Instrucciones de Ejecución

**2.1. Test de la Ventana (CongestionControl_test.py)**
Prueba automáticamente la lógica matemática de la clase `CongestionControl`.
- Ejecutar: `python3 CongestionControl_test.py`

**2.2. Transmisión y Pruebas de Red**
Para probar la transmisión de datos, levanta el servidor y luego envía datos desde el cliente:
- Servidor: `python3 servidor.py`
- Cliente: `time echo "Mensaje de prueba" | python3 cliente.py` (el Mensaje de prueba fueron multiples AAAAAAA hasta cubrir los necesarios)

---

## 3. Manejo de Pérdidas y Casos Borde

Al integrar la ventana deslizante con la clase base `SocketUDP`, resolvimos casos borde relacionados con el manejo de cronómetros e hilos de ejecución para evitar que el programa se quedara bloqueado:

### 3.1. Hilos Muertos tras un Timeout
Cuando el cronómetro se agota, el hilo de Python se destruye. Si intentábamos retransmitir usando el mismo índice de timer, el programa lanzaba un error por intentar iniciar un hilo inexistente. Lo solucionamos implementando un bloque `try-except` en la función `_safe_stop_timer` para limpiar los cronómetros agotados de forma segura.

### 3.2. Error de Hilos en Envíos de Ráfaga
Al enviar varios paquetes casi al mismo tiempo (Go-Back N), `SocketUDP` intentaba darle inicio (`start`) dos veces seguidas a un mismo cronómetro que apenas estaba arrancando. Esto provocaba una caída con `RuntimeError`. Se solucionó capturando e ignorando específicamente esta excepción dentro de `_sendto()`.

### 3.3. Bloqueos durante el Cierre de Conexión
Al forzar pérdidas de red (20%), la función `close` se quedaba trabada infinitamente. Esto ocurría porque al recibir ACKs viejos o basura atrasada de la red, el código apagaba el cronómetro principal de desconexión. La solución implementada fue mover la detención del cronómetro: ahora el timer **solo** se detiene si se recibe el paquete correcto de cierre (`FIN` o `FIN+ACK`), e ignora la basura atrasada dejándolo correr.

---

## 4. Experimento Comparativo y Resultados

Para medir el rendimiento de la red con y sin Control de Congestión, configuramos un escenario adverso utilizando el comando `netem` de Linux para inducir pérdida artificial.
- **Tasa de pérdida:** 20%
- **Timeout:** 0.5s
- **Archivo/Mensaje transmitido:** 100 Bytes

### Resultados (5 Iteraciones)

| Intento | Tiempo (Sin CC) | Segmentos Enviados (Sin CC) | Tiempo (Con CC) | Segmentos Enviados (Con CC) |
| :---: | :---: | :---: | :---: | :---: |
| **1** | 4,540 s | 52 segs | 2,032 s | 23 segs |
| **2** | 3,047 s | 35 segs | 3,536 s | 27 segs |
| **3** | 5,558 s | 59 segs | 4,041 s | 29 segs |
| **4** | 10,552 s | 126 segs | 2,046 s | 25 segs |
| **5** | 5,041 s | 68 segs | 3,037 s | 29 segs |
| **Promedio**| **5,748 s** | **68 segs** | **2,938 s** | **26,6 segs** |

### Análisis de Resultados: ¿Cuál toma menos tiempo y por qué?
Como se observa en la tabla, el envío **CON** Control de Congestión (TCP Tahoe) toma considerablemente menos tiempo e inyecta muchos menos segmentos a la red que el envío sin control.

Esto ocurre por cómo el protocolo reacciona al estado de la conexión. **Sin Control de Congestión**, Go-Back N intenta empujar su ventana completa de 8 segmentos constantemente. Con un 20% de pérdida, gran parte de esta ventana se descarta en la red, forzando múltiples retransmisiones de ventanas completas que ahogan la conexión.

En cambio, **CON Control de Congestión**, Al Detectar la Pérdida por *timeout*, asume que hay congestión y reduce su ventana a 1 MSS (`Slow Start`). Esta forma conservadora de envío evita retransmitir ráfagas inútiles de paquetes que igual se perderían, logrando enviar el mensaje en mucho menos tiempo y optimizando el ancho de banda.

---

## 5. Declaración de uso de Inteligencia Artificial

- Modelo utilizado: Gemini de Google.
- Forma de uso:
  - Ayuda para entender correctamnete errores generados en el proceso.
  - Ayudo en el aprendizaje gracias a la ayuda en los errores.
  - Apoyo en la refactorización lógica para resolver los bloqueos infinitos de cronómetro durante las desconexiones con pérdida de paquetes.
  - Corrección ortográfica y estructuración del texto del informe.