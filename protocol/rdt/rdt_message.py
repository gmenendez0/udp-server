class RdtMessage:
    def __init__(self, ack_flag: bool, max_window: int, seq_num: int, ref_num: int, data: bytes, last_packet: bool = False):
        self.ack_flag:      bool    = ack_flag
        self.max_window:    int     = max_window
        self.seq_num:       int     = seq_num
        self.ref_num:       int     = ref_num
        self.data:          bytes   = data
        self.last_packet:   bool    = last_packet

    #[ACK_BYTE][MAX WINDOW BYTE][LAST_PACKET_BYTE][SEQ_NUM][REF_NUM]_[DATA]
    #ACK_BYTE: 0 = DATA, 1 = ACK
    #MAX WINDOW BYTE: 0 = STOP AND WAIT, >1 = GO BACK N
    #LAST_PACKET_BYTE: 0 = NO, 1 = YES
    #[SEQ_NUM]: 4 bytes
    #[REF_NUM]: 4 bytes
    @classmethod
    def from_bytes(cls, raw: bytes) -> "RdtMessage":
        # ACK Flag  = primer byte
        ack_flag = raw[0] == 1
        # MaxWindow = segundo byte
        max_window = int.from_bytes(raw[1:2], byteorder="big")
        # LastPacket = tercer byte
        last_packet = raw[2] == 1
        # Seq Num   = cuarto a séptimo byte (inclusive)
        seq_num = int.from_bytes(raw[3:7], byteorder="big")
        # Ref Num   = octavo a undécimo byte (inclusive)
        ref_num = int.from_bytes(raw[7:11], byteorder="big")
        # Data      = duodécimo byte en adelante (inclusive)
        data = raw[11:]

        return cls(ack_flag, max_window, seq_num, ref_num, data, last_packet)

    def to_bytes(self) -> bytes:
        # Armamos el ack byte
        ack_byte = b'\x01' if self.ack_flag else b'\x00'
        # Armamos el max window byte
        max_window_byte = self.max_window.to_bytes(1, byteorder='big')
        # Armamos el last packet byte
        last_packet_byte = b'\x01' if self.last_packet else b'\x00'
        # Armamos el seq num bytes
        seq_num_bytes = self.seq_num.to_bytes(4, byteorder='big')
        # Armamos el ref num bytes
        ref_num_bytes = self.ref_num.to_bytes(4, byteorder='big')

        # Concatenamos
        return ack_byte + max_window_byte + last_packet_byte + seq_num_bytes + ref_num_bytes + self.data

class RdtResponse:
    def __init__(self, ack_flag: bool, max_window: int, seq_num: int, ref_num: int, data: bytes, last_packet: bool = False):
        self.message = RdtMessage(ack_flag, max_window, seq_num, ref_num, data, last_packet)

    @classmethod
    def new_ack_response(cls, max_window: int, seq_num: int, ref_num: int) -> "RdtResponse":
        return cls(ack_flag=True, max_window=max_window, seq_num=seq_num, ref_num=ref_num, data=b'', last_packet=False)

    @classmethod
    def new_data_response(cls, max_window: int, seq_num: int, ref_num: int, data: bytes, last_packet: bool = False) -> "RdtResponse":
        return cls(ack_flag=False, max_window=max_window, seq_num=seq_num, ref_num=ref_num, data=data, last_packet=last_packet)

class RdtRequest:
    def __init__(self, address: str, request: bytes):
        self.address = address
        self.message = RdtMessage.from_bytes(request)
    
    def is_ack(self) -> bool:
        return self.message.ack_flag
    
    def get_max_window(self) -> int:
        return self.message.max_window
    
    def get_seq_num(self) -> int:
        return self.message.seq_num
    
    def get_ref_num(self) -> int:
        return self.message.ref_num
    
    def get_data(self) -> bytes:
        return self.message.data
