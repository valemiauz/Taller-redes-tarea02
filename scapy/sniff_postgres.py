#!/usr/bin/env python3
"""
sniff_postgres.py
-----------------
INTERCEPCION del trafico del protocolo PostgreSQL Frontend/Backend con Scapy.

Se ejecuta dentro del contenedor 'scapy_mitm', que comparte la pila de red del
servidor (network_mode: "service:postgres_server"). Por lo tanto observa todos
los segmentos TCP que entran y salen por el puerto 5432 y muestra, para cada
uno, el byte de tipo del mensaje del protocolo y su direccion.

Uso:
    docker exec -it scapy_mitm python3 sniff_postgres.py
"""
from scapy.all import sniff, TCP, Raw

PG_PORT = 5432

# Byte de tipo (1er byte del mensaje) -> nombre del mensaje del protocolo v3.0
TIPOS = {
    b'Q': 'Query',            b'R': 'Authentication',   b'p': 'SASL/Password',
    b'S': 'ParameterStatus',  b'K': 'BackendKeyData',   b'Z': 'ReadyForQuery',
    b'T': 'RowDescription',   b'D': 'DataRow',          b'C': 'CommandComplete',
    b'E': 'ErrorResponse',    b'X': 'Terminate',        b'N': 'NoticeResponse / SSL-No',
    b'B': 'Bind',             b'P': 'Parse',            b'1': 'ParseComplete',
}


def ver(pkt):
    if not pkt.haslayer(Raw) or not pkt.haslayer(TCP):
        return
    raw = bytes(pkt[Raw].load)
    if not raw:
        return
    tcp = pkt[TCP]
    direccion = "C -> S" if tcp.dport == PG_PORT else "S -> C"
    tipo = raw[:1]
    nombre = TIPOS.get(tipo, "(continuacion / handshake / sin tipo)")
    # Vista previa imprimible del payload
    vista = raw[:48]
    print(f"[{direccion}] tipo={tipo!r:6} {nombre:22} len={len(raw):4}  {vista!r}")


if __name__ == "__main__":
    print("== Interceptando trafico PostgreSQL en el puerto 5432 (Ctrl+C para salir) ==")
    sniff(filter=f"tcp port {PG_PORT}", prn=ver, store=False)
