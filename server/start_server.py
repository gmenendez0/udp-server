from . import udp_server
import argparse
from protocol.rdt.rdt_server_handler import create_rdt_server_handler

def server_handler(data: bytes) -> bytes:
    """Handler principal que delega al RDT handler"""
    # Por ahora, usar una dirección simulada
    # 
    address = ("127.0.0.1", 12345)

    # Delegar al RDT handler
    rdt_handler = create_rdt_server_handler()

    print(f"[RDT] Recibido paquete de {address}: {data}")

    response = rdt_handler.handle_datagram(address, data)
    
    if response:
        return response
    else:
        # Si no hay respuesta del RDT handler, devolver echo como fallback
        return b"Echo: " + data.upper()

def parse_args():
    parser = argparse.ArgumentParser(prog="start-server", description="File transfer UDP server")

    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument("-v", "--verbose", action="store_true",
                           help="increase output verbosity")
    verbosity.add_argument("-q", "--quiet", action="store_true",
                           help="decrease output verbosity")

    parser.add_argument("-H", "--host", default="127.0.0.1",
                        help="service IP address")
    parser.add_argument("-p", "--port", type=int, default=9999,
                        help="service port")
    parser.add_argument("-s", "--storage", default="./storage",
                        help="storage directory path")

    return parser.parse_args()

def main():
    args = parse_args()

    if args.verbose:
        print(f"[INFO] Iniciando servidor en {args.host}:{args.port}")
    elif args.quiet:
        pass  # no mostrar nada
    else:
        print(f"Servidor escuchando en {args.host}:{args.port}")

    server = udp_server.UDPServer(host=args.host, port=args.port, buffer_size=1024, handler=server_handler)

    try:
        server.serve()
    except KeyboardInterrupt:
        print("Server stopped by user.")

if __name__ == "__main__":
    main()
