#!/usr/bin/env python3
"""
Cliente UDP para operación DOWNLOAD
Transfiere un archivo del servidor hacia el cliente
"""

import argparse
import socket
import os
import sys
from pathlib import Path

def parse_args():
    """Parsea argumentos de línea de comandos"""
    parser = argparse.ArgumentParser(
        prog="download", 
        description="Download file from server"
    )

    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument("-v", "--verbose", action="store_true",
                          help="increase output verbosity")
    verbosity.add_argument("-q", "--quiet", action="store_true",
                          help="decrease output verbosity")

    parser.add_argument("-H", "--host", metavar="HOST", default="127.0.0.1",
                        help="server IP address")
    parser.add_argument("-p", "--port", metavar="PORT", type=int, default=9999,
                        help="server port")
    parser.add_argument("-d", "--dst", required=True,
                        help="destination file path")
    parser.add_argument("-n", "--name", required=True,
                        help="file name")
    parser.add_argument("-r", "--protocol", metavar="protocol",
                        choices=["stop-and-wait", "go-back-n"], 
                        default="stop-and-wait",
                        help="error recovery protocol")

    return parser.parse_args()

def validate_destination(dst_path: str) -> Path:
    """Valida que el directorio destino existe y es escribible"""
    dest_path = Path(dst_path)
    
    if dest_path.is_dir():
        if not os.access(dest_path, os.W_OK):
            raise PermissionError(f"No se puede escribir en el directorio {dst_path}")
        return dest_path
    
    parent_dir = dest_path.parent
    if not parent_dir.exists():
        raise FileNotFoundError(f"El directorio {parent_dir} no existe")
    
    if not os.access(parent_dir, os.W_OK):
        raise PermissionError(f"No se puede escribir en el directorio {parent_dir}")
    
    if dest_path.exists():
        if not os.access(dest_path, os.W_OK):
            raise PermissionError(f"No se puede sobreescribir el archivo {dst_path}")
    
    return dest_path


def download_file(args):
    """Implementa la lógica de download del archivo"""
    try:
        destination = validate_destination(args.dst)
        
        if destination.is_dir():
            target_file = destination / args.name
        else:
            target_file = destination
        
        if args.verbose:
            print(f"[VERBOSE] Iniciando download de {args.name}")
            print(f"[VERBOSE] Servidor: {args.host}:{args.port}")
            print(f"[VERBOSE] Archivo destino: {target_file}")
            print(f"[VERBOSE] Protocolo: {args.protocol}")
        elif not args.quiet:
            print(f"Descargando {args.name} desde {args.host}:{args.port}")

        # Determinar el tamaño de ventana según el protocolo
        max_window = 1 if args.protocol == "stop-and-wait" else 5
        
        if args.protocol == "stop-and-wait":
            from .stop_and_wait import handle_download_stop_and_wait
            return handle_download_stop_and_wait(target_file, args.host, args.port, args.name, max_window)
        elif args.protocol == "go-back-n":
            from .go_back_n import handle_download_go_back_n
            return handle_download_go_back_n(target_file, args.host, args.port, args.name, max_window)
        else:
            print(f"Protocolo no soportado: {args.protocol}")
            from .constants import get_error_message, ERR_INVALID_PROTOCOL
            print(f"Código de error: {get_error_message(ERR_INVALID_PROTOCOL)}")
            return False
            
    except (FileNotFoundError, ValueError, PermissionError, socket.error) as e:
        print(f"Error: {e}")
        return False
    except Exception as e:
        print(f"Error inesperado: {e}")
        return False


def main():
    """Función principal del cliente download"""
    args = parse_args() 
    success = download_file(args)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
