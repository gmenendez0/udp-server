#!/usr/bin/env python3
"""
Proporciona una interfaz para enviar y recibir paquetes UDP,
incluyendo manejo de concurrencia mediante locks y detección
de señales especiales (por ejemplo, CLOSE_CONN definidas en el protocolo).
"""

import socket
import threading
from typing import Optional, Tuple
from protocol.dp.dp_request import DPRequest
from protocol import FunctionFlag

BUFFER_SIZE = 2048  # Tamaño máximo del buffer para recibir paquetes UDP


def get_udp_socket(host: str, port: int) -> socket.socket:
    """
    Crea un socket UDP (SOCK_DGRAM) y lo liga al host y puerto dados.
    """
    skt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    skt.bind((host, port))
    skt.setblocking(True)
    return skt


class UDPClient:
    """
    Encapsula envío y recepción de paquetes UDP, incluyendo detección
    de señal CLOSE_CONN.
    """

    def __init__(self, host: str, port: int):
        """
        Inicializa el cliente UDP.

        Args:
            host (str): IP del servidor.
            port (int): Puerto del servidor.
        """
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(True)
        self.lock = threading.Lock()
        self.closed_by_server = False

    def send(self, data: bytes):
        """
        Envía datos al servidor.

        Args:
            data (bytes): Datos a enviar.
        """
        with self.lock:
            self.sock.sendto(data, (self.host, self.port))

    def receive(self) -> Tuple[Optional[bytes], Optional[Tuple[str, int]], bool]:
        """
        Recibe datos desde el servidor.

        Returns:
            tuple:
                - data (bytes | None): Datos recibidos.
                - addr (tuple[str, int] | None): Dirección del remitente.
                - close_signal (bool): True si el servidor envió señal de cierre.
        """
        try:
            data, addr = self.sock.recvfrom(BUFFER_SIZE)
            if self._check_close_signal(data):
                self.closed_by_server = True
                return data, addr, True
            return data, addr, False
        except socket.timeout:
            return None, None, False

    def _check_close_signal(self, data: bytes) -> bool:
        """
        Verifica si el paquete recibido indica CLOSE_CONN.

        Args:
            data (bytes): Paquete recibido.

        Returns:
            bool: True si indica cerrar conexión.
        """
        try:
            dp = DPRequest(data)
            return dp.function_flag == FunctionFlag.CLOSE_CONN
        except Exception:
            return False

    def close(self):
        """
        Cierra el socket.
        """
        self.sock.close()
