"""
Módulo para manejo de conexiones RDT.
Se encarga únicamente de crear, mantener y limpiar conexiones activas.
"""

import time
import threading
from typing import Dict, Optional, Tuple

class Connection:
    """Representa una conexión activa con un cliente"""
    def __init__(self, address: Tuple[str, int], sid: int):
        self.address = address
        self.sid = sid
        self.last_activity = time.time()
        self.expected_seq = 0
        self.window_size = 1  # Stop-and-wait por defecto

class ConnectionManager:
    """
    Maneja las conexiones RDT activas.
    Se encarga únicamente de la gestión de conexiones.
    """
    
    def __init__(self):
        self.connections: Dict[Tuple[str, int], Connection] = {}
        self.connections_lock = threading.Lock()
        self.cleanup_interval = 30  # segundos
        self.connection_timeout = 300  # 5 minutos
    
    def get_connection(self, address: Tuple[str, int]) -> Optional[Connection]:
        """Obtiene una conexión existente por dirección"""
        with self.connections_lock:
            return self.connections.get(address, None)
    
    def create_connection(self, address: Tuple[str, int], sid: int) -> Connection:
        """Crea una nueva conexión"""
        with self.connections_lock:
            connection = Connection(address, sid)
            self.connections[address] = connection
            print(f"[CONN] Nueva conexión creada: {address} -> SID {sid}")
            return connection
    
    def update_activity(self, connection: Connection):
        """Actualiza la actividad de una conexión"""
        connection.last_activity = time.time()
        print(f"[CONN] Actividad actualizada para {connection.address}")
    
    def remove_connection(self, address: Tuple[str, int]):
        """Elimina una conexión específica"""
        with self.connections_lock:
            if address in self.connections:
                del self.connections[address]
                print(f"[CONN] Conexión eliminada: {address}")
    
    def get_or_create_connection(self, address: Tuple[str, int], sid: int) -> Optional[Connection]:
        """Obtiene conexión existente o crea nueva si es necesario"""
        # Buscar conexión existente
        connection = self.get_connection(address)
        
        if connection is not None:
            # Actualizar actividad de conexión existente
            self.update_activity(connection)
            return connection
        
        # Crear nueva conexión
        return self.create_connection(address, sid)
    
    def cleanup_old_connections(self):
        """Limpia conexiones inactivas"""
        current_time = time.time()
        with self.connections_lock:
            to_remove = []
            for address, connection in self.connections.items():
                if current_time - connection.last_activity > self.connection_timeout:
                    to_remove.append(address)
            
            for address in to_remove:
                del self.connections[address]
                print(f"[CONN] Conexión expirada eliminada: {address}")
    
    def get_connection_count(self) -> int:
        """Retorna el número de conexiones activas"""
        with self.connections_lock:
            return len(self.connections)
    
    def get_all_connections(self) -> Dict[Tuple[str, int], Connection]:
        """Retorna todas las conexiones activas (para debugging)"""
        with self.connections_lock:
            return self.connections.copy()
