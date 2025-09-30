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

# Importar implementaciones específicas
from .stop_and_wait import handle_upload_stop_and_wait, handle_download_stop_and_wait
from .go_back_n import handle_upload_go_back_n, handle_download_go_back_n

__all__ = [
    # Implementaciones específicas
    'handle_upload_stop_and_wait', 'handle_upload_go_back_n',
    'handle_download_stop_and_wait', 'handle_download_go_back_n',
    
    # Clases base
    'RdtClient', 'RdtHandshake', 'ConnectionState',
    
    # Utilidades
    'validate_file_size', 'calculate_file_hash', 'create_upload_request'
]
