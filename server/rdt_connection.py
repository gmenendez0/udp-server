import os
import threading
from abc import ABC, abstractmethod
from queue import Queue, Empty

from server.file_helpers import get_file_size_in_bytes, get_file_in_chunks, append_bytes_to_file
from protocol.rdt.rdt_message import RdtRequest, RdtResponse
from typing import Optional, Dict, List
import time
import logging
import socket

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SERVER_SEQ_NUM_START = 0
CONNECTION_TIMEOUT = 7.0            # Segundos de timeout de conexión
STORAGE_PATH = "files"
MAX_FILE_SIZE = 5_500_000           # 5.5MB
RETRANSMISSION_TIMEOUT = 2.0        # Segundos para el timeout de retransmisión
MAX_RETRANSMISSION_ATTEMPTS = 5     # Máximo de intentos de retransmisión
CHUNK_SIZE = 1024                   # Leer archivo en chunks de 1KB
UPLOAD_COMMAND = 'U'
DOWNLOAD_COMMAND = 'D'
FAST_RETRANSMIT_THRESHOLD = 3       # Número de ACKs duplicados para activar fast retransmit

class RdtConnection:
    def __init__(self, address: str):
        self.address                    : str               = address
        self.seq_num                    : Optional[int]     = None
        self.ref_num                    : Optional[int]     = None
        self.max_window                 : Optional[int]     = None

        self.request_queue              : Queue[bytes]      = Queue()
        self.is_active                  : bool              = True
        self.connection_established     : bool              = False
        self.packets_on_fly             : list[RdtResponse] = []
        self.last_activity              : float             = time.time()

        self.current_operation          : Optional[str]     = None  # "UPLOAD" o "DOWNLOAD"
        self.current_filename           : Optional[str]     = None
        self.current_filesize           : Optional[int]     = None   # in bytes
        self.bytes_sent                 : Optional[int]     = None
        self.bytes_received             : Optional[int]     = None
        self.pending_data_chunks        : List[bytes]       = []

        self.base_seq                   : Optional[int]     = 0

        self.retransmission_timer       : Optional[threading.Timer] = None
        self.retransmission_attempts    : int = 0

        self.duplicate_ack_count        : int = 0
        self.last_ack_num               : Optional[int] = None

    def add_request(self, data: bytes) -> None:
        self.request_queue.put(data)

    def shutdown(self) -> None:
        logger.info(f"Iniciando shutdown de conexión {self.address}")

        while not self.request_queue.empty():
            self.request_queue.get_nowait()
        self.is_active = False

        self._stop_retransmission_timer()

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

    def _process_message(self, request: bytes) -> None:
        rdt_request = RdtRequest(address=self.address, request=request)

        if not self.connection_established:
            return self._handle_handshake_message(rdt_request)

        if rdt_request.is_ack():
            self._handle_ack_message(rdt_request)
        elif rdt_request.is_data():
            self._handle_data_message(rdt_request)

    def _handle_handshake_message(self, rdt_request: RdtRequest) -> None:
        """Maneja mensajes de handshake"""
        if not rdt_request.is_valid_handshake_message():
            logger.error(f"Request de handshake inválido de {self.address}. Ignorando.")
            self.shutdown()
            return

        logger.info(f"Handshake recibido de {self.address} with max_window: {rdt_request.get_max_window()}, seq_num: {rdt_request.get_seq_num()}")

        self.max_window = rdt_request.get_max_window()
        self.ref_num = rdt_request.get_seq_num() + 1
        self.seq_num = SERVER_SEQ_NUM_START

        self._send_handshake_ack()
        self.connection_established = True

    def _send_handshake_ack(self) -> None:
        ack_response = RdtResponse.new_ack_response(self.max_window, self.seq_num, self.ref_num)
        self._send_response(ack_response.message.to_bytes()) #Usamos send_response y no _send_ack porque no queremos incrementar el seq_num
        logger.info(f"ACK de handshake enviado a {self.address}")

    def _handle_data_message(self, rdt_request: RdtRequest) -> None:
        data = rdt_request.get_data().decode('utf-8')
        logger.info(f"Datos recibidos de {self.address}: {data}")

        # Determinar operacion a ejecutar
        parts = data.split()

        if parts[0] == DOWNLOAD_COMMAND:
            filename = parts[1]
            self._handle_download_request(filename, rdt_request)
        elif parts[0] == UPLOAD_COMMAND:
            filename = parts[1]
            filesize = int(parts[2])
            self._handle_upload_request(filename, filesize, rdt_request)
        elif self.current_operation == "UPLOAD":
            self._handle_upload_data(rdt_request)

    def _handle_upload_request(self, filename: str, filesize: int, rdt_request: RdtRequest) -> None:
        logger.info(f"Solicitud de subida de {self.address} para el archivo {filename} de tamaño {filesize}")

        # Enviamos ACK del request
        self._send_ack_response(rdt_request.get_seq_num() + 1)

        # Verificamos que el archivo que se quiere subir no este ya presente y que no exceda el tamaño maximo permitido
        filepath = os.path.join(STORAGE_PATH, filename)
        file_already_exists = get_file_size_in_bytes(filepath) is not None

        if file_already_exists:
            logger.error(f"Archivo {filename} ya existe para {self.address}")
            self._send_error_response(b'FILE_ALREADY_EXISTS')
            self.shutdown()
            return

        if filesize > MAX_FILE_SIZE:
            logger.error(f"Archivo {filename} demasiado grande ({filesize}) para {self.address}")
            self._send_error_response(b'FILE_TOO_LARGE')
            self.shutdown()
            return

        # Preparamos la conexion para la subida
        self.current_operation = "UPLOAD"
        self.current_filename = filename
        self.current_filesize = filesize
        self.bytes_received = 0

        # Creamos la respuesta de ok y la enviamos
        ok_res = RdtResponse.new_data_response(self.max_window, self.seq_num, self.ref_num, b"D_OK")
        self._send_response(ok_res.message.to_bytes())

        # Enviada la respuesta de ok, actualizamos el seq_num y marcamos el paquete como en vuelo y prendemos el timer de retransmision
        self.seq_num += 1
        self.packets_on_fly.append(ok_res)
        self._start_retransmission_timer()

        logger.info(f"Preparado para recibir archivo {filename} de tamaño {filesize} de {self.address}")

    def _handle_upload_data(self, rdt_request: RdtRequest) -> None:
        # Obtener la data del archivo
        data = rdt_request.get_data()
        file_data = data[2:]  # Sacar el prefijo "D_"

        # Appendear los bytes al archivo
        filepath = os.path.join(STORAGE_PATH, self.current_filename)
        append_bytes_to_file(filepath, file_data)

        # Actualizar el contador de bytes recibidos
        self.bytes_received += len(file_data)
        logger.info(f"Recibidos {self.bytes_received}/{self.current_filesize} bytes de {self.address} para el archivo {self.current_filename}")

        # Enviar ACK
        self._send_ack_response(rdt_request.get_seq_num() + 1)

        # Verificar si la transferencia está completa. En caso que si, cerrar la conexion
        if rdt_request.is_last() or self.bytes_received >= self.current_filesize:
            logger.info(f"Archivo {self.current_filename} recibido completamente de {self.address}")
            self.shutdown()

    def _handle_download_request(self, filename: str, rdt_request: RdtRequest) -> None:
        logger.info(f"Solicitud de descarga de {self.address} para el archivo {filename}")

        # ? server.refNum = 1
        # ? server.seqNum = 0

        # Enviar ACK del request
        self._send_ack_response(rdt_request.get_seq_num() + 1)

        # ? server.refNum = 2
        # ? server.seqNum = 1

        # Verificar que el archivo exista
        filepath = os.path.join(STORAGE_PATH, filename)
        filesize = get_file_size_in_bytes(filepath)

        # Si no existe, respondemos con error y cerramos la conexion
        if filesize is None:
            logger.error(f"Archivo {filename} no encontrado para {self.address}")
            self._send_error_response(b'FILE_NOT_FOUND')
            self.shutdown()
            return

        # Si existe, preparamos la transferencia
        self.current_operation = "DOWNLOAD"
        self.current_filename = filename
        self.current_filesize = filesize
        self.bytes_sent = 0

        # Cargamos el archivo a memoria
        logger.info(f"Cargando archivo {filename} en memoria de tamaño {filesize} para {self.address}.")
        self.pending_data_chunks = get_file_in_chunks(filepath, CHUNK_SIZE)
        logger.info(f"Archivo {filename} cargado en memoria. Listo para enviar {len(self.pending_data_chunks)} chunks.")

        # Enviar ventana inicial
        self._send_window_packages()

    def _send_window_packages(self) -> None:
        packets_sent = 0

        # Mientras haya espacio en la ventana para enviar mas paquetes y queden paquetes para enviar...
        while len(self.packets_on_fly) < self.max_window and len(self.pending_data_chunks) > 0:
            # Obtengo el chunk a enviar y le agrego el prefijo de data
            chunk = self.pending_data_chunks.pop(0)
            data_with_prefix = b"D_" + chunk

            # Encapsulo la data en una RdtResponse
            is_last = len(self.pending_data_chunks) == 0
            if not is_last:
                response = RdtResponse.new_data_response(self.max_window, self.seq_num, self.ref_num, data_with_prefix)
            else:
                response = RdtResponse.new_last_response(self.max_window, self.seq_num, self.ref_num, data_with_prefix)

            # Envio la respuesta
            self._send_response(response.message.to_bytes())

            # Marco la respuesta como en vuelo
            self.packets_on_fly.append(response)

            # Si es el primer paquete enviado, actualizo la base de la ventana
            if self.base_seq == 0 and packets_sent == 0:
                self.base_seq = self.seq_num

            # Actualizo contadores
            self.seq_num += 1
            self.bytes_sent += len(chunk)
            packets_sent += 1

            logger.info(f"Paquete enviado a {self.address} con seq_num {self.seq_num}. Total bytes enviados: {self.bytes_sent}/{self.current_filesize}")

        # Si se envio algun paquete y no habia un timer previo activo, iniciarlo
        if packets_sent > 0 and self.retransmission_timer is None:
            self._start_retransmission_timer()

    def _handle_ack_message(self, rdt_request: RdtRequest) -> None:
        ack_num = rdt_request.get_ref_num()
        logger.info(f"ACK recibido de {self.address} con ref_num {ack_num}")

        # Si estamos en download
        if self.current_operation == "DOWNLOAD":
            # Si me estan ackeando un paquete el cual no es el base de la ventana:
            if ack_num > self.base_seq:
                # Quitamos de on fly aquellos paquetes que nos indica el cliente que llegaron
                self.packets_on_fly = [pkt for pkt in self.packets_on_fly if pkt.message.seq_num >= ack_num]

                # Actualizamos la base de la ventana
                self.base_seq = ack_num

                # Reiniciamos el contador de reintentos
                self.retransmission_attempts = 0
                self.duplicate_ack_count = 0
                self.last_ack_num = ack_num

                # Frenamos el timer y si quedan paquetes en vuelo, lo iniciamos otra vez
                self._stop_retransmission_timer()
                if len(self.packets_on_fly) > 0:
                    self._start_retransmission_timer()

                # Enviamos más paquetes si hay espacio en la ventana
                self._send_window_packages()
            # Si me estan ackeando el paquete base de la ventana:
            elif ack_num == self.base_seq:
                # Si last_ack_num es igual al ack_num, es un ACK duplicado
                if self.last_ack_num == ack_num:
                    self.duplicate_ack_count += 1
                    logger.warning(f"ACK Duplicado recibido de {self.address} con ref_num {ack_num}. Contador de duplicados: {self.duplicate_ack_count}")

                    if self.duplicate_ack_count >= FAST_RETRANSMIT_THRESHOLD:
                        self._fast_retransmit()
                # Si no, es el primer ACK duplicado que recibimos
                else:
                    logger.warning(f"Primer ACK duplicado recibido de {self.address} con ref_num {ack_num}.")
                    self.duplicate_ack_count = 1
                    self.last_ack_num = ack_num
            # Si no:
            else:
                logger.warning(f"ACK fuera de orden recibido de {self.address} con ref_num {ack_num}. Ignorando")

            # Si no quedan paquetes en vuelo y no hay más datos por enviar, cerrar conexión
            if len(self.packets_on_fly) == 0 and len(self.pending_data_chunks) == 0:
                logger.info(f"Todos los datos enviados y ACKs recibidos para {self.address}. Cerrando conexión.")
                self.shutdown()
        # Si estamos en el upload, solamente se deberia recibir un ack de parte del cliente correspondiente al paq "D_OK"
        elif self.current_operation == "UPLOAD":
            # Quitamos de on fly el paquete "D_OK" y matamos su timer
            self.packets_on_fly.clear()
            self._stop_retransmission_timer()
            logger.info(f"ACK de subida recibido de {self.address}. Esperando datos del cliente.")

    def _fast_retransmit(self) -> None:
        logger.info(f"Fast retransmit activado para {self.address}.")

        # Reiniciar contador de ACKs duplicados
        self.duplicate_ack_count = 0

        # Retransmitir todos los paquetes en vuelo
        for packet in self.packets_on_fly:
            self._send_response(packet.message.to_bytes())
            logger.info(f"Paquete retransmitido a {self.address} con seq_num {packet.message.seq_num}")

        # Frenar el timer
        self._stop_retransmission_timer()

        # Si quedan paquetes en vuelo, reiniciar el timer
        if len(self.packets_on_fly) > 0:
            self._start_retransmission_timer()

    def _start_retransmission_timer(self) -> None:
        if self.retransmission_timer:
            self.retransmission_timer.cancel()

        self.retransmission_timer = threading.Timer(RETRANSMISSION_TIMEOUT, self._handle_retransmission_timeout)
        self.retransmission_timer.start()

    def _stop_retransmission_timer(self) -> None:
        if self.retransmission_timer:
            self.retransmission_timer.cancel()
            self.retransmission_timer = None

    def _handle_retransmission_timeout(self) -> None:
        if not self.is_active:
            return

        self.retransmission_attempts += 1

        # Verificar si se supero el maximo de reintentos
        if self.retransmission_attempts > MAX_RETRANSMISSION_ATTEMPTS:
            logger.error(f"Máximo de intentos de retransmisión alcanzado para {self.address}. Cerrando conexión.")
            self.shutdown()
            return

        logger.warning(f"Timeout de retransmisión para {self.address}.")

        # Retransmitir todos los paquetes en vuelo
        if len(self.packets_on_fly) > 0:
            for packet in self.packets_on_fly:
                self._send_response(packet.message.to_bytes())
                logger.info(f"Paquete retransmitido a {self.address} con seq_num {packet.message.seq_num}")

            # Reiniciar el timer
            self._start_retransmission_timer()
        else:
            logger.warning(f"No hay paquetes para retransmitir a {self.address}.")

    def _send_ack_response(self, ref_num: int) -> None:
        self.ref_num = ref_num
        ack_response = RdtResponse.new_ack_response(self.max_window, self.seq_num, self.ref_num)
        self._send_response(ack_response.message.to_bytes())
        self.seq_num += 1
        logger.info(f"ACK enviado a {self.address} con ref_num {ref_num}")

    def _send_data_response(self, data: bytes) -> None:
        data_response = RdtResponse.new_data_response(self.max_window, self.seq_num, self.ref_num, data)
        self._send_response(data_response.message.to_bytes())
        logger.info(f"Data response enviado a {self.address} con seq_num {self.seq_num}")
        self.seq_num += 1

    def _send_error_response(self, data: bytes) -> None:
        data_response = RdtResponse.new_data_response(self.max_window, self.seq_num, self.ref_num, b"E_" + data)
        self._send_response(data_response.message.to_bytes())
        logger.info(f"Error response enviado a {self.address} con seq_num {self.seq_num}")
        self.seq_num += 1

    def _send_response(self, data: bytes) -> None:
        host, port = self.address.split(":")
        skt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        skt.sendto(data, (host, int(port)))
        skt.close()

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
