from enum import Enum

class FunctionFlag(Enum):
    NONE = 0
    CLOSE_CONN = 1

class RDTRequest:
    """
    {ack flag}{sequence number}|{reference number}_{data [X, HTTP]}
    """
    def __init__(self, raw: bytes):
        # Ack flag: "0" o "1"
        self.ack_flag: bool = raw[0:1] == b"1"

        # Buscar separadores
        pipe_idx = raw.index(b"|")
        us_idx = raw.index(b"_", pipe_idx)

        # Sequence number (entre flag y "|")
        self.sequence_number: int = int(raw[1:pipe_idx])

        # Reference number (entre "|" y "_")
        self.reference_number: int = int(raw[pipe_idx + 1:us_idx])

        # data: lo que queda después del "_"
        self.data: bytes = raw[us_idx + 1:]




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