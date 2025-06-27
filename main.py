import udp_server

def echo_upper_handler(address: tuple, data: bytes) -> None:
    print("Echo from", address, ":", data.decode('utf-8', errors='ignore').upper())

server = udp_server.UDPServer(host="127.0.0.1", port=9999, buffer_size=1024, handler=echo_upper_handler)

try:
    server.serve()
except KeyboardInterrupt:
    print("Server stopped by user.")
