from typing import Dict, Any

from protocol.rdt.rdt_connection import logger

class DataHandler:
    def __init__(self):
        self.operation_count = 0
        # Diccionario para almacenar paquetes por conexión
        self.connection_packets = {}
        self.connection_lock = {}
    
    def handle_data(self, data: bytes, context: Dict[str, Any] = None) -> bytes:
        logger.info(f"Recibido paquete de datos: {data}")
        return data
        
