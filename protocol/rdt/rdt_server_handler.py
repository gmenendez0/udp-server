"""
Manejador simplificado de paquetes RDT.
Solo maneja la llegada, procesamiento y envío para creación de conexiones.
Devuelve RDTRequest con tipo REQUEST_ACCEPTED.
"""

import threading
from typing import Optional, Tuple
from ..const import unpack_header
from .rdt_connection import RdtConnection, RdtConnectionRepository


# TODO: Manejo de errores, y que tmb el getters 
# TODO: data handler ( bytes -> manager -> response Bytes)

class RdtServerHandler:
    """
    Maneja únicamente el procesamiento de paquetes de control para creación de conexiones.
    Flujo: llegada → procesamiento → envío de RDTRequest con REQUEST_ACCEPTED.
    """
    
    def __init__(self):
        self.connection_manager = RdtConnectionRepository()
    
    def handle_datagram(self, address: Tuple[str, int], data: bytes) -> Optional[bytes]:
        """
        Maneja un datagrama recibido.
        Solo procesa paquetes de control para creación de conexiones.
        Devuelve RDTRequest serializada con tipo REQUEST_ACCEPTED.
        response = data_handler(data)
        send_response(response)
        """
        str_address = f"{address[0]}:{address[1]}"

        #1. Verifico si tengo una conexion con esa direccion, si no la creo 
        #2 luego , envio hacia el handler de datos la info que se encarga de procesarla
        #3 con la respuesta del handler de datos, envio hacia el handler de control la respuesta a la address mediante socket

        
        
       