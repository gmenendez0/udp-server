"""
Tests unitarios para el módulo download del cliente
"""

import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the module to test
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from client.download import validate_destination, parse_args


class TestDownload(unittest.TestCase):
    """Tests para funciones del módulo download"""
    
    def setUp(self):
        """Setup para cada test"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_subdir = Path(self.temp_dir) / "subdir"
        self.temp_file = Path(self.temp_dir) / "existing_file.txt"
        
    def tearDown(self):
        """Cleanup después de cada test"""
        if self.temp_file.exists():
            self.temp_file.unlink()
        if self.temp_subdir.exists():
            self.temp_subdir.rmdir()
        os.rmdir(self.temp_dir)
    
    def test_validate_destination_directory_exists(self):
        """Test que validate_destination funciona con directorio existente"""
        result = validate_destination(str(self.temp_dir))
        self.assertEqual(result, Path(self.temp_dir))
    
    def test_validate_destination_directory_not_exists(self):
        """Test que validate_destination falla con directorio padre inexistente"""
        non_existent_path = Path(self.temp_dir) / "non_existent" / "file.txt"
        
        with self.assertRaises(FileNotFoundError):
            validate_destination(str(non_existent_path))
    
    def test_validate_destination_file_path_valid(self):
        """Test que validate_destination funciona con ruta de archivo válida"""
        target_file = Path(self.temp_dir) / "new_file.txt"
        
        result = validate_destination(str(target_file))
        self.assertEqual(result, target_file)
    
    def test_validate_destination_file_already_exists(self):
        """Test que validate_destination maneja archivo existente correctamente"""
        self.temp_file.write_text("contenido existente")
        
        result = validate_destination(str(self.temp_file))
        self.assertEqual(result, self.temp_file)
    
    def test_validate_destination_readonly_directory(self):
        """Test que validate_destination falla con directorio sin permisos de escritura"""
        self.temp_subdir.mkdir()
        
        # Cambiar permisos a solo lectura
        os.chmod(self.temp_subdir, 0o444)
        
        try:
            with self.assertRaises(PermissionError):
                validate_destination(str(self.temp_subdir))
        finally:
            # Restaurar permisos para cleanup
            os.chmod(self.temp_subdir, 0o755)
    
    @patch('sys.argv', ['download', '-n', 'archivo.txt', '-d', '/tmp'])
    def test_parse_args_basic(self):
        """Test que parse_args funciona con argumentos básicos"""
        args = parse_args()
        
        self.assertEqual(args.name, 'archivo.txt')
        self.assertEqual(args.dst, '/tmp')
        self.assertEqual(args.host, '127.0.0.1')  # default
        self.assertEqual(args.port, 9999)  # default
        self.assertEqual(args.protocol, 'stop-and-wait')  # default
    
    @patch('sys.argv', ['download', '-n', 'test.pdf', '-d', './downloads/', 
                        '-H', '192.168.1.100', '-p', '8888', '-v'])
    def test_parse_args_all_options(self):
        """Test que parse_args funciona con todas las opciones"""
        args = parse_args()
        
        self.assertEqual(args.name, 'test.pdf')
        self.assertEqual(args.dst, './downloads/')
        self.assertEqual(args.host, '192.168.1.100')
        self.assertEqual(args.port, 8888)
        self.assertTrue(args.verbose)
        self.assertFalse(args.quiet)
        self.assertEqual(args.protocol, 'stop-and-wait')
    
    @patch('sys.argv', ['download', '-n', 'data.bin', '-d', '/home/user/', 
                        '-r', 'go-back-n', '-q'])
    def test_parse_args_protocol_and_quiet(self):
        """Test que parse_args funciona con protocolo go-back-n y modo quiet"""
        args = parse_args()
        
        self.assertEqual(args.name, 'data.bin')
        self.assertEqual(args.dst, '/home/user/')
        self.assertEqual(args.protocol, 'go-back-n')
        self.assertTrue(args.quiet)
        self.assertFalse(args.verbose)
    
    @patch('sys.argv', ['download', '-n', 'file.txt'])
    def test_parse_args_missing_required(self):
        """Test que parse_args falla cuando falta argumento requerido -d"""
        with self.assertRaises(SystemExit):
            parse_args()
    
    @patch('sys.argv', ['download', '-d', '/tmp'])
    def test_parse_args_missing_required_name(self):
        """Test que parse_args falla cuando falta argumento requerido -n"""
        with self.assertRaises(SystemExit):
            parse_args()
    
    def test_validate_destination_path_construction(self):
        """Test construcción correcta de rutas con validate_destination"""
        # Test con archivo específico
        target_file = Path(self.temp_dir) / "nuevo_archivo.dat"
        result = validate_destination(str(target_file))
        
        self.assertEqual(result, target_file)
        self.assertEqual(result.parent, Path(self.temp_dir))
        self.assertEqual(result.name, "nuevo_archivo.dat")


if __name__ == '__main__':
    unittest.main()
