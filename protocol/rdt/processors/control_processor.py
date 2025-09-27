"""
Processor para requests de control (creación de conexiones).
Se encarga únicamente de: llegada → procesamiento → envío de respuesta.
"""

from ...dp.dp_control_request import DPControlRequest
from ...const import ctrl_parse, OP_REQUEST_UPLOAD, OP_REQUEST_DOWNLOAD, OP_UPLOAD_ACCEPTED, OP_DOWNLOAD_ACCEPTED

class ControlRequestProcessor:
    """
    Procesa requests de control para creación de conexiones.
    Se encarga únicamente de: llegada → procesamiento → envío de respuesta.
    """
    
    @staticmethod
    def is_valid_control_opcode(opcode: int) -> bool:
        """Verifica si el opcode de control es válido para creación de conexión"""
        return opcode in [OP_REQUEST_UPLOAD, OP_REQUEST_DOWNLOAD]
    
    @staticmethod
    def parse_control_payload(payload: bytes) -> tuple[int, list]:
        """Parsea el payload de control y retorna opcode y TLVs"""
        try:
            return ctrl_parse(payload)
        except Exception as e:
            print(f"[CTRL] Error al parsear control: {e}")
            raise
    
    @staticmethod
    def create_dp_request(opcode: int, tlvs: list, sid: int) -> DPControlRequest:
        """Crea un DP request desde un mensaje de control"""
        return DPControlRequest(
            opcode=opcode,
            tlvs=tlvs,
            sid=sid
        )
    
    @staticmethod
    def get_accepted_opcode(request_opcode: int) -> int:
        """Mapea el opcode de request al opcode de accepted correspondiente"""
        if request_opcode == OP_REQUEST_UPLOAD:
            return OP_UPLOAD_ACCEPTED
        elif request_opcode == OP_REQUEST_DOWNLOAD:
            return OP_DOWNLOAD_ACCEPTED
        else:
            raise ValueError(f"No hay opcode de accepted para: {request_opcode}")
    
    @staticmethod
    def process_control_request(opcode: int, tlvs: list, sid: int) -> tuple[DPControlRequest, int]:
        """
        Procesa una request de control completa.
        Retorna: (DP request, opcode de accepted)
        """
        # 1. Validar opcode
        if not ControlRequestProcessor.is_valid_control_opcode(opcode):
            raise ValueError(f"Opcode de control no reconocido: {opcode}")
        
        # 2. Crear DP request
        dp_request = ControlRequestProcessor.create_dp_request(opcode, tlvs, sid)
        print(f"[CTRL] DP request creado: Opcode {dp_request.opcode}, SID {dp_request.sid}")
        
        # 3. Obtener opcode de accepted
        accepted_opcode = ControlRequestProcessor.get_accepted_opcode(opcode)
        print(f"[CTRL] Opcode de accepted: {accepted_opcode}")
        
        # 4. Procesar la request (aquí se implementaría la lógica de negocio)
        # Por simplicidad, asumimos que siempre se acepta la request
        print(f"[CTRL] Request de control procesada exitosamente")
        
        return dp_request, accepted_opcode
