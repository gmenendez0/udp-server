import threading
from typing import Callable

from server_helpers import get_udp_socket
from protocol.rdt.rdt_connection import RdtConnectionRepository, RdtConnection

class RDTServer:
    def __init__(self, host: str, port: int, buffer_size: int, handler: Callable[[tuple, bytes], None], conn_repo: RdtConnectionRepository):
        self._host              = host
        self._port              = port
        self._handler           = handler
        self._recv_buffer_size  = buffer_size
        self._skt               = None
        self._conn_repo         = conn_repo

    def serve(self) -> None:
        self._skt = get_udp_socket(self._host, self._port)
        self._skt.setblocking(True)

        print(f"RDT server listening on {self._host}:{self._port}")
        try:
            while True:
                data, address = self._skt.recvfrom(self._recv_buffer_size)
                str_address = f"{address[0]}:{address[1]}"

                connection = self._conn_repo.get_connection(str_address)
                if connection:
                    connection.request_queue.put(data)
                else:
                    connection = RdtConnection(address=str_address)
                    connection.request_queue.put(data)
                    self._conn_repo.add_connection(str_address, connection)
                    thread = threading.Thread(target=connection.handle_connection, args=(), daemon=True)
                    thread.start()
        finally:
            self._shutdown()

    def _shutdown(self) -> None:
        if self._skt:
            self._skt.close()

        print("Server shutdown complete.")