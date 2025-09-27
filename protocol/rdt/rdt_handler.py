from abc import ABC, abstractmethod
from enum import Enum
from .rdt_request import RDTRequest
from ..const import OP_REQUEST_DOWNLOAD, OP_REQUEST_UPLOAD, T_CTRL, T_DATA, T_ACK, ctrl_parse, unpack_header
from ..const import make_ack_packet
import threading
import time
import random

# Damos por sentado un formato de, para un cliente, una request y luego una response.
# Es decir, no puede darse el caso de un cliente (ip+port) que manda dos requests sin esperar response entre medio.

# ? Automatic Repeat reQuest Protocols
class ARQProtocol(Enum):
    STOP_AND_WAIT = 1
    GO_BACK_N = 2

class RdtConnection:
    def __init__(self, seq_num: int, ref_num: int, arq_protocol: ARQProtocol):
        self.seq_num        = seq_num
        self.ref_num        = ref_num
        self.arqProtocol    = arq_protocol
        self.buffer         = bytearray()
        self.expected_seq   = 0  # Número de secuencia esperado para el siguiente paquete
        self.pending_packets = {}  # Diccionario para almacenar paquetes fuera de orden
        self.expected_length = None  # Longitud total esperada del mensaje (opcional)
        self.last_activity = time.time()  # Para timeout de conexión

class RdtConnectionRepository(ABC):
    @abstractmethod
    def get_connection(self, address: tuple) -> RdtConnection | None:
        pass

    @abstractmethod
    def remove_connection(self, address: tuple) -> None:
        pass

class MemoryRdtConnectionRepository(RdtConnectionRepository):
    def __init__(self):
        self.connections = {}

    def get_connection(self, address: tuple) -> RdtConnection | None:
        return self.connections.get(address, None)

    def remove_connection(self, address: tuple) -> None:
        if address in self.connections:
            del self.connections[address]

from threading import Lock

CONNECTION_TIMEOUT = 5

class RdtHandler:
    def __init__(self, connection_timeout: int = CONNECTION_TIMEOUT):
        self.connections = {}
        self.connections_lock = Lock()
        self.connection_timeout = connection_timeout

    def handle_datagram(self, address: tuple, data: bytes) -> None:
        # TODO: Implementar
        # 1. Check if connection exists for address
        # 2. If not, create new connection and store in connections dict
        # 3. Process data according to ARQ protocol

        # 3A. Envia ACK a cliente.
        # 3B. Chequea en connection.buffer si con el paquete recibido, los bytes ya se pueden subir a la capa de datos
        # 3C. Si se pueden subir, llama a data_handler.handle_data() con los bytes en orden y limpia connection.buffer
        #     Los bytes que devuelva data_handler.handle_data() deben wrappearse en una RDTRequest y enviarse a cliente como response.
        # 3D. Si no se pueden subir, guarda los bytes en connection.buffer y finaliza. 
        
        print(f"[RDT] Procesando datagrama de {address}, tamaño: {len(data)} bytes")
        
        try:
            # Parsear el paquete RDT recibido
            header = unpack_header(data)
            rdt_request = RDTRequest(header)
            print(f"[RDT] Paquete parseado - Seq: {rdt_request.seq}, Ref: {rdt_request.ref}, ACK: {rdt_request.ack_flag}, Last: {rdt_request.last_flag}")
        except Exception as e:
            print(f"[RDT] Error al parsear paquete de {address}: {e}")
            return None

        with self.connections_lock:
            # 1. Check if connection exists for address
            connection = self.connections.get(address, None)
            
            # 2. Si no existe conexión, verificar si es una request de control válida
            if connection is None:
                if rdt_request.type == T_CTRL:
                    # Parsear el payload de control
                    try:
                        opcode, tlvs = ctrl_parse(rdt_request.payload)
                        # Por el momento, solo upload hasta ver que funcione
                        if opcode == OP_REQUEST_UPLOAD :
                            print(f"[RDT] Creando nueva conexión para upload desde {address}")
                            connection = self._create_new_connection(address, rdt_request.sid)
                            return self._handle_upload_request(connection, tlvs)
                        else:
                            print(f"[RDT] Opcode de control no reconocido: {opcode}")
                            return None
                    except Exception as e:
                        print(f"[RDT] Error al parsear control: {e}")
                        return None
                else:
                    print(f"[RDT] Paquete sin conexión establecida: {rdt_request.type}")
                    return None
            else:
                # Actualizar actividad de la conexión
                connection.last_activity = time.time()
                print(f"[RDT] Usando conexión existente para {address}")

            # 3. Process data according to ARQ protocol
            #TODO
            

    def _create_new_connection(self, address: tuple, sid: int) -> RdtConnection:
        """Crea una nueva conexión RDT"""
        connection = RdtConnection(
            seq_num=0, 
            ref_num=sid,  # Usar el SID como ref_num
            arq_protocol=ARQProtocol.STOP_AND_WAIT
        )
        self.connections[address] = connection
        return connection

    def _handle_upload_request(self, connection: RdtConnection, tlvs: list) -> bytes:
        """Maneja una request de upload"""
        # Extraer información del archivo de los TLVs
        file_info = {}
        
        for tlv_type, tlv_value in tlvs:
            if tlv_type == 0x01:  # TLV_FILENAME
                file_info['filename'] = tlv_value.decode('utf-8')
            elif tlv_type == 0x02:  # TLV_FILESIZE
                import struct
                file_info['filesize'] = struct.unpack('>Q', tlv_value)[0]
            elif tlv_type == 0x03:  # TLV_PROTOCOL
                file_info['protocol'] = tlv_value[0]
        
        print(f"[RDT] Upload request - File: {file_info.get('filename', 'unknown')}, Size: {file_info.get('filesize', 0)}")
        
        # Crear respuesta de aceptación
        return make_ack_packet(connection.ref_num, connection.expected_seq)
        
    def cleanup_expired_connections(self):
        """Limpia conexiones expiradas"""
        current_time = time.time()
        with self.connections_lock:
            expired_addresses = []
            for address, connection in self.connections.items():
                if current_time - connection.last_activity > self.connection_timeout:
                    expired_addresses.append(address)
            
            for address in expired_addresses:
                del self.connections[address]
                print(f"[RDT] Conexión expirada removida: {address}")

