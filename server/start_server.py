from . import rdt_server
import argparse
from server.rdt_connection import MemoryRdtConnectionRepository

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

    # Crear repositorio de conexiones
    conn_repo = MemoryRdtConnectionRepository()
    
    # Crear servidor RDT directamente
    server = rdt_server.RDTServer(
        host=args.host, 
        port=args.port, 
        buffer_size=2048,
        conn_repo=conn_repo
    )

    try:
        server.serve()
    except KeyboardInterrupt:
        print("Server stopped by user.")

if __name__ == "__main__":
    main()
