from abc import ABC, abstractmethod
from queue import Queue, Empty
from server.server_helpers import get_udp_socket
from .rdt_message import RdtRequest, RdtResponse
from typing import Optional, Dict
import threading
import time
import json
import logging
from protocol.data_handler.data_handler import DataHandler

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SERVER_SEQ_NUM_START = 0

class RdtConnection:
    def __init__(self, address: str):
        self.address: str = address
        self.seq_num: Optional[int] = None
        self.ref_num: Optional[int] = None
        self.max_window: Optional[int] = None
        self.request_queue: Queue[bytes] = Queue()
        self.data_handler: DataHandler = DataHandler()
        
        # Hilo principal de la conexión que persiste
        self.connection_thread: Optional[threading.Thread] = None
        self.is_active = True
        
        # Iniciar el hilo principal de la conexión
        self._start_connection_handler()

    def _start_connection_handler(self) -> None:
        """Inicia el hilo principal que maneja la conexión"""
        self.connection_thread = threading.Thread(
            target=self._connection_loop, 
            daemon=True,
            name=f"Connection-{self.address}"
        )
        self.connection_thread.start()
        logger.info(f"Iniciado hilo de conexión para {self.address}")

    def _connection_loop(self) -> None:
        """Loop principal que maneja toda la comunicación de la conexión"""
        logger.info(f"Iniciando conexión persistente para {self.address}")
        
        while self.is_active:
            try:
                request = self._get_next_message()
                if request is not None:
                    self._process_message(request)
            except Exception as e:
                logger.error(f"Error en connection loop para {self.address}: {e}")
                break
        
        logger.info(f"Conexión cerrada para {self.address}")

    def _get_next_message(self) -> Optional[bytes]:
        """Obtiene el siguiente mensaje de la cola, retorna None si no hay mensajes"""
        try:
            return self.request_queue.get(timeout=1.0)
        except Empty:
            # No hay mensajes disponibles, retornar None
            return None

    def _process_message(self, request: bytes) -> None:
        """Procesa un mensaje recibido"""
        try:
            rdt_request = RdtRequest(address=self.address, request=request)
            
            # Si es un ACK, ignorar para conexiones ya establecidas
            if rdt_request.is_ack():
                logger.debug(f"ACK recibido de {self.address}. Ignorando.")
                return

            # Procesar según el estado de la conexión
            if self.seq_num is None:
                self._handle_initial_connection(rdt_request)
            else:
                self._handle_data_message(rdt_request)
                
        except Exception as e:
            logger.error(f"Error procesando mensaje de {self.address}: {e}")

    def _handle_initial_connection(self, rdt_request: RdtRequest) -> None:
        """Maneja el handshake inicial de la conexión"""
        try:
            # Extraer información del HEADER del paquete
            client_max_window = rdt_request.get_max_window()
            client_seq_num = rdt_request.get_seq_num()
            
            logger.info(f"Handshake recibido de {self.address}")
            logger.info(f"Client max_window: {client_max_window}, seq_num: {client_seq_num}")
            
            # Configurar parámetros de la conexión
            self.max_window = client_max_window
            self.ref_num = client_seq_num + 1
            self.seq_num = SERVER_SEQ_NUM_START

            # Enviar ACK response
            ack_response = RdtResponse.new_ack_response(self.max_window, self.seq_num, self.ref_num)
            self._send_response(ack_response.to_bytes())
            
            logger.info(f"Conexión establecida con {self.address}")
            logger.info(f"Server seq_num: {self.seq_num}, ref_num: {self.ref_num}")
            
        except Exception as e:
            logger.error(f"Error en handshake para {self.address}: {e}")

    def _handle_data_message(self, rdt_request: RdtRequest) -> None:
        """Maneja mensajes de datos del archivo (upload del cliente)"""
        try:
            seq_num = rdt_request.get_seq_num()
            is_last_packet = rdt_request.message.last_packet
            
            context = {
                'connection_id': self.address,
                'seq_num': seq_num,
                'is_last_packet': is_last_packet,
                'packet_data': rdt_request.message.data
            }
            
            logger.info(f"Procesando paquete {seq_num} de {self.address}")
            logger.info(f"Es último paquete: {is_last_packet}")
            
            # Procesar los datos recibidos
            if self.data_handler:
                response = self.data_handler.handle_data(rdt_request.message.data, context)
                self._send_response(response)
            
            logger.info(f"Paquete {seq_num} procesado exitosamente")
            
        except Exception as e:
            logger.error(f"Error procesando paquete de datos: {e}")

    def _send_response(self, response: bytes) -> None:
        """Envía respuesta al cliente"""
        try:
            host, port = self.address.split(':')
            with get_udp_socket(host, int(port)) as socket:
                socket.sendto(response, (host, int(port)))
        except Exception as e:
            logger.error(f"Error enviando respuesta a {self.address}: {e}")

    def add_request(self, data: bytes) -> None:
        """Añade una nueva petición a la cola"""
        self.request_queue.put(data)

    def shutdown(self) -> None:
        """Cierra la conexión y libera recursos"""
        logger.info(f"Iniciando shutdown de conexión {self.address}")
        self.is_active = False
        
        if self.connection_thread and self.connection_thread.is_alive():
            self.connection_thread.join(timeout=2.0)
        
        logger.info(f"Conexión {self.address} cerrada")


class RdtConnectionRepository(ABC):
    @abstractmethod
    def get_connection(self, address: str) -> Optional['RdtConnection']:
        pass

    @abstractmethod
    def remove_connection(self, address: str) -> None:
        pass

    @abstractmethod
    def add_connection(self, address: str, connection: 'RdtConnection') -> None:
        pass


class MemoryRdtConnectionRepository(RdtConnectionRepository):
    def __init__(self):
        self.connections: Dict[str, RdtConnection] = {}

    def get_connection(self, address: str) -> Optional[RdtConnection]:
        return self.connections.get(address)

    def add_connection(self, address: str, connection: RdtConnection) -> None:
        if address not in self.connections:
            self.connections[address] = connection

    def remove_connection(self, address: str) -> None:
        self.connections.pop(address, None)
