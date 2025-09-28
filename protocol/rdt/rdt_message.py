class RdtMessage:
    def __init__(self, ack_flag: bool, max_window: int, seq_num: int, ref_num: int, data: bytes):
        self.ack_flag:      bool    = ack_flag
        self.max_window:    int     = max_window
        self.seq_num:       int     = seq_num
        self.ref_num:       int     = ref_num
        self.data:          bytes   = data

    #[ACK_BYTE][MAX WINDOW BYTE][SEQ_NUM][REF_NUM]_[DATA]
    #ACK_BYTE: 0 = DATA, 1 = ACK
    #MAX WINDOW BYTE: 0 = STOP AND WAIT, >1 = GO BACK N
    #[SEQ_NUM]: 4 bytes
    #[REF_NUM]: 4 bytes
    @classmethod
    def from_bytes(cls, raw: bytes) -> "RdtMessage":
        # ACK Flag  = primer byte
        ack_flag = raw[0] == 1
        # MaxWindow = segundo byte
        max_window = int.from_bytes(raw[1:2], byteorder="big")
        # Seq Num   = tercer a sexto byte (inclusive)
        seq_num = int.from_bytes(raw[2:6], byteorder="big")
        # Ref Num   = septimo a decimo byte (inclusive)
        ref_num = int.from_bytes(raw[6:10], byteorder="big")
        # Data      = decimo primer byte en adelante (inclusive)
        data = raw[10:]

        return cls(ack_flag, max_window, seq_num, ref_num, data)

    def to_bytes(self) -> bytes:
        # Armamos el ack byte
        ack_byte = b'\x01' if self.ack_flag else b'\x00'
        # Armamos el max window byte
        max_window_byte = self.max_window.to_bytes(1, byteorder='big')
        # Armamos el seq num bytes
        seq_num_bytes = self.seq_num.to_bytes(4, byteorder='big')
        # Armamos el ref num bytes
        ref_num_bytes = self.ref_num.to_bytes(4, byteorder='big')

        # Concatenamos
        return ack_byte + max_window_byte + seq_num_bytes + ref_num_bytes + self.data

class RdtResponse:
    def __init__(self, ack_flag: bool, max_window: int, seq_num: int, ref_num:int, data: bytes):
        self.message = RdtMessage(ack_flag, max_window, seq_num, ref_num, data)

    @classmethod
    def new_ack_response(cls, max_window: int, seq_num: int, ref_num: int) -> "RdtResponse":
        return cls(ack_flag=True, max_window=max_window, seq_num=seq_num, ref_num=ref_num, data=b'')

    @classmethod
    def new_data_response(cls, max_window: int, seq_num: int, ref_num: int, data: bytes) -> "RdtResponse":
        return cls(ack_flag=False, max_window=max_window, seq_num=seq_num, ref_num=ref_num, data=data)

    def to_bytes(self) -> bytes:
        return self.message.to_bytes()

class RdtRequest:
    def __init__(self, address: str, request: bytes):
        self.address: str = address
        self.message = RdtMessage.from_bytes(request)

    def is_ack(self) -> bool:
        return self.message.ack_flag

    def get_ref_num(self) -> int:
        return self.message.ref_num

    def get_seq_num(self) -> int:
        return self.message.seq_num

    def get_max_window(self) -> int:
        return self.message.max_window