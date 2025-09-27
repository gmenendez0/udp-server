import unittest
from protocol.rdt import RDTRequest
from protocol.const import T_DATA, T_ACK, T_CTRL, F_LAST, F_ERR

class TestRDTRequest(unittest.TestCase):
    def test_rdt_request_data_packet(self):
        """Test que RDTRequest funciona con un paquete de datos"""
        header = {
            'type': T_DATA,
            'flags': F_LAST,
            'wnd': 0,
            'seq': 42,
            'sid': 12345,
            'len': 5,
            'payload': b'hello'
        }
        rdt = RDTRequest(header)
        
        self.assertEqual(rdt.type, T_DATA)
        self.assertEqual(rdt.flags, F_LAST)
        self.assertEqual(rdt.wnd, 0)
        self.assertEqual(rdt.seq, 42)
        self.assertEqual(rdt.sid, 12345)
        self.assertEqual(rdt.len, 5)
        self.assertEqual(rdt.payload, b'hello')

    def test_rdt_request_ack_packet(self):
        """Test que RDTRequest funciona con un paquete ACK"""
        header = {
            'type': T_ACK,
            'flags': 0,
            'wnd': 0,
            'seq': 43,
            'sid': 12345,
            'len': 0,
            'payload': b''
        }
        rdt = RDTRequest(header)
        
        self.assertEqual(rdt.type, T_ACK)
        self.assertEqual(rdt.flags, 0)
        self.assertEqual(rdt.seq, 43)
        self.assertEqual(rdt.sid, 12345)
        self.assertEqual(rdt.len, 0)
        self.assertEqual(rdt.payload, b'')

    def test_rdt_request_control_packet(self):
        """Test que RDTRequest funciona con un paquete de control"""
        control_payload = b'\x01\x01\x04test'  # OP_REQUEST_UPLOAD + TLV filename
        header = {
            'type': T_CTRL,
            'flags': 0,
            'wnd': 0,
            'seq': 0,
            'sid': 0,
            'len': len(control_payload),
            'payload': control_payload
        }
        rdt = RDTRequest(header)
        
        self.assertEqual(rdt.type, T_CTRL)
        self.assertEqual(rdt.flags, 0)
        self.assertEqual(rdt.seq, 0)
        self.assertEqual(rdt.sid, 0)
        self.assertEqual(rdt.len, len(control_payload))
        self.assertEqual(rdt.payload, control_payload)

    def test_rdt_request_from_bytes(self):
        """Test que RDTRequest.from_bytes funciona correctamente"""
        # Crear un paquete de datos usando pack_header
        from protocol.const import pack_header
        payload = b'hello'
        packet = pack_header(T_DATA, F_LAST, 0, 42, 12345, payload) + payload
        
        rdt = RDTRequest.from_bytes(packet)
        
        self.assertEqual(rdt.type, T_DATA)
        self.assertEqual(rdt.flags, F_LAST)
        self.assertEqual(rdt.seq, 42)
        self.assertEqual(rdt.sid, 12345)
        self.assertEqual(rdt.payload, payload)

    def test_rdt_request_serialize(self):
        """Test que serialize funciona correctamente"""
        header = {
            'type': T_DATA,
            'flags': F_LAST,
            'wnd': 0,
            'seq': 42,
            'sid': 12345,
            'len': 5,
            'payload': b'hello'
        }
        rdt = RDTRequest(header)
        serialized = rdt.serialize()
        
        # Verificar que se puede deserializar correctamente
        rdt2 = RDTRequest.from_bytes(serialized + rdt.payload)
        self.assertEqual(rdt.type, rdt2.type)
        self.assertEqual(rdt.flags, rdt2.flags)
        self.assertEqual(rdt.seq, rdt2.seq)
        self.assertEqual(rdt.sid, rdt2.sid)
        self.assertEqual(rdt.payload, rdt2.payload)

    def test_rdt_request_invalid_header(self):
        """Test que RDTRequest falla con header inválido"""
        with self.assertRaises(KeyError):
            RDTRequest({'type': T_DATA})  # Faltan campos requeridos

    def test_rdt_request_go_back_n_window(self):
        """Test que RDTRequest funciona con ventana Go-Back-N"""
        header = {
            'type': T_DATA,
            'flags': 0,
            'wnd': 5,  # Ventana de tamaño 5
            'seq': 10,
            'sid': 54321,
            'len': 3,
            'payload': b'abc'
        }
        rdt = RDTRequest(header)
        
        self.assertEqual(rdt.wnd, 5)
        self.assertEqual(rdt.seq, 10)
        self.assertEqual(rdt.sid, 54321)
        self.assertEqual(rdt.payload, b'abc')
