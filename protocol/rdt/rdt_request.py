from enum import Enum
from ..dp.dp_request import DPRequest

class FunctionFlag(Enum):
    NONE = 0
    CLOSE_CONN = 1

class RDTRequest:
    """
    {ack flag}{sequence number}|{reference number}_{data [X, HTTP]}
    """
    def __init__(self, raw: bytes):
        # Ack flag: "0" o "1"
        if raw[0:1] not in (b"0", b"1"):
            raise ValueError("Invalid ack flag, must be '0' or '1'")
        self.ack_flag = raw[0:1] == b"1"

        # Buscar separadores
        pipe_idx = raw.index(b"|")
        us_idx = raw.index(b"_", pipe_idx)

        # Sequence number (entre flag y "|")
        self.sequence_number = int(raw[1:pipe_idx])

        # Reference number (entre "|" y "_")
        self.reference_number = int(raw[pipe_idx + 1:us_idx])

        # data: lo que queda después del "_"
        self.data = raw[us_idx + 1:]

    @classmethod
    def from_dp_request(cls, dp: DPRequest, seq: int, ref: int, ack: bool = False):
        """
        Construye un RDTRequest a partir de un DPRequest.
        """
        data = dp.serialize()
        ack_flag = "1" if ack else "0"
        raw = f"{ack_flag}{seq}|{ref}_".encode() + data
        return cls(raw)

    def serialize(self) -> bytes:
        """
        Devuelve el formato final en bytes para enviar por UDP.
        """
        ack_flag = b"1" if self.ack_flag else b"0"
        header = f"{ack_flag.decode()}{self.sequence_number}|{self.referencenumber}_".encode()
        return header + self.data

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