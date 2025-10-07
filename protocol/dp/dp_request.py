#!/usr/bin/env python3
"""
Implementación del protocolo DP (Data Protocol) para señales de control.
"""

from enum import IntEnum
from typing import Optional

class FunctionFlag(IntEnum):
    """Flags de función para el protocolo DP"""
    CLOSE_CONN = 0x10
    ERROR = 0x7F

class DPRequest:
    """
    Clase para manejar requests del protocolo DP.
    """
    
    def __init__(self, data: bytes):
        """
        Inicializa un DPRequest desde bytes.
        
        Args:
            data (bytes): Datos del request
        """
        self.data = data
        self.function_flag: Optional[FunctionFlag] = None
        
        if len(data) >= 1:
            try:
                self.function_flag = FunctionFlag(data[0])
            except ValueError:
                # No es un flag válido, asumir que es un request normal
                self.function_flag = None
    
    def is_close_connection(self) -> bool:
        """Verifica si es una señal de cierre de conexión"""
        return self.function_flag == FunctionFlag.CLOSE_CONN
    
    def is_error(self) -> bool:
        """Verifica si es una señal de error"""
        return self.function_flag == FunctionFlag.ERROR
    
    def get_data(self) -> bytes:
        """Obtiene los datos del request"""
        return self.data
