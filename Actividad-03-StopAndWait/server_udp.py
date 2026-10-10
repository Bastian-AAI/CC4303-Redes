import socket
import sys
from SocketTCP import SocketTCP, UDP_BUFFER_SIZE

SERVER_IP = "localhost"
SERVER_PORT = 8000

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((SERVER_IP, SERVER_PORT))
    print(f"Servidor UDP escuchando en {SERVER_IP}:{SERVER_PORT}")

    while True:
        data, _ = sock.recvfrom(UDP_BUFFER_SIZE)
        if not data:
            break
        segment = SocketTCP.parse_segment(data)
        sys.stdout.buffer.write(segment["data"])
        sys.stdout.buffer.flush()

if __name__ == "__main__":
    main()
