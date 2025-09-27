# proto_min.py — header sin VERSION ni CRC, sin ACKNO
import struct
import time

# ==== Constantes ====
T_DATA, T_ACK, T_CTRL = 0x00, 0x01, 0x02
F_LAST, F_ERR = 0x01, 0x02

OP_REQUEST_UPLOAD, OP_UPLOAD_ACCEPTED = 0x01, 0x02
OP_DOWNLOAD_ACCEPTED = 0x04
OP_REQUEST_DOWNLOAD, OP_END_SESSION, OP_ERROR = 0x03, 0x10, 0x7F


# ==== Constantes TLV ====
TLV_FILENAME = 0x01
TLV_FILESIZE = 0x02
TLV_PROTOCOL = 0x03
TLV_WINDOW_REQ = 0x04
TLV_CHUNK_SIZE = 0x05
TLV_ERROR_CODE = 0x06
TLV_ERROR_MESSAGE = 0x07


PROTO_STOP_WAIT, PROTO_GBN = 0, 1

# Header fijo: >BBBIQH  = 17 bytes
HDR_FMT = '>BBBIQH'
HDR_LEN = struct.calcsize(HDR_FMT)  # 17

def pack_header(typ, flags, wnd, seq, sid, payload):
    """Empaca header + devuelve header (sin payload).
    LEN sale de len(payload)."""
    return struct.pack(HDR_FMT, typ, flags, wnd, seq, sid, len(payload))

def unpack_header(packet: bytes):
    """Devuelve dict con campos y payload extraído."""
    if len(packet) < HDR_LEN:
        raise ValueError("Packet too short")
    typ, flags, wnd, seq, sid, length = struct.unpack(HDR_FMT, packet[:HDR_LEN])
    payload = packet[HDR_LEN:HDR_LEN+length]
    if len(payload) != length:
        raise ValueError("LEN mismatch")
    return {"type": typ, "flags": flags, "wnd": wnd, "seq": seq,
            "sid": sid, "len": length, "payload": payload}

# ==== TLVs para CTRL ====
def _tlv_pack(t, val: bytes): 
    if len(val) > 255: raise ValueError("TLV too long")
    return struct.pack('>BB', t, len(val)) + val

def tlv_u8(t, v):   return _tlv_pack(t, struct.pack('>B', v))
def tlv_u16(t, v):  return _tlv_pack(t, struct.pack('>H', v))
def tlv_u64(t, v):  return _tlv_pack(t, struct.pack('>Q', v))
def tlv_str(t, s):  return _tlv_pack(t, s.encode('utf-8'))

def tlv_parse_all(buf: bytes):
    i, out = 0, []
    while i+2 <= len(buf):
        t, l = buf[i], buf[i+1]; i += 2
        if i+l > len(buf): raise ValueError("TLV overflow")
        out.append((t, buf[i:i+l])); i += l
    if i != len(buf): raise ValueError("Trailing bytes")
    return out

def ctrl_build(opcode: int, tlvs: list[bytes]) -> bytes:
    """Construye payload de control: OPCODE + RESERVED + TLVs"""
    return struct.pack('>BB', opcode, 0) + b''.join(tlvs)

def ctrl_parse(payload: bytes):
    """Parsea payload de control: OPCODE + RESERVED + TLVs"""
    if len(payload) < 2: raise ValueError("CTRL too short")
    opcode, reserved = struct.unpack('>BB', payload[:2])
    return opcode, tlv_parse_all(payload[2:])

# ==== Constructores de paquetes ====
def make_ctrl_packet(opcode, tlvs, sid=0, wnd=0, seq=0):
    body = ctrl_build(opcode, tlvs)
    hdr  = pack_header(T_CTRL, 0, wnd, seq, sid, body)
    return hdr + body

def make_data_packet(sid, seq, payload: bytes, last=False, wnd=0):
    flags = F_LAST if last else 0
    hdr = pack_header(T_DATA, flags, wnd, seq, sid, payload)
    return hdr + payload

def make_ack_packet(sid, ackno, wnd=0):
    """En ACK reutilizamos SEQ para el 'next expected' (ACK acumulativo)."""
    body = b''
    hdr  = pack_header(T_ACK, 0, wnd, ackno, sid, body)
    return hdr  # sin payload

# ==== Ejemplos de uso ====
def build_request_upload(filename: str, size_bytes: int, proto: int, window_req: int|None=None, chunk_size: int|None=None):
    tlvs = [
        tlv_str(TLV_FILENAME, filename),
        tlv_u64(TLV_FILESIZE, size_bytes),
        tlv_u8 (TLV_PROTOCOL, proto),
    ]
    if window_req is not None: tlvs.append(tlv_u16(TLV_WINDOW_REQ, window_req))
    if chunk_size is not None: tlvs.append(tlv_u16(TLV_CHUNK_SIZE, chunk_size))
    return make_ctrl_packet(OP_REQUEST_UPLOAD, tlvs, sid=0)


def generate_new_sid():
    """Genera un nuevo SID (simplemente un timestamp por simplicidad)"""
    return int(time.time() * 1000) & 0xFFFFFFFF  # 32 bits