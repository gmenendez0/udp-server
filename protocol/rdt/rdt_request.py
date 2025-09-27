from enum import Enum
from ..dp.dp_request import DPRequest
from ..const import pack_header, unpack_header

class FunctionFlag(Enum):
    NONE = 0
    CLOSE_CONN = 1

class RDTRequest:
    """
    Offset  Size  Campo   Descripción
    0       1     TYPE    0x00=DATA | 0x01=ACK | 0x02=CTRL
    1       1     FLAGS   bit0: LAST (1=último DATA) | bit1: ERR (opcional)
    2       1     WND     0=Stop&Wait | N=Go-Back-N (N es el tamaño de la ventana)
    3       4     SEQ     DATA: número de secuencia; ACK: next_expected (ack acumulativo)
    7       8     SID     Session-ID (uint64) — identificador de sesión/transacción
    15      2     LEN     Longitud del payload en bytes (0..65535) — 0 si es CTRL
    17      LEN   PAYLOAD Bytes de datos o control

    """
    def __init__(self, header: dict):
        """
        Constructor que recibe un diccionario con los campos del header.
        El diccionario debe tener las claves: type, flags, wnd, seq, sid, len, payload
        """
        self.type = header["type"]
        self.flags = header["flags"]
        self.wnd = header["wnd"]
        self.seq = header["seq"]
        self.sid = header["sid"]
        self.len = header["len"]
        self.payload = header["payload"]

    def serialize(self) -> bytes:
        """
        Devuelve el formato final en bytes para enviar por UDP.
        """
        return pack_header(self.type, self.flags, self.wnd, self.seq, self.sid, self.payload)

    @classmethod
    def from_dp_request(cls, dp: DPRequest, seq: int, ref: int, ack: bool = False):
        """
        Construye un RDTRequest a partir de un DPRequest.
        """
        pass

    @classmethod
    def from_bytes(cls, data: bytes):
        """
        Crea un RDTRequest a partir de bytes usando unpack_header.
        """
        header = unpack_header(data)
        return cls(header)
