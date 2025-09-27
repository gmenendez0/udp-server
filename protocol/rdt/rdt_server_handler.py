"""
Manejador simplificado de paquetes RDT.
Solo maneja la llegada, procesamiento y envío para creación de conexiones.
Devuelve RDTRequest con tipo REQUEST_ACCEPTED.
"""

from typing import Optional, Tuple
from ..const import unpack_header, T_CTRL
from .rdt_request import RDTRequest
from .connection_manager import ConnectionManager
from .processors import ControlRequestProcessor
from ..data_flow import DataFlowProcessor

# TODO: Manejo de errores, y que tmb el getters 
# TODO: data handler ( bytes -> manager -> response Bytes)

class RdtServerHandler:
    """
    Maneja únicamente el procesamiento de paquetes de control para creación de conexiones.
    Flujo: llegada → procesamiento → envío de RDTRequest con REQUEST_ACCEPTED.
    """
    
    def __init__(self):
        self.connection_manager = ConnectionManager()
        self.control_processor = ControlRequestProcessor()
        self.data_flow_processor = DataFlowProcessor()
    
    def handle_datagram(self, address: Tuple[str, int], data: bytes) -> Optional[bytes]:
        """
        Maneja un datagrama recibido.
        Solo procesa paquetes de control para creación de conexiones.
        Devuelve RDTRequest serializada con tipo REQUEST_ACCEPTED.



        response = data_handler(data)
        send_response(response)
        """
        print(f"[RDT] Procesando datagrama de {address}, tamaño: {len(data)} bytes")
        
        # 1. PARSEAR PAQUETE RDT
        rdt_request = self._parse_rdt_packet(address, data)
        if rdt_request is None:
            return None

        # 2. SOLO PROCESAR PAQUETES DE CONTROL -> POR AHORA, LA IDEA ES METER ACA PARTE DE LA LOGICA DE DATAFLOW
        if rdt_request.type != T_CTRL:
            print(f"[RDT] Ignorando paquete no de control: tipo {rdt_request.type}")
            return None

        # 3. PROCESAR CONTROL PARA CREACIÓN DE CONEXIÓN
        return self._handle_control_for_connection(address, rdt_request)

    def _parse_rdt_packet(self, address: Tuple[str, int], data: bytes) -> Optional[RDTRequest]:
        """Parsea un paquete RDT y retorna RDTRequest o None si hay error"""
        try:
            header = unpack_header(data)
            rdt_request = RDTRequest(header)
            print(f"[RDT] Paquete parseado - Tipo: {header['type']}, Seq: {header['seq']}, SID: {header['sid']}")
            return rdt_request
        except Exception as e:
            print(f"[RDT] Error al parsear paquete de {address}: {e}")
            return None

    def _handle_control_for_connection(self, address: Tuple[str, int], rdt_request: RDTRequest) -> Optional[bytes]:
        """
        Maneja paquetes de control para creación de conexiones.
        Flujo: parsear control → crear conexión → procesar request → enviar REQUEST_ACCEPTED
        """
        try:
            # 1. Parsear payload de control
            opcode, tlvs = self.control_processor.parse_control_payload(rdt_request.payload)
            print(f"[RDT] Control parseado - Opcode: {opcode}")
            
            # 2. Validar que es un opcode válido para creación de conexión
            if not self.control_processor.is_valid_control_opcode(opcode):
                print(f"[RDT] Opcode no válido para creación de conexión: {opcode}")
                return None
            
            # 3. Crear nueva conexión
            print(f"[RDT] Creando nueva conexión para {opcode} desde {address}")
            connection = self.connection_manager.create_connection(address, rdt_request.sid)
            
            # 4. Procesar request de control
            dp_request, accepted_opcode = self.control_processor.process_control_request(opcode, tlvs, connection.sid)

            # No esta la verificaicon de la data, solo acepta el request de control
            
            # 5. Crear RDTRequest de respuesta con REQUEST_ACCEPTED
            response_rdt = self._create_request_accepted_response(connection.sid, rdt_request.seq, accepted_opcode)
            
            # 6. Serializar y enviar respuesta
            response_bytes = response_rdt.serialize() + response_rdt.payload
            print(f"[RDT] Enviando REQUEST_ACCEPTED para SID {connection.sid}, Seq {rdt_request.seq}, Opcode {accepted_opcode}")
            
            return response_bytes
            
        except Exception as e:
            print(f"[RDT] Error al procesar control para conexión: {e}")
            return None

    def _create_request_accepted_response(self, sid: int, ack_seq: int, accepted_opcode: int) -> RDTRequest:
        """Crea una RDTRequest de respuesta con tipo REQUEST_ACCEPTED"""
        # Crear payload de control con el opcode de accepted
        from ..const import ctrl_build
        control_payload = ctrl_build(accepted_opcode, [])
        
        # Crear header para la respuesta
        response_header = {
            'type': T_CTRL,  # Tipo control
            'flags': 0,      # Sin flags especiales
            'wnd': 0,        # Ventana por defecto
            'seq': ack_seq,  # ACK del número de secuencia recibido
            'sid': sid,      # SID de la conexión creada
            'len': len(control_payload),
            'payload': control_payload
        }
        
        return RDTRequest(response_header)


    # Métodos delegados al ConnectionManager
    def cleanup_old_connections(self):
        """Limpia conexiones inactivas"""
        self.connection_manager.cleanup_old_connections()

    def get_connection_count(self) -> int:
        """Retorna el número de conexiones activas"""
        return self.connection_manager.get_connection_count()
    
    def get_connection_manager(self) -> ConnectionManager:
        """Retorna el ConnectionManager para acceso directo si es necesario"""
        return self.connection_manager

    # Métodos delegados al ControlRequestProcessor
    
    def get_control_processor(self) -> ControlRequestProcessor:
        """Retorna el ControlRequestProcessor para acceso directo si es necesario"""
        return self.control_processor
    
    # Métodos delegados al DataFlowProcessor
    def get_data_flow_processor(self) -> DataFlowProcessor:
        """Retorna el DataFlowProcessor para acceso directo si es necesario"""
        return self.data_flow_processor
