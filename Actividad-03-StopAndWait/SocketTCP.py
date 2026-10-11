import socket
import struct
import random

HEADER_FORMAT = "!II???"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
MAX_DATA_SIZE = 16
UDP_BUFFER_SIZE = HEADER_SIZE + MAX_DATA_SIZE

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

    @staticmethod
    def create_segment(segment):
        seq = segment.get('seq', 0)
        ack_num = segment.get('ack_num', 0)
        syn = segment.get('syn', False)
        ack = segment.get('ack', False)
        fin = segment.get('fin', False)
        data = segment.get('data', b'')
        if isinstance(data, str):
            data = data.encode('utf-8')

        header = struct.pack(HEADER_FORMAT, seq, ack_num, syn, ack, fin)
        return header + data

    @staticmethod
    def parse_segment(segment_bytes):
        header = segment_bytes[:HEADER_SIZE]
        data = segment_bytes[HEADER_SIZE:]
        seq, ack_num, syn, ack, fin = struct.unpack(HEADER_FORMAT, header)
        return {
            'seq': seq,
            'ack_num': ack_num,
            'syn': syn,
            'ack': ack,
            'fin': fin,
            'data': data
        }

    def bind(self, address):
        self.socket.bind(address)
        self.address = self.socket.getsockname()

    def connect(self, address):
        self.dest_address = address
        if self.address is None:
            self.socket.bind(('', 0))
            self.address = self.socket.getsockname()

        self.seq = random.randint(0, 100)

        # 1. Enviar SYN
        syn_seg = self.create_segment({
            'seq': self.seq,
            'ack_num': 0,
            'syn': True,
            'ack': False,
            'fin': False,
            'data': b''
        })
        self.socket.sendto(syn_seg, self.dest_address)

        # 2. Recibir SYN-ACK
        while True:
            data, sender_addr = self.socket.recvfrom(UDP_BUFFER_SIZE)
            seg = self.parse_segment(data)
            if seg['syn'] and seg['ack'] and seg['ack_num'] == self.seq + 1:
                self.dest_address = sender_addr
                self.ack = seg['seq'] + 1
                self.seq += 1
                break

        # 3. Enviar ACK final
        ack_seg = self.create_segment({
            'seq': self.seq,
            'ack_num': self.ack,
            'syn': False,
            'ack': True,
            'fin': False,
            'data': b''
        })
        self.socket.sendto(ack_seg, self.dest_address)
        self.is_connected = True

    def accept(self):
        # 1. Recibir SYN
        while True:
            data, client_addr = self.socket.recvfrom(UDP_BUFFER_SIZE)
            seg = self.parse_segment(data)
            if seg['syn'] and not seg['ack']:
                client_seq = seg['seq']
                break

        # 2. Crear nuevo socket con dirección distinta
        new_socket = SocketTCP()
        bind_host = self.address[0] if self.address else 'localhost'
        new_socket.bind((bind_host, 0))
        new_socket.dest_address = client_addr
        new_socket.ack = client_seq + 1
        new_socket.seq = random.randint(0, 100)

        # Enviar SYN-ACK desde el nuevo socket
        syn_ack_seg = new_socket.create_segment({
            'seq': new_socket.seq,
            'ack_num': new_socket.ack,
            'syn': True,
            'ack': True,
            'fin': False,
            'data': b''
        })
        new_socket.socket.sendto(syn_ack_seg, client_addr)

        # 3. Recibir ACK final
        while True:
            ack_data, _ = new_socket.socket.recvfrom(UDP_BUFFER_SIZE)
            ack_seg = new_socket.parse_segment(ack_data)
            if ack_seg['ack'] and not ack_seg['syn'] and ack_seg['ack_num'] == new_socket.seq + 1:
                new_socket.seq += 1
                new_socket.is_connected = True
                break

        return new_socket, new_socket.address
