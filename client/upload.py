#!/usr/bin/env python3
"""
Cliente UDP para operación UPLOAD.
Transfiere un archivo del cliente hacia el servidor
"""

import argparse
import os
import sys
import re
from pathlib import Path

def parse_args():
    """Parsea argumentos de línea de comandos"""
    parser = argparse.ArgumentParser(
        prog="upload", 
        description="Upload file to server"
    )

    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument("-v", "--verbose", action="store_true",
                          help="increase output verbosity")
    verbosity.add_argument("-q", "--quiet", action="store_true",
                          help="decrease output verbosity")

    parser.add_argument("-H", "--host", metavar="ADDR", default="127.0.0.1",
                        help="server IP address")
    parser.add_argument("-p", "--port", metavar="PORT", type=int, default=9999,
                        help="server port")
    parser.add_argument("-s", "--src", metavar="FILEPATH", required=True,
                        help="source file path")
    parser.add_argument("-n", "--name", metavar="FILENAME",
                        help="file name")
    parser.add_argument("-r", "--protocol", metavar="protocol",
                        choices=["stop-and-wait", "go-back-n"], 
                        default="stop-and-wait",
                        help="error recovery protocol")

    return parser.parse_args()

def validate_file(filepath: str) -> Path:
    """Valida que el archivo existe y es accesible"""
    file_path = Path(filepath)
    
    if not file_path.exists():
        raise FileNotFoundError(f"El archivo {filepath} no existe")
    
    if not file_path.is_file():
        raise ValueError(f"{filepath} no es un archivo válido")
    
    if not os.access(file_path, os.R_OK):
        raise PermissionError(f"No se puede leer el archivo {filepath}")
    
    # Verificar tamaño máximo (5MB según consigna)
    file_size = file_path.stat().st_size
    max_size = 5 * 1024 * 1024  # 5MB
    if file_size > max_size:
        raise ValueError(f"El archivo {filepath} excede el tamaño máximo de 5MB ({file_size} bytes)")
    
    return file_path

def validate_filename(filename: str, source_file: Path) -> str:
    """
    Valida que `filename` sea un nombre válido de archivo (sin caracteres
    inválidos y no vacío).
    Si no lo es, devuelve el nombre del archivo original `source_file`.
    """
    if not filename:
        return source_file.name

    # No permite caracteres: / \ : * ? " < > | y no debe estar vacío
    invalid_chars = r'[\/\\:\*\?"<>\|]'
    if re.search(invalid_chars, filename) or filename.strip() == "":
        print(f"[WARNING] Nombre inválido '{filename}'. Usando '{source_file.name}' en su lugar.")
        return source_file.name

    return filename


def upload_file(args):
    """Implementa la lógica de upload del archivo"""
    try:
        source_file = validate_file(args.src)
        target_name = validate_filename(args.name, source_file)
                
        if args.verbose:
            print(f"[VERBOSE] Iniciando upload de {source_file}")
            print(f"[VERBOSE] Servidor: {args.host}:{args.port}")
            print(f"[VERBOSE] Archivo destino: {target_name}")
            print(f"[VERBOSE] Protocolo: {args.protocol}")
            print(f"[VERBOSE] Tamaño: {source_file.stat().st_size} bytes")
        elif not args.quiet:
            print(f"Subiendo {source_file.name} a {args.host}:{args.port}")

        # Determinar el tamaño de ventana según el protocolo
        max_window = 1 if args.protocol == "stop-and-wait" else 5
        
        if args.protocol == "stop-and-wait":
            from .stop_and_wait import handle_upload_stop_and_wait
            return handle_upload_stop_and_wait(source_file, args.host, args.port, target_name, max_window)
        elif args.protocol == "go-back-n":
            from .go_back_n import handle_upload_go_back_n
            return handle_upload_go_back_n(source_file, args.host, args.port, target_name, max_window)
        else:
            print(f"Protocolo no soportado: {args.protocol}")
            from .constants import get_error_message, ERR_INVALID_PROTOCOL
            print(f"Código de error: {get_error_message(ERR_INVALID_PROTOCOL)}")
            return False
            
    except Exception as e:
        print(f"Error al subir el archivo: {e}")
        return False

def main():
    """Función principal del cliente upload"""
    args = parse_args()
    success = upload_file(args)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
