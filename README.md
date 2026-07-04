# Taller de Redes y Servicios — Tareas 02 y 03 (Protocolo PostgreSQL)

> Resolución completa de las Tareas 02 y 03 para el Taller de Redes y Servicios (Semestre 2026-1) By Sebastian Quintero y Valentina Martinez ; Protocolo = PostgreSQL Frontend/Backend.
> 🎥 Demostración Tarea 02: [Ver en Google Drive](https://drive.google.com/file/d/1E7D9Mztg_WDtbUt6iYXz46ZSLjgJODKr/view?usp=sharing)
> 🎥 Demostración Tarea 03: _(https://drive.google.com/file/d/1w-StOqau1wTsYGMon5ouDZdJEcnylIcm/view?usp=sharing)_

---

## Tabla de Contenidos

1. [Resumen](#1-resumen)
2. [Tecnologías Utilizadas](#2-tecnologías-utilizadas)
3. [Archivos del Proyecto](#3-archivos-del-proyecto)
4. [Arquitectura de Red (Modo Bridge)](#4-arquitectura-de-red-modo-bridge)
5. [Instalación y Uso (Paso a Paso)](#5-instalación-y-uso-paso-a-paso)
   - [Tarea 02 — Despliegue y análisis de tráfico (Pasos 1–7)](#tarea-02--despliegue-y-análisis-de-tráfico)
   - [Tarea 03 — Modificación de tráfico y análisis de métricas (Pasos 8–13)](#-continuación--tarea-03-modificación-de-tráfico-y-análisis-de-métricas)

---

## 1. Resumen

Este repositorio contiene la infraestructura, scripts y configuraciones necesarias para desplegar un entorno aislado de base de datos relacional, analizar su tráfico en la capa de aplicación y, posteriormente, **interceptarlo, modificarlo e inyectarlo** para estudiar las repercusiones sobre el servicio.

El objetivo de la **Tarea 02** fue estudiar la máquina de estados del protocolo **PostgreSQL Frontend/Backend (v3.0)**, identificando:
- Las fases de negociación de seguridad (SSL).
- El intercambio de desafíos criptográficos síncronos bajo el mecanismo **SCRAM-SHA-256**.
- La transmisión de transacciones lógicas en texto plano.

El objetivo de la **Tarea 03** es llevar esas observaciones a la práctica usando **Scapy** y **Docker**:
- **Interceptar** el tráfico cliente/servidor con Scapy.
- **Inyectar** 2 paquetes mediante técnicas de **fuzzing**.
- **Modificar** 3 campos del protocolo en tiempo real (MITM) para forzar comportamientos anómalos.
- Medir **2 métricas de red** (latencia y pérdida de paquetes) y determinar su **cota de desempeño**, graficando **métrica vs throughput**.

Este entorno se construye de forma nativa utilizando **Dockerfiles** personalizados basados en Ubuntu 22.04, los cuales clonan el repositorio del código fuente y compilan el motor de base de datos directamente en el contenedor del servidor.

---

## 2. Tecnologías Utilizadas

| Herramienta | Rol |
|---|---|
| **Docker y Docker Compose** | Contenerización, orquestación, construcción local desde Dockerfile y aislamiento de red |
| **PostgreSQL (Nativo en C)** | Servidor compilado a medida en Ubuntu y cliente interactivo de bases de datos |
| **Netshoot** (`nicolaka/netshoot`) | Contenedor de diagnóstico con `tcpdump` integrado de forma automática en el stack de servicios |
| **Wireshark** | Analizador de protocolos para inspección, filtrado y desglose de los paquetes `.pcap` |
| **Scapy** (en contenedor) | Intercepción, inyección y modificación de paquetes del protocolo (Tarea 3) |
| **NetfilterQueue + iptables** | Desvío del tráfico del puerto 5432 a una cola en espacio de usuario para modificarlo en vivo (MITM) |
| **tc / netem** (`iproute2`) | Inyección de latencia y pérdida de paquetes para el análisis de métricas |
| **Python + matplotlib** | Medición de throughput y generación de los gráficos métrica vs throughput |

---

## 3. Archivos del Proyecto

| Archivo / Carpeta | Descripción |
|---|---|
| `docker-compose.yml` | Orquestación de los 5 servicios: servidor, cliente, captura y los 2 atacantes Scapy |
| `server/Dockerfile` | Compilación del servidor PostgreSQL desde el código fuente (Git + `gcc`/`make`) |
| `client/Dockerfile` | Aprovisionamiento del entorno interactivo cliente con `psql` |
| `Comandos Video.txt` | Secuencia exacta de comandos y sentencias SQL ejecutadas en la demostración |
| `captura_postgres.pcap` | Tráfico de red crudo generado durante la interacción cliente-servidor, listo para Wireshark |
| `scapy/Dockerfile` | Imagen `python:3.12` con Scapy + NetfilterQueue + iptables + `tc` |
| `scapy/sniff_postgres.py` | **Intercepción** del tráfico del protocolo con Scapy |
| `scapy/mitm_postgres.py` | **3 modificaciones** de campos en vivo (`MITM_MODE=tipo \| sql \| datarow`) |
| `scapy/fuzz_postgres.py` | **2 inyecciones** por fuzzing (`FUZZ_MODE=framing \| contenido`) |
| `metricas/cargar_datos.sql` | Crea la tabla `tareas` y una tabla `carga` (~7 MB) para medir throughput |
| `metricas/medir_metricas.py` | Barre latencia/pérdida y mide el throughput → `resultados_metricas.csv` |
| `metricas/graficar_metricas.py` | Genera `delay_vs_throughput.png` y `loss_vs_throughput.png` con la cota de desempeño |

---

## 4. Arquitectura de Red (Modo Bridge)

El proyecto implementa una red virtual de tipo **Bridge** denominada `red_taller`. En Docker, este componente actúa como un switch de red virtual integrado. Al iniciar los servicios, los contenedores quedan enlazados a este segmento privado:

| Contenedor | Red | Puerto | Rol |
|---|---|---|---|
| Servidor (`psql_server`) | `172.18.0.2/16` | `5432` | Servidor PostgreSQL compilado desde el fuente |
| Cliente (`psql_client`) | `172.18.0.3/16` | — | Cliente `psql` |
| Captura (`psql_capture`) | comparte red del servidor | — | `tcpdump` → `captura_postgres.pcap` |
| **MITM** (`scapy_mitm`) | comparte red del servidor | — | Modifica el tráfico en vivo (NFQUEUE+Scapy) y aplica `tc netem` |
| **Atacante** (`scapy_attacker`) | bridge `red_taller` | — | Inyecta tráfico / fuzzing con Scapy |

Mediante la directiva `network_mode: "service:postgres_server"`, los contenedores de captura y de **MITM** comparten directamente la interfaz de red del servidor, observando y modificando exactamente el tráfico que entra y sale por el puerto 5432, sin ruido externo. El contenedor `scapy_attacker` vive en la red bridge y ataca al servidor por su IP.

---

## 5. Instalación y Uso (Paso a Paso)

## Tarea 02 — Despliegue y análisis de tráfico

### Paso 1 — Construir y Levantar la Infraestructura

Abre una terminal en la carpeta raíz del proyecto (donde se encuentra tu archivo `docker-compose.yml`) y ejecuta el comando de compilación:

```bash
docker compose up -d --build
```

> **⏳ Nota:** Debido a que Docker compilará todo el código de PostgreSQL en C desde cero, el proceso de construcción puede tardar **varios minutos**. Los contenedores de captura y de ataque (`scapy_mitm`, `scapy_attacker`) iniciarán en segundo plano automáticamente al terminar.

Espera hasta que todos los servicios aparezcan en **color verde** antes de continuar. Verifica con `docker ps` que estén los 5 contenedores: `psql_server`, `psql_client`, `psql_capture`, `scapy_mitm` y `scapy_attacker`.

---

### Paso 2 — Entrar al Contenedor Cliente

Una vez que el stack esté levantado, ingresa de forma interactiva al shell del contenedor cliente:

```bash
docker exec -it psql_client sh
```

---

### Paso 3 — Conectarse al Servidor Remoto

Desde dentro del contenedor, inicia la herramienta `psql` apuntando al host del servidor y al superusuario `postgres` a través de la red:

```bash
psql -h postgres_server -U postgres
```

Cuando la terminal solicite la contraseña (`Password for user postgres:`), escribe:

```
123
```

Presiona **Enter** para confirmar.

> **🔒 Nota:** En entornos Linux, la contraseña **no se muestra en pantalla** mientras escribes. Esto es comportamiento normal.

---

### Paso 4 — Ejecutar la Secuencia SQL Transaccional

Una vez dentro del prompt activo `postgres=#`, ejecuta los siguientes comandos uno por uno para registrar el tráfico de red:

**A. Crear la tabla relacional**
Gatilla mensajes `Q` y `C` de definición de esquema.

```sql
CREATE TABLE tareas (id SERIAL PRIMARY KEY, nombre_ramo VARCHAR(50));
```

**B. Insertar un registro de datos**
Gatilla el flujo de escritura hacia el servidor.

```sql
INSERT INTO tareas (nombre_ramo) VALUES ('Taller de Redes');
```

**C. Consultar y extraer datos**
Gatilla los mensajes `T` (descripción de columnas) y `D` (filas de datos) en texto plano.

```sql
SELECT * FROM tareas;
```

**D. Cerrar la sesión de forma limpia**
Gatilla el mensaje de terminación `X` del protocolo.

```sql
\q
```

---

### Paso 5 — Salir del Contenedor Cliente

Para cerrar el canal interactivo y regresar a tu sistema operativo anfitrión:

```bash
exit
```

---

### Paso 6 — Desmontar los Servicios y Consolidar la Captura

Para detener de forma segura el laboratorio y forzar que `tcpdump` guarde todos los búferes de red en disco sin corromper bytes, ejecuta:

```bash
docker compose down
```

Al completarse el desmontaje, se habrá generado automáticamente el archivo binario **`captura_postgres.pcap`** en el directorio raíz del proyecto.

> **💡 Tip:** Si vas a continuar con la Tarea 03, **no ejecutes `docker compose down`** todavía: mantén el entorno levantado para los pasos siguientes.

---

### Paso 7 — Inspección y Análisis en Wireshark

1. Abre la aplicación **Wireshark** en tu computadora.
2. Carga el archivo recién generado: **File → Open → `captura_postgres.pcap`**.
3. Aplica el filtro de visualización en la barra superior:

```
pgsql
```

4. Presiona **Enter** para filtrar y analizar la máquina de estados del protocolo PostgreSQL.

---

## 🔴 Continuación — Tarea 03: Modificación de tráfico y análisis de métricas

> A partir de aquí se asume que el entorno está levantado (Paso 1) y que tienes **Python con matplotlib** en el host (`pip install matplotlib`) para graficar. **Scapy no se instala en el host**: corre dentro de los contenedores `scapy_mitm` y `scapy_attacker`.
>
> Comprueba que Scapy quedó listo:
> ```bash
> docker exec scapy_mitm python3 -c "import scapy; print('Scapy', scapy.__version__)"
> docker exec scapy_mitm python3 -c "from netfilterqueue import NetfilterQueue; print('NFQUEUE OK')"
> ```

### Paso 8 — Cargar los datos de prueba

Crea la tabla pequeña (`tareas`) para las modificaciones y la tabla grande (`carga`, ~7 MB) para medir throughput:

```bash
docker exec -e PGPASSWORD=123 psql_client psql -h postgres_server -U postgres -d postgres -f /metricas/cargar_datos.sql
```

---

### Paso 9 — Interceptar el tráfico con Scapy

En una terminal, lanza el interceptor (corre dentro de `scapy_mitm`, que comparte la red del servidor):

```bash
docker exec -it scapy_mitm python3 sniff_postgres.py
```

En **otra** terminal, genera tráfico para verlo pasar:

```bash
docker exec -it psql_client sh -c "PGPASSWORD=123 psql -h postgres_server -U postgres -c 'SELECT * FROM tareas;'"
```

Verás impreso cada mensaje del protocolo con su byte de tipo y dirección (`Q` Query, `T` RowDescription, `D` DataRow, `C` CommandComplete, `Z` ReadyForQuery…). Esto es la **intercepción** exigida. Pulsa `Ctrl+C` para salir.

---

### Paso 10 — Inyección de tráfico mediante fuzzing (2 inyecciones)

Se ejecuta desde `scapy_attacker`. El script hace el handshake TCP a mano e inyecta mensajes de inicio (`StartupMessage`) malformados.

```bash
# Las dos campañas de una vez (framing + contenido):
docker exec -it scapy_attacker python3 fuzz_postgres.py

# O por separado:
docker exec -it -e FUZZ_MODE=framing   -e ITERS=8 scapy_attacker python3 fuzz_postgres.py
docker exec -it -e FUZZ_MODE=contenido -e ITERS=8 scapy_attacker python3 fuzz_postgres.py
```

- **Inyección 1 — fuzzing del encuadre:** aleatoriza el **prefijo de longitud** (4 bytes) del paquete de inicio. *Se espera* que el servidor rechace longitudes fuera de rango (`invalid length of startup packet`) o cierre la conexión → demuestra la robustez del control de **framing**.
- **Inyección 2 — fuzzing del contenido:** versión de protocolo y parámetros con bytes aleatorios. *Se espera* `ErrorResponse` (`unsupported frontend protocol` / `invalid startup packet layout`).

El script imprime, por cada inyección, la respuesta del servidor (`ErrorResponse`, `RST` o cierre).

---

### Paso 11 — Modificación de campos del protocolo (3 modificaciones)

Cada modificación usa `mitm_postgres.py` en `scapy_mitm`. **Procedimiento:** (1) lanza el interceptor en el modo deseado en una terminal; (2) genera la consulta desde `psql_client` en otra; (3) observa el efecto; (4) `Ctrl+C` para retirar las reglas iptables.

> Las sustituciones son de **igual longitud** para no romper la conexión TCP.

**Modificación 1 — Byte de tipo `Q` → `X` (denegación de servicio · Caso A)**

```bash
# Terminal A:
docker exec -it -e MITM_MODE=tipo scapy_mitm python3 mitm_postgres.py
# Terminal B:
docker exec -it psql_client sh -c "PGPASSWORD=123 psql -h postgres_server -U postgres -c 'SELECT * FROM tareas;'"
```
> **Esperado:** el servidor lee `X` como `Terminate`, cierra el socket y **no ejecuta** la consulta. `psql` reporta *"server closed the connection unexpectedly"*.

**Modificación 2 — Texto SQL del Query (el servidor ejecuta otra consulta)**

```bash
# Terminal A:
docker exec -it -e MITM_MODE=sql -e OLD=tareas -e NEW=xareas scapy_mitm python3 mitm_postgres.py
# Terminal B:
docker exec -it psql_client sh -c "PGPASSWORD=123 psql -h postgres_server -U postgres -c 'SELECT * FROM tareas;'"
```
> **Esperado:** aunque escribiste `tareas`, el servidor recibe `xareas` y responde `relation "xareas" does not exist`.

**Modificación 3 — Payload de un `DataRow` (datos falsificados · Caso B)**

```bash
# Terminal A:
docker exec -it -e MITM_MODE=datarow -e OLD="Taller de Redes" -e NEW="HACKED de Redes" scapy_mitm python3 mitm_postgres.py
# Terminal B:
docker exec -it psql_client sh -c "PGPASSWORD=123 psql -h postgres_server -U postgres -c 'SELECT * FROM tareas;'"
```
> **Esperado:** `psql` muestra `HACKED de Redes`, un valor que nunca existió en la base de datos. Al cerrar el interceptor y repetir la consulta, vuelve a aparecer el valor real.

---

### Paso 12 — Análisis de métricas de red (latencia y pérdida)

Dos métricas distintas a throughput/goodput, que miden aspectos diferentes: **latencia** (temporal) y **pérdida de paquetes** (fiabilidad). Se inyectan con `tc netem` sobre `eth0` del servidor (desde `scapy_mitm`). El script de medición corre en el **host**:

```bash
# Desde la carpeta del proyecto, en el host:
cd metricas
python medir_metricas.py        # barre delay y loss, mide throughput -> resultados_metricas.csv
python graficar_metricas.py     # genera delay_vs_throughput.png y loss_vs_throughput.png
```

Resultados obtenidos en este equipo (corrida de referencia; la **cota de desempeño** es el valor donde el throughput cae por debajo del 10 % del valor base):

| Latencia (ms) | 0 | 50 | 100 | **200** | 400 | 800 |
|---|---|---|---|---|---|---|
| Throughput (Mbps) | 247 | 60 | 34 | **19** | 9.9 | 4.7 |

→ **Cota de desempeño ≈ 200 ms** de latencia añadida.

| Pérdida (%) | 0 | 1 | 5 | **10** | 20 | 40 |
|---|---|---|---|---|---|---|
| Throughput (Mbps) | 257 | 296 | 101 | **16** | 0.9 | falla |

→ **Cota de desempeño ≈ 10 %** de pérdida; con ≥ 40 % la transferencia ya no completa (la conexión expira).

Para aplicar/quitar las métricas manualmente (útil para el video):

```bash
docker exec scapy_mitm tc qdisc add dev eth0 root netem delay 200ms   # añade latencia
docker exec scapy_mitm tc qdisc change dev eth0 root netem loss 10%   # cambia a pérdida
docker exec scapy_mitm tc qdisc del dev eth0 root                     # restaura
```

---

### Paso 13 — Limpieza

```bash
docker exec scapy_mitm tc qdisc del dev eth0 root   # quita netem si quedó aplicado
docker compose down                                  # detiene y elimina los contenedores
```

---

### 🛠️ Solución de problemas (Tarea 03)

| Síntoma | Causa / solución |
|---|---|
| `NetfilterQueue` no intercepta / error al hacer `bind` | El kernel WSL2 no expone `nfnetlink_queue`. Añade `privileged: true` al servicio `scapy_mitm` en `docker-compose.yml` y vuelve a levantar. |
| `tc: Unknown qdisc "netem"` | Falta `sch_netem`; actualiza Docker Desktop (los kernels recientes lo incluyen). |
| La interfaz no es `eth0` | `docker exec scapy_mitm ip -o link` y ajusta `IFACE` en `metricas/medir_metricas.py`. |
| El fuzzing no recibe respuesta | El `RST` del kernel cortó la conexión cruda; verifica `docker exec scapy_attacker iptables -S OUTPUT` (debe existir el DROP de RST). |
| La modificación `sql`/`datarow` no ocurre | El patrón quedó partido entre dos segmentos TCP; usa consultas en una sola línea y cadenas `OLD` cortas y exactas. |
