"""
Módulo cliente para transferencia de archivos UDP

Contiene los clientes para operaciones UPLOAD y DOWNLOAD
Implementa protocolos Stop & Wait y Go-Back-N con handshake
"""

__version__ = "1.0.0"

# Importar clases base
from .rdt_client import (
    RdtClient, ConnectionState, validate_file_size
)

__all__ = [
    
    # Clases base
    'RdtClient', 'ConnectionState',
    
    # Utilidades
    'validate_file_size'
]
