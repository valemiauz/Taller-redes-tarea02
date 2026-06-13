# Taller de Redes y Servicios — Tarea 02

> Resolución completa de la Tarea 02 para el Taller de Redes y Servicios (Semestre 2026-1).  
> 🎥 Demostración práctica en video: [Ver en Google Drive](https://drive.google.com/file/d/1aetlOuwnfRZ2zABWUQRfC8VXzE2_egc6/view?usp=sharing)

---

## Tabla de Contenidos

1. [Resumen](#1-resumen)
2. [Tecnologías Utilizadas](#2-tecnologías-utilizadas)
3. [Archivos del Proyecto](#3-archivos-del-proyecto)
4. [Arquitectura de Red (Modo Bridge)](#4-arquitectura-de-red-modo-bridge)
5. [Instalación y Uso (Paso a Paso)](#5-instalación-y-uso-paso-a-paso)

---

## 1. Resumen

Este repositorio contiene la infraestructura, scripts y configuraciones necesarias para desplegar un entorno aislado de base de datos relacional y analizar de forma exhaustiva su tráfico en la capa de aplicación.

El objetivo primordial de la tarea es estudiar la máquina de estados del protocolo **PostgreSQL Frontend/Backend (v3.0)**, identificando detalladamente:

- Las fases de negociación de seguridad (SSL).
- El intercambio de desafíos criptográficos síncronos bajo el mecanismo **SCRAM-SHA-256**.
- La transmisión de transacciones lógicas en texto plano.

---

## 2. Tecnologías Utilizadas

| Herramienta | Rol |
|---|---|
| **Docker y Docker Compose** | Contenerización, orquestación y aislamiento de los entornos de software |
| **PostgreSQL v15 (Alpine)** | Motor de base de datos relacional (Servidor) y consola interactiva (Cliente) |
| **Netshoot** (`nicolaka/netshoot`) | Contenedor de diagnóstico con `tcpdump` para captura de tramas crudas a nivel de red |
| **Wireshark** | Analizador de protocolos para inspección, filtrado y desglose de los paquetes `.pcap` |

---

## 3. Archivos del Proyecto

| Archivo | Descripción |
|---|---|
| `docker-compose.yml` | Orquestación de la infraestructura: servicios, IPs, volúmenes y contenedor de captura automatizada |
| `Comandos Video.txt` | Secuencia exacta de comandos y sentencias SQL ejecutadas durante la demostración |
| `captura_postgres.pcap` | Tráfico de red crudo generado durante la interacción cliente-servidor, listo para Wireshark |

---

## 4. Arquitectura de Red (Modo Bridge)

El proyecto implementa una red virtual de tipo **Bridge** denominada `red_taller`. En Docker, este componente actúa como un switch de red virtual integrado. Al iniciar los servicios, los contenedores quedan enlazados a este segmento privado con las siguientes direcciones:

| Contenedor | IP | Puerto |
|---|---|---|
| Servidor (`postgres_server`) | `172.18.0.2/16` | `5432` |
| Cliente (`postgres_client`) | `172.18.0.3/16` | — |

Esta topología garantiza el **aislamiento hermético** del tráfico transaccional frente al sistema operativo anfitrión y redes externas, permitiendo que la herramienta de captura intercepte paquetes de la interfaz virtual sin interferencia de ruido de red doméstico o de Internet.

---

## 5. Instalación y Uso (Paso a Paso)

### Paso 1 — Levantar la Infraestructura

Abre una terminal en la carpeta raíz del proyecto y ejecuta:

```bash
docker compose up -d
```

> Docker descargará las imágenes e inicializará los contenedores en segundo plano.

---

### Paso 2 — Iniciar el Contenedor de Captura

En una **segunda terminal**, lanza el contenedor espía de Netshoot. Este se acoplará a la red del servidor y comenzará a registrar todo el tráfico del puerto 5432:

```bash
docker run --rm -it --network container:psql_server -v .:/data nicolaka/netshoot tcpdump -i any port 5432 -w /data/captura_postgres.pcap
```

> Mantén esta terminal abierta durante toda la sesión. La captura se detendrá al interrumpirla con `Ctrl+C`.

---

### Paso 3 — Acceder a la Consola del Cliente

En una **tercera terminal**, ingresa de forma interactiva al contenedor cliente:

```bash
docker exec -it psql_client sh
```

> El prompt de tu terminal cambiará, indicando que estás operando dentro del contenedor Linux aislado.

---

### Paso 4 — Conectarse a la Base de Datos

```bash
psql -h postgres_server -U sebastian -d taller_redes
```

> Cuando se soliciten las credenciales, ingresa la contraseña: `mi_password123`

---

### Paso 5 — Generar el Tráfico Transaccional

Ejecuta las siguientes sentencias SQL una por una dentro del prompt `taller_redes=#`:

```sql
-- 1. Crear la tabla (gatilla mensajes 'Q' y 'C')
CREATE TABLE tareas (id SERIAL PRIMARY KEY, nombre_ramo VARCHAR(50));

-- 2. Insertar un registro (gatilla flujo de escritura)
INSERT INTO tareas (nombre_ramo) VALUES ('Taller de Redes');

-- 3. Consultar los datos (gatilla mensajes 'T' y 'D' con payload en texto plano)
SELECT * FROM tareas;

-- 4. Cerrar la sesión limpiamente (gatilla el mensaje 'X' de término)
\q
```

---

### Paso 6 — Salir del Contenedor Cliente

```bash
exit
```

---

### Paso 7 — Detener la Captura y Desmontar el Entorno

Vuelve a la terminal del contenedor de captura y detente con `Ctrl+C`. El archivo `captura_postgres.pcap` quedará guardado en la carpeta raíz del proyecto.

Luego, desmonta los servicios:

```bash
docker compose down
```

---

### Paso 8 — Inspección en Wireshark

1. Abre **Wireshark**.
2. Carga el archivo: `File → Open → captura_postgres.pcap`.
3. Aplica el filtro de visualización `pgsql` en la barra de búsqueda y presiona Enter.
