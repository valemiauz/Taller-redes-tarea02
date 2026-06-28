#!/usr/bin/env python3
"""
graficar_metricas.py
--------------------
Lee 'resultados_metricas.csv' (generado por medir_metricas.py) y produce los
graficos METRICA vs THROUGHPUT exigidos por la Tarea 3:

    delay_vs_throughput.png   (latencia vs throughput)
    loss_vs_throughput.png    (perdida de paquetes vs throughput)

Ademas estima y marca la COTA DE DESEMPENO de cada metrica: el valor a partir
del cual el throughput cae por debajo del 10 % del valor base (condicion sin
degradacion). Se ejecuta en el HOST con matplotlib instalado.

Uso:
    python graficar_metricas.py
"""
import csv
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CSV = "resultados_metricas.csv"
UMBRAL = 0.10  # 10 % del throughput base define la cota de desempeno


def cargar(csv_path):
    series = {}
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            m = row["metrica"]
            series.setdefault(m, []).append(
                (float(row["valor"]), float(row["throughput_mbps"]))
            )
    for m in series:
        series[m].sort()
    return series


def cota(puntos):
    """Primer valor cuyo throughput baja del 10 % del base."""
    base = puntos[0][1] if puntos else 0.0
    if base <= 0:
        return None
    for valor, thr in puntos:
        if thr < UMBRAL * base:
            return valor
    return None


def graficar(puntos, titulo, xlabel, archivo, color):
    xs = [p[0] for p in puntos]
    ys = [p[1] for p in puntos]
    c = cota(puntos)

    fig, ax = plt.subplots(figsize=(7, 4.3))
    ax.plot(xs, ys, marker="o", color=color, linewidth=2, label="Throughput medido")
    ax.fill_between(xs, ys, alpha=0.12, color=color)

    if c is not None:
        ax.axvline(c, color="red", linestyle="--", linewidth=1.5,
                   label=f"Cota de desempeño ≈ {c:g}")
        ax.annotate("servicio degradado",
                    xy=(c, max(ys) * 0.5),
                    xytext=(c, max(ys) * 0.78),
                    color="red", fontsize=9, ha="center",
                    arrowprops=dict(arrowstyle="->", color="red"))

    ax.set_title(titulo, fontsize=12, fontweight="bold")
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Throughput (Mbps)")
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend()
    fig.tight_layout()
    fig.savefig(archivo, dpi=140)
    plt.close(fig)
    print(f"Generado: {archivo}  (cota de desempeño: {c})")


def main():
    if not os.path.exists(CSV):
        sys.exit(f"No se encontro {CSV}. Ejecute primero 'python medir_metricas.py' "
                 f"(o use el CSV de ejemplo incluido).")
    series = cargar(CSV)

    if "delay_ms" in series:
        graficar(series["delay_ms"],
                 "Latencia vs Throughput (PostgreSQL)",
                 "Latencia añadida (ms)",
                 "delay_vs_throughput.png", "#2563eb")
    if "loss_pct" in series:
        graficar(series["loss_pct"],
                 "Pérdida de paquetes vs Throughput (PostgreSQL)",
                 "Pérdida de paquetes (%)",
                 "loss_vs_throughput.png", "#c2410c")


if __name__ == "__main__":
    main()
