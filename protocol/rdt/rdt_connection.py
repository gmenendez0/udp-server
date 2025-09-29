from abc import ABC, abstractmethod
from queue import Queue, Empty
from server.server_helpers import get_udp_socket
from .rdt_message import RdtRequest, RdtResponse
from typing import Optional, Dict
import time
import logging
from protocol.data_handler.data_handler import DataHandler
import threading

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================================[CONSTANTES]===============================
SERVER_SEQ_NUM_START = 0
CONNECTION_TIMEOUT = 30  # 30 segundos de timeout de conexión
HANDSHAKE_TIMEOUT = 5    # 5 segundos de timeout para handshake
HANDSHAKE_MAX_ATTEMPTS = 3

# ================================[CLASE PRINCIPAL]===============================
class RdtConnection:
    def __init__(self, address: str):
        self.address: str = address
        self.seq_num: Optional[int] = None
        self.ref_num: Optional[int] = None
        self.max_window: Optional[int] = None
        self.request_queue: Queue[bytes] = Queue()
        self.data_handler: DataHandler = DataHandler()
        self.is_active = True
        self.last_activity = time.time()
        self.handshake_completed = False
        self.handshake_ack_sent = False
        self.handshake_ack_received = False
        self.handshake_attempts = 0
        self.handshake_timer = None  # Timer para detectar timeout

# ================================[PROCESAMIENTO PRINCIPAL]===============================
    def process_requests(self) -> None:
        """Procesa todas las peticiones de la conexión"""
        logger.info(f"Iniciando procesamiento de conexión para {self.address}")
        
        while self.is_active:
            try:
                # Verificar timeout de conexión general
                if time.time() - self.last_activity > CONNECTION_TIMEOUT:
                    logger.warning(f"Timeout de conexión para {self.address}")
                    break
                
                # Procesar mensajes
                request = self._get_next_message()
                if request is not None:
                    self.last_activity = time.time()
                    self._process_message(request)
                
                    
            except Exception as e:
                logger.error(f"Error en procesamiento para {self.address}: {e}")
                self._handle_connection_error()
                break
        
        logger.info(f"Conexión cerrada para {self.address}")

    def _get_next_message(self) -> Optional[bytes]:
        """Obtiene el siguiente mensaje de la cola, retorna None si no hay mensajes"""
        try:
            return self.request_queue.get(timeout=1.0)
        except Empty:
            return None

    def _process_message(self, request: bytes) -> None:
        """Procesa un mensaje recibido"""
        try:
            rdt_request = RdtRequest(address=self.address, request=request)
            
            # Procesar según el estado de la conexión
            if not self.handshake_completed:
                self._handle_handshake(rdt_request)
            else:
                self._handle_data_message(rdt_request)
                
        except Exception as e:
            logger.error(f"Error procesando mensaje de {self.address}: {e}")
            self._handle_message_error()

# ================================[MANEJO DE HANDSHAKE]===============================
    def _handle_handshake(self, rdt_request: RdtRequest) -> None:
        """Maneja el handshake completo de la conexión"""
        try:
            if not self.handshake_ack_sent:
                # Primer mensaje del cliente
                self._handle_initial_connection(rdt_request)
            elif not self.handshake_ack_received:
                # Segundo mensaje - ACK del cliente
                self._handle_client_ack(rdt_request)
            else:
                # Handshake completado
                self.handshake_completed = True
                self._handle_data_message(rdt_request)
        except Exception as e:
            logger.error(f"Error en handshake para {self.address}: {e}")
            self._handle_handshake_error()

    def _handle_initial_connection(self, rdt_request: RdtRequest) -> None:
        """Maneja el primer mensaje del handshake"""
        try:
            # Validar que el request sea válido
            if not self._validate_handshake_request(rdt_request):
                raise ValueError("Request de handshake inválido")
            
            client_max_window = rdt_request.get_max_window()
            client_seq_num = rdt_request.get_seq_num()
            
            logger.info(f"Handshake inicial recibido de {self.address}")
            logger.info(f"Client max_window: {client_max_window}, seq_num: {client_seq_num}")
            
            # Configurar parámetros
            self.max_window = client_max_window
            self.ref_num = client_seq_num + 1
            self.seq_num = SERVER_SEQ_NUM_START

            # Enviar ACK e iniciar timer
            self._send_handshake_ack()
            self.handshake_ack_sent = True
            self._start_handshake_timer()
            
        except Exception as e:
            logger.error(f"Error en handshake inicial para {self.address}: {e}")
            self._handle_handshake_error()

    def _handle_client_ack(self, rdt_request: RdtRequest) -> None:
        """Maneja el ACK del cliente"""
        try:
            if not rdt_request.is_ack():
                raise ValueError("Se esperaba un ACK del cliente")
            
            logger.info(f"ACK de cliente recibido de {self.address}")
            self.handshake_ack_received = True
            self.handshake_completed = True
            self._stop_handshake_timer()
            logger.info(f"Handshake completado con {self.address}")
                
        except Exception as e:
            logger.error(f"Error procesando ACK de cliente para {self.address}: {e}")
            self._handle_handshake_error()

# ================================[MANEJO DE DATOS -> TODO]===============================
    def _handle_data_message(self, rdt_request: RdtRequest) -> None:
        """Maneja mensajes de datos del archivo (upload del cliente)"""
        try:
            # Procesar los datos recibidos
            if self.data_handler:
                response = self.data_handler.handle_data(rdt_request.message.data)
                self._send_response(response)
            
        except Exception as e:
            logger.error(f"Error procesando paquete de datos: {e}")

# ================================[ENVÍO DE RESPUESTAS]===============================
    def _send_response(self, response: bytes) -> None:
        """Envía respuesta al cliente"""
        try:
            if not response:
                raise ValueError("Response vacío")
            
            host, port = self.address.split(':')
            with get_udp_socket(host, int(port)) as socket:
                socket.sendto(response, (host, int(port)))
        except Exception as e:
            logger.error(f"Error enviando respuesta a {self.address}: {e}")
            raise  # Re-lanzar para que el método llamador pueda manejarlo

    def _send_handshake_ack(self) -> None:
        """Envía el ACK del handshake al cliente"""
        try:
            if not all([self.max_window is not None, self.seq_num is not None, self.ref_num is not None]):
                raise ValueError("Parámetros de handshake no configurados correctamente")
            
            ack_response = RdtResponse.new_ack_response(self.max_window, self.seq_num, self.ref_num)
            self._send_response(ack_response.message.to_bytes())
            logger.info(f"ACK de handshake enviado a {self.address}")
        except Exception as e:
            logger.error(f"Error enviando ACK de handshake a {self.address}: {e}")
            raise  # Re-lanzar para que el método llamador pueda manejarlo

# ================================[VALIDACIÓN]===============================
    def _validate_handshake_request(self, rdt_request: RdtRequest) -> bool:
        """Valida que el request de handshake sea válido"""
        try:
            max_window = rdt_request.get_max_window()
            seq_num = rdt_request.get_seq_num()
            
            # Validaciones básicas
            if max_window is None or max_window <= 0:
                logger.error(f"Max window inválido: {max_window}")
                return False
            
            if seq_num is None or seq_num < 0:
                logger.error(f"Seq num inválido: {seq_num}")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error validando handshake request: {e}")
            return False

# ================================[MANEJO DE ERRORES]===============================
    def _handle_handshake_error(self) -> None:
        """Maneja errores durante el handshake"""
        self.handshake_attempts += 1
        logger.warning(f"Error en handshake para {self.address} (intento {self.handshake_attempts}/{HANDSHAKE_MAX_ATTEMPTS})")
        
        if self.handshake_attempts >= HANDSHAKE_MAX_ATTEMPTS:
            logger.error(f"Máximo número de intentos alcanzado para {self.address}")
            logger.error(f"Descartando conexión con {self.address}")
            self.is_active = False
        else:
            # Resetear estado para reintento
            self._reset_handshake_state()

    def _handle_message_error(self) -> None:
        """Maneja errores en el procesamiento de mensajes"""
        logger.warning(f"Error procesando mensaje de {self.address}")
        # Para errores de mensajes, no incrementamos handshake_attempts
        # Solo logueamos y continuamos

    def _handle_connection_error(self) -> None:
        """Maneja errores críticos de conexión"""
        logger.error(f"Error crítico en conexión con {self.address}")
        self.is_active = False

    def _reset_handshake_state(self) -> None:
        """Resetea el estado del handshake para reintento"""
        self.handshake_ack_sent = False
        self.handshake_ack_received = False
        self.handshake_completed = False
        self._stop_handshake_timer()

# ================================[MANEJO DE TIMERS]===============================
    def _start_handshake_timer(self) -> None:
        """Inicia un timer para detectar timeout de handshake"""
        try:
            if self.handshake_timer:
                self.handshake_timer.cancel()
            
            self.handshake_timer = threading.Timer(HANDSHAKE_TIMEOUT, self._on_handshake_timeout)
            self.handshake_timer.start()
        except Exception as e:
            logger.error(f"Error iniciando timer de handshake: {e}")

    def _stop_handshake_timer(self) -> None:
        """Detiene el timer de handshake"""
        try:
            if self.handshake_timer:
                self.handshake_timer.cancel()
                self.handshake_timer = None
        except Exception as e:
            logger.error(f"Error deteniendo timer de handshake: {e}")

    def _on_handshake_timeout(self) -> None:
        """Handle de timeout de handshake"""
        try:
            if not self.handshake_completed and self.is_active:
                self.handshake_attempts += 1
                
                # Si el cliente no ha respondido, reintentar enviar el ACK
                if self.handshake_ack_sent and not self.handshake_ack_received:
                    logger.warning(f"Timeout esperando confirmación del cliente para {self.address} (intento {self.handshake_attempts}/{HANDSHAKE_MAX_ATTEMPTS})")
                    self._send_handshake_ack()
                    self._start_handshake_timer()  # Reiniciar timer
                else:
                    logger.warning(f"Timeout de handshake para {self.address} (intento {self.handshake_attempts}/{HANDSHAKE_MAX_ATTEMPTS})")
                
                # Verificar que no se haya superado el máximo de intentos
                if self.handshake_attempts >= HANDSHAKE_MAX_ATTEMPTS:
                    logger.error(f"Máximo número de intentos alcanzado para {self.address}")
                    logger.error(f"Descartando conexión con {self.address}")
                    self.is_active = False
        except Exception as e:
            logger.error(f"Error en timeout de handshake: {e}")
            self.is_active = False

# ================================[API PÚBLICA]===============================
    def add_request(self, data: bytes) -> None:
        """Añade una nueva petición a la cola"""
        try:
            if not data:
                logger.warning("Intentando agregar request vacío")
                return
            
            self.request_queue.put(data)
        except Exception as e:
            logger.error(f"Error agregando request a la cola: {e}")

    def shutdown(self) -> None:
        """Cierra la conexión y libera recursos"""
        logger.info(f"Iniciando shutdown de conexión {self.address}")
        self.is_active = False
        self._stop_handshake_timer()  # Detener timer al cerrar
        logger.info(f"Conexión {self.address} cerrada")

# ================================[REPOSITORIO ABSTRACTO]===============================
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

# ================================[REPOSITORIO EN MEMORIA]===============================
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
