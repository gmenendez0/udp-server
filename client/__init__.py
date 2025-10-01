"""
Módulo cliente para transferencia de archivos UDP

Contiene los clientes para operaciones UPLOAD y DOWNLOAD
Implementa protocolos Stop & Wait y Go-Back-N con handshake
"""

__version__ = "1.0.0"

# Importar clases base
from .rdt_client import (
    RdtClient, RdtHandshake, ConnectionState,
    validate_file_size, calculate_file_hash, create_upload_request
)

__all__ = [
    
    # Clases base
    'RdtClient', 'RdtHandshake', 'ConnectionState',
    
    # Utilidades
    'validate_file_size', 'calculate_file_hash', 'create_upload_request'
]
