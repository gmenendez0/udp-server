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
        return pack_header(self.type, self.flags, self.wnd, self.seq, self.sid, self.len, self.payload)

    @classmethod
    def from_dp_request(cls, dp: DPRequest, seq: int, ref: int, ack: bool = False):
        """
        Construye un RDTRequest a partir de un DPRequest.
        """
        pass

"""
# ? LO QUE VIMOS AYER
{ack flag}{function flag}{sequence number}|{reference number}_{uuid}_{data}

1. Manejar acks, entrega garantiza, entrega en orden, evitar duplicados,

# ? UDP

# ? RDT
{ack flag}{sequence number}|{reference number}_{data [X, HTTP]}
1. Manejar acks, entrega garantiza, entrega en orden, evitar duplicados

# ? Protocolo de datos X
{function flag}_{uuid}_payload
logica de negocio

# 1. Hacer RDTRequest
- ack flag
- seqNumber
- refNumber
- data: []bytes
# 2. Hacer DPRequest (data protocol request)
# 3. DPRequestHandler
# 4. RDTRequestHandler
"""