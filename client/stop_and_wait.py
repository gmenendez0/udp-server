#!/usr/bin/env python3
"""
Implementación del protocolo Stop & Wait para transferencia de archivos.
"""

import logging
from pathlib import Path
from typing import Tuple, Optional
from protocol.rdt.rdt_message import RdtMessage, RdtRequest
from protocol.const import T_DATA, T_ACK, F_LAST, T_GETDATA, get_error_message, ERR_NOT_FOUND, ERR_TOO_BIG
from .rdt_client import RdtClient, ConnectionState, CHUNK_SIZE, MAX_RETRIES, validate_file_size, MAX_FILE_SIZE_MB

logger = logging.getLogger(__name__)


def handle_upload_stop_and_wait(path: Path, host: str, port: int, filename: str) -> bool:
    """
    Maneja la subida de un archivo usando Stop & Wait con handshake.

    Args:
        path (Path): Ruta del archivo a subir.
        host (str): IP del servidor.
        port (int): Puerto del servidor.
        filename (str): Nombre con el que guardar en servidor.

    Returns:
        bool: True si se completó con éxito, False si falló.
    """
    if not path.exists():
        logger.error(f"Archivo no encontrado: {path}")
        logger.error(f"Código de error: {get_error_message(ERR_NOT_FOUND)}")
        return False

    is_valid, error_code = validate_file_size(path)
    if not is_valid:
        logger.error(f"Archivo excede el tamaño máximo de {MAX_FILE_SIZE_MB}MB: {path}")
        logger.error(f"Código de error: {get_error_message(error_code)}")
        return False

    client = RdtClient(host, port)
    
    try:
        if not client.connect():
            logger.error("No se pudo establecer conexión con el servidor")
            return False
        
        logger.info("Conexión establecida, iniciando transferencia de archivo")
        
        # Crear estado de conexión basado en la información del handshake
        connection_state = ConnectionState(client.get_handshake_info())
        
        total_size = path.stat().st_size
        total_chunks = (total_size // CHUNK_SIZE) + (1 if total_size % CHUNK_SIZE else 0)
        current_chunk = 1
        
        # Enviar nombre del archivo como primer mensaje
        filename_msg = RdtMessage(
            flag=T_DATA,
            max_window=connection_state.get_max_window(),
            seq_num=connection_state.get_next_sequence_number(),
            ref_num=connection_state.get_current_reference_number(),
            data=filename.encode('utf-8')
        )
        
        client.send(filename_msg.to_bytes())
        logger.info(f"Enviado nombre del archivo: {filename}")
        connection_state.increment_sequence_number()
        
        # Enviar archivo por chunks
        with open(path, "rb") as file:
            while chunk := file.read(CHUNK_SIZE):
                success = False
                retries = 0
                is_last_chunk = current_chunk == total_chunks
                
                while not success and retries < MAX_RETRIES:
                    flag = F_LAST if is_last_chunk else T_DATA
                    rdt_msg = RdtMessage(
                        flag=flag,
                        max_window=connection_state.get_max_window(),
                        seq_num=connection_state.get_next_sequence_number(),
                        ref_num=connection_state.get_current_reference_number(),
                        data=chunk
                    )
                    
                    client.send(rdt_msg.to_bytes())
                    logger.info(f"Enviado chunk seq={connection_state.get_next_sequence_number()} ({current_chunk}/{total_chunks}), esperando ACK...")
                    
                    data, _, close_signal = client.receive()
                    
                    if close_signal:
                        logger.info("Servidor solicitó cerrar la conexión.")
                        return True
                    
                    if not data:
                        logger.warning(f"Timeout esperando ACK para chunk seq={connection_state.get_next_sequence_number()}")
                        retries += 1
                        client.stats['retransmissions'] += 1
                        continue
                    
                    try:
                        rdt_response = RdtRequest(address=f"{host}:{port}", request=data)
                        
                        if rdt_response.is_error():
                            error_code = rdt_response.get_error_code()
                            logger.error(f"Error del servidor: {get_error_message(error_code)}")
                            return False
                        
                        expected_ref_num = connection_state.get_next_sequence_number() + 1
                        if rdt_response.is_ack() and rdt_response.get_ref_num() == expected_ref_num:
                            logger.info(f"ACK recibido para chunk seq={connection_state.get_next_sequence_number()}")
                            success = True
                            connection_state.update_reference_number(rdt_response.get_ref_num())
                            connection_state.increment_sequence_number()
                        else:
                            logger.warning(f"ACK inválido para chunk seq={connection_state.get_next_sequence_number()}")
                            retries += 1
                            client.stats['errors'] += 1
                            
                    except Exception as e:
                        logger.error(f"Error parseando ACK: {e}")
                        retries += 1
                        client.stats['errors'] += 1
                
                if not success:
                    logger.error(f"No se recibió ACK después de {MAX_RETRIES} intentos. Abortando.")
                    return False
                
                current_chunk += 1
        
        # Mostrar estadísticas
        stats = client.get_stats()
        logger.info(f"Upload completado. Estadísticas: {stats}")
        return True
        
    except Exception as e:
        logger.error(f"Upload falló: {e}")
        return False
    finally:
        client.close()


def handle_download_stop_and_wait(path: Path, host: str, port: int, filename: str) -> bool:
    """
    Maneja la descarga de un archivo usando Stop & Wait con handshake.

    Args:
        path (Path): Ruta donde guardar el archivo.
        host (str): IP del servidor.
        port (int): Puerto del servidor.
        filename (str): Nombre del archivo a descargar.

    Returns:
        bool: True si se completó con éxito, False si falló.
    """
    client = RdtClient(host, port)
    
    try:
        if not client.connect():
            logger.error("No se pudo establecer conexión con el servidor")
            return False
        
        logger.info("Conexión establecida, solicitando descarga de archivo")
        
        connection_state = ConnectionState(client.get_handshake_info())

        # TODO: ver si esto lo dejamos así o lo definimos diferente
        request_msg = RdtMessage(
            flag=T_GETDATA,
            max_window=connection_state.get_max_window(),
            seq_num=connection_state.get_next_sequence_number(),
            ref_num=connection_state.get_current_reference_number(),
            data=filename.encode('utf-8')
        )
        
        client.send(request_msg.to_bytes())
        logger.info(f"Solicitando descarga de {filename}...")
        
        connection_state.increment_sequence_number()
        
        expected_seq_num = 0
        file_data = b''
        
        while True:
            data, _, close_signal = client.receive()
            
            if close_signal:
                logger.info("Servidor solicitó cerrar la conexión.")
                break
            
            if not data:
                logger.warning("Timeout esperando datos del servidor")
                continue
            
            try:
                rdt_response = RdtRequest(address=f"{host}:{port}", request=data)
                
                if rdt_response.get_seq_num() == expected_seq_num:
                    logger.info(f"Recibido chunk {expected_seq_num}")
                    
                    file_data += rdt_response.get_data()
                    
                    ack_msg = RdtMessage(
                        flag=T_ACK,
                        max_window=connection_state.get_max_window(),
                        seq_num=expected_seq_num,
                        ref_num=expected_seq_num + 1,
                        data=b''
                    )
                    client.send(ack_msg.to_bytes())
                    
                    if rdt_response.is_last():
                        logger.info("Recibido último paquete")
                        break
                    
                    expected_seq_num += 1
                    
                elif rdt_response.get_seq_num() < expected_seq_num:
                    logger.info(f"Paquete duplicado {rdt_response.get_seq_num()}, reenviando ACK")
                    ack_msg = RdtMessage(
                        flag=T_ACK,
                        max_window=connection_state.get_max_window(),
                        seq_num=rdt_response.get_seq_num(),
                        ref_num=rdt_response.get_seq_num() + 1,
                        data=b''
                    )
                    client.send(ack_msg.to_bytes())
                    
                else:
                    # Paquete fuera de orden, descartar
                    logger.warning(f"Paquete fuera de orden {rdt_response.get_seq_num()}, esperado {expected_seq_num}")
                    
            except Exception as e:
                logger.error(f"Error parseando paquete: {e}")
                client.stats['errors'] += 1
                continue
        
        # Guardar archivo
        if file_data:
            with open(path, "wb") as file:
                file.write(file_data)
            logger.info(f"Archivo guardado exitosamente en {path}")
            
            # Mostrar estadísticas
            stats = client.get_stats()
            logger.info(f"Download completado. Estadísticas: {stats}")
            return True
        else:
            logger.error("No se recibieron datos del archivo")
            return False
            
    except Exception as e:
        logger.error(f"Download falló: {e}")
        return False
    finally:
        client.close()
