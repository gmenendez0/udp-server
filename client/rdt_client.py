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
from protocol.const import (
    # Códigos de error
    ERR_TOO_BIG, ERR_NOT_FOUND, ERR_BAD_REQUEST, ERR_PERMISSION_DENIED,
    ERR_NETWORK_ERROR, ERR_TIMEOUT_ERROR, ERR_INVALID_PROTOCOL, ERR_SERVER_ERROR,
    get_error_message,
    # Constantes de protocolo
    PROTO_STOP_WAIT, PROTO_GBN,
    # Tipos de mensaje y flags
    T_DATA, T_ACK, T_CTRL, T_HANDSHAKE, F_LAST, F_ERR,
    # Constantes TLV
    TLV_FILENAME, TLV_FILESIZE, TLV_PROTOCOL, TLV_WINDOW_REQ, TLV_CHUNK_SIZE,
    TLV_ERROR_CODE, TLV_ERROR_MESSAGE,
    # Operaciones
    OP_REQUEST_UPLOAD, OP_UPLOAD_ACCEPTED, OP_DOWNLOAD_ACCEPTED,
    OP_REQUEST_DOWNLOAD, OP_END_SESSION, OP_ERROR,
    # Funciones de construcción
    build_error_response, build_request_upload
)

# Configurar logging
logger = logging.getLogger(__name__)

# Constantes del protocolo
BUFFER_SIZE = 2048
HANDSHAKE_TIMEOUT = 5
HANDSHAKE_MAX_ATTEMPTS = 3
CHUNK_SIZE = 1024
ACK_TIMEOUT = 2
MAX_RETRIES = 5
WINDOW_SIZE_GO_BACK_N = 5
MAX_FILE_SIZE_MB = 5  # Según consigna del trabajo


class RdtHandshake:
    """
    Maneja el protocolo de handshake RDT.
    """
    
    def __init__(self, max_window: int = 1):
        """
        Inicializa el handshake.
        
        Args:
            max_window (int): Tamaño máximo de ventana (1 = stop and wait, 2-9 = go back N)
        """
        if max_window < 1 or max_window > 9:
            raise ValueError("max_window debe estar entre 1 y 9")
        
        self.max_window = max_window
        self.sequence_number = 0  # Comenzamos en 0 por simplicidad
        self.reference_number = 0  # En handshake se envía 0 y se ignora
        self.handshake_completed = False
        self.server_sequence_number: Optional[int] = None
        self.server_reference_number: Optional[int] = None
    
    def create_handshake_request(self) -> RdtMessage:
        """
        Crea el mensaje de handshake inicial usando RdtMessage.
        
        Returns:
            RdtMessage: Mensaje de handshake formateado
        """
        handshake_msg = RdtMessage(
            flag=T_HANDSHAKE,
            max_window=self.max_window,
            seq_num=self.sequence_number,
            ref_num=self.reference_number,
            data=b''
        )
        
        logger.info(f"Creando handshake request: window={self.max_window}, seq={self.sequence_number}")
        return handshake_msg
    
    def parse_handshake_response(self, rdt_request: RdtRequest) -> bool:
        """
        Parsea la respuesta del servidor al handshake.
        
        Args:
            rdt_request (RdtRequest): Respuesta del servidor
            
        Returns:
            bool: True si el handshake fue exitoso, False en caso contrario
        """
        try:
            if rdt_request.message.flag != T_ACK:
                logger.error(f"Flag incorrecto del servidor: {rdt_request.message.flag}, esperado: {T_ACK} (ACK)")
                return False
            if not rdt_request.is_ack():
                logger.error("El servidor no envió un ACK")
                return False
            
            if rdt_request.get_max_window() != self.max_window:
                logger.error(f"Max window no coincide: {rdt_request.get_max_window()}, esperado: {self.max_window}")
                return False
            
            self.server_sequence_number = rdt_request.get_seq_num()
            self.server_reference_number = rdt_request.get_ref_num()
            self.reference_number = rdt_request.get_seq_num() + 1
            
            expected_ref_num = self.sequence_number + 1
            if self.server_reference_number != expected_ref_num:
                logger.error(f"Reference number incorrecto: {self.server_reference_number}, esperado: {expected_ref_num}")
                return False
            
            self.handshake_completed = True
            logger.info("Handshake completado exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error parseando respuesta de handshake: {e}")
            return False
    
    def is_handshake_completed(self) -> bool:
        """Verifica si el handshake fue completado."""
        return self.handshake_completed
    
    def get_server_sequence_number(self) -> Optional[int]:
        """Obtiene el número de secuencia del servidor."""
        return self.server_sequence_number
    
    def get_server_reference_number(self) -> Optional[int]:
        """Obtiene el número de referencia del servidor."""
        return self.server_reference_number
    
    def get_max_window(self) -> int:
        """Obtiene el tamaño máximo de ventana."""
        return self.max_window
    
    def is_stop_and_wait(self) -> bool:
        """Verifica si el protocolo es Stop and Wait."""
        return self.max_window == 1
    
    def is_go_back_n(self) -> bool:
        """Verifica si el protocolo es Go Back N."""
        return self.max_window > 1

class ConnectionState:
    """
    Maneja el estado de la conexión después del handshake.
    Gestiona dinámicamente sequence numbers y reference numbers.
    """
    
    def __init__(self, handshake_info: dict):
        """
        Inicializa el estado de la conexión basado en la información del handshake.
        
        Args:
            handshake_info (dict): Información del handshake completado
        """
        self.max_window = handshake_info['max_window']
        self.server_seq_num = handshake_info['server_seq_num']
        self.server_ref_num = handshake_info['server_ref_num']
        
        self.client_seq_num = 1
        self.client_ref_num = self.server_seq_num + 1
        
        logger.info(f"Estado de conexión inicializado: client_seq={self.client_seq_num}, client_ref={self.client_ref_num} (basado en server_seq={self.server_seq_num})")
    
    def get_next_sequence_number(self) -> int:
        """
        Obtiene el siguiente sequence number para enviar.
        
        Returns:
            int: Sequence number actual (no lo incrementa)
        """
        return self.client_seq_num
    
    def get_current_reference_number(self) -> int:
        """
        Obtiene el reference number actual.
        
        Returns:
            int: Reference number actual
        """
        return self.client_ref_num
    
    def increment_sequence_number(self) -> None:
        """
        Incrementa el sequence number después de enviar un mensaje exitosamente.
        """
        self.client_seq_num += 1
        logger.debug(f"Sequence number incrementado a: {self.client_seq_num}")
    
    def update_reference_number(self, new_ref_num: int) -> None:
        """
        Actualiza el reference number basado en el ACK recibido.
        
        Args:
            new_ref_num (int): Nuevo reference number del ACK
        """
        self.client_ref_num = new_ref_num
        logger.debug(f"Reference number actualizado a: {self.client_ref_num}")
    
    def get_max_window(self) -> int:
        """
        Obtiene el tamaño máximo de ventana.
        
        Returns:
            int: Tamaño máximo de ventana
        """
        return self.max_window
    
    def is_stop_and_wait(self) -> bool:
        """
        Verifica si el protocolo es Stop and Wait.
        
        Returns:
            bool: True si es Stop and Wait
        """
        return self.max_window == 1
    
    def is_go_back_n(self) -> bool:
        """
        Verifica si el protocolo es Go Back N.
        
        Returns:
            bool: True si es Go Back N
        """
        return self.max_window > 1


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
        self.handshake = RdtHandshake(max_window)
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
                handshake_msg = self.handshake.create_handshake_request()
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
                
                if self.handshake.parse_handshake_response(rdt_request):
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
        return self.connected and self.handshake.is_handshake_completed()

    def get_handshake_info(self) -> dict:
        """
        Obtiene información del handshake completado.
        
        Returns:
            dict: Información del handshake
        """
        return {
            'max_window': self.handshake.get_max_window(),
            'server_seq_num': self.handshake.get_server_sequence_number(),
            'server_ref_num': self.handshake.get_server_reference_number(),
            'is_stop_and_wait': self.handshake.is_stop_and_wait(),
            'is_go_back_n': self.handshake.is_go_back_n()
        }

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

# TODO: ver si usaremos esto
def calculate_file_hash(file_path: Path) -> str:
    """
    Calcula el hash MD5 de un archivo para verificar integridad.
    
    Args:
        file_path (Path): Ruta del archivo
        
    Returns:
        str: Hash MD5 del archivo
    """
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


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


def create_upload_request(filename: str, file_size: int, protocol: str, window_size: int = 1) -> bytes:
    """
    Crea un mensaje de solicitud de upload usando las funciones del protocolo.
    
    Args:
        filename (str): Nombre del archivo
        file_size (int): Tamaño del archivo en bytes
        protocol (str): Protocolo a usar ("stop-and-wait" o "go-back-n")
        window_size (int): Tamaño de ventana
        
    Returns:
        bytes: Mensaje de solicitud formateado
    """
    proto_code = PROTO_STOP_WAIT if protocol == "stop-and-wait" else PROTO_GBN
    return build_request_upload(filename, file_size, proto_code, window_size, CHUNK_SIZE)
