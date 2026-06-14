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

A diferencia del enfoque anterior, este entorno se construye de forma nativa utilizando **Dockerfiles** personalizados basados en Ubuntu 22.04, los cuales clonan el repositorio del código fuente y compilan el motor de base de datos directamente en el contenedor del servidor.

---

## 2. Tecnologías Utilizadas

| Herramienta | Rol |
|---|---|
| **Docker y Docker Compose** | Contenerización, orquestación, construcción local desde Dockerfile y aislamiento de red |
| **PostgreSQL (Nativo en C)** | Servidor compilado a medida en Ubuntu y cliente interactivo de bases de datos |
| **Netshoot** (`nicolaka/netshoot`) | Contenedor de diagnóstico con `tcpdump` integrado de forma automática en el stack de servicios |
| **Wireshark** | Analizador de protocolos para inspección, filtrado y desglose de los paquetes `.pcap` |

---

## 3. Archivos del Proyecto

| Archivo / Carpeta | Descripción |
|---|---|
| `docker-compose.yml` | Orquestación de la infraestructura, construcción de imágenes locales, IPs de red y automatización del contenedor espía |
| `server/Dockerfile` | Instrucciones de compilación para el servidor: instalación de herramientas (`gcc`, `make`), clonación de Git y configuración de permisos |
| `client/Dockerfile` | Instrucciones de aprovisionamiento del entorno interactivo cliente con las librerías de conexión remota necesarias |
| `Comandos Video.txt` | Secuencia exacta de comandos y sentencias SQL ejecutadas durante la demostración |
| `captura_postgres.pcap` | Tráfico de red crudo generado durante la interacción cliente-servidor, listo para Wireshark |

---

## 4. Arquitectura de Red (Modo Bridge)

El proyecto implementa una red virtual de tipo **Bridge** denominada `red_taller`. En Docker, este componente actúa como un switch de red virtual integrado. Al iniciar los servicios, los contenedores quedan enlazados a este segmento privado con las siguientes direcciones:

| Contenedor | IP | Puerto |
|---|---|---|
| Servidor (`postgres_server`) | `172.18.0.2/16` | `5432` |
| Cliente (`postgres_client`) | `172.18.0.3/16` | — |

Esta topología garantiza el **aislamiento hermético** del tráfico transaccional frente al sistema operativo anfitrión y redes externas. Además, mediante la directiva `network_mode: "service:postgres_server"`, el contenedor de captura comparte de manera directa la interfaz de red del servidor, capturando el tráfico sin interferencias de ruido doméstico o de Internet.

---

## 5. Instalación y Uso (Paso a Paso)

### Paso 1 — Construir y Levantar la Infraestructura

Abre una terminal en la carpeta raíz del proyecto (donde se encuentra tu archivo `docker-compose.yml`) y ejecuta el comando de compilación:

```bash
docker compose up -d --build