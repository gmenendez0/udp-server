import unittest
from protocol.rdt import RdtRequest
from protocol.rdt.rdt_message import RdtMessage

class TestRDTRequest(unittest.TestCase):
    def test_rdt_request_data_packet(self):
        """Test que RdtRequest funciona con un paquete de datos"""
        # Crear un RdtMessage con flag=0 (DATA)
        rdt_message = RdtMessage(flag=0, max_window=1, seq_num=42, ref_num=12345, data=b'hello')
        request_bytes = rdt_message.to_bytes()
        
        rdt_request = RdtRequest(address="127.0.0.1:8080", session_id=12345, request=request_bytes)
        
        self.assertFalse(rdt_request.is_ack())
        self.assertFalse(rdt_request.is_last())
        self.assertEqual(rdt_request.get_max_window(), 1)
        self.assertEqual(rdt_request.get_seq_num(), 42)
        self.assertEqual(rdt_request.get_ref_num(), 12345)
        self.assertEqual(rdt_request.get_data(), b'hello')

    def test_rdt_request_ack_packet(self):
        """Test que RdtRequest funciona con un paquete ACK"""
        # Crear un RdtMessage con flag=1 (ACK)
        rdt_message = RdtMessage(flag=1, max_window=1, seq_num=43, ref_num=12345, data=b'')
        request_bytes = rdt_message.to_bytes()
        
        rdt_request = RdtRequest(address="127.0.0.1:8080", session_id=12345, request=request_bytes)
        
        self.assertTrue(rdt_request.is_ack())
        self.assertFalse(rdt_request.is_last())
        self.assertEqual(rdt_request.get_max_window(), 1)
        self.assertEqual(rdt_request.get_seq_num(), 43)
        self.assertEqual(rdt_request.get_ref_num(), 12345)
        self.assertEqual(rdt_request.get_data(), b'')

    def test_rdt_request_last_packet(self):
        """Test que RdtRequest funciona con un paquete LAST"""
        # Crear un RdtMessage con flag=2 (LAST)
        rdt_message = RdtMessage(flag=2, max_window=1, seq_num=44, ref_num=12345, data=b'final')
        request_bytes = rdt_message.to_bytes()
        
        rdt_request = RdtRequest(address="127.0.0.1:8080", session_id=12345, request=request_bytes)
        
        self.assertFalse(rdt_request.is_ack())
        self.assertTrue(rdt_request.is_last())
        self.assertEqual(rdt_request.get_max_window(), 1)
        self.assertEqual(rdt_request.get_seq_num(), 44)
        self.assertEqual(rdt_request.get_ref_num(), 12345)
        self.assertEqual(rdt_request.get_data(), b'final')

    def test_rdt_request_go_back_n_window(self):
        """Test que RdtRequest funciona con ventana Go-Back-N"""
        # Crear un RdtMessage con max_window > 1 (Go-Back-N)
        rdt_message = RdtMessage(flag=0, max_window=5, seq_num=10, ref_num=54321, data=b'abc')
        request_bytes = rdt_message.to_bytes()
        
        rdt_request = RdtRequest(address="127.0.0.1:8080", session_id=54321, request=request_bytes)
        
        self.assertEqual(rdt_request.get_max_window(), 5)
        self.assertEqual(rdt_request.get_seq_num(), 10)
        self.assertEqual(rdt_request.get_ref_num(), 54321)
        self.assertEqual(rdt_request.get_data(), b'abc')

    def test_rdt_request_stop_and_wait(self):
        """Test que RdtRequest funciona con Stop-and-Wait (max_window=1)"""
        # Crear un RdtMessage con max_window=1 (Stop-and-Wait)
        rdt_message = RdtMessage(flag=0, max_window=1, seq_num=1, ref_num=100, data=b'test')
        request_bytes = rdt_message.to_bytes()
        
        rdt_request = RdtRequest(address="127.0.0.1:8080", session_id=100, request=request_bytes)
        
        self.assertEqual(rdt_request.get_max_window(), 1)
        self.assertEqual(rdt_request.get_seq_num(), 1)
        self.assertEqual(rdt_request.get_ref_num(), 100)
        self.assertEqual(rdt_request.get_data(), b'test')

    def test_rdt_request_from_bytes_integration(self):
        """Test que RdtRequest funciona correctamente con bytes reales"""
        # Crear un RdtMessage y convertirlo a bytes
        original_message = RdtMessage(flag=0, max_window=3, seq_num=100, ref_num=200, data=b'hello world')
        request_bytes = original_message.to_bytes()
        
        # Crear RdtRequest desde los bytes
        rdt_request = RdtRequest(address="127.0.0.1:8080", session_id=200, request=request_bytes)
        
        # Verificar que los datos se extraen correctamente
        self.assertEqual(rdt_request.get_max_window(), 3)
        self.assertEqual(rdt_request.get_seq_num(), 100)
        self.assertEqual(rdt_request.get_ref_num(), 200)
        self.assertEqual(rdt_request.get_data(), b'hello world')

    def test_rdt_request_empty_data(self):
        """Test que RdtRequest funciona con datos vacíos"""
        rdt_message = RdtMessage(flag=1, max_window=1, seq_num=0, ref_num=0, data=b'')
        request_bytes = rdt_message.to_bytes()
        
        rdt_request = RdtRequest(address="127.0.0.1:8080", session_id=0, request=request_bytes)
        
        self.assertTrue(rdt_request.is_ack())
        self.assertEqual(rdt_request.get_data(), b'')

    def test_rdt_request_large_data(self):
        """Test que RdtRequest funciona con datos grandes"""
        large_data = b'x' * 1000  # 1000 bytes
        rdt_message = RdtMessage(flag=0, max_window=10, seq_num=999, ref_num=888, data=large_data)
        request_bytes = rdt_message.to_bytes()
        
        rdt_request = RdtRequest(address="127.0.0.1:8080", session_id=888, request=request_bytes)
        
        self.assertEqual(rdt_request.get_data(), large_data)
        self.assertEqual(len(rdt_request.get_data()), 1000)

    def test_rdt_request_address_and_session(self):
        """Test que RdtRequest mantiene correctamente address y session_id"""
        rdt_message = RdtMessage(flag=0, max_window=1, seq_num=1, ref_num=1, data=b'test')
        request_bytes = rdt_message.to_bytes()
        
        rdt_request = RdtRequest(address="192.168.1.100:9000", session_id=99999, request=request_bytes)
        
        self.assertEqual(rdt_request.address, "192.168.1.100:9000")
        # Nota: session_id no está expuesto en la nueva interfaz, pero se pasa al constructor

if __name__ == '__main__':
    unittest.main()
