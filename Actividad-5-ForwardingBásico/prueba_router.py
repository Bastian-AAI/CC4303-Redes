import sys
import socket
from router import create_packet


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print('Uso: python3 prueba_router.py "IP;puerto;TTL" IP_router_inicial puerto_router_inicial')
        sys.exit(1)

    header_parts = sys.argv[1].split(";")
    if len(header_parts) != 3:
        print('Formato de headers inválido. Use "IP;puerto;TTL" (ej: "127.0.0.1;8885;10")')
        sys.exit(1)

    ip_final = header_parts[0]
    puerto_final = int(header_parts[1])
    ttl = int(header_parts[2])
    ip_inicial = sys.argv[2]
    puerto_inicial = int(sys.argv[3])

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        for linea in sys.stdin:
            mensaje = linea.rstrip("\r\n")
            paquete = create_packet({
                "ip": ip_final,
                "puerto": puerto_final,
                "ttl": ttl,
                "mensaje": mensaje
            })
            sock.sendto(paquete, (ip_inicial, puerto_inicial))
    finally:
        sock.close()
