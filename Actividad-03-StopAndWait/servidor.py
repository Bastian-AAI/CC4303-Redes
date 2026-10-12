import sys
from SocketTCP import SocketTCP

host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000

server = SocketTCP()
server.bind((host, port))
conn, _ = server.accept()

# Recibir e imprimir datos en trozos de 16 bytes
sys.stdout.buffer.write(conn.recv(16))
while conn.remaining_bytes > 0:
    sys.stdout.buffer.write(conn.recv(16))
sys.stdout.buffer.flush()

conn.recv_close()
server.socket.close()
