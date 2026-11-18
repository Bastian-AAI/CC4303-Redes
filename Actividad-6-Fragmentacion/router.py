import sys
import socket
import struct
import ipaddress
import itertools

ciclos_por_area = {}
buffer_fragmentos = {}


def parse_packet(IP_packet: bytes) -> dict:
    raw_ip, port, ttl, pkt_id, offset, tamano, flag = struct.unpack("!4sHBHHIB", IP_packet[:16])
    return {
        "ip": socket.inet_ntoa(raw_ip),
        "puerto": port,
        "ttl": ttl,
        "id": pkt_id,
        "offset": offset,
        "tamano": tamano,
        "flag": flag,
        "mensaje": IP_packet[16:]
    }


def create_packet(parsed_IP_packet: dict) -> bytes:
    ip_bytes = socket.inet_aton(parsed_IP_packet["ip"])
    msg = parsed_IP_packet["mensaje"]
    if isinstance(msg, str):
        msg = msg.encode("utf-8")

    tamano = parsed_IP_packet.get("tamano", len(msg))
    header = struct.pack(
        "!4sHBHHIB",
        ip_bytes,
        int(parsed_IP_packet["puerto"]),
        int(parsed_IP_packet["ttl"]),
        int(parsed_IP_packet.get("id", 0)),
        int(parsed_IP_packet.get("offset", 0)),
        int(tamano),
        int(parsed_IP_packet.get("flag", 0))
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
            if len(parts) != 6:
                continue

            cidr, p_ini, p_fin, next_ip, next_port, mtu = parts
            p_ini, p_fin, next_port, mtu = int(p_ini), int(p_fin), int(next_port), int(mtu)

            if ipaddress.ip_address(dest_ip) in ipaddress.ip_network(cidr, strict=False) and (p_ini <= dest_port <= p_fin):
                if area_clave is None:
                    area_clave = (cidr, p_ini, p_fin)
                if (cidr, p_ini, p_fin) == area_clave:
                    rutas_area.append(((next_ip, next_port), mtu))

    if not rutas_area:
        return None

    if area_clave not in ciclos_por_area:
        ciclos_por_area[area_clave] = itertools.cycle(rutas_area)

    return next(ciclos_por_area[area_clave])


def fragment_IP_packet(IP_packet: bytes, MTU: int) -> list:
    if len(IP_packet) <= MTU:
        return [IP_packet]

    pkt = parse_packet(IP_packet)
    datos = pkt["mensaje"]
    max_datos = MTU - 16
    if max_datos <= 0:
        raise ValueError(f"MTU ({MTU}) debe ser mayor que el tamaño del header (16 bytes)")
    fragmentos = []
    desplazamiento = 0

    while desplazamiento < len(datos):
        trozo = datos[desplazamiento:desplazamiento + max_datos]
        es_ultimo = (desplazamiento + len(trozo)) >= len(datos)
        nuevo_flag = pkt["flag"] if es_ultimo else 1

        fragmentos.append(create_packet({
            "ip": pkt["ip"],
            "puerto": pkt["puerto"],
            "ttl": pkt["ttl"],
            "id": pkt["id"],
            "offset": pkt["offset"] + desplazamiento,
            "tamano": len(trozo),
            "flag": nuevo_flag,
            "mensaje": trozo
        }))
        desplazamiento += len(trozo)

    return fragmentos


def reassemble_IP_packet(fragment_list: list):
    if not fragment_list:
        return None

    fragmentos = [parse_packet(f) for f in fragment_list]
    fragmentos.sort(key=lambda x: x["offset"])

    if fragmentos[0]["offset"] != 0 or fragmentos[-1]["flag"] != 0:
        return None

    offset_esperado = 0
    datos_unidos = b""
    vistos = set()

    for frag in fragmentos:
        clave = (frag["offset"], frag["tamano"])
        if clave in vistos:
            continue
        if frag["offset"] != offset_esperado:
            return None
        vistos.add(clave)
        datos_unidos += frag["mensaje"]
        offset_esperado += frag["tamano"]

    primero = fragmentos[0]
    return create_packet({
        "ip": primero["ip"],
        "puerto": primero["puerto"],
        "ttl": primero["ttl"],
        "id": primero["id"],
        "offset": 0,
        "tamano": len(datos_unidos),
        "flag": 0,
        "mensaje": datos_unidos
    })


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
        pkt = parse_packet(paquete_ip)
        destino = (pkt["ip"], pkt["puerto"])

        if pkt["ttl"] <= 0:
            print(f"Se recibió paquete {paquete_ip} con TTL 0")
            continue

        if destino == mi_direccion:
            pkt_id = pkt["id"]
            if pkt_id not in buffer_fragmentos:
                buffer_fragmentos[pkt_id] = []
            buffer_fragmentos[pkt_id].append(paquete_ip)

            paquete_completo = reassemble_IP_packet(buffer_fragmentos[pkt_id])
            if paquete_completo is not None:
                del buffer_fragmentos[pkt_id]
                pkt_final = parse_packet(paquete_completo)
                print(pkt_final["mensaje"].decode("utf-8"))
        else:
            resultado = check_routes(archivo_rutas, destino)
            if resultado is None:
                print(f"No hay rutas hacia {destino} para paquete {paquete_ip}")
            else:
                next_hop, mtu = resultado
                pkt["ttl"] -= 1
                reenvio = create_packet(pkt)
                lista_fragmentos = fragment_IP_packet(reenvio, mtu)
                for frag in lista_fragmentos:
                    print(
                        f"redirigiendo paquete {frag} con destino final {destino} "
                        f"desde {mi_direccion} hacia {next_hop}"
                    )
                    sock.sendto(frag, next_hop)