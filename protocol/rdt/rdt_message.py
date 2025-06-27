# FLAGS
FLAG_HANDSHAKE = 0
FLAG_ACK = 1
FLAG_DATA = 2
FLAG_LAST = 3

class RdtMessage:
    
    def __init__(self, flag: int, max_window: int, seq_num: int, ref_num: int, data: bytes):
        self.flag:          int     = flag # T_DATA, T_ACK, F_LAST
        self.max_window:    int     = max_window
        self.seq_num:       int     = seq_num
        self.ref_num:       int     = ref_num
        self.data:          bytes   = data
       

    #[FLAG_BYTE][MAX WINDOW BYTE][SEQ_NUM][REF_NUM][DATA]
    #FLAG_BYTE: T_DATA, T_ACK, F_LAST
    #MAX WINDOW BYTE: 1 = STOP AND WAIT, >1 = GO BACK N
    #[SEQ_NUM]: 8 bytes
    #[REF_NUM]: 8 bytes
    @classmethod
    def from_bytes(cls, raw: bytes) -> "RdtMessage":
        # Flag = primer byte
        flag = raw[0]  # 0, 1, 2, 3
        # MaxWindow = segundo byte
        max_window = int.from_bytes(raw[1:2], byteorder="big")
        # Seq Num = tercero a décimo byte (inclusive) - 8 bytes
        seq_num = int.from_bytes(raw[2:10], byteorder="big")
        # Ref Num = undécimo a decimoctavo byte (inclusive) - 8 bytes
        ref_num = int.from_bytes(raw[10:18], byteorder="big")
        # Data = decimonoveno byte en adelante (inclusive)
        data = raw[18:]

        return cls(flag, max_window, seq_num, ref_num, data)

    def to_bytes(self) -> bytes:
        # Armamos el flag byte
        flag_byte = self.flag.to_bytes(1, byteorder='big')
        # Armamos el max window byte
        max_window_byte = self.max_window.to_bytes(1, byteorder='big')
        # Armamos el seq num bytes
        seq_num_bytes = self.seq_num.to_bytes(8, byteorder='big')
        # Armamos el ref num bytes
        ref_num_bytes = self.ref_num.to_bytes(8, byteorder='big')

        # Concatenamos
        return flag_byte + max_window_byte + seq_num_bytes + ref_num_bytes + self.data

class RdtResponse:
    def __init__(self, flag: int, max_window: int, seq_num: int, ref_num: int, data: bytes):
        self.message = RdtMessage(flag, max_window, seq_num, ref_num, data)

    @classmethod
    def new_ack_response(cls, max_window: int, seq_num: int, ref_num: int) -> "RdtResponse":
        return cls(flag=FLAG_ACK, max_window=max_window, seq_num=seq_num, ref_num=ref_num, data=b'')

    @classmethod
    def new_data_response(cls, max_window: int, seq_num: int, ref_num: int, data: bytes) -> "RdtResponse":
        return cls(flag=FLAG_DATA, max_window=max_window, seq_num=seq_num, ref_num=ref_num, data=data)

    def is_last(self) -> bool:
        return self.message.flag == FLAG_LAST

class RdtRequest:
    def __init__(self, address: str, request: bytes):
        self.address = address
        self.message = RdtMessage.from_bytes(request)
    
    def is_data(self) -> bool:
        return self.message.flag == FLAG_DATA or self.message.flag == FLAG_LAST
    
    def is_ack(self) -> bool:
        return self.message.flag == FLAG_ACK
    
    def is_last(self) -> bool:
        return self.message.flag == FLAG_LAST

    def is_handshake(self) -> bool:
        return self.message.flag == FLAG_HANDSHAKE
    
    def get_max_window(self) -> int:
        return self.message.max_window
    
    def get_seq_num(self) -> int:
        return self.message.seq_num
    
    def get_ref_num(self) -> int:
        return self.message.ref_num
    
    def get_data(self) -> bytes:
        return self.message.data

    def is_valid_handshake_message(self) -> bool:
        if self.get_max_window() is None or self.get_max_window() <= 0:
            print(f"Max window inválido: {self.get_max_window()}")
            return False

        if self.get_seq_num() is None or self.get_seq_num() < 0:
            print(f"Seq num inválido: {self.get_seq_num()}")
            return False

        return True
