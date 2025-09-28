from abc import ABC, abstractmethod
from queue import Queue
from server.server_helpers import get_udp_socket
from .rdt_message import RdtRequest, RdtResponse
from typing import Optional

SERVER_SEQ_NUM_START = 0

class RdtConnection:
    def __init__(self, address: str):
        self.address:       str           = address
        self.seq_num:       Optional[int] = None
        self.ref_num:       Optional[int] = None
        self.max_window:    Optional[int] = None
        self.request_queue: Queue[bytes]  = Queue()

    def handle_connection(self) -> None:
        # Escuchamos el canal de recepcion de mensajes de la conexion
        request = self.request_queue.get()
        rdt_request = RdtRequest(address=self.address, request=request)

        # Si es un ACK, ignorar. Nunca deberia llegar un ACK de un cliente que aun no tiene conexion.
        if rdt_request.is_ack():
            print(f"Received ACK for unknown connection from {self.address}. Ignoring.")
            return

        # Actualizamos la conexion con los datos del request
        self.max_window = rdt_request.get_max_window()
        self.ref_num = rdt_request.get_seq_num() + 1
        self.seq_num = SERVER_SEQ_NUM_START

        # Construimos la ACK response
        ack_response = RdtResponse.new_ack_response(self.max_window, self.seq_num, self.ref_num)

        # Abrimos socket para enviar ACK response
        host, port = self.address.split(':')
        socket = get_udp_socket(host, int(port))
        socket.sendto(ack_response.to_bytes(), self.address)

        # Esperamos el siguiente mensaje que deberia ser el segundo ack del handshake. TODO: Deberiamos esperar con un timeout, si hay timeout, retransmitir el primer ack de handshake.
        request = self.request_queue.get()
        rdt_request = RdtRequest(address=self.address, request=request)













class RdtConnectionRepository(ABC):
    @abstractmethod
    def get_connection(self, address: str) -> RdtConnection | None:
        pass

    @abstractmethod
    def remove_connection(self, address: str) -> None:
        pass

    @abstractmethod
    def add_connection(self, address: str, connection: RdtConnection) -> None:
        pass

class MemoryRdtConnectionRepository(RdtConnectionRepository):
    def __init__(self):
        self.connections = {}

    def get_connection(self, address: str) -> RdtConnection | None:
        return self.connections.get(address)

    def add_connection(self, address: str, connection: RdtConnection) -> None:
        if not address in self.connections:
            self.connections[address] = connection

    def remove_connection(self, address: str) -> None:
        if address in self.connections:
            del self.connections[address]