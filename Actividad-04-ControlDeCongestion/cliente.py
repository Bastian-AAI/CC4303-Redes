import sys
from SocketTCP import SocketTCP

host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000

client = SocketTCP()

SocketTCP.loss_rate = 0.2
client.timeout = 0.5
client.set_congestion_control(False)

client.connect((host, port))
client.send(sys.stdin.buffer.read(), mode="go_back_n")
print(f"\n Segmentos enviados a la red: {client.number_of_sent_segments}")
client.close()
