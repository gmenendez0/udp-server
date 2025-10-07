#!/usr/bin/env python3
"""
Clases base para el cliente RDT.
Contiene las clases fundamentales compartidas por todos los protocolos.
"""

import socket
import threading
import time
import logging
import hashlib
from typing import Optional, Tuple, Dict, Any
from pathlib import Path
from protocol.rdt.rdt_message import RdtMessage, RdtRequest
from protocol.dp.dp_request import DPRequest
from protocol import FunctionFlag

# Importar constantes desde constants.py
from .constants import (
    FLAG_DATA, FLAG_ACK, FLAG_LAST,
    ERR_TOO_BIG, ERR_NOT_FOUND, ERR_BAD_REQUEST, ERR_PERMISSION_DENIED,
    ERR_NETWORK_ERROR, ERR_TIMEOUT_ERROR, ERR_INVALID_PROTOCOL, ERR_SERVER_ERROR,
    get_error_message
)

# Constantes específicas de este módulo
PROTO_STOP_WAIT, PROTO_GBN = 0, 1

# Constantes TLV
TLV_FILENAME = 0x01
TLV_FILESIZE = 0x02
TLV_PROTOCOL = 0x03
TLV_WINDOW_REQ = 0x04
TLV_CHUNK_SIZE = 0x05
TLV_ERROR_CODE = 0x06
TLV_ERROR_MESSAGE = 0x07

# Operaciones
OP_REQUEST_UPLOAD, OP_UPLOAD_ACCEPTED = 0x01, 0x02
OP_DOWNLOAD_ACCEPTED = 0x04
OP_REQUEST_DOWNLOAD, OP_END_SESSION, OP_ERROR = 0x03, 0x10, 0x7F

# Configurar logging
logger = logging.getLogger(__name__)

# Constantes del protocolo
BUFFER_SIZE = 2048
HANDSHAKE_TIMEOUT = 5
HANDSHAKE_MAX_ATTEMPTS = 3
CHUNK_SIZE = 1024
ACK_TIMEOUT = 5
MAX_RETRIES = 5
WINDOW_SIZE_GO_BACK_N = 5
MAX_FILE_SIZE_MB = 5  # Según consigna del trabajo

class ConnectionState:
    """
    Maneja todo el estado de la conexión RDT, incluyendo handshake y comunicación.
    Gestiona sequence numbers y reference numbers de forma unificada.
    """
    
    def __init__(self, max_window: int = 1):
        """
        Inicializa el estado de la conexión.
        
        Args:
            max_window (int): Tamaño máximo de ventana
        """
        if max_window < 1:
            raise ValueError("max_window debe ser mayor o igual a 1")
        
        self.max_window = max_window
        self.handshake_completed = False
        
        # Números del cliente (mis números)
        self.client_seq_num = 0  # Comenzamos en 0 para handshake
        self.client_ref_num = 0  # En handshake se envía 0 y se ignora
        
        # Números del servidor (se configuran después del handshake)
        self.server_seq_num: Optional[int] = None
        self.server_ref_num: Optional[int] = None
    
    def create_handshake_request(self) -> RdtMessage:
        """
        Crea el mensaje de handshake inicial.
        
        Returns:
            RdtMessage: Mensaje de handshake formateado
        """
        handshake_msg = RdtMessage(
            flag=FLAG_DATA,
            max_window=self.max_window,
            seq_num=self.client_seq_num,
            ref_num=self.client_ref_num,
            data=b''
        )
        
        logger.info(f"Creando handshake request: window={self.max_window}, seq={self.client_seq_num}")
        return handshake_msg
    
    def process_handshake_response(self, rdt_request: RdtRequest) -> bool:
        """
        Procesa la respuesta del servidor al handshake.
        
        Args:
            rdt_request (RdtRequest): Respuesta del servidor
            
        Returns:
            bool: True si el handshake fue exitoso, False en caso contrario
        """
        try:
            # Validar que es un ACK
            if not rdt_request.is_ack():
                logger.error(f"Servidor no envió ACK. Flag recibido: {rdt_request.message.flag}")
                return False
            
            # Validar max_window
            if rdt_request.get_max_window() != self.max_window:
                logger.error(f"Max window no coincide: {rdt_request.get_max_window()}, esperado: {self.max_window}")
                return False
            
            # Obtener números del servidor
            server_seq = rdt_request.get_seq_num()
            server_ref = rdt_request.get_ref_num()
            
            # Validar que el servidor confirma mi handshake inicial
            if server_seq != self.client_seq_num:
                logger.error(f"Server SEQ incorrecto: {server_seq}, esperado: {self.client_seq_num}")
                return False
                
            # El servidor debe confirmar nuestro seq_num con su ref_num
            
            if server_ref != (self.client_seq_num + 1):
                logger.error(f"Server REF incorrecto: {server_ref}, esperado: {self.client_seq_num}")
                return False
            
            # Guardar información del servidor
            self.server_seq_num = server_seq
            self.server_ref_num = server_ref
            
            # Configurar mis números para la comunicación
            # Después del handshake, incremento mis números para la siguiente comunicación
            self.client_seq_num += 1  # Próximo SEQ a usar
            self.client_ref_num = server_seq + 1  # Próximo REF que espero del servidor
            
            self.handshake_completed = True
            logger.info(f"Handshake completado. Cliente configurado: SEQ={self.client_seq_num}, REF={self.client_ref_num}")
            return True
            
        except Exception as e:
            logger.error(f"Error procesando respuesta de handshake: {e}")
            return False
    
    def get_next_sequence_number(self) -> int:
        """Obtiene el siguiente sequence number para enviar."""
        return self.client_seq_num
    
    def get_current_reference_number(self) -> int:
        """Obtiene el reference number actual."""
        return self.client_ref_num
    
    def increment_sequence_number(self) -> None:
        """Incrementa el sequence number después de enviar un mensaje exitosamente."""
        self.client_seq_num += 1
        logger.debug(f"Sequence number incrementado a: {self.client_seq_num}")
    
    def update_reference_number(self, new_ref_num: int) -> None:
        """Actualiza el reference number basado en el ACK recibido."""
        self.client_ref_num = new_ref_num
        logger.debug(f"Reference number actualizado a: {self.client_ref_num}")
    
    def get_max_window(self) -> int:
        """Obtiene el tamaño máximo de ventana."""
        return self.max_window
    
    def is_handshake_completed(self) -> bool:
        """Verifica si el handshake fue completado."""
        return self.handshake_completed
    
    def is_stop_and_wait(self) -> bool:
        """Verifica si el protocolo es Stop and Wait."""
        return self.max_window == 1
    
    def is_go_back_n(self) -> bool:
        """Verifica si el protocolo es Go Back N."""
        return self.max_window > 1
    
    def get_server_sequence_number(self) -> Optional[int]:
        """Obtiene el número de secuencia del servidor."""
        return self.server_seq_num
    
    def get_server_reference_number(self) -> Optional[int]:
        """Obtiene el número de referencia del servidor."""
        return self.server_ref_num


class RdtClient:
    """
    Cliente RDT con protocolo de handshake y manejo de errores.
    Maneja la comunicación completa con el servidor.
    """

    def __init__(self, host: str, port: int, max_window: int = 1):
        """
        Inicializa el cliente RDT.

        Args:
            host (str): IP del servidor.
            port (int): Puerto del servidor.
            max_window (int): Tamaño máximo de ventana (1 = stop and wait, 2-9 = go back N).
        """
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(True)
        self.sock.settimeout(HANDSHAKE_TIMEOUT)
        self.lock = threading.Lock()
        self.closed_by_server = False
        self.connection_state = ConnectionState(max_window)
        self.connected = False
        self.stats = {
            'packets_sent': 0,
            'packets_received': 0,
            'retransmissions': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None
        }

    def connect(self) -> bool:
        """
        Establece conexión con el servidor mediante handshake.
        
        Returns:
            bool: True si la conexión fue exitosa, False en caso contrario
        """
        logger.info(f"Iniciando handshake con {self.host}:{self.port}")
        self.stats['start_time'] = time.time()
        
        for attempt in range(HANDSHAKE_MAX_ATTEMPTS):
            try:
                logger.info(f"Intento de handshake {attempt + 1}/{HANDSHAKE_MAX_ATTEMPTS}")
                
                # Enviar handshake inicial
                handshake_msg = self.connection_state.create_handshake_request()
                self.send(handshake_msg.to_bytes())
                logger.info("Handshake inicial enviado")
                
                # Esperar respuesta del servidor
                data, addr, close_signal = self.receive()
                
                if close_signal:
                    logger.error("Servidor envió señal de cierre durante handshake")
                    return False
                
                if not data:
                    logger.warning(f"Timeout esperando respuesta del servidor (intento {attempt + 1})")
                    continue
                
                # Parsear respuesta
                rdt_request = RdtRequest(address=f"{self.host}:{self.port}", request=data)
                
                if self.connection_state.process_handshake_response(rdt_request):
                    self.connected = True
                    logger.info("Conexión establecida exitosamente")
                    return True
                else:
                    logger.warning(f"Respuesta de handshake inválida (intento {attempt + 1})")
                    
            except Exception as e:
                logger.error(f"Error en handshake (intento {attempt + 1}): {e}")
                self.stats['errors'] += 1
        
        logger.error("No se pudo establecer conexión después de todos los intentos")
        return False

    def send(self, data: bytes):
        """
        Envía datos al servidor.

        Args:
            data (bytes): Datos a enviar.
        """
        with self.lock:
            self.sock.sendto(data, (self.host, self.port))
            self.stats['packets_sent'] += 1

    def receive(self) -> Tuple[Optional[bytes], Optional[Tuple[str, int]], bool]:
        """
        Recibe datos desde el servidor.

        Returns:
            tuple:
                - data (bytes | None): Datos recibidos.
                - addr (tuple[str, int] | None): Dirección del remitente.
                - close_signal (bool): True si el servidor envió señal de cierre.
        """
        try:
            data, addr = self.sock.recvfrom(BUFFER_SIZE)
            self.stats['packets_received'] += 1
            if self._check_close_signal(data):
                self.closed_by_server = True
                return data, addr, True
            return data, addr, False
        except socket.timeout:
            return None, None, False

    def _check_close_signal(self, data: bytes) -> bool:
        """
        Verifica si el paquete recibido indica CLOSE_CONN.

        Args:
            data (bytes): Paquete recibido.

        Returns:
            bool: True si indica cerrar conexión.
        """
        try:
            dp = DPRequest(data)
            return dp.function_flag == FunctionFlag.CLOSE_CONN
        except Exception:
            return False

    def is_connected(self) -> bool:
        """
        Verifica si la conexión está establecida.
        
        Returns:
            bool: True si está conectado
        """
        return self.connected and self.connection_state.is_handshake_completed()

    def get_connection_state(self) -> ConnectionState:
        """
        Obtiene el estado de la conexión.
        
        Returns:
            ConnectionState: Estado actual de la conexión
        """
        return self.connection_state

    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de la conexión.
        
        Returns:
            dict: Estadísticas de la conexión
        """
        if self.stats['start_time'] and self.stats['end_time']:
            self.stats['duration'] = self.stats['end_time'] - self.stats['start_time']
        return self.stats.copy()

    def close(self):
        """
        Cierra el socket.
        """
        self.connected = False
        self.stats['end_time'] = time.time()
        self.sock.close()
        logger.info("Conexión cerrada")

def validate_file_size(file_path: Path, max_size_mb: int = MAX_FILE_SIZE_MB) -> Tuple[bool, Optional[int]]:
    """
    Valida que el archivo no exceda el tamaño máximo.
    
    Args:
        file_path (Path): Ruta del archivo
        max_size_mb (int): Tamaño máximo en MB
        
    Returns:
        tuple: (es_valido, codigo_error) donde codigo_error es None si es válido
    """
    file_size = file_path.stat().st_size
    max_size_bytes = max_size_mb * 1024 * 1024
    if file_size > max_size_bytes:
        return False, ERR_TOO_BIG
    return True, None
