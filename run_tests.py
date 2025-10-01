#!/usr/bin/env python3
"""
Script para ejecutar todos los tests del proyecto
"""

import unittest
import sys
import os
from pathlib import Path


def discover_and_run_tests():
    """Descubre y ejecuta todos los tests del proyecto"""
    
    # Añadir el directorio raíz al path para imports
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))
    
    # Descubrir tests
    loader = unittest.TestLoader()
    test_suite = loader.discover('tests', pattern='test_*.py')
    
    # Ejecutar tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Retornar código de salida apropiado
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    exit_code = discover_and_run_tests()
    sys.exit(exit_code)
