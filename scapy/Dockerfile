FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

# Dependencias del sistema:
#   - iptables        -> redirigir trafico a NFQUEUE y descartar RST del kernel
#   - iproute2        -> 'tc netem' para el analisis de metricas (delay/loss)
#   - tcpdump         -> verificacion/captura
#   - build-essential -> gcc + libc6-dev (cabeceras de C, p.ej. stdlib.h) + make
#   - libnetfilter-queue-dev -> cabeceras para compilar el binding NetfilterQueue
RUN apt-get update && apt-get install -y --no-install-recommends \
    iptables \
    iproute2 \
    tcpdump \
    build-essential \
    libnetfilter-queue-dev \
    && rm -rf /var/lib/apt/lists/*

# Ultima version de Scapy + binding de NetfilterQueue
RUN pip install --no-cache-dir scapy NetfilterQueue

WORKDIR /scapy
COPY . /scapy

# El contenedor queda vivo; se entra con 'docker exec' para lanzar los scripts.
CMD ["sleep", "infinity"]
