import sys
import socket
import random
from router import create_packet

if __name__ == "__main__":
    if len(sys.argv) not in (7, 8):
        print('Uso: python3 sender.py <IP_final> <puerto_final> <TTL> "<mensaje>" <IP_envio> <puerto_envio> [ID]')
        sys.exit(1)

    ip_final = sys.argv[1]
    puerto_final = int(sys.argv[2])
    ttl = int(sys.argv[3])
    mensaje = sys.argv[4]
    ip_envio = sys.argv[5]
    puerto_envio = int(sys.argv[6])
    pkt_id = int(sys.argv[7]) if len(sys.argv) == 8 else random.randint(1, 65535)

    msg_bytes = mensaje.encode("utf-8")
    paquete = create_packet({
        "ip": ip_final,
        "puerto": puerto_final,
        "ttl": ttl,
        "id": pkt_id,
        "offset": 0,
        "tamano": len(msg_bytes),
        "flag": 0,
        "mensaje": msg_bytes
    })

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(paquete, (ip_envio, puerto_envio))
    sock.close()