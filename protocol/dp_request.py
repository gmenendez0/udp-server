from enum import Enum

class FunctionFlag(Enum):
    NONE = 0
    CLOSE_CONN = 1

class DPRequest:
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
