# Control 01
## Actividad-02-DNS: construyamos un resolver
**Integrantes:** Bastián Arias y Tomás León
**Repositorio:** https://github.com/Bastian-AAI/CC4303-Redes/tree/C1/Actividad-02
**Archivo principal:** `Actividad-02-DNS/resolver.py`
**Informe:** `Actividad-02-DNS/README.md`

### 1. Descripción de la Solución e Implementación

En esta actividad se desarrolló un resolver DNS iterativo con caché en Python. Se utilizaron sockets y la librería dnslib para empaquetar y desglosar mensajes DNS.

#### Configuración del Socket

Se utilizó el socket no orientado a conexión (`SOCK_DGRAM`) del módulo socket para el envío de mensajes DNS. La justificación de usar este tipo de socket es que el protocolo DNS necesita enviar mensajes cortos y de baja latencia, por lo que no requiere el establecimiento de una conexión previa que lo haga más ineficiente.

#### Algoritmo de Resolución Iterativa

El resolver implementa la función `resolver` que recibe como parámetros el mensaje DNS en bytes y la dirección IP del servidor DNS. Siguiendo la lógica iterativa desde la IP raíz (`198.41.0.4`):

1. Envía la query en bytes al puerto `53` de la dirección `ip_addr`.
2. Si la respuesta del servidor DNS contiene un registro de tipo `A` en la sección `ANSWER`, finaliza la búsqueda y retorna el mensaje DNS en bytes.
3. Si la sección `AUTHORITY` contiene registros de tipo `NS`, verifica si la sección `ADDITIONAL` incluye la dirección IP (registro `A`) de dicho Name Server.
   - Si la IP está en `ADDITIONAL`, reenvía la consulta inicial a esa IP.
   - Si la IP NO está en `ADDITIONAL`, resuelve recursivamente el nombre de dominio del Name Server (consultando desde la raíz `ROOT_IP`), y posteriormente consulta por el dominio original a la IP obtenida del Name Server.
4. Si la respuesta no es reconocida o está vacía, retorna el mensaje recibido.

#### Sistema de Caché

El resolver cuenta con la función `resolver_with_cache` que permite utilizar un sistema de caché para almacenar y recuperar respuestas DNS. Mantiene las últimas 20 consultas recibidas en una estructura `history = deque(maxlen=20)` y calcula los 3 dominios más frecuentes mediante `Counter(history).most_common(3)`. Si la consulta actual pertenece a los 3 dominios más frecuentes y ya se encuentra almacenada en `dns_cache`, se retorna directamente la respuesta guardada sin realizar consultas de red.

### 2. Pruebas de Funcionalidad

Las pruebas ejecutadas contra el resolver fueron las siguientes:

1. **`eol.uchile.cl`**:
    - **Comando:** `dig -p8000 @127.0.0.1 eol.uchile.cl`
    - **Resultado:** Retorna respuestas de tipo `A` pertenecientes al rango `146.83.63.X`.
    - **Cantidad de respuestas:** Se obtuvieron 11 direcciones IP tipo `A` asociadas al balanceador de carga del sitio EOL.

2. **Prueba de Caché con `eol.uchile.cl`**:
    - Al realizar una segunda consulta a `eol.uchile.cl`, la respuesta fue entregada en **0 ms**, confirmando que el sistema de caché funciona según lo requerido.

3. **`www.uchile.cl`**:
    - **Comando:** `dig -p8000 @127.0.0.1 www.uchile.cl`
    - **Resultado:** Resuelve exitosamente a la dirección IP `200.89.76.36`.

4. **`cc4303.bachmann.cl`**:
    - **Comando:** `dig -p8000 @127.0.0.1 cc4303.bachmann.cl`
    - **Resultado:** Resuelve exitosamente a la dirección IP `104.248.65.245`.
   
### 3. Experimentos

#### Experimento 1: `www.webofscience.com`

- **¿Resuelve su programa este dominio?**  
    No, en el diseño base no logra resolverlo y entra en un bucle de consultas y timeout.
- **¿Qué sucede?**  
    El resolver realiza consultas continuas sin lograr obtener un registro tipo `A` en la sección `ANSWER`.
- **¿Por qué?**  
    Al consultar a los servidores de nombre autoritativos de Web of Science (`ns-342.awsdns-42.com`), estos responden con un alias `CNAME` en la sección `ANSWER` y servidores `NS` en la sección `AUTHORITY`, pero ningún registro de tipo `A`. El algoritmo básico verifica únicamente la presencia de registros tipo `A`, al no encontrarlos pero detectar la sección `AUTHORITY`, intenta delegar la consulta de nuevo al mismo Name Server, generando un ciclo de recursión.
- **¿Cómo arreglaría usted este problema?**  
    Se arregla modificando la función `resolver` para que identifique si la sección `ANSWER` contiene un registro de tipo `CNAME`. En caso de encontrarlo, debe extraer el nombre de dominio del alias y llamar de manera recursiva a la función `resolver` para obtener la dirección IP tipo `A` del alias, combinando posteriormente ambos registros en la respuesta entregada al cliente.

#### Experimento 2: `www.cc4303.bachmann.cl`

- **¿Qué ocurre?**  
    Al ejecutar `dig -p8000 @127.0.0.1 www.cc4303.bachmann.cl`, la consulta entra en un bucle donde nunca retorna direcciones IP en la sección `ANSWER` (retorna 0 respuestas).
- **¿Qué habría esperado que ocurriera?**  
    Se habría esperado que resolviera a una IP o retornara un error explícito.
- **Contraste con `dig @1.1.1.1 www.cc4303.bachmann.cl` y explicación DNS:**  
    Al consultar a Cloudflare (`1.1.1.1`), este responde con el estado `NXDOMAIN`. Esto ocurre porque en la zona DNS del dominio `bachmann.cl`, el registro `cc4303.bachmann.cl` existe, pero el subdominio `www.cc4303.bachmann.cl` no ha sido creado ni configurado.

#### Experimento 3: Variación de Name Servers y Direcciones IP

- **¿Son siempre los mismos Name Servers y direcciones IP a los que le pregunta su resolver en cada consulta?**
    
    Sí, al realizar múltiples consultas consecutivas a un mismo dominio, el resolver le pregunta siempre exactamente a los mismos Name Servers y a las mismas direcciones IP intermedias. Esto se verificó tanto para dominios locales (`.cl`) como para dominios globales (`google.com`, `wikipedia.org`, `amazon.com`, `mit.edu`).
    
    Se realizaron 10 consultas consecutivas de cada dominio y se verificó que siempre se pregunta a los mismos Name Servers y direcciones IP. Esto puede no ser siempre el caso en ambientes reales con múltiples servidores DNS y balanceo de carga, pero para esta entrega es constante.

- **¿Por qué cree usted que sucede esto?**  
    Esto sucede porque las funciones `extract_ns_name` y `extract_a_ip` del resolver siempre seleccionan el primer registro encontrado en la sección `AUTHORITY` o `ADDITIONAL` respectivamente. Por lo tanto, siempre que la respuesta del servidor DNS sea la misma, el resolver extraerá siempre el mismo Name Server y la misma dirección IP.


### 4. Declaración de uso de Inteligencia Artificial

**Modelo utilizado:** Gemini 3.6 de Google.

**Forma de uso:**

- Se utilizó para explicar y resolver dudas puntuales del enunciado, así como para crear una ruta de trabajo específica.
- Ayudó en la búsqueda de una estructura de datos eficiente para implementar el sistema de caché (librería collections: deque, Counter).
- Ayudó a entender el comportamiento del código frente a distintos escenarios (experimentos).
- Corrección ortográfica y mejora de redacción del presente informe.