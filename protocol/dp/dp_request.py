from enum import Enum

class FunctionFlag(Enum):
    NONE = 0
    CLOSE_CONN = 1

class DPRequest:
    """
    {function flag}_{uuid}_payload
    """
    def __init__(self, raw: bytes):
        # Separadores
        first_us_idx = raw.index(b"_")
        second_us_idx = raw.index(b"_", first_us_idx + 1)

        # Function flag (un dígito al inicio)
        func_value = int(raw[:first_us_idx])
        try:
            self.function_flag: FunctionFlag = FunctionFlag(func_value)
        except ValueError:
            self.function_flag: FunctionFlag = FunctionFlag.NONE

        # UUID
        self.uuid: str = raw[first_us_idx + 1:second_us_idx].decode()

        # Payload
        self.payload: bytes = raw[second_us_idx + 1:]

    @classmethod
    def from_user_input(cls, function_flag, uuid: str, payload: str):
        """
        Construye un DPRequest a partir de datos "lógicos" (lado cliente).
        """
        raw = f"{function_flag.value}{uuid}_{payload}".encode()
        return cls(raw)

    def serialize(self) -> bytes:
        """
        Devuelve el formato en bytes para enviar por red.
        """
        return f"{self.function_flag.value}{self.uuid}_{self.payload.decode()}".encode()
