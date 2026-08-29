import socket

IP_VM = "0.0.0.0"
PORT = 8000
BUFFER_SIZE = 4096

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((IP_VM, PORT))
    print(f"-> Resolver DNS escuchando en {IP_VM}:{PORT}")
    
    while True:
        data, addr = sock.recvfrom(BUFFER_SIZE)
        print(f"-> Mensaje recibido desde {addr}")
        print(data)

if __name__ == "__main__":
    main()
