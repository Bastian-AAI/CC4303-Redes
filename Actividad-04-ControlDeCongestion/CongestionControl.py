class CongestionControl:
    def __init__(self, MSS: int):
        # Guardamos el tamaño máximo del segmento
        self.MSS = MSS

        # Inicializamos la ventana de congestión en 1 MSS (como float para mayor precisión)
        self.cwnd = float(1 * self.MSS)

        # El ssthresh se define luego del primer timeout (antes es None)
        self.ssthresh = None

        # Siempre se inicializa el estado como slow start
        self.current_state = "slow start"

    def get_cwnd(self):
        # Retorna el valor cwnd almacenado (tamaño en bytes)
        return self.cwnd

    def get_MSS_in_cwnd(self) -> int:
        # Retorna la cantidad de MSS completos que caben en cwnd
        return int(self.cwnd // self.MSS)

    def event_ack_received(self):
        # Maneja los aumentos de ventana al recibir un ACK
        if self.is_state_slow_start():
            # En slow start aumenta en 1 MSS cada vez que recibe un ACK
            self.cwnd += self.MSS

            # Si cwnd pasa el límite ssthresh, pasamos a congestion avoidance
            if self.ssthresh is not None and self.cwnd >= self.ssthresh:
                self.current_state = "congestion avoidance"

        elif self.is_state_congestion_avoidance():
            # En congestion avoidance (AIMD) aumenta una fracción (MSS/cwnd)
            mss_in_cwnd = self.get_MSS_in_cwnd()
            if mss_in_cwnd > 0:
                self.cwnd += self.MSS / mss_in_cwnd

    def event_timeout(self):
        # Maneja los cambios de estado y ventana cuando ocurre un timeout

        # 1. Seteamos ssthresh a la mitad de la ventana actual (asegurando entero)
        self.ssthresh = int(self.cwnd / 2)

        # 2. Reiniciamos la ventana a 1 MSS
        self.cwnd = float(1 * self.MSS)

        # 3. Volvemos al estado slow start
        self.current_state = "slow start"

    def is_state_slow_start(self) -> bool:
        # Retorna True si estamos en slow start
        return self.current_state == "slow start"

    def is_state_congestion_avoidance(self) -> bool:
        # Retorna True si estamos en congestion avoidance
        return self.current_state == "congestion avoidance"

    def get_ssthresh(self):
        # Retorna el valor de ssthresh almacenado
        return self.ssthresh