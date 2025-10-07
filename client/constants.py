#!/usr/bin/env python3
"""
Constantes del cliente RDT.
"""

# Constantes de protocolo RDT
FLAG_ACK = 1
FLAG_DATA = 2
FLAG_LAST = 3

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

def parse_server_error(data: bytes) -> tuple[bool, str]:
    """
    Parsea un mensaje de error del servidor.
    
    Args:
        data (bytes): Datos del mensaje de error
        
    Returns:
        tuple: (es_error, mensaje_error)
    """
    if not data:
        return False, ""
    
    try:
        # Intentar decodificar como UTF-8 primero
        data_str = data.decode('utf-8', errors='ignore')
    except:
        try:
            # Si falla, intentar con latin-1
            data_str = data.decode('latin-1', errors='ignore')
        except:
            return False, ""
    
    # Verificar si es un error del servidor
    if data_str.startswith('E_'):
        error_type = data_str[2:]  # Remover 'E_'
        
        # Mapear tipos de error específicos del servidor
        error_messages = {
            'FILE_ALREADY_EXISTS': 'El archivo ya existe en el servidor',
            'FILE_TOO_LARGE': 'El archivo excede el tamaño máximo permitido',
            'FILE_NOT_FOUND': 'El archivo no fue encontrado en el servidor',
            'INVALID_DATA_FORMAT': 'Formato de datos inválido',
            'PERMISSION_DENIED': 'Permisos insuficientes',
            'SERVER_ERROR': 'Error interno del servidor',
            'NETWORK_ERROR': 'Error de red',
            'TIMEOUT_ERROR': 'Timeout en la operación'
        }
        
        error_msg = error_messages.get(error_type, f"Error del servidor: {error_type}")
        return True, error_msg
    
    # Verificar si contiene palabras clave de error
    if any(keyword in data_str.upper() for keyword in ['ERROR', 'ERR', 'FAIL', 'INVALID']):
        return True, f"Error del servidor: {data_str}"
    
    return False, ""

def get_server_error_message(data: bytes) -> str:
    """
    Obtiene un mensaje de error descriptivo del servidor.
    
    Args:
        data (bytes): Datos del mensaje de error
        
    Returns:
        str: Mensaje de error descriptivo
    """
    is_error, error_msg = parse_server_error(data)
    if is_error:
        return error_msg
    
    # Si no se pudo parsear como error específico, intentar decodificar
    try:
        data_str = data.decode('utf-8', errors='ignore')
        if data_str:
            return f"Error del servidor: {data_str}"
    except:
        try:
            data_str = data.decode('latin-1', errors='ignore')
            if data_str:
                return f"Error del servidor: {data_str}"
        except:
            pass
    
    return "Error del servidor: mensaje no reconocido"

# Comandos de operación
UPLOAD_COMMAND = 'U'
DOWNLOAD_COMMAND = 'D'

# Prefijos de mensajes (como bytes para mayor eficiencia)
PREFIX_DATA = b""
PREFIX_ERROR = b"E_"
PREFIX_DOWNLOAD = b"D_"
PREFIX_UPLOAD = b"U_"

def format_upload_request(filename: str, file_size: int) -> str:
    """
    Formatea un mensaje de solicitud de upload.
    
    Args:
        filename (str): Nombre del archivo
        file_size (int): Tamaño del archivo en bytes
        
    Returns:
        str: Mensaje formateado (ej: "U archivo.txt 5000000")
    """
    return f"{UPLOAD_COMMAND} {filename} {file_size}"

def format_download_request(filename: str) -> str:
    """
    Formatea un mensaje de solicitud de download.
    
    Args:
        filename (str): Nombre del archivo
        
    Returns:
        str: Mensaje formateado (ej: "D archivo.txt")
    """
    return f"{DOWNLOAD_COMMAND} {filename}"

def format_chunk_data(prefix: bytes, data: bytes) -> bytes:
    """
    Formatea datos de chunk con el prefijo correspondiente.
    
    Args:
        prefix (bytes): Prefijo a usar (b"U_" o b"D_")
        data (bytes): Datos del chunk
        
    Returns:
        bytes: Datos formateados con prefijo
    """
    return prefix + data

def remove_prefix(data: bytes, expected_prefix: bytes) -> bytes:
    """
    Remueve el prefijo de los datos si está presente.
    
    Args:
        data (bytes): Datos con posible prefijo
        expected_prefix (bytes): Prefijo esperado (b"U_" o b"D_")
        
    Returns:
        bytes: Datos sin prefijo
    """
   
    return data[2:]
    

def validate_prefix(data: bytes, expected_prefix: bytes) -> tuple[bool, str]:
    """
    Valida que los datos tengan el prefijo esperado.
    
    Args:
        data (bytes): Datos a validar
        expected_prefix (bytes): Prefijo esperado (b"U_" o b"D_")
        
    Returns:
        tuple: (es_valido, mensaje_error)
    """
    if data.startswith(expected_prefix):
        return True, ""
    
    # Verificar si tiene el prefijo opuesto (error)
    opposite_prefix = PREFIX_DOWNLOAD if expected_prefix == PREFIX_UPLOAD else PREFIX_UPLOAD
    
    if data.startswith(opposite_prefix):
        operation = "download" if expected_prefix == PREFIX_UPLOAD else "upload"
        return False, f"Error: recibido chunk de {operation} durante operación incorrecta"
    
    # Verificar si es un mensaje de error con PREFIX_ERROR
    if data.startswith(PREFIX_ERROR):
        try:
            error_text = data.decode('latin-1', errors='ignore')
            return False, f"Error del servidor: {error_text}"
        except:
            return False, "Error del servidor: no se pudo parsear el mensaje de error"
    
    # Prefijo no reconocido, intentar parsear como error
    try:
        error_text = data.decode('latin-1', errors='ignore')
        if 'ERROR' in error_text.upper() or 'ERR' in error_text.upper():
            return False, f"Error del servidor: {error_text}"
        else:
            return False, f"Error desconocido del servidor: {error_text}"
    except:
        return False, "Error del servidor: no se pudo parsear el mensaje de error"

