import socket
from SocketTCP import SocketTCP, MAX_DATA_SIZE

SERVER_IP = "localhost"
SERVER_PORT = 8000

def main():
    file_path = input("Ingrese la ruta del archivo a enviar: ")
    with open(file_path, "rb") as f:
        content = f.read()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    seq = 0
    for i in range(0, len(content), MAX_DATA_SIZE):
        chunk = content[i : i + MAX_DATA_SIZE]
        segment = SocketTCP.create_segment({
            "seq": seq,
            "ack_num": 0,
            "syn": False,
            "ack": False,
            "fin": False,
            "data": chunk
        })
        sock.sendto(segment, (SERVER_IP, SERVER_PORT))
        seq += len(chunk)

    sock.close()

if __name__ == "__main__":
    main()
