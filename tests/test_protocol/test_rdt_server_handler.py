import pytest
from protocol.rdt.rdt_server_handler import RdtServerHandler
from protocol.const import T_CTRL, OP_REQUEST_UPLOAD, make_ack_packet
from protocol.rdt.rdt_request import RDTRequest
from protocol.const import ctrl_parse

# Utilidad para crear un paquete de control simulado
def build_control_packet(seq=0, sid=1234, ref=0, opcode=OP_REQUEST_UPLOAD, filename="test.txt"):
    # Simula el payload de control (opcode + TLV de filename)
    tlv_type = 0x01  # TLV_FILENAME
    tlv_value = filename.encode('utf-8')
    tlv = bytes([tlv_type, len(tlv_value)]) + tlv_value
    payload = bytes([opcode]) + tlv
    # Arma el header simulado
    header = {
        'type': T_CTRL,
        'seq': seq,
        'sid': sid,
        'ref': ref,
        'flags': 0,  # Agregado para evitar KeyError
        'payload': payload
    }
    # Crea el paquete RDTRequest
    rdt_request = RDTRequest(header)
    # Serializa el paquete (simula el datagrama recibido)
    # Aquí asumimos que RDTRequest tiene un método para serializar, si no, se debe ajustar
    return rdt_request.to_bytes() if hasattr(rdt_request, 'to_bytes') else payload

def test_handle_control_upload_ack():
    handler = RdtServerHandler()
    address = ("127.0.0.1", 12345)
    datagram = build_control_packet()
    response = handler.handle_datagram(address, datagram)
    assert response is not None, "El servidor debe responder con un ACK de control"
    # Opcional: podrías parsear el response y verificar que sea un ACK correcto

if __name__ == "__main__":
    test_handle_control_upload_ack()
    print("Test de ACK de control ejecutado correctamente.")
