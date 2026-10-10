import socket
import sys

SERVER_IP = "localhost"
SERVER_PORT = 8000
BUFFER_SIZE = 16

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((SERVER_IP, SERVER_PORT))
    print(f"Servidor UDP escuchando en {SERVER_IP}:{SERVER_PORT}")

    while True:
        data, _ = sock.recvfrom(BUFFER_SIZE)
        if not data:
            break
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()

if __name__ == "__main__":
    main()
