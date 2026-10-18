import sys
from SocketTCP import SocketTCP

host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000

client = SocketTCP()
client.connect((host, port))
client.send(sys.stdin.buffer.read(), mode="go_back_n")
client.close()
