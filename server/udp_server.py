import threading
from typing import Callable
from .server_helpers import get_udp_socket

class UDPServer:
    def __init__(self, host: str, port: int, buffer_size: int, handler: Callable[[bytes], bytes]):
        self._host              = host
        self._port              = port
        self._handler           = handler
        self._recv_buffer_size  = buffer_size
        self._skt               = None

    def serve(self) -> None:
        self._skt = get_udp_socket(self._host, self._port)
        self._skt.setblocking(True)

        print(f"UDP server listening on {self._host}:{self._port}")
        try:
            while True:
                data, address = self._skt.recvfrom(self._recv_buffer_size)
                thread = threading.Thread(target=self._process_request, args=(data, address), daemon=True)
                thread.start()
        finally:
            self._shutdown()

    def _process_request(self, data: bytes, address: tuple) -> None:
        try:
            print(f"Received {len(data)} bytes from {address}: {data.decode('utf-8', errors='ignore')}")
            response = self._handler(data)
            self._skt.sendto(response, address)
        except Exception as e:
            print(f"Error processing request from {address}: {e}")

    def _shutdown(self) -> None:
        if self._skt:
            self._skt.close()

        print("Server shutdown complete.")