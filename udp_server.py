import asyncio
from typing import Callable
from server_helpers import get_udp_socket

class AsyncUDPServer:
    def __init__(self, host: str, port: int, buffer_size: int, handler: Callable[[bytes], bytes]):
        self._host              = host
        self._port              = port
        self._handler           = handler
        self._recv_buffer_size  = buffer_size
        self._skt               = None

    async def serve(self) -> None:
        self._skt = get_udp_socket(self._host, self._port)
        self._skt.setblocking(False)
        loop = asyncio.get_running_loop()

        print(f"UDP server listening on {self._host}:{self._port}")
        try:
            async with asyncio.TaskGroup() as tg:
                while True:
                    data, address = await loop.sock_recvfrom(self._skt, self._recv_buffer_size)
                    tg.create_task(self._process_request(data, address))
        finally:
            await self._shutdown()

    async def _process_request(self, data: bytes, address: tuple) -> None:
        try:
            print(f"Received {len(data)} bytes from {address}: {data.decode('utf-8', errors='ignore')}")
            response = self._handler(data)
            await asyncio.get_running_loop().sock_sendto(self._skt, response, address)
        except Exception as e:
            print(f"Error processing request from {address}: {e}")

    async def _shutdown(self) -> None:
        if self._skt:
            self._skt.close()

        print("Server shutdown complete.")