import asyncio
from typing import Callable
from server_helpers import get_udp_socket

class AsyncUDPServer:
    def __init__(self, host: str, port: int, buffer_size: int, handler: Callable[[bytes], bytes]):
        self._host          = host
        self._port          = port
        self._handler       = handler
        self._buffer_size   = buffer_size
        self._skt           = None
        self._tasks         = set()

    async def serve(self) -> None:
        self._skt = get_udp_socket(self._host, self._port)
        self._skt.setblocking(False)
        print(f"UDP server listening on {self._host}:{self._port}")
        loop = asyncio.get_running_loop()

        try:
            while True:
                data, address = await loop.sock_recvfrom(self._skt, self._buffer_size)
                task = asyncio.create_task(self._process_request(data, address))
                self._tasks.add(task)
                task.add_done_callback(self._handle_task_ending)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            await self._shutdown()

    async def _process_request(self, data: bytes, address: tuple) -> None:
        print(f"Received {len(data)} bytes from {address}: {data.decode('utf-8', errors='ignore')}")
        response = self._handler(data)
        await asyncio.get_running_loop().sock_sendto(self._skt, response, address)

    def _handle_task_ending(self, task: asyncio.Task) -> None:
        self._tasks.discard(task)
        if task.exception():
            print(f"Task error: {task.exception()}")

    async def _shutdown(self) -> None:
        for task in self._tasks:
            task.cancel()

        await asyncio.gather(*self._tasks, return_exceptions=True)
        if self._skt:
            self._skt.close()

        print("Server shutdown complete.")