# Actividad 05: Forwarding Básico (Mini-Internet)
- **Integrantes:** Bastián Arias y Tomás León
- **Repositorio:** https://github.com/Bastian-AAI/CC4303-Redes
- **Archivos principales:** `router.py`, `sender.py`, `prueba_router.py`
- **Informe:** `README.md`

---

## 1. Implementación y Preguntas Teóricas

En esta actividad simulamos la capa de red usando sockets UDP no orientados a conexión, donde cada router corre como un proceso independiente escuchando en un par `(IP, puerto)` específico sobre `localhost`.

### 1.1. Similitudes y diferencias con una tabla de rutas real
* **Similitudes:** Ambas definen redes de destino en notación CIDR (ej. `127.0.0.1/24`), especifican un *Gateway* (siguiente salto), evalúan reglas en orden de prioridad y soportan rutas por defecto (`0.0.0.0/0`).
* **Diferencias:** En nuestra simulación todas las subredes comparten la misma IP `127.0.0.1` y se distinguen mediante **rangos de puertos** (`[puerto_ini, puerto_fin]`). En una tabla real (como `ip route` en Linux), cada subred tiene su propia IP única, los puertos no intervienen en el ruteo (son de capa de transporte) y se especifica la interfaz física de salida (`eth0`, `wlan0`) junto con métricas de costo.

### 1.2. Diseño de Headers y Scripts de Envío
* **Header IP (7 bytes):** Empaquetado en Big-Endian (`!4sHB` con `struct`): 4 bytes para la IPv4 destino (`socket.inet_aton`), 2 bytes para el puerto destino (`H`) y 1 byte para el `TTL` (`B`), seguidos del mensaje en UTF-8.
* **Script `sender.py`:** Permite enviar un mensaje puntual recibiendo 6 argumentos por consola:
  `python3 sender.py <IP_final> <puerto_final> <TTL> "<mensaje>" <IP_envio> <puerto_envio>`
* **Script `prueba_router.py`:** Lee un archivo desde `stdin` línea por línea, encapsula cada línea con los headers pasados en el primer argumento (`IP;puerto;TTL`) y los envía por UDP al router inicial.

### 1.3. Diseño de Round-Robin por Área de Red
Para alternar rutas cuando hay múltiples caminos hacia un mismo destino, usamos un diccionario global (`ciclos_por_area`) cuya llave es la tupla `(CIDR, puerto_inicial, puerto_final)`. Cada llave guarda un iterador circular (`itertools.cycle`) independiente con los *next-hops* de esa área. De este modo, el ciclado en una zona de la red no altera los turnos de otra zona.

### 1.4. Posición de la Ruta Default
La ruta default (`0.0.0.0/0 0 65535 127.0.0.1 7000`) **debe ir siempre en la última línea** de la tabla de rutas. Como `check_routes` revisa el archivo de arriba hacia abajo y toma la primera coincidencia, ponerla antes absorbería todo el tráfico interno de la red antes de revisar las rutas locales.

```text
# Ejemplo rutas_R1_default.txt
127.0.0.1/24 8882 8883 127.0.0.1 8882
0.0.0.0/0 0 65535 127.0.0.1 7000
```

---

## 2. Instrucciones de Ejecución

1. **Levantar un router:**
   ```bash
   python3 router.py 127.0.0.1 8881 archivos_texto/rutas_R1_v1.txt
   ```
2. **Enviar un mensaje puntual (`sender.py`):**
   ```bash
   python3 sender.py 127.0.0.1 8882 10 "hola R2!" 127.0.0.1 8881
   ```
3. **Enviar un archivo línea por línea (`prueba_router.py`):**
   ```bash
   python3 prueba_router.py "127.0.0.1;8885;15" 127.0.0.1 8881 < archivo.txt
   ```

---

## 3. Pruebas y Observaciones: Mini-Internet sin TTL

1. **Tabla de rutas mal configurada (Bucle infinito):** Al modificar `R2` para enviar el tráfico de `8883` de vuelta hacia `R1` (`8881`), mientras `R1` lo envía hacia `R2` (`8882`), se genera un *routing loop* infinito. Sin TTL, el paquete rebota eternamente entre ambos routers sin llegar jamás a `R3`.
2. **Red de 5 routers y Round-Robin:** Al enviar paquetes desde `R1` (`8881`) hacia `R5` (`8885`), los paquetes alternan caminos y **no siempre dan la misma cantidad de saltos**. El camino mínimo es de **3 saltos** (`8881 -> 8882 -> 8884 -> 8885`, visto en los envíos pares), mientras que en los envíos impares los desvíos por Round-Robin en `R3` y `R4` hicieron que los paquetes dieran **7 saltos** (`8881 -> 8882 -> 8883 -> 8882 -> 8884 -> 8882 -> 8883 -> 8885`).
3. **Red ampliada de 7 routers (R0 y R6 añadidos):** Al intercalar envíos entre `R1 -> R5` y `R5 -> R1`, comprobamos que `R2` cicla de forma independiente en cada área: alternó `8883` y `8884` para los paquetes hacia `R5`, y alternó `8880` y `8881` para los paquetes de vuelta hacia `R1`.

#### Tablas creadas para la topología de 7 routers:
```text
# rutas_R0_v4.txt
127.0.0.1/24 8881 8886 127.0.0.1 8881
127.0.0.1/24 8881 8886 127.0.0.1 8882

# rutas_R1_v4.txt
127.0.0.1/24 8880 8880 127.0.0.1 8880
127.0.0.1/24 8882 8886 127.0.0.1 8882

# rutas_R2_v4.txt
127.0.0.1/24 8880 8881 127.0.0.1 8880
127.0.0.1/24 8880 8881 127.0.0.1 8881
127.0.0.1/24 8883 8886 127.0.0.1 8883
127.0.0.1/24 8883 8886 127.0.0.1 8884

# rutas_R3_v4.txt
127.0.0.1/24 8880 8882 127.0.0.1 8882
127.0.0.1/24 8880 8882 127.0.0.1 8885
127.0.0.1/24 8884 8886 127.0.0.1 8882
127.0.0.1/24 8884 8886 127.0.0.1 8885

# rutas_R4_v4.txt
127.0.0.1/24 8880 8883 127.0.0.1 8882
127.0.0.1/24 8880 8883 127.0.0.1 8885
127.0.0.1/24 8885 8886 127.0.0.1 8882
127.0.0.1/24 8885 8886 127.0.0.1 8885

# rutas_R5_v4.txt
127.0.0.1/24 8880 8884 127.0.0.1 8884
127.0.0.1/24 8880 8884 127.0.0.1 8883
127.0.0.1/24 8886 8886 127.0.0.1 8884

# rutas_R6_v4.txt
127.0.0.1/24 8880 8885 127.0.0.1 8882
127.0.0.1/24 8880 8885 127.0.0.1 8883
```

---

## 4. Pruebas y Observaciones: Mini-Internet con TTL

1. **Bucle infinito con `TTL = 10`:** Al repetir el bucle entre `R1` y `R2` con `TTL = 10`, el paquete dejó de circular infinitamente. En cada salto el TTL disminuyó en 1 hasta llegar a `0`, momento en que el router lo descartó imprimiendo `Se recibió paquete ... con TTL 0`, evitando la congestión eterna.
2. **Orden de llegada en archivos grandes:** Al transmitir un archivo de varias líneas por la red de 5 routers usando `prueba_router.py`, **los paquetes llegan desordenados** a `R5`. Esto sucede porque cada línea viaja en un datagrama UDP independiente y el algoritmo Round-Robin los reparte por caminos de distinta cantidad de saltos (3 vs. 7 saltos), haciendo que paquetes enviados después adelanten a los anteriores.

---

## 5. Declaración de uso de Inteligencia Artificial
- **Modelo utilizado:** Gemini de Google.
- **Forma de uso:**
  - Apoyo en el diseño del empaquetado binario de headers con `struct` y manejo de iteradores circulares (`itertools.cycle`) por área de red.
  - Estructuración y redacción del informe.