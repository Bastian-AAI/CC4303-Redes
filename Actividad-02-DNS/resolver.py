import socket
from dnslib import DNSRecord
from dnslib.dns import CLASS, QTYPE
import dnslib

IP_VM = "0.0.0.0"
PORT = 8000
BUFFER_SIZE = 4096

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

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((IP_VM, PORT))
    print(f"-> Resolver DNS escuchando en {IP_VM}:{PORT}")
    
    while True:
        data, addr = sock.recvfrom(BUFFER_SIZE)
        print(f"-> Mensaje recibido desde {addr}")
        print(f"-> Mensaje: {data}")
        info = parse_dns_message(data)
        print(f"-> Mensaje parseado: {info}")

if __name__ == "__main__":
    main()
