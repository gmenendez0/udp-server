"""
Manejador simplificado de paquetes RDT.
Maneja la llegada, procesamiento y distribución de paquetes a conexiones.
"""

import threading
from typing import Optional, Tuple
from ..const import unpack_header
from .rdt_connection import RdtConnection, MemoryRdtConnectionRepository

class RdtServerHandler:
    """
    Maneja el procesamiento de paquetes RDT y los distribuye a las conexiones apropiadas.
    Flujo: llegada → conexión → operación específica → respuesta.
    """
    
    def __init__(self):
        self.connection_manager = MemoryRdtConnectionRepository()
    
    def handle_datagram(self, address: Tuple[str, int], data: bytes) -> Optional[bytes]:
        """
        Maneja un datagrama recibido.
        Distribuye el paquete a la conexión apropiada para procesamiento.
        
        Args:
            address: Dirección del cliente (IP, puerto)
            data: Datos del paquete recibido
            
        Returns:
            None (las respuestas se manejan dentro de las conexiones)
        """
        str_address = f"{address[0]}:{address[1]}"

        # 1. Verificar si tengo una conexión con esa dirección
        connection = self.connection_manager.get_connection(str_address)
        
        if connection:
            # 2. Conexión existente - añadir petición a la cola
            connection.add_request(data)
            print(f"[RDT] Petición añadida a conexión existente {str_address}")
        else:
            # 3. Nueva conexión - crear y añadir petición
            connection = RdtConnection(address=str_address)
            connection.add_request(data)
            self.connection_manager.add_connection(str_address, connection)
            print(f"[RDT] Nueva conexión creada para {str_address}")
        
        return None
    
    def shutdown(self):
        """Cierra todas las conexiones activas"""
        print("[RDT] Iniciando shutdown del servidor RDT")
        for address, connection in self.connection_manager.connections.items():
            connection.shutdown()
        self.connection_manager.connections.clear()
        print("[RDT] Shutdown del servidor RDT completado")
