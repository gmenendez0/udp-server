import os
from typing import List

def get_file_in_chunks(filename, chunk_size=1024) -> List[bytes]:
    """Lee un archivo y lo devuelve en una lista de bytes divididos en chunks de tamaño chunk_size"""
    if not os.path.isfile(filename):
        return []

    chunks = []
    with open(filename, 'rb') as file:
        while True:
            chunk = file.read(chunk_size)
            if not chunk:
                break
            chunks.append(chunk)

    return chunks

def get_file_size_in_bytes(filename) -> int | None:
    """Devuelve el tamaño del archivo en bytes como int"""
    if not os.path.isfile(filename):
        return None
    return os.path.getsize(filename)

def append_bytes_to_file(filename, bytes) -> None:
    """Añade bytes al final de un archivo"""
    print(f"Bytes a añadir: \n")
    print(bytes)
    with open(filename, 'ab') as file:
        file.write(bytes)