#!/usr/bin/env python3
r"""
medir_metricas.py
-----------------
Orquesta el ANALISIS DE METRICAS de la Tarea 3. Se ejecuta en el HOST
(Windows, con Python ya instalado) y usa 'docker exec' para:

  1. Aplicar una condicion de red en la interfaz eth0 del servidor con
     'tc netem' (desde el contenedor scapy_mitm, que comparte la pila de red
     del servidor).
  2. Medir el THROUGHPUT transfiriendo una tabla grande con COPY ... TO STDOUT
     desde el cliente psql_client, contando los bytes y el tiempo.

Se barren dos metricas, distintas a throughput y goodput, que miden aspectos
diferentes de la red:

    * LATENCIA (delay)        -> aspecto temporal
    * PERDIDA DE PAQUETES     -> aspecto de fiabilidad

Resultado: archivo 'resultados_metricas.csv' con columnas
    metrica,valor,throughput_mbps,segundos,bytes,ok

Requisitos previos (ver GUIA_PASO_A_PASO.md):
    docker compose up -d --build
    docker exec -e PGPASSWORD=123 psql_client \
        psql -h postgres_server -U postgres -d postgres -f /metricas/cargar_datos.sql
    (monte ./metricas en psql_client o copie el .sql; la guia lo explica)

Uso:
    python medir_metricas.py
"""
import csv
import subprocess
import sys
import time

PGPASSWORD = "123"
SERVER_NS = "scapy_mitm"     # comparte la pila de red del servidor (tiene tc)
CLIENT = "psql_client"       # cliente psql
IFACE = "eth0"

# Valores a barrer para cada metrica
DELAYS_MS = [0, 10, 25, 50, 100, 200, 400, 800]
LOSSES_PCT = [0, 1, 2, 5, 10, 20, 40, 60]

# Consulta de medicion: transfiere toda la tabla 'carga' en texto.
COPY = "COPY (SELECT * FROM carga) TO STDOUT"
MEAS_TIMEOUT = 90  # s


def run(args, timeout=30, capture=True):
    return subprocess.run(
        args, capture_output=capture, timeout=timeout, text=False
    )


def netem_reset():
    run(["docker", "exec", SERVER_NS, "tc", "qdisc", "del", "dev", IFACE, "root"])


def netem_apply(kind, value):
    netem_reset()
    if value == 0:
        return  # sin qdisc = condicion base
    if kind == "delay":
        spec = ["delay", f"{value}ms"]
    elif kind == "loss":
        spec = ["loss", f"{value}%"]
    else:
        raise ValueError(kind)
    run(["docker", "exec", SERVER_NS, "tc", "qdisc", "add",
         "dev", IFACE, "root", "netem", *spec])


def medir_throughput():
    """Devuelve (bytes, segundos, ok). Mide COPY -> STDOUT | wc -c."""
    cmd = [
        "docker", "exec", "-e", f"PGPASSWORD={PGPASSWORD}", CLIENT,
        "sh", "-c",
        f"psql -h postgres_server -U postgres -d postgres -tA "
        f"-c \"{COPY}\" | wc -c",
    ]
    t0 = time.perf_counter()
    try:
        res = run(cmd, timeout=MEAS_TIMEOUT)
    except subprocess.TimeoutExpired:
        return 0, MEAS_TIMEOUT, False
    dt = time.perf_counter() - t0
    if res.returncode != 0:
        return 0, dt, False
    try:
        nbytes = int(res.stdout.decode().strip().split()[-1])
    except (ValueError, IndexError):
        return 0, dt, False
    return nbytes, dt, nbytes > 0


def barrer(metrica, valores, kind):
    filas = []
    print(f"\n===== Metrica: {metrica} =====")
    for v in valores:
        netem_apply(kind, v)
        time.sleep(0.5)
        nbytes, dt, ok = medir_throughput()
        mbps = (nbytes * 8 / dt / 1e6) if (ok and dt > 0) else 0.0
        estado = "OK" if ok else "FALLO/timeout"
        print(f"  {metrica}={v:<5} -> {mbps:8.2f} Mbps  ({dt:5.2f}s, "
              f"{nbytes} bytes, {estado})")
        filas.append([metrica, v, round(mbps, 3), round(dt, 3), nbytes, int(ok)])
    return filas


def main():
    # Verificar que los contenedores existan
    chk = run(["docker", "ps", "--format", "{{.Names}}"], timeout=15)
    nombres = chk.stdout.decode() if chk.stdout else ""
    for c in (SERVER_NS, CLIENT):
        if c not in nombres:
            sys.exit(f"El contenedor '{c}' no esta corriendo. "
                     f"Ejecute 'docker compose up -d --build' primero.")

    filas = []
    try:
        filas += barrer("delay_ms", DELAYS_MS, "delay")
        filas += barrer("loss_pct", LOSSES_PCT, "loss")
    finally:
        netem_reset()
        print("\nnetem reiniciado (condicion de red normal).")

    with open("resultados_metricas.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metrica", "valor", "throughput_mbps", "segundos", "bytes", "ok"])
        w.writerows(filas)
    print("\nGuardado: resultados_metricas.csv")
    print("Ahora ejecute:  python graficar_metricas.py")


if __name__ == "__main__":
    main()
