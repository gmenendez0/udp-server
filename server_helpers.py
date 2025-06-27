import socket

def get_udp_socket(host: str = "127.0.0.1", port: int = 9999) -> socket.socket:
    return get_socket(socket.SOCK_DGRAM, host, port)

def get_socket(kind: int, host: str, port: int) -> socket.socket:
    if kind != socket.SOCK_DGRAM and kind != socket.SOCK_STREAM:
        raise ValueError("Invalid socket kind. Use socket.SOCK_DGRAM or socket.SOCK_STREAM.")

    skt = socket.socket(socket.AF_INET, kind)
    skt.bind((host, port))

    return skt