import socket
import struct
import random
import time
import sys

from socketUDP import SocketUDP
from slidingWindowCC import SlidingWindowCC
from CongestionControl import CongestionControl

HEADER_FORMAT = "!II???"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
MAX_DATA_SIZE = 16
UDP_BUFFER_SIZE = HEADER_SIZE + MAX_DATA_SIZE


class SocketTCP:
    debug = False
    loss_rate = 0.0

    def __init__(self):
        self.socket = SocketUDP()
        self.address = None
        self.dest_address = None
        self.seq = 0
        self.ack = 0
        self.timeout = 0.5
        self.recv_buffer = bytearray()
        self.remaining_bytes = 0
        self.buffered_packet = None
        self.is_connected = False
        self.is_closed = False

        self.congestion_control_on = False
        self.congestion_controler = CongestionControl(8)
        self.congestion_controler = CongestionControl(8)
        self.number_of_sent_segments = 0

    def set_congestion_control(self, is_on: bool):
        self.congestion_control_on = is_on

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

    def _safe_stop_timer(self, index=0):
        try:
            self.socket.stop_timer(index)
        except AttributeError:
            pass

    def _sendto(self, data, addr, timer_index=0):
        is_lost = False
        if SocketTCP.loss_rate > 0.0 and random.random() < SocketTCP.loss_rate:
            if SocketTCP.debug:
                print(f"[DEBUG LOSS] Paquete simulado como perdido hacia {addr}", file=sys.stderr)
            is_lost = True
        self.number_of_sent_segments += 1
        try:
            if is_lost:
                self.socket.sendto(data, ("127.0.0.1", 65530), timer_index=timer_index)
            else:
                self.socket.sendto(data, addr, timer_index=timer_index)
        except RuntimeError as e:
            if "threads can only be started once" in str(e):
                pass
            else:
                raise

    def bind(self, address):
        self.socket.bind(address)
        self.address = self.socket.socket_udp.getsockname()

    def connect(self, address):
        self.dest_address = address
        if self.address is None:
            self.socket.bind(('', 0))
            self.address = self.socket.socket_udp.getsockname()

        self.seq = random.randint(0, 100)
        self.socket.settimeout(self.timeout)
        self.socket.set_timer_list_length(1)

        # 1. Enviar SYN
        syn_seg = self.create_segment({
            'seq': self.seq,
            'ack_num': 0,
            'syn': True,
            'ack': False,
            'fin': False,
            'data': b''
        })

        # 2. Recibir SYN-ACK
        while True:
            self._sendto(syn_seg, self.dest_address, timer_index=0)
            try:
                data, sender_addr = self.socket.recvfrom(UDP_BUFFER_SIZE)
                self._safe_stop_timer(0)
                seg = self.parse_segment(data)
                if seg['syn'] and seg['ack'] and seg['ack_num'] == self.seq + 1:
                    self.dest_address = sender_addr
                    self.ack = seg['seq'] + 1
                    self.seq += 1
                    break
            except TimeoutError:
                self._safe_stop_timer(0)
                if SocketTCP.debug:
                    print("[DEBUG] Timeout en connect esperando SYN-ACK, retransmitiendo SYN...", file=sys.stderr)
                continue

        # 3. Enviar ACK final
        ack_seg = self.create_segment({
            'seq': self.seq,
            'ack_num': self.ack,
            'syn': False,
            'ack': True,
            'fin': False,
            'data': b''
        })
        self._sendto(ack_seg, self.dest_address)
        self.is_connected = True

    def accept(self):
        self.socket.settimeout(-1.0)
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
        new_socket.socket.settimeout(new_socket.timeout)
        new_socket.socket.set_timer_list_length(1)

        # Enviar SYN-ACK desde el nuevo socket
        syn_ack_seg = new_socket.create_segment({
            'seq': new_socket.seq,
            'ack_num': new_socket.ack,
            'syn': True,
            'ack': True,
            'fin': False,
            'data': b''
        })

        # 3. Recibir ACK final
        while True:
            new_socket._sendto(syn_ack_seg, client_addr, timer_index=0)
            try:
                ack_data, sender_addr = new_socket.socket.recvfrom(UDP_BUFFER_SIZE)
                new_socket._safe_stop_timer(0)
                ack_seg = new_socket.parse_segment(ack_data)

                # Caso normal: Recibe ACK final
                if ack_seg['ack'] and not ack_seg['syn'] and ack_seg['ack_num'] == new_socket.seq + 1:
                    new_socket.dest_address = sender_addr
                    new_socket.seq += 1
                    new_socket.is_connected = True
                    break

                # Caso borde: El último ACK se perdió pero el cliente ya pasó a enviar datos
                if not ack_seg['syn'] and not ack_seg['ack'] and not ack_seg['fin']:
                    if SocketTCP.debug:
                        print("[DEBUG] Caso borde: Recibidos datos durante accept.", file=sys.stderr)
                    new_socket.buffered_packet = ack_data
                    new_socket.dest_address = sender_addr
                    new_socket.seq += 1
                    new_socket.is_connected = True
                    break

            except TimeoutError:
                new_socket._safe_stop_timer(0)
                if SocketTCP.debug:
                    print("[DEBUG] Timeout en accept esperando ACK final, retransmitiendo SYN-ACK...", file=sys.stderr)
                continue

        return new_socket, new_socket.address

    def _send_stop_and_wait(self, data):
        packet = self.create_segment({
            'seq': self.seq,
            'ack_num': 0,
            'syn': False,
            'ack': False,
            'fin': False,
            'data': data
        })
        expected_ack = self.seq + len(data)
        self.socket.settimeout(self.timeout)
        self.socket.set_timer_list_length(1)

        while True:
            try:
                self._sendto(packet, self.dest_address, timer_index=0)
                ack_data, sender_addr = self.socket.recvfrom(UDP_BUFFER_SIZE)
                self._safe_stop_timer(0)
                ack_seg = self.parse_segment(ack_data)

                # Si recibimos un SYN-ACK duplicado (caso borde de ACK perdido en handshake)
                if ack_seg['syn'] and ack_seg['ack']:
                    if SocketTCP.debug:
                        print("[DEBUG] Recibido SYN-ACK durante send: reenviando ACK del handshake...", file=sys.stderr)
                    handshake_ack = self.create_segment({
                        'seq': self.seq,
                        'ack_num': self.ack,
                        'syn': False,
                        'ack': True,
                        'fin': False,
                        'data': b''
                    })
                    self._sendto(handshake_ack, sender_addr)
                    continue

                if ack_seg['ack'] and ack_seg['ack_num'] == expected_ack:
                    self.seq = expected_ack
                    break
            except TimeoutError:
                self._safe_stop_timer(0)
                if SocketTCP.debug:
                    print(f"[DEBUG] Timeout en send (seq={self.seq}), retransmitiendo paquete...", file=sys.stderr)
                continue

    def send(self, message, mode="stop_and_wait"):
        if mode == "stop_and_wait":
            self.send_using_stop_and_wait(message)
        elif mode == "go_back_n":
            self.send_using_go_back_n(message)

    def recv(self, buff_size, mode="stop_and_wait"):
        if mode == "stop_and_wait":
            return self.recv_using_stop_and_wait(buff_size)
        elif mode == "go_back_n":
            return self.recv_using_go_back_n(buff_size)

    def send_using_stop_and_wait(self, message):
        if isinstance(message, str):
            message = message.encode('utf-8')

        message_length = len(message)

        # 1. Enviar el largo del mensaje en el primer segmento
        length_data = str(message_length).encode('utf-8')
        self._send_stop_and_wait(length_data)

        # 2. Enviar el contenido del mensaje en fragmentos de hasta MAX_DATA_SIZE bytes
        for i in range(0, message_length, MAX_DATA_SIZE):
            chunk = message[i: i + MAX_DATA_SIZE]
            self._send_stop_and_wait(chunk)

    def recv_using_stop_and_wait(self, buff_size):
        self.socket.settimeout(-1.0)

        # 1. Si no hay un mensaje en curso ni datos pendientes en el buffer, esperamos el message_length
        if self.remaining_bytes == 0 and len(self.recv_buffer) == 0:
            while True:
                if self.buffered_packet is not None:
                    data = self.buffered_packet
                    sender_addr = self.dest_address
                    self.buffered_packet = None
                else:
                    data, sender_addr = self.socket.recvfrom(UDP_BUFFER_SIZE)

                self.dest_address = sender_addr
                seg = self.parse_segment(data)
                if not seg['syn'] and not seg['fin'] and not seg['ack']:
                    if seg['seq'] == self.ack:
                        message_length = int(seg['data'].decode('utf-8'))
                        self.remaining_bytes = message_length
                        self.ack += len(seg['data'])
                        ack_seg = self.create_segment({
                            'seq': self.seq,
                            'ack_num': self.ack,
                            'syn': False,
                            'ack': True,
                            'fin': False,
                            'data': b''
                        })
                        self._sendto(ack_seg, self.dest_address)
                        break
                    elif seg['seq'] < self.ack:
                        ack_seg = self.create_segment({
                            'seq': self.seq,
                            'ack_num': self.ack,
                            'syn': False,
                            'ack': True,
                            'fin': False,
                            'data': b''
                        })
                        self._sendto(ack_seg, self.dest_address)

        # 2. Recibir trozos de datos hasta acumular al menos min(remaining_bytes, buff_size)
        target_bytes = min(self.remaining_bytes, buff_size)
        while len(self.recv_buffer) < target_bytes and self.remaining_bytes > len(self.recv_buffer):
            if self.buffered_packet is not None:
                data = self.buffered_packet
                sender_addr = self.dest_address
                self.buffered_packet = None
            else:
                data, sender_addr = self.socket.recvfrom(UDP_BUFFER_SIZE)

            self.dest_address = sender_addr
            seg = self.parse_segment(data)
            if not seg['syn'] and not seg['fin'] and not seg['ack']:
                if seg['seq'] == self.ack:
                    self.recv_buffer.extend(seg['data'])
                    self.ack += len(seg['data'])
                    ack_seg = self.create_segment({
                        'seq': self.seq,
                        'ack_num': self.ack,
                        'syn': False,
                        'ack': True,
                        'fin': False,
                        'data': b''
                    })
                    self._sendto(ack_seg, self.dest_address)
                elif seg['seq'] < self.ack:
                    ack_seg = self.create_segment({
                        'seq': self.seq,
                        'ack_num': self.ack,
                        'syn': False,
                        'ack': True,
                        'fin': False,
                        'data': b''
                    })
                    self._sendto(ack_seg, self.dest_address)

        # 3. Extraer a lo más buff_size bytes del buffer interno
        to_return_len = min(buff_size, len(self.recv_buffer))
        chunk_to_return = bytes(self.recv_buffer[:to_return_len])
        self.recv_buffer = self.recv_buffer[to_return_len:]
        self.remaining_bytes -= to_return_len

        return chunk_to_return

    def send_using_go_back_n(self, message):
        if isinstance(message, str):
            message = message.encode('utf-8')

        mss = 8
        message_length_bytes = str(len(message)).encode('utf-8')

        # 1. Enviar el largo del mensaje en el primer segmento
        data_list = [message_length_bytes]

        # 2. Enviar el contenido del mensaje en fragmentos
        for i in range(0, len(message), mss):
            data_list.append(message[i: i + mss])

        initial_seq = self.seq
        window_size = 8
        if self.congestion_control_on:
            window_size = self.congestion_controler.get_MSS_in_cwnd()

        data_window = SlidingWindowCC(window_size, data_list, initial_seq)

        self.socket.settimeout(self.timeout)
        self.socket.set_timer_list_length(1)

        def send_window_element(index):
            data = data_window.get_data(index)
            if data is not None:
                seq = data_window.get_sequence_number(index)
                seg = self.create_segment({
                    'seq': seq,
                    'ack_num': 0,
                    'syn': False,
                    'ack': False,
                    'fin': False,
                    'data': data
                })
                self._sendto(seg, self.dest_address, timer_index=0)

        for i in range(data_window.window_size):
            send_window_element(i)

        while data_window.get_data(0) is not None:
            try:
                answer, address = self.socket.recvfrom(UDP_BUFFER_SIZE)
                seg = self.parse_segment(answer)

                if seg['ack'] and not seg['syn'] and not seg['fin']:
                    ack_num = seg['ack_num']
                    base_seq = data_window.get_sequence_number(0)

                    if base_seq is not None and ack_num > base_seq:
                        steps_to_move = 0
                        for i in range(data_window.window_size):
                            s = data_window.get_sequence_number(i)
                            if s is not None and s < ack_num:
                                steps_to_move += 1
                            else:
                                break

                        if steps_to_move > 0:
                            old_window_size = data_window.window_size
                            self._safe_stop_timer(0)
                            data_window.move_window(steps_to_move)

                            if self.congestion_control_on:
                                self.congestion_controler.event_ack_received()
                                new_ws = self.congestion_controler.get_MSS_in_cwnd()
                                data_window.update_window_size(new_ws)

                            new_elements_count = steps_to_move + (data_window.window_size - old_window_size)
                            start_index = max(0, data_window.window_size - new_elements_count)

                            sent_valid_data = False
                            for i in range(start_index, data_window.window_size):
                                if data_window.get_data(i) is not None:
                                    send_window_element(i)
                                    sent_valid_data = True

                            if not sent_valid_data and data_window.get_data(0) is not None:
                                send_window_element(0)

            except TimeoutError:
                self._safe_stop_timer(0)
                if self.congestion_control_on:
                    self.congestion_controler.event_timeout()
                    new_ws = self.congestion_controler.get_MSS_in_cwnd()
                    data_window.update_window_size(new_ws)

                for i in range(data_window.window_size):
                    send_window_element(i)

        last_seq = initial_seq
        for d in data_list:
            last_seq += len(d)
        self.seq = last_seq

    def recv_using_go_back_n(self, buff_size):
        return self.recv_using_stop_and_wait(buff_size)

    def close(self):
        self.socket.settimeout(self.timeout)
        self.socket.set_timer_list_length(1)
        fin_seg = self.create_segment({
            'seq': self.seq,
            'ack_num': self.ack,
            'syn': False,
            'ack': False,
            'fin': True,
            'data': b''
        })

        host_b_fin_seq = 0
        received_fin_ack = False
        timeouts_count = 0

        while not received_fin_ack and timeouts_count < 3:
            self._sendto(fin_seg, self.dest_address, timer_index=0)
            try:
                while not received_fin_ack:
                    data, _ = self.socket.recvfrom(UDP_BUFFER_SIZE)
                    seg = self.parse_segment(data)
                    # Recibe FIN y ACK
                    if seg['fin'] and seg['ack']:
                        self._safe_stop_timer(0)
                        received_fin_ack = True
                        host_b_fin_seq = seg['seq']
                        break
            except TimeoutError:
                self._safe_stop_timer(0)
                timeouts_count += 1
                if SocketTCP.debug:
                    print(f"[DEBUG] Timeout {timeouts_count}/3 en close esperando FIN+ACK, reenviando FIN...",
                          file=sys.stderr)
                if timeouts_count >= 3:
                    if SocketTCP.debug:
                        print("[DEBUG] Alcanzado límite de 3 timeouts en close. Cerrando conexión.", file=sys.stderr)
                    break

        if received_fin_ack:
            ack_seg = self.create_segment({
                'seq': self.seq + 1,
                'ack_num': host_b_fin_seq + 1,
                'syn': False,
                'ack': True,
                'fin': False,
                'data': b''
            })
            for i in range(3):
                self._sendto(ack_seg, self.dest_address)
                if i < 2:
                    time.sleep(self.timeout)

        self.is_connected = False
        self.is_closed = True
        self.socket.close()

    def recv_close(self):
        # Esperar FIN
        self.socket.settimeout(-1.0)
        while True:
            data, sender_addr = self.socket.recvfrom(UDP_BUFFER_SIZE)
            self.dest_address = sender_addr
            seg = self.parse_segment(data)
            if seg['fin'] and not seg['ack']:
                host_a_seq = seg['seq']
                self.ack = host_a_seq + 1
                break
            elif not seg['syn'] and not seg['fin'] and not seg['ack']:
                # El cliente sigue retransmitiendo datos porque se perdió el último ACK en send/recv
                ack_seg = self.create_segment({
                    'seq': self.seq,
                    'ack_num': self.ack,
                    'syn': False,
                    'ack': True,
                    'fin': False,
                    'data': b''
                })
                self._sendto(ack_seg, self.dest_address)

        # Enviar FIN y ACK
        fin_ack_seg = self.create_segment({
            'seq': self.seq,
            'ack_num': self.ack,
            'syn': False,
            'ack': True,
            'fin': True,
            'data': b''
        })
        self._sendto(fin_ack_seg, self.dest_address)

        # Esperar el último ACK con hasta 3 timeouts
        self.socket.settimeout(self.timeout)
        self.socket.set_timer_list_length(1)
        timeouts_count = 0

        while timeouts_count < 3:
            try:
                data, _ = self.socket.recvfrom(UDP_BUFFER_SIZE)
                seg = self.parse_segment(data)
                if seg['ack'] and not seg['fin']:
                    # Recibido último ACK
                    self._safe_stop_timer(0)
                    break
                elif seg['fin'] and not seg['ack']:
                    # No le llegó el FIN+ACK, reenviar FIN+ACK
                    self._safe_stop_timer(0)
                    self._sendto(fin_ack_seg, self.dest_address, timer_index=0)
                elif not seg['syn'] and not seg['fin'] and not seg['ack']:
                    # Reenviar ACK de datos por si aún retransmite
                    ack_seg = self.create_segment({
                        'seq': self.seq,
                        'ack_num': self.ack,
                        'syn': False,
                        'ack': True,
                        'fin': False,
                        'data': b''
                    })
                    self._sendto(ack_seg, self.dest_address, timer_index=0)
            except TimeoutError:
                self._safe_stop_timer(0)
                timeouts_count += 1
                if SocketTCP.debug:
                    print(f"[DEBUG] Timeout {timeouts_count}/3 en recv_close esperando último ACK...", file=sys.stderr)
                self._sendto(fin_ack_seg, self.dest_address, timer_index=0)
                if timeouts_count >= 3:
                    if SocketTCP.debug:
                        print("[DEBUG] Alcanzado límite de 3 timeouts en recv_close. Cerrando conexión.",
                              file=sys.stderr)
                    break

        self.is_connected = False
        self.is_closed = True
        self.socket.close()