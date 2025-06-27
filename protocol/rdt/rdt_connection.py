from abc import ABC, abstractmethod
from queue import Queue, Empty
from server.server_helpers import get_udp_socket
from .rdt_message import RdtRequest, RdtResponse
from typing import Optional, Dict
import time
import logging
from protocol.data_handler.data_handler import DataHandler
import socket
import threading

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================================[CONSTANTES]===============================
SERVER_SEQ_NUM_START = 0
CONNECTION_TIMEOUT = 5.0  # 30 segundos de timeout de conexión
DATA_WAIT_TIMEOUT = 5    # 5 segundos esperando primer paquete de datos después del handshake
DATA_WAIT_MAX_ATTEMPTS = 3  # Máximo 3 intentos de reenvío del ACK

# FLAGS
FLAG_HANDSHAKE = 0
FLAG_ACK = 1
FLAG_DATA = 0  # DATA usa el mismo flag que HANDSHAKE pero con datos
FLAG_LAST = 2

# ================================[CLASE PRINCIPAL]===============================
class RdtConnection:
    def __init__(self, address: str):
        self.address: str = address
        self.seq_num: Optional[int] = None
        self.ref_num: Optional[int] = None
        self.max_window: Optional[int] = None

        self.request_queue: Queue[bytes] = Queue()
        self.last_activity = time.time()
        self.connection_established: bool = False
        self.is_active = True

        self.data_handler: DataHandler = DataHandler()

    def add_request(self, data: bytes) -> None:
        self.request_queue.put(data)

    def shutdown(self) -> None:
        logger.info(f"Iniciando shutdown de conexión {self.address}")

        while not self.request_queue.empty():
            self.request_queue.get_nowait()
        self.is_active = False

        logger.info(f"Conexión {self.address} cerrada")

    def process_requests(self) -> None:
        logger.info(f"Iniciando procesamiento de conexión para {self.address}")
        
        while self.is_active:
            # Verificar timeout
            if time.time() - self.last_activity > CONNECTION_TIMEOUT:
                logger.warning(f"Timeout de conexión para {self.address}")
                self.shutdown()
                return

            # Procesar mensajes
            request = self._get_next_message()
            if request is not None:
                self.last_activity = time.time()
                self._process_message(request)

    def _get_next_message(self) -> Optional[bytes]:
        try:
            return self.request_queue.get(timeout=1.0)
        except Empty:
            return None

    def _process_message1(self, request: bytes) -> None:
        rdt_request = RdtRequest(address=self.address, request=request)

        if not self.connection_established:
            self._handle_handshake_message(rdt_request)
        if rdt_request.is_ack():
           self._handle_ack_message1(rdt_request)
        if rdt_request.is_data():
            self._handle_data_message1(rdt_request)

    def _handle_handshake_message(self, rdt_request: RdtRequest) -> None:
        """Maneja mensajes de handshake"""
        if rdt_request.message.flag != FLAG_HANDSHAKE:
            logger.warning(f"Se esperaba mensaje de handshake (FLAG=0) de {self.address}, se recibió FLAG={rdt_request.message.flag}. Ignorando.")
            # BUG ACA REVISAR
            return

        if not self._validate_handshake_message(rdt_request):
            logger.error(f"Request de handshake inválido de {self.address}. Ignorando.")
            # BUG ACA REVISAR
            return

        logger.info(f"Handshake recibido de {self.address} with max_window: {rdt_request.get_max_window()}, seq_num: {rdt_request.get_seq_num()}")

        self.max_window = rdt_request.get_max_window()
        self.ref_num = rdt_request.get_seq_num() + 1
        self.seq_num = SERVER_SEQ_NUM_START

        self._send_handshake_ack()
        self.connection_established = True

    def _validate_handshake_message(self, rdt_request: RdtRequest) -> bool:
        if rdt_request.get_max_window() is None or rdt_request.get_max_window() <= 0:
            logger.error(f"Max window inválido: {rdt_request.get_max_window()}")
            return False

        if rdt_request.get_seq_num() is None or rdt_request.get_seq_num() < 0:
            logger.error(f"Seq num inválido: {rdt_request.get_seq_num()}")
            return False

        return True

    def _send_handshake_ack(self) -> None:
        ack_response = RdtResponse.new_ack_response(self.max_window, self.seq_num, self.ref_num)
        self._send_response(ack_response.message.to_bytes())
        logger.info(f"ACK de handshake enviado a {self.address}")

    def _handle_data_message1(self, rdt_request: RdtRequest) -> None:
        pass
        #1. Mandar ACK
        while pkg_on_fly < max_window && QuedanPaqsPorEnviar: max window = 3 y mandar 5 paqs
            nuevo pkg = service.getNextPkg()
            enviarPkg()
            pkg_on_fly++
            quedanPaqsPorEnviar = service.QuedanPaqsPorEnviar

        #2. Procesar rdt req con data handler y obtener rta en bytes
        #3. Si hay una rta para enviar, enviarla

    def _handle_ack_message1(self, rdt_request: RdtRequest) -> None:
        pass
        # 1. Analizo... ACK de que?






















    def _process_message(self, request: bytes) -> None:
        """Procesa un mensaje recibido"""
        try:
            rdt_request = RdtRequest(address=self.address, request=request)
            
            # Procesar según el estado de la conexión
            if not self.handshake_ack_sent:
                # Esperamos el primer mensaje con FLAG = HANDSHAKE (0)
                self._handle_initial_handshake(rdt_request)
            elif self.waiting_first_data:
                # Esperamos el primer paquete de datos
                self._handle_first_data_packet(rdt_request)
            elif self.handshake_completed:
                self._handle_data_message(rdt_request)
            else:
                logger.warning(f"Mensaje recibido en estado inesperado de {self.address}")
                
        except Exception as e:
            logger.error(f"Error procesando mensaje de {self.address}: {e}")
            self._handle_message_error()

# ================================[MANEJO DE HANDSHAKE]===============================
    def _handle_initial_handshake(self, rdt_request: RdtRequest) -> None:
        """Maneja el primer mensaje con FLAG = HANDSHAKE (0)"""
        try:
            # Validar que sea un mensaje de handshake
            if rdt_request.message.flag != FLAG_DATA:
                logger.warning(f"Se esperaba mensaje de handshake (FLAG=0) de {self.address}, se recibió FLAG={rdt_request.message.flag}. Ignorando.")
                return  # Ignorar cualquier otro mensaje
            
            # Validar que el request sea válido
            if not self._validate_handshake_request(rdt_request):
                logger.error(f"Request de handshake inválido de {self.address}. Ignorando.")
                return
            
            client_max_window = rdt_request.get_max_window()
            client_seq_num = rdt_request.get_seq_num()
            
            logger.info(f"Handshake inicial recibido de {self.address}")
            logger.info(f"Client max_window: {client_max_window}, seq_num: {client_seq_num}")
            
            # Configurar parámetros
            self.max_window = client_max_window
            self.ref_num = client_seq_num + 1
            self.seq_num = SERVER_SEQ_NUM_START

            # Enviar ACK e iniciar timer para esperar primer paquete de datos
            self._send_handshake_ack()
            self.handshake_ack_sent = True
            self.waiting_first_data = True  # Ahora esperamos datos, no ACK
            self._start_data_wait_timer()
            
        except Exception as e:
            logger.error(f"Error en handshake inicial para {self.address}: {e}")
            self._handle_handshake_error()

    def _handle_first_data_packet(self, rdt_request: RdtRequest) -> None:
        """Maneja el primer paquete de datos después del handshake"""
        try:
            # Validar que sea un paquete de datos 
            if not rdt_request.is_data():
                logger.warning(f"Se esperaba paquete de datos de {self.address}, se recibió FLAG={rdt_request.message.flag}")
                return
            
            logger.info(f"Primer paquete de datos recibido de {self.address}")
            self.waiting_first_data = False
            self.handshake_completed = True
            self._stop_data_wait_timer()
            
            # Procesar el paquete de datos que corresponde al primer paquete de datos
            self._handle_data_message(rdt_request)
            #self.send_ack()
            #self.start_data_wait_timer()
                
        except Exception as e:
            logger.error(f"Error procesando primer paquete de datos de {self.address}: {e}")
            self._handle_message_error()

# ================================[MANEJO DE DATOS]===============================
    def _handle_data_message(self, rdt_request: RdtRequest) -> None:
        """Maneja mensajes de datos del archivo (upload del cliente)"""
        try:
            # Procesar los datos recibidos que corresponden a un paquete de datos ya parte de la transferencia de datos
            if self.data_handler:
                response = self.data_handler.handle_data(rdt_request.message.data)
                self._send_response(response)
                #self.send_ack()
                #self.start_data_wait_timer()
            
        except Exception as e:
            logger.error(f"Error procesando paquete de datos: {e}")

    def _send_response(self, response: bytes) -> None:
        """Envía respuesta al cliente"""
        try:
            if not response:
                raise ValueError("Response vacío")
            
            host, port = self.address.split(":")
            # Crear socket temporal para enviar respuesta
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(response, (host, int(port)))
            sock.close()
        except Exception as e:
            logger.error(f"Error enviando respuesta a {self.address}: {e}")
            raise  # Re-lanzar para que el método llamador pueda manejarlo

# ================================[MANEJO DE ERRORES]===============================
    def _handle_handshake_error(self) -> None:
        """Maneja errores durante el handshake"""
        logger.error(f"Error en handshake para {self.address}")
        self.is_active = False

    def _handle_message_error(self) -> None:
        """Maneja errores en el procesamiento de mensajes"""
        logger.warning(f"Error procesando mensaje de {self.address}")
        # Para errores de mensajes, solo logueamos y continuamos

    def _handle_connection_error(self) -> None:
        """Maneja errores críticos de conexión"""
        logger.error(f"Error crítico en conexión con {self.address}")
        self.is_active = False

    def _reset_handshake_state(self) -> None:
        """Resetea el estado del handshake para reintento"""
        self.handshake_ack_sent = False
        self.waiting_first_data = False
        self.handshake_completed = False
        self._stop_data_wait_timer()

# ================================[MANEJO DE TIMERS]===============================
    def _start_data_wait_timer(self) -> None:
        """Inicia un timer para detectar timeout esperando el primer paquete de datos"""
        try:
            if self.data_wait_timer:
                self.data_wait_timer.cancel()
            
            self.data_wait_timer = threading.Timer(DATA_WAIT_TIMEOUT, self._on_data_wait_timeout)
            self.data_wait_timer.start()
        except Exception as e:
            logger.error(f"Error iniciando timer de espera de datos: {e}")

    def _stop_data_wait_timer(self) -> None:
        """Detiene el timer de espera de datos"""
        try:
            if self.data_wait_timer:
                self.data_wait_timer.cancel()
                self.data_wait_timer = None
        except Exception as e:
            logger.error(f"Error deteniendo timer de espera de datos: {e}")

    def _on_data_wait_timeout(self) -> None:
        """Handle de timeout esperando el primer paquete de datos"""
        try:
            if self.waiting_first_data and self.is_active:
                # Verificar si ya se superó el máximo de intentos
                if self.data_wait_attempts >= DATA_WAIT_MAX_ATTEMPTS:
                    logger.error(f"Máximo número de intentos alcanzado esperando datos de {self.address}")
                    logger.error(f"Descartando conexión con {self.address}")
                    self.is_active = False
                    self.shutdown()
                    return
                
                self.data_wait_attempts += 1
                
                # Reintentar enviar el ACK
                logger.warning(f"Timeout esperando primer paquete de datos de {self.address} (intento {self.data_wait_attempts}/{DATA_WAIT_MAX_ATTEMPTS})")
                self._send_handshake_ack()
                self._start_data_wait_timer()  # Reiniciar timer
                
        except Exception as e:
            logger.error(f"Error en timeout de espera de datos: {e}")
            self.is_active = False

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
