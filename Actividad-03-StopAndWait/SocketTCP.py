import socket
import struct

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