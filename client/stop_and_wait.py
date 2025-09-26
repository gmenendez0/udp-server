#!/usr/bin/env python3
"""
Cliente UDP para subir archivos usando Stop-and-Wait (RDT).

Notas:
- Los paquetes UDP tienen un límite: MTU típica ~1500 bytes → conviene enviar menos (~1024 bytes).
- Implementa stop and wait: enviar un chunk, esperar ACK, reintentar si falla.
- Detecta señal de cierre enviada por el servidor.
"""

import random
import threading
import uuid as uuid_lib
from pathlib import Path
from protocol.dp.dp_request import DPRequest
from protocol.rdt.rdt_request import RDTRequest
from protocol import FunctionFlag
from client.udp_client import UDPClient

CHUNK_SIZE = 1024  # Tamaño máximo por chunk (bytes)
ACK_TIMEOUT = 2     # Timeout en segundos para recibir ACK
MAX_RETRIES = 5     # Reintentos por chunk

class StopAndWaitState:
    """
    Singleton que mantiene el estado del protocolo Stop & Wait:
    - Número de secuencia
    - Número de referencia
    - Lock para concurrencia
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
                    cls._instance.sequence_number = random.randint(0, 1000)
                    cls._instance.reference_number = 0
                    cls._instance.lock = threading.Lock()
                    cls._instance.waiting_ack = False
        return cls._instance

    def next_sequence(self):
        """Incrementa y devuelve el próximo número de secuencia."""
        with self.lock:
            self.sequence_number += 1
            return self.sequence_number
        
    def get_reference_number(self):
        """Devuelve el número de referencia actual."""
        return self.reference_number

def parse_received_packet(data: bytes) -> dict:
    """
    Parsear paquete recibido de ACK.
    Formato esperado: {ack_flag}{seq}|{ref}_...

    Retorna:
        dict con ack_flag, sequence_number, reference_number
    """
    try:
        ack_flag = data[0:1] == b"1"
        pipe_idx = data.index(b"|")
        us_idx = data.index(b"_", pipe_idx)
        sequence_number = int(data[1:pipe_idx])
        reference_number = int(data[pipe_idx + 1:us_idx])
        return {
            "ack_flag": ack_flag,
            "sequence_number": sequence_number,
            "reference_number": reference_number
        }
    except Exception as e:
        print(f"[ERROR] parse_received_packet: {e}")
        return {}

# TODO ver cómo mandamos el filename -> pienso que podríamos mandarlo como 1er mensaje, antes de empezar con los datos
def handle_upload(path: Path, host: str, port: int, filename: str) -> bool:
    """
    Maneja la subida de un archivo usando Stop & Wait.

    Args:
        path (Path): Ruta del archivo a subir.
        host (str): IP del servidor.
        port (int): Puerto del servidor.
        filename (str): Nombre con el que guardar en servidor.

    Returns:
        bool: True si se completó con éxito, False si falló.
    """
    if not path.exists():
        print(f"[ERROR] Archivo no encontrado: {path}")
        return False

    state = StopAndWaitState()
    socket_interface = UDPClient(host, port)

    try:
        total_size = path.stat().st_size
        total_chunks = (total_size // CHUNK_SIZE) + (1 if total_size % CHUNK_SIZE else 0)
        current_chunk = 1
        uuid = str(uuid_lib.uuid4())  # UUID único para identificar esta transferencia

        with open(path, "rb") as file:
            while chunk := file.read(CHUNK_SIZE):
                success = False
                retries = 0
                flag = FunctionFlag.CLOSE_CONN if current_chunk == total_chunks else FunctionFlag.NONE

                while not success and retries < MAX_RETRIES:
                    seq = state.next_sequence()
                    dp_request = DPRequest.from_user_input(flag, uuid, chunk)
                    rdt_request_bytes = RDTRequest.from_dp_request(dp_request, seq, state.get_reference_number()).serialize()

                    socket_interface.send(rdt_request_bytes)
                    print(f"[INFO] Enviado chunk {seq} ({current_chunk}/{total_chunks}), esperando ACK...")

                    data, _, close_signal = socket_interface.receive()

                    if close_signal:
                        print("[INFO] Servidor solicitó cerrar la conexión.")
                        socket_interface.close()
                        return True

                    if not data:
                        print(f"[WARNING] Timeout esperando ACK para chunk {seq}")
                        retries += 1
                        continue

                    ack_info = parse_received_packet(data)
                    if ack_info and ack_info["ack_flag"] and ack_info["reference_number"] == seq + 1:
                        print(f"[INFO] ACK recibido para chunk {seq}")
                        state.reference_number = ack_info["reference_number"]
                        success = True
                    else:
                        print(f"[WARNING] ACK inválido para chunk {seq}")
                        retries += 1

                if not success:
                    print(f"[ERROR] No se recibió ACK después de {MAX_RETRIES} intentos. Abortando.")
                    socket_interface.close()
                    return False

                current_chunk += 1

        print("[INFO] Upload completado con éxito.")
        socket_interface.close()
        return True

    except Exception as e:
        print(f"[ERROR] Upload falló: {e}")
        socket_interface.close()
        return False

def handle_download(path: Path,host: str, port: int, filename: str) -> bool:
    
    state = StopAndWaitState()
    socket_interface = UDPClient(host, port)
    socket_interface.socket.settimeout(ACK_TIMEOUT)
    uuid = str(uuid_lib.uuid4())  # UUID único para identificar esta transferencia


    try: #primero solicitamos la descarga al server

        print(f"[INFO] Solicitando descarga de {filename}...")

        seq = state.next_sequence()
        dp_request = DPRequest.from_user_input(FunctionFlag.NONE,uuid,filename.encode())
        rdt_request_bytes = RDTRequest.from_dp_request(dp_request, seq,0).serialize()
        socket_interface.send(rdt_request_bytes)

        print(f"[INFO] Esperando respuesta del servidor a la solicitud (seq = {seq})...")

        expected_seq_num = 0 # la secuencia de datos empieza en 0

        with open(path, "wb") as file:
            while True:
                data, _,_ = socket_interface.receive() #le pido un chunk de datos al servidor
            
                if not data:
                    print(f"[WARNING] Timeout esperando datos del servidor {seq}")
                    continue #siguiente iteracion del while hasta conseguir datos o cerrar conexion
                
                # se recibio data
                try:
                    #TODO: parsear data recibida
                    pass  # Agrega lógica de parseo aquí

                except Exception as e:
                    print(f"[ERROR] Se recibio un paquete corrupto: {e}")
                    print("Descartando paquete...")
                    continue #sigueinte iteracion para conseguir un paquete valido

                """
                Ya se parseo la data, ahora hay 3 casos posibles:
                - El paquete es el esperado (si es asi chequeo si es el ultimo)
                - El paquete es un duplicado
                - El paquete esta fuera de orden
                """

                # caso 1

                # caso 2

                # caso 3
            pass

    except Exception as e:
        print(f"[ERROR] Download falló: {e}")
        socket_interface.close()
        return False    