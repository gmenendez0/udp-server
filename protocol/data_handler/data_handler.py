from typing import Dict, Any
import logging

# Configurar logger local para evitar importación circular
logger = logging.getLogger(__name__)

class DataHandler:
    def __init__(self):
        self.operation_count = 0
        # Diccionario para almacenar paquetes por conexión
        self.connection_packets = {}
        self.connection_lock = {}
    
    def handle_data(self, data: bytes) -> bytes:
        logger.info(f"Recibido paquete de datos: {data}")
        return data
        

