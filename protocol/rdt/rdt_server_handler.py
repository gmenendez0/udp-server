#!/usr/bin/env python3
"""
RDT Server Handler - Se encarga solo del protocolo RDT (confiabilidad).
Delega la lógica de datos al DP Handler.
"""

from abc import ABC, abstractmethod
import time
from threading import Lock
from enum import Enum

from protocol.dp.dp_control_request import DPControlRequest
from protocol.rdt.rdt_request import RDTRequest
from ..const import unpack_header, ctrl_parse, T_CTRL, T_DATA, T_ACK, OP_REQUEST_UPLOAD, OP_REQUEST_DOWNLOAD, make_ack_packet, generate_new_sid
from ..dp.dp_request import DPRequest

# Automatic Repeat reQuest Protocols
class ARQProtocol(Enum):
    STOP_AND_WAIT = 1
    GO_BACK_N = 2

class RdtConnection:
    def __init__(self, seq_num: int, ref_num: int, arq_protocol: ARQProtocol):
        self.seq_num        = seq_num
        self.ref_num        = ref_num
        self.sid            = generate_new_sid()  # Session ID, asignado al crear la conexión
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



class RdtServerHandler:
    def __init__(self, connection_timeout: int = 5):
        self.connections = {}
        self.connections_lock = Lock()
        self.connection_timeout = connection_timeout
        self.socket = None  


    def set_socket(self, socket):
        """Asigna el socket para enviar respuestas"""
        self.socket = socket
    
    def handle_datagram(self, address: tuple, data: bytes) -> bytes:
        """
        Maneja un datagrama recibido.
        Retorna la respuesta a enviar al cliente.
        """
        print(f"[RDT] Procesando datagrama de {address}, tamaño: {len(data)} bytes")
        
        try:
            # Parsear el paquete RDT recibido
            header = unpack_header(data)
            rdt_request = RDTRequest(header)
            print(f"[RDT] Paquete parseado - Tipo: {header['type']}, Seq: {header['seq']}, SID: {header['sid']}")
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

                        if opcode in [OP_REQUEST_UPLOAD, OP_REQUEST_DOWNLOAD]:
                            print(f"[RDT] Creando nueva conexión para {opcode} desde {address} para upload/download")
                            connection = self._create_new_connection(address, rdt_request.sid)

                            # Manejar la request de control y obtener ACK
                            dp_request = self._create_dp_request_from_control(opcode, tlvs, connection.sid)
                            print(f"[RDT] Creando DP request desde control: Opcode {dp_request.opcode}, TLVs {dp_request.tlvs}, SID {dp_request.sid}")
                            # Aquí se debería llamar al DP handler para procesar la request
                            # Por simplicidad, asumimos que siempre se acepta la request

                            # Generar y retornar ACK de control - CORREGIDO
                            ack_packet = make_ack_packet(
                                sid=connection.sid,
                                ackno=rdt_request.seq  # ACK del número de secuencia recibido
                            )
                            print(f"[RDT] Enviando ACK de control para SID {connection.sid}, Seq {rdt_request.seq}")
                            return ack_packet
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
            if rdt_request.type == T_DATA:
                return self._handle_data_packet(connection, rdt_request)
            elif rdt_request.type == T_ACK:
                return self._handle_ack_packet(connection, rdt_request)
            else:
                print(f"[RDT] Tipo de paquete no soportado: {rdt_request.type}")
                return None

    def _create_dp_request_from_control(self, opcode: int, tlvs: list, sid: int) -> DPControlRequest:
        """Crea un DP request desde un mensaje de control"""
        # Extraer información de los TLVs
        filename = None
        for tlv_type, tlv_value in tlvs:
            if tlv_type == 0x01:  # TLV_FILENAME
                filename = tlv_value.decode('utf-8')
                break
        
        # Crear payload para DP
        if opcode == OP_REQUEST_UPLOAD:
            payload = f"upload_{filename}".encode()
        elif opcode == OP_REQUEST_DOWNLOAD:
            payload = filename.encode() if filename else b"download"
        else:
            payload = b"unknown"
        
        # Crear DP request
        dp_request = DPControlRequest(opcode, tlvs, sid)
        
        return dp_request

    def _handle_ack_packet(self, connection: RdtConnection, header: dict) -> bytes:
        """Maneja paquetes ACK (no debería recibirse en servidor)"""
        print(f"[RDT] Servidor recibió ACK inesperado de sesión {connection.sid}")
        return None

    def _create_new_connection(self, address: tuple, sid: int) -> RdtConnection:
        """Crea una nueva conexión RDT"""
        connection = RdtConnection(
            seq_num=0, 
            ref_num=sid,  # Usar el SID como ref_num
            arq_protocol=ARQProtocol.STOP_AND_WAIT
        )
        self.connections[address] = connection
        return connection

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


def create_rdt_server_handler(connection_timeout: int = 5):
    """Factory function para crear el RDT server handler"""
    return RdtServerHandler(connection_timeout)
