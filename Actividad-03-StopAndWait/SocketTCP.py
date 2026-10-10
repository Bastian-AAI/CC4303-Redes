import socket

class SocketTCP:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.address = None
        self.dest_address = None
        self.seq = 0
        self.ack = 0
        self.timeout = 1.0
        self.recv_buffer = bytearray()
        self.remaining_bytes = 0
        self.is_connected = False
        self.is_closed = False
