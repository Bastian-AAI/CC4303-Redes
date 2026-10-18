import threading
import time
from SocketTCP import SocketTCP

address = ("localhost", 8055)
n = 13
message = b"A" * (2 * n)

def server():
    s = SocketTCP()
    s.bind(address)
    conn, _ = s.accept()
    resultado = conn.recv(n) + conn.recv(n)
    conn.recv_close()
    s.socket.close()

    print("Recibido:", resultado)
    print("Test buffer 2n:", "Passed" if resultado == message else "Failed")

threading.Thread(target=server).start()
time.sleep(0.2)

client = SocketTCP()
client.connect(address)
client.send(message)
client.close()
