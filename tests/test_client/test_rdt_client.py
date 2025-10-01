"""
Tests unitarios para el módulo rdt_client
"""

import unittest
import tempfile
import os
import socket
import threading
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock

# Import the module to test
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from client.rdt_client import (
    RdtClient, RdtHandshake, ConnectionState,
    validate_file_size, calculate_file_hash, create_upload_request,
    get_error_message, ERR_TOO_BIG, ERR_NOT_FOUND, ERR_BAD_REQUEST,
    ERR_PERMISSION_DENIED, ERR_NETWORK_ERROR, ERR_TIMEOUT_ERROR,
    ERR_INVALID_PROTOCOL, ERR_SERVER_ERROR,
    FLAG_DATA, FLAG_ACK, FLAG_LAST, PROTO_STOP_WAIT, PROTO_GBN
)
from protocol.rdt.rdt_message import RdtMessage, RdtRequest


class TestRdtHandshake(unittest.TestCase):
    """Tests para la clase RdtHandshake"""
    
    def setUp(self):
        """Setup para cada test"""
        self.handshake = RdtHandshake(max_window=1)
    
    def test_handshake_initialization_stop_and_wait(self):
        """Test inicialización de handshake para Stop & Wait"""
        handshake = RdtHandshake(max_window=1)
        
        self.assertEqual(handshake.max_window, 1)
        self.assertEqual(handshake.sequence_number, 0)
        self.assertEqual(handshake.reference_number, 0)
        self.assertFalse(handshake.handshake_completed)
        self.assertIsNone(handshake.server_sequence_number)
        self.assertIsNone(handshake.server_reference_number)
        self.assertTrue(handshake.is_stop_and_wait())
        self.assertFalse(handshake.is_go_back_n())
    
    def test_handshake_initialization_go_back_n(self):
        """Test inicialización de handshake para Go Back N"""
        handshake = RdtHandshake(max_window=5)
        
        self.assertEqual(handshake.max_window, 5)
        self.assertEqual(handshake.sequence_number, 0)
        self.assertEqual(handshake.reference_number, 0)
        self.assertFalse(handshake.handshake_completed)
        self.assertIsNone(handshake.server_sequence_number)
        self.assertIsNone(handshake.server_reference_number)
        self.assertFalse(handshake.is_stop_and_wait())
        self.assertTrue(handshake.is_go_back_n())
    
    def test_handshake_invalid_max_window(self):
        """Test que handshake falla con max_window inválido"""
        with self.assertRaises(ValueError):
            RdtHandshake(max_window=0)
        
        with self.assertRaises(ValueError):
            RdtHandshake(max_window=10)
    
    def test_create_handshake_request(self):
        """Test creación de mensaje de handshake"""
        handshake = RdtHandshake(max_window=3)
        request = handshake.create_handshake_request()
        
        self.assertIsInstance(request, RdtMessage)
        self.assertEqual(request.flag, FLAG_DATA)
        self.assertEqual(request.max_window, 3)
        self.assertEqual(request.seq_num, 0)
        self.assertEqual(request.ref_num, 0)
        self.assertEqual(request.data, b'')
    
    def test_parse_handshake_response_success(self):
        """Test parsing exitoso de respuesta de handshake"""
        # Crear respuesta de servidor simulada
        ack_message = RdtMessage(
            flag=FLAG_ACK,
            max_window=1,
            seq_num=0,  # Server seq num
            ref_num=1,  # Client seq num + 1
            data=b''
        )
        ack_bytes = ack_message.to_bytes()
        rdt_request = RdtRequest(address="127.0.0.1:9999", request=ack_bytes)
        
        # Parsear respuesta
        result = self.handshake.parse_handshake_response(rdt_request)
        
        self.assertTrue(result)
        self.assertTrue(self.handshake.handshake_completed)
        self.assertEqual(self.handshake.server_sequence_number, 0)
        self.assertEqual(self.handshake.server_reference_number, 1)
        self.assertEqual(self.handshake.reference_number, 1)
    
    def test_parse_handshake_response_wrong_flag(self):
        """Test parsing falla con flag incorrecto"""
        # Crear mensaje con flag incorrecto
        wrong_message = RdtMessage(
            flag=FLAG_DATA,  # Debería ser FLAG_ACK
            max_window=1,
            seq_num=0,
            ref_num=1,
            data=b''
        )
        wrong_bytes = wrong_message.to_bytes()
        rdt_request = RdtRequest(address="127.0.0.1:9999", request=wrong_bytes)
        
        result = self.handshake.parse_handshake_response(rdt_request)
        
        self.assertFalse(result)
        self.assertFalse(self.handshake.handshake_completed)
    
    def test_parse_handshake_response_wrong_max_window(self):
        """Test parsing falla con max_window incorrecto"""
        # Crear respuesta con max_window incorrecto
        wrong_message = RdtMessage(
            flag=FLAG_ACK,
            max_window=5,  # Debería ser 1
            seq_num=0,
            ref_num=1,
            data=b''
        )
        wrong_bytes = wrong_message.to_bytes()
        rdt_request = RdtRequest(address="127.0.0.1:9999", request=wrong_bytes)
        
        result = self.handshake.parse_handshake_response(rdt_request)
        
        self.assertFalse(result)
        self.assertFalse(self.handshake.handshake_completed)
    
    def test_parse_handshake_response_wrong_ref_num(self):
        """Test parsing falla con reference number incorrecto"""
        # Crear respuesta con ref_num incorrecto
        wrong_message = RdtMessage(
            flag=FLAG_ACK,
            max_window=1,
            seq_num=0,
            ref_num=5,  # Debería ser 1 (client seq + 1)
            data=b''
        )
        wrong_bytes = wrong_message.to_bytes()
        rdt_request = RdtRequest(address="127.0.0.1:9999", request=wrong_bytes)
        
        result = self.handshake.parse_handshake_response(rdt_request)
        
        self.assertFalse(result)
        self.assertFalse(self.handshake.handshake_completed)


class TestConnectionState(unittest.TestCase):
    """Tests para la clase ConnectionState"""
    
    def setUp(self):
        """Setup para cada test"""
        self.handshake_info = {
            'max_window': 3,
            'server_seq_num': 0,
            'server_ref_num': 1,
            'is_stop_and_wait': False,
            'is_go_back_n': True
        }
        self.connection_state = ConnectionState(self.handshake_info)
    
    def test_connection_state_initialization(self):
        """Test inicialización de ConnectionState"""
        self.assertEqual(self.connection_state.max_window, 3)
        self.assertEqual(self.connection_state.server_seq_num, 0)
        self.assertEqual(self.connection_state.server_ref_num, 1)
        self.assertEqual(self.connection_state.client_seq_num, 1)
        self.assertEqual(self.connection_state.client_ref_num, 1)  # server_seq + 1
    
    def test_get_next_sequence_number(self):
        """Test obtención de siguiente sequence number"""
        seq_num = self.connection_state.get_next_sequence_number()
        self.assertEqual(seq_num, 1)
        
        # No debería incrementar automáticamente
        seq_num2 = self.connection_state.get_next_sequence_number()
        self.assertEqual(seq_num2, 1)
    
    def test_get_current_reference_number(self):
        """Test obtención de reference number actual"""
        ref_num = self.connection_state.get_current_reference_number()
        self.assertEqual(ref_num, 1)
    
    def test_increment_sequence_number(self):
        """Test incremento de sequence number"""
        initial_seq = self.connection_state.get_next_sequence_number()
        self.connection_state.increment_sequence_number()
        
        new_seq = self.connection_state.get_next_sequence_number()
        self.assertEqual(new_seq, initial_seq + 1)
    
    def test_update_reference_number(self):
        """Test actualización de reference number"""
        new_ref_num = 5
        self.connection_state.update_reference_number(new_ref_num)
        
        current_ref = self.connection_state.get_current_reference_number()
        self.assertEqual(current_ref, new_ref_num)
    
    def test_protocol_detection(self):
        """Test detección de protocolo"""
        # Stop and Wait
        stop_wait_info = {
            'max_window': 1,
            'server_seq_num': 0,
            'server_ref_num': 1,
            'is_stop_and_wait': True,
            'is_go_back_n': False
        }
        stop_wait_state = ConnectionState(stop_wait_info)
        
        self.assertTrue(stop_wait_state.is_stop_and_wait())
        self.assertFalse(stop_wait_state.is_go_back_n())
        
        # Go Back N
        self.assertFalse(self.connection_state.is_stop_and_wait())
        self.assertTrue(self.connection_state.is_go_back_n())


class TestRdtClient(unittest.TestCase):
    """Tests para la clase RdtClient"""
    
    def setUp(self):
        """Setup para cada test"""
        self.client = RdtClient(host="127.0.0.1", port=9999)
    
    def tearDown(self):
        """Cleanup después de cada test"""
        if hasattr(self.client, 'sock') and self.client.sock:
            self.client.sock.close()
    
    def test_client_initialization(self):
        """Test inicialización de RdtClient"""
        self.assertEqual(self.client.host, "127.0.0.1")
        self.assertEqual(self.client.port, 9999)
        self.assertIsInstance(self.client.handshake, RdtHandshake)
        self.assertFalse(self.client.connected)
        self.assertFalse(self.client.closed_by_server)
        self.assertIsInstance(self.client.stats, dict)
    
    def test_client_initialization_with_max_window(self):
        """Test inicialización con max_window personalizado"""
        client = RdtClient(host="192.168.1.1", port=8888, max_window=5)
        
        self.assertEqual(client.host, "192.168.1.1")
        self.assertEqual(client.port, 8888)
        self.assertEqual(client.handshake.max_window, 5)
        client.sock.close()
    
    def test_get_handshake_info(self):
        """Test obtención de información de handshake"""
        # Simular handshake completado
        self.client.handshake.handshake_completed = True
        self.client.handshake.server_sequence_number = 0
        self.client.handshake.server_reference_number = 1
        
        info = self.client.get_handshake_info()
        
        self.assertIsInstance(info, dict)
        self.assertEqual(info['max_window'], 1)
        self.assertEqual(info['server_seq_num'], 0)
        self.assertEqual(info['server_ref_num'], 1)
        self.assertTrue(info['is_stop_and_wait'])
        self.assertFalse(info['is_go_back_n'])
    
    def test_get_stats(self):
        """Test obtención de estadísticas"""
        stats = self.client.get_stats()
        
        self.assertIsInstance(stats, dict)
        self.assertIn('packets_sent', stats)
        self.assertIn('packets_received', stats)
        self.assertIn('retransmissions', stats)
        self.assertIn('errors', stats)
        self.assertIn('start_time', stats)
        self.assertIn('end_time', stats)
    
    def test_is_connected_before_handshake(self):
        """Test estado de conexión antes del handshake"""
        self.assertFalse(self.client.is_connected())
    
    def test_is_connected_after_handshake(self):
        """Test estado de conexión después del handshake"""
        self.client.connected = True
        self.client.handshake.handshake_completed = True
        
        self.assertTrue(self.client.is_connected())
    
    @patch('socket.socket')
    def test_send_data(self, mock_socket):
        """Test envío de datos"""
        mock_sock = Mock()
        mock_socket.return_value = mock_sock
        self.client.sock = mock_sock
        
        test_data = b"test data"
        self.client.send(test_data)
        
        mock_sock.sendto.assert_called_once_with(test_data, ("127.0.0.1", 9999))
        self.assertEqual(self.client.stats['packets_sent'], 1)
    
    @patch('socket.socket')
    def test_receive_data(self, mock_socket):
        """Test recepción de datos"""
        mock_sock = Mock()
        mock_socket.return_value = mock_sock
        self.client.sock = mock_sock
        
        # Simular recepción de datos
        mock_sock.recvfrom.return_value = (b"response data", ("127.0.0.1", 9999))
        
        data, addr, close_signal = self.client.receive()
        
        self.assertEqual(data, b"response data")
        self.assertEqual(addr, ("127.0.0.1", 9999))
        self.assertFalse(close_signal)
        self.assertEqual(self.client.stats['packets_received'], 1)
    
    @patch('socket.socket')
    def test_receive_timeout(self, mock_socket):
        """Test timeout en recepción"""
        mock_sock = Mock()
        mock_socket.return_value = mock_sock
        self.client.sock = mock_sock
        
        # Simular timeout
        mock_sock.recvfrom.side_effect = socket.timeout()
        
        data, addr, close_signal = self.client.receive()
        
        self.assertIsNone(data)
        self.assertIsNone(addr)
        self.assertFalse(close_signal)
    
    def test_close_connection(self):
        """Test cierre de conexión"""
        # Simular que el socket está abierto
        self.client.connected = True
        
        # Llamar close y verificar que se actualiza el estado
        self.client.close()
        
        self.assertFalse(self.client.connected)
        self.assertIsNotNone(self.client.stats['end_time'])


class TestUtilityFunctions(unittest.TestCase):
    """Tests para funciones utilitarias"""
    
    def setUp(self):
        """Setup para cada test"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = Path(self.temp_dir) / "test_file.txt"
    
    def tearDown(self):
        """Cleanup después de cada test"""
        if self.temp_file.exists():
            self.temp_file.unlink()
        os.rmdir(self.temp_dir)
    
    def test_validate_file_size_valid(self):
        """Test validación de tamaño de archivo válido"""
        # Crear archivo pequeño
        self.temp_file.write_text("small content")
        
        is_valid, error_code = validate_file_size(self.temp_file)
        
        self.assertTrue(is_valid)
        self.assertIsNone(error_code)
    
    def test_validate_file_size_too_big(self):
        """Test validación de archivo demasiado grande"""
        # Crear archivo grande (simulado)
        large_content = "x" * (6 * 1024 * 1024)  # 6MB
        self.temp_file.write_text(large_content)
        
        is_valid, error_code = validate_file_size(self.temp_file)
        
        self.assertFalse(is_valid)
        self.assertEqual(error_code, ERR_TOO_BIG)
    
    def test_validate_file_size_custom_limit(self):
        """Test validación con límite personalizado"""
        # Crear archivo de 2MB
        content = "x" * (2 * 1024 * 1024)
        self.temp_file.write_text(content)
        
        # Validar con límite de 1MB
        is_valid, error_code = validate_file_size(self.temp_file, max_size_mb=1)
        
        self.assertFalse(is_valid)
        self.assertEqual(error_code, ERR_TOO_BIG)
    
    def test_calculate_file_hash(self):
        """Test cálculo de hash de archivo"""
        content = "test content for hash"
        self.temp_file.write_text(content)
        
        hash_value = calculate_file_hash(self.temp_file)
        
        self.assertIsInstance(hash_value, str)
        self.assertEqual(len(hash_value), 32)  # MD5 hash length
    
    def test_calculate_file_hash_consistency(self):
        """Test consistencia del hash"""
        content = "consistent content"
        self.temp_file.write_text(content)
        
        hash1 = calculate_file_hash(self.temp_file)
        hash2 = calculate_file_hash(self.temp_file)
        
        self.assertEqual(hash1, hash2)
    
    def test_create_upload_request_stop_and_wait(self):
        """Test creación de request de upload para Stop & Wait"""
        request_bytes = create_upload_request(
            filename="test.txt",
            file_size=1024,
            protocol="stop-and-wait",
            window_size=1
        )
        
        self.assertIsInstance(request_bytes, bytes)
        self.assertGreater(len(request_bytes), 0)
        
        # Verificar que se puede parsear
        rdt_request = RdtRequest(address="127.0.0.1:9999", request=request_bytes)
        self.assertEqual(rdt_request.get_max_window(), 1)
    
    def test_create_upload_request_go_back_n(self):
        """Test creación de request de upload para Go Back N"""
        request_bytes = create_upload_request(
            filename="test.txt",
            file_size=2048,
            protocol="go-back-n",
            window_size=5
        )
        
        self.assertIsInstance(request_bytes, bytes)
        self.assertGreater(len(request_bytes), 0)
        
        # Verificar que se puede parsear
        rdt_request = RdtRequest(address="127.0.0.1:9999", request=request_bytes)
        self.assertEqual(rdt_request.get_max_window(), 5)
    
    def test_get_error_message_valid_codes(self):
        """Test obtención de mensajes de error válidos"""
        self.assertEqual(get_error_message(ERR_TOO_BIG), "Archivo excede el tamaño máximo permitido")
        self.assertEqual(get_error_message(ERR_NOT_FOUND), "Archivo no encontrado")
        self.assertEqual(get_error_message(ERR_BAD_REQUEST), "Solicitud malformada")
        self.assertEqual(get_error_message(ERR_PERMISSION_DENIED), "Permisos insuficientes")
        self.assertEqual(get_error_message(ERR_NETWORK_ERROR), "Error de red")
        self.assertEqual(get_error_message(ERR_TIMEOUT_ERROR), "Timeout en la operación")
        self.assertEqual(get_error_message(ERR_INVALID_PROTOCOL), "Protocolo no soportado")
        self.assertEqual(get_error_message(ERR_SERVER_ERROR), "Error interno del servidor")
    
    def test_get_error_message_invalid_code(self):
        """Test obtención de mensaje para código de error inválido"""
        message = get_error_message(999)
        self.assertEqual(message, "Error desconocido (código: 999)")


if __name__ == '__main__':
    unittest.main()
