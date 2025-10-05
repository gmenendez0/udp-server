import os

class FileService:
    def get_file_size(self, filename) -> str | None:
        """Devuelve el tamaño del archivo formateado en bytes"""
        if not os.path.isfile(filename):
            return None
        file_size = os.path.getsize(filename)
        return self.format_file_size(file_size)

    def format_file_size(size_in_bytes) -> str:
        """Formatea el tamaño del archivo dado en bytes a una cadena legible"""
        size = size_in_bytes
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} PB"

    def get_bytes_from_file(filename, offset, bytes_amount) -> bytes:
        """Lee una cantidad específica de bytes desde un archivo comenzando en un offset dado
            sin incluir el ultimo byte del offset"""
        with open(filename, 'rb') as file:
            file.seek(offset + 1)
            return file.read(bytes_amount)

    def append_bytes_to_file(filename, bytes) -> None:
        """Añade bytes al final de un archivo"""
        with open(filename, 'ab') as file:
            file.write(bytes)