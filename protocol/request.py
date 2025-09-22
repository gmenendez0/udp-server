from enum import Enum

class FunctionFlag(Enum):
    NONE = 0
    CLOSE_CONN = 1

class RDTRequest:
    def __init__(self, raw: bytes):
        # Ack flag: "0" o "1"
        self.ack_flag: bool = raw[0:1] == b"1"

        # Function flag
        func_value = int(raw[1:2].decode())
        try:
            self.function_flag: FunctionFlag = FunctionFlag(func_value)
        except ValueError:
            self.function_flag: FunctionFlag = FunctionFlag.NONE

        # Índices de separadores
        pipe_idx = raw.index(b'|')
        first_us_idx = raw.index(b'_', pipe_idx)
        second_us_idx = raw.index(b'_', first_us_idx + 1)

        # Sequence number (texto hasta el '|')
        self.sequence_number: int = int(raw[2:pipe_idx].decode())

        # Reference number (texto entre | y _)
        self.reference_number: int = int(raw[pipe_idx + 1:first_us_idx].decode())

        # UUID (entre _ y segundo _)
        self.uuid: str = raw[first_us_idx + 1:second_us_idx].decode()

        # Data (resto después del segundo _)
        self.payload: str = raw[second_us_idx + 1:].decode()
