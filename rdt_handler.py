from abc import ABC, abstractmethod
from enum import Enum
from data_handler import DataHandler


# Damos por sentado un formato de, para un cliente, una request y luego una response.
# Es decir, no puede darse el caso de un cliente (ip+port) que manda dos requests sin esperar response entre medio.

# ? Automatic Repeat reQuest Protocols
class ARQProtocol(Enum):
    STOP_AND_WAIT = 1
    GO_BACK_N = 2

class RdtConnection:
    def __init__(self, seq_num: int, ref_num: int, arq_protocol: ARQProtocol):
        self.seq_num        = seq_num
        self.ref_num        = ref_num
        self.arqProtocol    = arq_protocol # Quizas deberia ser una abstraccion?
        self.buffer         = bytearray()

class RdtConnectionRepository(ABC):
    @abstractmethod
    def get_connection(self, address: tuple) -> RdtConnection | None:
        pass

    @abstractmethod
    def remove_connection(self, address: tuple) -> None:
        pass

class MemoryRdtConnectionRepository(RdtConnectionRepository):
    def __init__(self):
        self.connections = {}

    def get_connection(self, address: tuple) -> RdtConnection | None:
        return self.connections.get(address, None)

    def remove_connection(self, address: tuple) -> None:
        if address in self.connections:
            del self.connections[address]

from threading import Lock

CONNECTION_TIMEOUT = 5

class RdtHandler:
    def __init__(self, connections: dict, connections_lock: Lock, connection_timeout: int, data_handler: DataHandler):
        self.connections:           dict        = connections
        self.connections_lock:      Lock        = connections_lock
        self.connection_timeout:    int         = connection_timeout   # in seconds
        self.data_handler:          DataHandler = data_handler

    def handle_datagram(self, address: tuple, data: bytes) -> None:
        pass
        # 1. Check if connection exists for address
        # 2. If not, create new connection and store in connections dict
        # 3. Process data according to ARQ protocol

        # 3A. Envia ACK a cliente.
        # 3B. Chequea en connection.buffer si con el paquete recibido, los bytes ya se pueden subir a la capa de datos
        # 3C. Si se pueden subir, llama a data_handler.handle_data() con los bytes en orden y limpia connection.buffer
        #     Los bytes que devuelva data_handler.handle_data() deben wrappearse en una RDTRequest y enviarse a cliente como response.
        # 3D. Si no se pueden subir, guarda los bytes en connection.buffer y finaliza.