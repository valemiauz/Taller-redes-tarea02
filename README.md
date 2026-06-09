# Taller de Redes - Tarea 02
> Resolución de la Tarea 02 para el Taller de Redes.
> Demostración en video [_aquí_](https://drive.google.com/file/d/1aetlOuwnfRZ2zABWUQRfC8VXzE2_egc6/view?usp=sharing).

## Tabla de Contenidos
* [Resumen](#resumen)
* [Tecnologías Utilizadas](#tecnologías-utilizadas)
* [Archivos del Proyecto](#archivos-del-proyecto)
* [Instalación y Uso](#instalación-y-uso)
* [Estado del Proyecto](#estado-del-proyecto)

## Resumen
Este repositorio contiene los archivos necesarios para desplegar un entorno de base de datos y analizar su tráfico de red. El objetivo de la tarea es levantar un servicio mediante contenedores, ejecutar comandos específicos y capturar los paquetes de red resultantes para evidenciar la comunicación.

## Tecnologías Utilizadas
- Docker y Docker Compose
- PostgreSQL
- Wireshark (para análisis de tráfico)

## Archivos del Proyecto
- `docker-compose.yml`: Archivo de configuración que contiene la infraestructura y los servicios a levantar en los contenedores.
- `Comandos Video.txt`: Documento que detalla los comandos exactos ejecutados en la terminal durante la demostración práctica.
- `captura_postgres.pcap`: Captura de tráfico de red generada durante la interacción con la base de datos, lista para ser inspeccionada.

## Instalación y Uso
Para iniciar el entorno localmente, es necesario contar con Docker. Debes posicionarte en la carpeta del proyecto y ejecutar:

```bash
docker-compose up -d
