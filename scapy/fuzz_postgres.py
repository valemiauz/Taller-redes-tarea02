#!/usr/bin/env python3
"""
fuzz_postgres.py
----------------
INYECCION DE TRAFICO MEDIANTE FUZZING contra el servidor PostgreSQL usando
Scapy. Se ejecuta en el contenedor 'scapy_attacker' (red bridge red_taller),
apuntando a la IP del servidor (postgres_server).

Para inyectar datos dentro de un flujo TCP real, el script realiza el
handshake de tres vias MANUALMENTE con Scapy y luego envia un mensaje de
inicio (StartupMessage) MALFORMADO. Como el kernel no conoce esta conexion
"cruda", responderia con un RST y la abortaria; por eso se instala la regla:

    iptables -A OUTPUT -p tcp --tcp-flags RST RST -j DROP

Dos campañas de fuzzing (variable de entorno FUZZ_MODE):

  framing   -> Inyeccion 1. Se aleatoriza el PREFIJO DE LONGITUD (4 bytes) del
               paquete de inicio: longitudes enormes, cero o que no coinciden
               con el cuerpo real. Pone a prueba el "framing"/encuadre del
               servidor (funcion ProcessStartupPacket).

  contenido -> Inyeccion 2. StartupMessage con la VERSION DE PROTOCOLO y los
               pares parametro/valor compuestos por bytes ALEATORIOS. Pone a
               prueba el parser de parametros de inicio.

  ambos     -> ejecuta las dos campañas (por defecto).

Uso (dentro de scapy_attacker):
    python3 fuzz_postgres.py                 # ambas campañas
    FUZZ_MODE=framing   ITERS=8 python3 fuzz_postgres.py
    FUZZ_MODE=contenido ITERS=8 python3 fuzz_postgres.py
"""
import os
import random
import socket
import struct
import subprocess
import sys

from scapy.all import IP, TCP, Raw, sr1, send, conf

conf.verb = 0

TARGET = os.environ.get("TARGET", "postgres_server")
DPORT = int(os.environ.get("PG_PORT", "5432"))
ITERS = int(os.environ.get("ITERS", "6"))
FUZZ_MODE = os.environ.get("FUZZ_MODE", "ambos").lower()

PROTO_V3 = 196608  # version 3.0 del protocolo (0x00030000)


def resolver(nombre):
    try:
        return socket.gethostbyname(nombre)
    except socket.gaierror:
        return nombre


DST = resolver(TARGET)


def drop_kernel_rst():
    subprocess.run(
        ["iptables", "-C", "OUTPUT", "-p", "tcp",
         "--tcp-flags", "RST", "RST", "-j", "DROP"],
        check=False,
    )
    subprocess.run(
        ["iptables", "-A", "OUTPUT", "-p", "tcp",
         "--tcp-flags", "RST", "RST", "-j", "DROP"],
        check=False,
    )


def handshake(sport):
    """3-way handshake manual. Devuelve (ip, seq, ack) o None."""
    ip = IP(dst=DST)
    syn = ip / TCP(sport=sport, dport=DPORT, flags="S", seq=random.randint(1, 2**31))
    synack = sr1(syn, timeout=3)
    if synack is None or not synack.haslayer(TCP) or synack[TCP].flags != 0x12:
        return None
    seq = synack[TCP].ack
    ack = synack[TCP].seq + 1
    send(ip / TCP(sport=sport, dport=DPORT, flags="A", seq=seq, ack=ack))
    return ip, seq, ack


def enviar(ctx, sport, payload):
    """Envia un segmento PSH/ACK con 'payload' y espera la respuesta."""
    ip, seq, ack = ctx
    seg = ip / TCP(sport=sport, dport=DPORT, flags="PA", seq=seq, ack=ack) / Raw(load=payload)
    return sr1(seg, timeout=3)


def describir_respuesta(resp):
    if resp is None:
        return "sin respuesta / conexion descartada (posible cierre del servidor)"
    if resp.haslayer(TCP) and resp[TCP].flags & 0x04:
        return "RST (el servidor abortó la conexion)"
    if resp.haslayer(Raw):
        data = bytes(resp[Raw].load)
        if data[:1] == b"E":
            # ErrorResponse: campos separados por \x00; el texto es legible
            texto = data.replace(b"\x00", b" ").decode("latin-1", "replace").strip()
            return f"ErrorResponse del servidor -> {texto[:140]}"
        return f"respuesta {data[:60]!r}"
    return "respuesta sin payload (ACK)"


# --------------------------- generadores de payload -------------------------
def payload_framing():
    cuerpo = struct.pack("!I", PROTO_V3) + b"user\x00postgres\x00database\x00postgres\x00\x00"
    longitud_falsa = random.choice(
        [0, 1, 2, 3, 5, 0xFFFFFFFF, random.randint(10**6, 10**9)]
    )
    return struct.pack("!I", longitud_falsa) + cuerpo


def payload_contenido():
    version = random.getrandbits(32)
    basura = bytes(random.getrandbits(8) for _ in range(random.randint(8, 80)))
    cuerpo = struct.pack("!I", version) + basura
    return struct.pack("!I", len(cuerpo) + 4) + cuerpo


def campana(nombre, generador):
    print(f"\n===== Campaña de fuzzing: {nombre}  ({ITERS} inyecciones) =====")
    for i in range(1, ITERS + 1):
        sport = random.randint(20000, 60000)
        ctx = handshake(sport)
        if ctx is None:
            print(f"  [{i}] handshake fallido (puerto {sport})")
            continue
        payload = generador()
        resp = enviar(ctx, sport, payload)
        print(f"  [{i}] inyectados {len(payload):>4} bytes "
              f"(cabecera len={payload[:4].hex()}) -> {describir_respuesta(resp)}")


def main():
    print(f"== Fuzzing PostgreSQL ==  objetivo={TARGET} ({DST}):{DPORT}  modo={FUZZ_MODE}")
    drop_kernel_rst()
    if FUZZ_MODE in ("framing", "ambos"):
        campana("framing (prefijo de longitud)", payload_framing)
    if FUZZ_MODE in ("contenido", "ambos"):
        campana("contenido (version y parametros aleatorios)", payload_contenido)
    if FUZZ_MODE not in ("framing", "contenido", "ambos"):
        sys.exit(f"FUZZ_MODE invalido: {FUZZ_MODE!r}. Use framing | contenido | ambos.")
    print("\nFuzzing finalizado.")


if __name__ == "__main__":
    main()
