import udp_server
import asyncio

def echo_upper_handler(data: bytes) -> bytes:
    return b"Echo: " + data.upper()

server = udp_server.AsyncUDPServer(host="127.0.0.1", port=9999, buffer_size=1024, handler=echo_upper_handler)

try:
    asyncio.run(server.serve())
except KeyboardInterrupt:
    print("Server stopped by user.")

