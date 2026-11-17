import sys
import socket
import struct
import ipaddress
import itertools

ciclos_por_area = {}


def parse_packet(IP_packet: bytes) -> dict:
    if len(IP_packet) < 7:
        raise ValueError(f"Paquete IP inválido: se esperaban al menos 7 bytes, se recibieron {len(IP_packet)}")
    raw_ip, port, ttl = struct.unpack("!4sHB", IP_packet[:7])
    return {
        "ip": socket.inet_ntoa(raw_ip),
        "puerto": port,
        "ttl": ttl,
        "mensaje": IP_packet[7:]
    }


def create_packet(parsed_IP_packet: dict) -> bytes:
    ip_bytes = socket.inet_aton(parsed_IP_packet["ip"])
    msg = parsed_IP_packet["mensaje"]
    if isinstance(msg, str):
        msg = msg.encode("utf-8")

    header = struct.pack(
        "!4sHB",
        ip_bytes,
        int(parsed_IP_packet["puerto"]),
        int(parsed_IP_packet["ttl"])
    )
    return header + msg


def check_routes(routes_file_name: str, destination_address: tuple):
    dest_ip, dest_port = destination_address
    rutas_area = []
    area_clave = None

    with open(routes_file_name, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split()
            if len(parts) != 5:
                continue

            cidr, p_ini, p_fin, next_ip, next_port = parts
            p_ini, p_fin, next_port = int(p_ini), int(p_fin), int(next_port)

            if ipaddress.ip_address(dest_ip) in ipaddress.ip_network(cidr, strict=False) and (p_ini <= dest_port <= p_fin):
                if area_clave is None:
                    area_clave = (cidr, p_ini, p_fin)
                if (cidr, p_ini, p_fin) == area_clave:
                    rutas_area.append((next_ip, next_port))

    if not rutas_area:
        return None

    clave_ciclo = (routes_file_name,) + area_clave
    if clave_ciclo not in ciclos_por_area:
        ciclos_por_area[clave_ciclo] = itertools.cycle(rutas_area)

    return next(ciclos_por_area[clave_ciclo])


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Uso: python3 router.py router_IP router_puerto router_rutas.txt")
        sys.exit(1)

    router_ip = sys.argv[1]
    router_puerto = int(sys.argv[2])
    archivo_rutas = sys.argv[3]
    mi_direccion = (router_ip, router_puerto)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(mi_direccion)

    while True:
        paquete_ip, _ = sock.recvfrom(4096)
        try:
            pkt = parse_packet(paquete_ip)
        except ValueError as err:
            print(err)
            continue
        destino = (pkt["ip"], pkt["puerto"])

        if pkt["ttl"] <= 0:
            print(f"Se recibió paquete {paquete_ip} con TTL 0")
            continue

        if destino == mi_direccion:
            print(pkt["mensaje"].decode("utf-8", errors="replace"))
        else:
            next_hop = check_routes(archivo_rutas, destino)
            if next_hop is None:
                print(f"No hay rutas hacia {destino} para paquete {paquete_ip}")
            else:
                pkt["ttl"] -= 1
                reenvio = create_packet(pkt)
                print(
                    f"redirigiendo paquete {paquete_ip} con destino final {destino} "
                    f"desde {mi_direccion} hacia {next_hop}"
                )
                sock.sendto(reenvio, next_hop)