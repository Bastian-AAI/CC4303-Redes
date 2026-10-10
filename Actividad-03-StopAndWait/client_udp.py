import socket

SERVER_IP = "localhost"
SERVER_PORT = 8000
BUFFER_SIZE = 16

def main():
    file_path = input("Ingrese la ruta del archivo a enviar: ")
    with open(file_path, "rb") as f:
        content = f.read()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    for i in range(0, len(content), BUFFER_SIZE):
        chunk = content[i : i + BUFFER_SIZE]
        sock.sendto(chunk, (SERVER_IP, SERVER_PORT))

    sock.close()

if __name__ == "__main__":
    main()
