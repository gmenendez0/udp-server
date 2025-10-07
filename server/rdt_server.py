import threading
from server.rdt_connection import RdtConnectionRepository, RdtConnection
import socket

class RDTServer:
    def __init__(self, host: str, port: int, buffer_size: int, conn_repo: RdtConnectionRepository = None):
        self._host = host
        self._port = port
        self._recv_buffer_size = buffer_size
        self._skt = None
        self._conn_repo = conn_repo
        self._active_threads = {}  # Diccionario para manejar hilos activos
        self._is_running = True

    def serve(self) -> None:
        self._skt = get_udp_socket(self._host, self._port)
        self._skt.setblocking(True)

        print(f"RDT server listening on {self._host}:{self._port}")
        try:
            while self._is_running:
                data, address = self._skt.recvfrom(self._recv_buffer_size)
                str_address = f"{address[0]}:{address[1]}"

                connection = self._conn_repo.get_connection(str_address)
                if connection:
                    connection.add_request(data)
                    print(f"[RDT] Petición añadida a conexión existente {str_address}")
                else:
                    # Crear nueva conexión sin hilo
                    connection = RdtConnection(address=str_address)
                    connection.add_request(data)
                    self._conn_repo.add_connection(str_address, connection)
                    
                    # Crear y manejar hilo para esta conexión
                    connection_thread = threading.Thread(
                        target=self._handle_connection,
                        args=(str_address, connection),
                        daemon=True,
                        name=f"Connection-{str_address}"
                    )
                    connection_thread.start()
                    self._active_threads[str_address] = connection_thread
                    
                    print(f"[RDT] Nueva conexión creada para {str_address}")
        finally:
            self._shutdown()

    def _handle_connection(self, address: str, connection: RdtConnection) -> None:
        """Maneja una conexión específica en su propio hilo"""
        try:
            connection.process_requests()
        except Exception as e:
            print(f"Error manejando conexión {address}: {e}")
        finally:
            # Limpiar recursos cuando la conexión termine
            print(f"[RDT] Conexión {address} cerrada y limpiada")

    def _shutdown(self) -> None:
        """Cierra el servidor y todos los hilos activos"""
        print("Iniciando shutdown del servidor...")
        self._is_running = False
        
        # Esperar a que todos los hilos terminen
        for address, thread in self._active_threads.items():
            if thread.is_alive():
                print(f"Esperando que termine el hilo de {address}")
                thread.join(timeout=2.0)
        
        if self._skt:
            self._skt.close()

        print("Server shutdown complete.")

def get_udp_socket(host: str, port: int) -> socket.socket:
    return get_socket(socket.SOCK_DGRAM, host, port)

def get_socket(kind: int, host: str, port: int) -> socket.socket:
    if kind != socket.SOCK_DGRAM and kind != socket.SOCK_STREAM:
        raise ValueError("Invalid socket kind. Use socket.SOCK_DGRAM or socket.SOCK_STREAM.")

    skt = socket.socket(socket.AF_INET, kind)
    skt.bind((host, port))

    return skt



