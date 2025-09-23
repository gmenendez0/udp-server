import udp_server

def echo_upper_handler(data: bytes) -> bytes:
    return b"Echo: " + data.upper()

server = udp_server.UDPServer(host="127.0.0.1", port=9999, buffer_size=1024, handler=echo_upper_handler)

try:
    server.serve()
except KeyboardInterrupt:
    print("Server stopped by user.")

