import socket
from collections import Counter, deque
from dnslib import DNSRecord
from dnslib.dns import CLASS, QTYPE
import dnslib

IP_VM = "0.0.0.0"
PORT = 8000
BUFFER_SIZE = 4096
ROOT_IP = "198.41.0.4"

history = deque(maxlen=10)
dns_cache = {}

def send_query(message: bytes, ip_addr: str) -> bytes:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(message, (ip_addr, 53))
    response, _ = sock.recvfrom(BUFFER_SIZE)
    sock.close()
    return response

def extract_a_ip(rr_list):
    for rr in rr_list:
        if rr.rtype == QTYPE.A:
            return str(rr.rdata)
    return None

def extract_ns_name(rr_list):
    for rr in rr_list:
        if rr.rtype == QTYPE.NS:
            return str(rr.rdata)
    return None

def parse_dns_message(data: bytes):
    record = DNSRecord.parse(data)
    qname = str(record.get_q().get_qname()) if record.get_q() else "N/A"
    return {
        "qname": qname,
        "ancount": record.header.a,
        "nscount": record.header.auth,
        "arcount": record.header.ar,
        "answers": record.rr,
        "authority": record.auth,
        "additional": record.ar,
    }

def resolver(mensaje_consulta: bytes, ip_addr: str = ROOT_IP, ns_name: str = ".", debug: bool = True) -> bytes:
    # debug
    if debug:
        print(f"-> (debug) Consultando '{parse_dns_message(mensaje_consulta)['qname']}' a '{ns_name}' con dirección IP '{ip_addr}'")

    # a
    reply_bytes = send_query(mensaje_consulta, ip_addr)
    reply = parse_dns_message(reply_bytes)

    # b
    if any(rr.rtype == QTYPE.A for rr in reply["answers"]):
        if debug:
            ip_addr = extract_a_ip(reply["answers"])
            print(f"-> (debug) Respuesta encontrada para '{reply['qname']}' en '{ns_name}' con dirección IP '{ip_addr}'")
        return reply_bytes

    # c
    if reply["authority"]:
        ns_name = extract_ns_name(reply["authority"]) or ns_name
        additional_ip = extract_a_ip(reply["additional"])
        if additional_ip:
            return resolver(mensaje_consulta, additional_ip, ns_name, debug)
        else:
            if ns_name:
                ns_query = DNSRecord.question(ns_name).pack()
                ns_reply_bytes = resolver(ns_query, ROOT_IP, ns_name, debug)
                ns_reply = parse_dns_message(ns_reply_bytes)
                ns_ip = extract_a_ip(ns_reply["answers"])
                if ns_ip:
                    return resolver(mensaje_consulta, ns_ip, ns_name, debug)

    #d
    return reply_bytes

def resolver_with_cache(mensaje_consulta: bytes, debug: bool = True) -> bytes:
    qname = parse_dns_message(mensaje_consulta)["qname"]
    query_id = DNSRecord.parse(mensaje_consulta).header.id
    history.append(qname)

    top_3 = Counter(history).most_common(3)
    top_3_names = [name for name, _ in top_3]

    remove = [name for name in dns_cache if name not in top_3_names]
    for name in remove:
        del dns_cache[name]

    if qname in top_3_names and qname in dns_cache:
        if debug:
            print(f"-> (debug) Usando caché para '{qname}'")
        return dns_cache[qname]

    response = resolver(mensaje_consulta, debug=debug)
    if qname in top_3_names:
        dns_cache[qname] = response
        if debug:
            print(f"-> (debug) Guardando en caché '{qname}'")

    return response

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((IP_VM, PORT))
    print(f"-> Resolver DNS escuchando en {IP_VM}:{PORT}")
    
    while True:
        data, addr = sock.recvfrom(BUFFER_SIZE)
        info = parse_dns_message(data)
        print(f"-> Consulta recibida de {addr}: {info['qname']}")
        response = resolver_with_cache(data)

        # Fix: mantener el mismo ID de consulta en la respuesta
        query_id = DNSRecord.parse(data).header.id
        response_record = DNSRecord.parse(response)
        response_record.header.id = query_id
        response = response_record.pack()
        
        sock.sendto(response, addr)
        print(f"-> Respuesta enviada a {addr}: {info['qname']}")

if __name__ == "__main__":
    main()
