#!/usr/bin/env python3
"""
Constantes del cliente RDT.
"""

# Constantes de protocolo
T_DATA, T_ACK, T_GETDATA = 0x00, 0x01, 0x04
F_LAST = 0x01

# Códigos de error
ERR_TOO_BIG = 1
ERR_NOT_FOUND = 2
ERR_BAD_REQUEST = 3
ERR_PERMISSION_DENIED = 4
ERR_NETWORK_ERROR = 5
ERR_TIMEOUT_ERROR = 6
ERR_INVALID_PROTOCOL = 7
ERR_SERVER_ERROR = 8

ERROR_MESSAGES = {
    ERR_TOO_BIG: "Archivo excede el tamaño máximo permitido",
    ERR_NOT_FOUND: "Archivo no encontrado",
    ERR_BAD_REQUEST: "Solicitud malformada",
    ERR_PERMISSION_DENIED: "Permisos insuficientes",
    ERR_NETWORK_ERROR: "Error de red",
    ERR_TIMEOUT_ERROR: "Timeout en la operación",
    ERR_INVALID_PROTOCOL: "Protocolo no soportado",
    ERR_SERVER_ERROR: "Error interno del servidor"
}

def get_error_message(error_code: int) -> str:
    """
    Obtiene el mensaje de error correspondiente al código.
    
    Args:
        error_code (int): Código de error
        
    Returns:
        str: Mensaje de error descriptivo
    """
    return ERROR_MESSAGES.get(error_code, f"Error desconocido (código: {error_code})")

# Prefijos de mensajes
PREFIX_UPLOAD = "U_"
PREFIX_DOWNLOAD = "D_"
def format_upload_request(filename: str, file_size: int) -> str:
    """
    Formatea un mensaje de solicitud de upload.
    
    Args:
        filename (str): Nombre del archivo
        file_size (int): Tamaño del archivo en bytes
        
    Returns:
        str: Mensaje formateado (ej: "U_archivo.txt_5000000")
    """
    return f"{PREFIX_UPLOAD}{filename}_{file_size}"

def format_download_request(filename: str) -> str:
    """
    Formatea un mensaje de solicitud de download.
    
    Args:
        filename (str): Nombre del archivo
        
    Returns:
        str: Mensaje formateado (ej: "D_archivo.txt")
    """
    return f"{PREFIX_DOWNLOAD}{filename}"

def format_chunk_data(prefix: str, data: bytes) -> bytes:
    """
    Formatea datos de chunk con el prefijo correspondiente.
    
    Args:
        prefix (str): Prefijo a usar ("U_" o "D_")
        data (bytes): Datos del chunk
        
    Returns:
        bytes: Datos formateados con prefijo
    """
    return f"{prefix}{data.decode('latin-1')}".encode('latin-1')

def remove_prefix(data: bytes, expected_prefix: str) -> bytes:
    """
    Remueve el prefijo de los datos si está presente.
    
    Args:
        data (bytes): Datos con posible prefijo
        expected_prefix (str): Prefijo esperado ("U_" o "D_")
        
    Returns:
        bytes: Datos sin prefijo
    """
    prefix_bytes = expected_prefix.encode('utf-8')
    if data.startswith(prefix_bytes):
        return data[len(prefix_bytes):]
    return data

def validate_prefix(data: bytes, expected_prefix: str) -> tuple[bool, str]:
    """
    Valida que los datos tengan el prefijo esperado.
    
    Args:
        data (bytes): Datos a validar
        expected_prefix (str): Prefijo esperado ("U_" o "D_")
        
    Returns:
        tuple: (es_valido, mensaje_error)
    """
    prefix_bytes = expected_prefix.encode('utf-8')
    
    if data.startswith(prefix_bytes):
        return True, ""
    
    # Verificar si tiene el prefijo opuesto (error)
    opposite_prefix = PREFIX_DOWNLOAD if expected_prefix == PREFIX_UPLOAD else PREFIX_UPLOAD
    opposite_bytes = opposite_prefix.encode('utf-8')
    
    if data.startswith(opposite_bytes):
        operation = "download" if expected_prefix == PREFIX_UPLOAD else "upload"
        return False, f"Error: recibido chunk de {operation} durante operación incorrecta"
    
    # Prefijo no reconocido, intentar parsear como error
    try:
        error_text = data.decode('utf-8', errors='ignore')
        if 'ERROR' in error_text.upper() or 'ERR' in error_text.upper():
            return False, f"Error del servidor: {error_text}"
        else:
            return False, f"Error desconocido del servidor: {error_text}"
    except:
        return False, "Error del servidor: no se pudo parsear el mensaje de error"

