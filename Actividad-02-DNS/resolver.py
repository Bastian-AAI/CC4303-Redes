import socket
from dnslib import DNSRecord
from dnslib.dns import CLASS, QTYPE
import dnslib

IP_VM = "0.0.0.0"
PORT = 8000
BUFFER_SIZE = 4096
ROOT_IP = "198.41.0.4"

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

def resolver(mensaje_consulta: bytes, ip_addr: str = ROOT_IP) -> bytes:
    # a
    reply_bytes = send_query(mensaje_consulta, ip_addr)
    reply = parse_dns_message(reply_bytes)

    # b
    if any(rr.rtype == QTYPE.A for rr in reply["answers"]):
        return reply_bytes

    # c
    if reply["authority"]:
        aditional_ip = extract_a_ip(reply["additional"])
        if aditional_ip:
            return resolver(mensaje_consulta, aditional_ip)
        else:
            ns_name = extract_ns_name(reply["authority"])
            if ns_name:
                ns_query = DNSRecord.question(ns_name).pack()
                ns_reply_bytes = send_query(ns_query, ROOT_IP)
                ns_reply = parse_dns_message(ns_reply_bytes)
                ns_ip = extract_a_ip(ns_reply["answers"])
                if ns_ip:
                    return resolver(mensaje_consulta, ns_ip)

    #d
    return reply_bytes

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((IP_VM, PORT))
    print(f"-> Resolver DNS escuchando en {IP_VM}:{PORT}")
    
    while True:
        data, addr = sock.recvfrom(BUFFER_SIZE)
        info = parse_dns_message(data)
        print(f"-> Consulta recibida de {addr}: {info['qname']}")
        response = resolver(data)
        sock.sendto(response, addr)
        print(f"-> Respuesta enviada a {addr}: {info['qname']}")

if __name__ == "__main__":
    main()
