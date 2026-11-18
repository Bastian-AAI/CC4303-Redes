# Actividad 06: Fragmentación IP
- **Integrantes:** Bastián Arias y Tomás León
- **Repositorio:** https://github.com/Bastian-AAI/CC4303-Redes/tree/C3/Actividad-06
- **Archivos principales:** `router.py`, `sender.py`
- **Informe:** `README.md`

## 1. Implementación
Tomando como base el código de la actividad anterior (*Forwarding Básico con TTL*), extendimos nuestros routers para soportar fragmentación y reensamblaje de datagramas IP según el MTU de cada enlace:

### 1.1. Estructura del Header IP (16 Bytes)
Empaquetamos los campos en Big-Endian (`!4sHBHHIB` mediante `struct`):
- **IP Destino (4 bytes):** Dirección IPv4 codificada con `socket.inet_aton`.
- **Puerto Destino (2 bytes):** Entero sin signo (`H`).
- **TTL (1 byte):** Tiempo de vida (`B`), decrementado en 1 por cada salto.
- **ID (2 bytes):** Identificador único del datagrama original (`H`), permite agrupar sus fragmentos en destino.
- **Offset (2 bytes):** Desplazamiento en bytes del trozo de datos respecto al mensaje original (`H`).
- **Tamaño (4 bytes):** Largo en bytes del campo `[mensaje]` sin incluir el header (`I`).
- **FLAG (1 byte):** *More Fragments* (`B`); toma valor `1` si quedan fragmentos posteriores y `0` si es el último (o único).

### 1.2. Fragmentación, Re-fragmentación y Reensamblaje
- **`check_routes`:** Lee la sexta columna de las tablas de rutas y retorna `(next_hop, MTU)` manteniendo el balanceo *Round-Robin* por área.
- **`fragment_IP_packet(IP_packet, MTU)`:** Si el tamaño total del paquete (header + datos) es menor o igual al `MTU`, retorna `[IP_packet]`. Si lo supera, divide los datos en bloques de tamaño máximo `MTU - 16`, actualiza `offset` sumando el desplazamiento acumulado al `offset` previo, y asigna `FLAG = 1` a todos los trozos intermedios, mientras que el último fragmento hereda el `FLAG` que traía el paquete entrante. Esto permite que un fragmento vuelva a fragmentarse sin perder consistencia.
- **`reassemble_IP_packet(fragment_list)`:** Ordena los fragmentos recibidos según su `offset`, verifica que inicien en `offset == 0`, que no existan saltos entre `offset` y `tamano` de fragmentos consecutivos, y que el último tenga `FLAG == 0`. Si falta algún trozo, retorna `None` y el router sigue esperando; cuando está completo, reconstruye el mensaje y lo imprime.

## 2. Instrucciones de Ejecución
1. **Levantar los 5 routers con tablas MTU:**
   ```bash
   for i in 1 2 3 4 5; do
     python3 router.py 127.0.0.1 888$i archivos_texto/rutas_R${i}_v3_mtu.txt &
   done
   ```
2. **Enviar un paquete puntual (`sender.py`):**
   ```bash
   python3 sender.py <IP_final> <puerto_final> <TTL> "<mensaje>" <IP_envio> <puerto_envio> [ID]
   ```

## 3. Pruebas y Observaciones

### 3.1. Envío sin fragmentación (`ID = 347`, `TTL = 10`, mensaje `"hola!"`)
Al enviar el paquete de 21 bytes totales (`16B header + 5B datos`) desde `R1` hacia `R5`:
- Ningún enlace posee un MTU menor a 21 bytes, por lo que el paquete viaja sin fragmentarse (`Offset = 0`, `FLAG = 0`).
- El `TTL` disminuye correctamente de `10` hasta `3` tras 7 saltos producto del *Round-Robin* en `R2`, `R3` y `R4`, llegando íntegro a `R5` donde se imprime `hola!`.

### 3.2. Envío de paquete de 150 bytes totales (`16B header + 134B datos`) desde `R1` a `R5`
Al inyectar un datagrama de 150 bytes totales desde `R1` (`8881`) hacia `R5` (`8885`):
- **Primera fragmentación en `R1` (`MTU = 100`):** `R1` divide los 134 bytes de datos en un primer fragmento de **100 bytes** totales (`84B datos`, `Offset = 0`, `FLAG = 1`) y un segundo fragmento de **66 bytes** totales (`50B datos`, `Offset = 84`, `FLAG = 0`).
- **Re-fragmentación en `R2` (`MTU = 80` hacia `R4` y `MTU = 50` hacia `R3`):** Al llegar los dos fragmentos a `R2`, el algoritmo *Round-Robin* envía el primero hacia `R4` (`MTU = 80`) y el segundo hacia `R3` (`MTU = 50`):
  - El fragmento de `84B` de datos (`Offset = 0`, `FLAG = 1`) se re-fragmenta en dos sub-fragmentos: uno de `64B` de datos (`Offset = 0`, `FLAG = 1`) y otro de `20B` de datos (`Offset = 64`, `FLAG = 1`).
  - El fragmento de `50B` de datos (`Offset = 84`, `FLAG = 0`) se re-fragmenta en dos sub-fragmentos: uno de `34B` de datos (`Offset = 84`, `FLAG = 1`) y el último de `16B` de datos (`Offset = 118`, `FLAG = 0`).
- **Reensamblaje en `R5`:** Aunque los 4 sub-fragmentos viajan por caminos distintos y llegan en desorden a `R5`, el router los agrupa por su campo `ID`, los ordena por `offset` (`0, 64, 84, 118`) y logra reconstruir e imprimir exactamente los 134 caracteres originales sin pérdida de información.

### 3.3. Envío desde otros routers (`R4` hacia `R1`, 150 bytes)
Al enviar el datagrama de 150 bytes desde `R4` (`8884`) con destino `R1` (`8881`):
- El enlace `R4 -> R2` tiene `MTU = 80`, por lo que `R4` fragmenta los 134 bytes de datos en **3 fragmentos** de `64B` (`Offset = 0`, `FLAG = 1`), `64B` (`Offset = 64`, `FLAG = 1`) y `6B` (`Offset = 128`, `FLAG = 0`).
- Al llegar a `R2`, el enlace hacia `R1` tiene `MTU = 100`. Como los tres fragmentos miden `80B`, `80B` y `22B` (todos menores o iguales a `100`), `R2` **no necesita volver a fragmentarlos** y los reenvía directamente a `R1`, donde se reensamblan con éxito.

## 4. Declaración de uso de Inteligencia Artificial
- **Modelo utilizado:** Gemini de Google.
- **Forma de uso:**
  - Automatización de scripts de prueba en terminal y estructuración del informe.