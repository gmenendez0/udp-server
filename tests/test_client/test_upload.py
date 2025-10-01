"""
Tests unitarios para el módulo upload del cliente
"""

import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the module to test
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from client.upload import validate_file, parse_args


class TestUpload(unittest.TestCase):
    """Tests para funciones del módulo upload"""
    
    def setUp(self):
        """Setup para cada test"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = Path(self.temp_dir) / "test_file.txt"
        
    def tearDown(self):
        """Cleanup después de cada test"""
        if self.temp_file.exists():
            self.temp_file.unlink()
        os.rmdir(self.temp_dir)
    
    def test_validate_file_exists(self):
        """Test que validate_file funciona con archivo válido"""
        # Crear archivo de prueba
        self.temp_file.write_text("contenido de prueba")
        
        # Validar archivo
        result = validate_file(str(self.temp_file))
        
        self.assertEqual(result, self.temp_file)
    
    def test_validate_file_not_exists(self):
        """Test que validate_file falla con archivo inexistente"""
        with self.assertRaises(FileNotFoundError):
            validate_file("/archivo/inexistente.txt")
    
    def test_validate_file_too_large(self):
        """Test que validate_file falla con archivo demasiado grande"""
        # Crear archivo grande (simulado)
        large_content = "x" * (6 * 1024 * 1024)  # 6MB
        self.temp_file.write_text(large_content)
        
        with self.assertRaises(ValueError):
            validate_file(str(self.temp_file))
    
    @patch('sys.argv', ['upload', '-s', 'test.txt', '-H', '192.168.1.1'])
    def test_parse_args_basic(self):
        """Test que parse_args funciona con argumentos básicos"""
        args = parse_args()
        
        self.assertEqual(args.src, 'test.txt')
        self.assertEqual(args.host, '192.168.1.1')
        self.assertEqual(args.port, 9999)  # default
        self.assertEqual(args.protocol, 'stop-and-wait')  # default


if __name__ == '__main__':
    unittest.main()
