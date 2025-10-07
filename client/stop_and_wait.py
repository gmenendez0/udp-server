#!/usr/bin/env python3
"""
Implementación del protocolo Stop & Wait para transferencia de archivos.
"""

import logging
from pathlib import Path
from typing import Tuple, Optional
from protocol.rdt.rdt_message import RdtMessage, RdtRequest
from .rdt_client import RdtClient, CHUNK_SIZE, MAX_RETRIES, validate_file_size, MAX_FILE_SIZE_MB
from server.file_helpers import get_file_in_chunks
import os

# Importar constantes
from .constants import (
    FLAG_DATA, FLAG_ACK, FLAG_LAST,
    PREFIX_UPLOAD, PREFIX_DOWNLOAD, PREFIX_DATA, PREFIX_ERROR,
    ERR_TOO_BIG, ERR_NOT_FOUND, ERR_BAD_REQUEST, ERR_PERMISSION_DENIED,
    ERR_NETWORK_ERROR, ERR_TIMEOUT_ERROR, ERR_INVALID_PROTOCOL, ERR_SERVER_ERROR,
    get_error_message, format_upload_request, format_download_request,
    format_chunk_data, remove_prefix, validate_prefix
)

logger = logging.getLogger(__name__)

def handle_upload_stop_and_wait(path: Path, host: str, port: int, filename: str, max_window: int = 1) -> bool:
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

    client = RdtClient(host, port, max_window)
    
    try:
        if not client.connect():
            logger.error("No se pudo establecer conexión con el servidor")
            return False
        
        logger.info("Conexión establecida, iniciando transferencia de archivo")
        
        connection_state = client.get_connection_state()
        
        total_size = path.stat().st_size
        total_chunks = (total_size // CHUNK_SIZE) + (1 if total_size % CHUNK_SIZE else 0)
        current_chunk = 1
        file_info = format_upload_request(filename, total_size)
        file_info_msg = RdtMessage(
            flag=FLAG_DATA,
            max_window=connection_state.get_max_window(),
            seq_num=connection_state.get_next_sequence_number(),
            ref_num=connection_state.get_current_reference_number(),
            data=file_info.encode('utf-8')
        )
        
        client.send(file_info_msg.to_bytes())
        logger.info(f"Enviado información del archivo: {file_info}")
        
        data, _, close_signal = client.receive()
        if close_signal:
            logger.info("Servidor solicitó cerrar la conexión.")
            return True
        if not data:
            logger.error("Timeout esperando ACK del mensaje inicial")
            return False
        
        try:
            rdt_response = RdtRequest(address=f"{host}:{port}", request=data)
            
            if rdt_response.is_error():
                error_code = rdt_response.get_error_code()
                logger.error(f"Error del servidor en mensaje inicial: {get_error_message(error_code)}")
                return False
            
            response_data = rdt_response.get_data()
            if response_data and not response_data.startswith(b'U_') and not response_data.startswith(b'D_'):
                try:
                    error_text = response_data.decode('utf-8', errors='ignore')
                    if 'ERROR' in error_text.upper() or 'ERR' in error_text.upper():
                        logger.error(f"Error del servidor: {error_text}")
                    else:
                        logger.error(f"Error desconocido del servidor: {error_text}")
                except:
                    logger.error("Error del servidor: no se pudo parsear el mensaje de error")
                return False
            
            if rdt_response.is_ack():
                # Para el mensaje inicial, el servidor debe confirmar nuestro seq_num
                expected_ref_num = connection_state.get_next_sequence_number() + 1
                if rdt_response.get_ref_num() == expected_ref_num:
                    logger.info("ACK recibido para mensaje inicial")
                    connection_state.update_reference_number(rdt_response.get_ref_num())
                    connection_state.increment_sequence_number()
                else:
                    logger.error(f"ACK inválido para mensaje inicial: {rdt_response.get_ref_num()}, esperado: {expected_ref_num}")
                    return False
            else:
                logger.error("Servidor no envió ACK para mensaje inicial")
                return False
        except Exception as e:
            logger.error(f"Error parseando ACK del mensaje inicial: {e}")
            return False
        
        # Esperar mensaje D_OK o E_ después del ACK inicial
        data, _, close_signal = client.receive()
        if close_signal:
            logger.info("Servidor solicitó cerrar la conexión.")
            return True
        if not data:
            logger.error("Timeout esperando confirmación D_OK/E_ del servidor")
            return False
        
        try:
            rdt_response = RdtRequest(address=f"{host}:{port}", request=data)
            
            if rdt_response.is_error():
                error_code = rdt_response.get_error_code()
                logger.error(f"Error del servidor: {get_error_message(error_code)}")
                return False
            
            response_data = rdt_response.get_data()
            if response_data:
                try:
                    response_text = response_data.decode('utf-8', errors='ignore')
                    if response_text.startswith('D_OK'):
                        logger.info("Servidor confirmó que está listo para recibir el archivo")
                    elif response_text.startswith('E_'):
                        logger.error(f"Error del servidor: {response_text}")
                        return False
                    else:
                        logger.error(f"Respuesta inesperada del servidor: {response_text}")
                        return False
                except:
                    logger.error("Error decodificando respuesta del servidor")
                    return False
            
            # Enviar ACK de confirmación para el mensaje D_OK/E_
            ack_msg = RdtMessage(
                flag=FLAG_ACK,
                max_window=connection_state.get_max_window(),
                seq_num=connection_state.get_next_sequence_number(),
                ref_num=connection_state.get_next_sequence_number(),
                data=b''
            )
            client.send(ack_msg.to_bytes())
            logger.info("ACK enviado para confirmación del servidor")
            connection_state.increment_sequence_number()
            
        except Exception as e:
            logger.error(f"Error parseando confirmación del servidor: {e}")
            return False
        
        file_chunks = get_file_in_chunks(str(path), CHUNK_SIZE)
        total_chunks = len(file_chunks)
        
        for current_chunk in range(1, total_chunks + 1):
            chunk = file_chunks[current_chunk - 1]
            success = False
            retries = 0
            is_last_chunk = current_chunk == total_chunks
            
            while not success and retries < MAX_RETRIES:
                flag = FLAG_LAST if is_last_chunk else FLAG_DATA
                chunk_with_prefix = format_chunk_data(PREFIX_DATA, chunk)
                current_seq = connection_state.get_next_sequence_number()
                rdt_msg = RdtMessage(
                    flag=flag,
                    max_window=connection_state.get_max_window(),
                    seq_num=current_seq,
                    ref_num=connection_state.get_current_reference_number(),
                    data=chunk_with_prefix
                )
                
                client.send(rdt_msg.to_bytes())
                logger.info(f"Enviado chunk seq={current_seq} ({current_chunk}/{total_chunks}), esperando ACK...")
                
                data, _, close_signal = client.receive()
                
                if close_signal:
                    logger.info("Servidor solicitó cerrar la conexión.")
                    return True
                
                if not data:
                    logger.warning(f"Timeout esperando ACK para chunk seq={current_seq}")
                    retries += 1
                    client.stats['retransmissions'] += 1
                    continue
                
                try:
                    rdt_response = RdtRequest(address=f"{host}:{port}", request=data)
                    
                    if rdt_response.is_error():
                        error_code = rdt_response.get_error_code()
                        logger.error(f"Error del servidor: {get_error_message(error_code)}")
                        return False
                    
                    expected_ref_num = current_seq + 1
                    if rdt_response.is_ack() and rdt_response.get_ref_num() == expected_ref_num:
                        logger.info(f"ACK recibido para chunk seq={current_seq}")
                        success = True
                        connection_state.update_reference_number(rdt_response.get_ref_num())
                        connection_state.increment_sequence_number()
                    else:
                        logger.warning(f"ACK inválido para chunk seq={current_seq}")
                        print(f'expected_ref_num: {expected_ref_num}, rdt_response.is_ack(): {rdt_response.is_ack()}, rdt_response.get_ref_num(): {rdt_response.get_ref_num()}')
                        retries += 1
                        client.stats['errors'] += 1
                            
                except Exception as e:
                    logger.error(f"Error parseando ACK: {e}")
                    retries += 1
                    client.stats['errors'] += 1
            
            if not success:
                logger.error(f"No se recibió ACK después de {MAX_RETRIES} intentos. Abortando.")
                return False
        
        # Mostrar estadísticas
        stats = client.get_stats()
        logger.info(f"Upload completado. Estadísticas: {stats}")
        return True
        
    except Exception as e:
        logger.error(f"Upload falló: {e}")
        return False
    finally:
        client.close()


def handle_download_stop_and_wait(path: Path, host: str, port: int, filename: str, max_window: int = 1) -> bool:
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
    client = RdtClient(host, port, max_window)
    
    try:
        if not client.connect():
            logger.error("No se pudo establecer conexión con el servidor")
            return False
        
        logger.info("Conexión establecida, solicitando descarga de archivo")
        
        connection_state = client.get_connection_state()

        download_request = format_download_request(filename)
        request_msg = RdtMessage(
            flag=FLAG_DATA,
            max_window=connection_state.get_max_window(),
            seq_num=connection_state.get_next_sequence_number(),
            ref_num=connection_state.get_current_reference_number(),
            data=download_request.encode('utf-8')
        )
        
        client.send(request_msg.to_bytes())
        logger.info(f"Solicitando descarga: {download_request}")
        
        data, _, close_signal = client.receive()
        if close_signal:
            logger.info("Servidor solicitó cerrar la conexión.")
            return True
        if not data:
            logger.error("Timeout esperando ACK de la solicitud de download")
            return False
        
        try:
            rdt_response = RdtRequest(address=f"{host}:{port}", request=data)
            
            if rdt_response.is_error():
                error_code = rdt_response.get_error_code()
                logger.error(f"Error del servidor en solicitud de download: {get_error_message(error_code)}")
                return False
            
            response_data = rdt_response.get_data()
            if response_data and not response_data.startswith(b'U_') and not response_data.startswith(b'D_'):
                try:
                    error_text = response_data.decode('utf-8', errors='ignore')
                    if 'ERROR' in error_text.upper() or 'ERR' in error_text.upper():
                        logger.error(f"Error del servidor: {error_text}")
                    else:
                        logger.error(f"Error desconocido del servidor: {error_text}")
                except:
                    logger.error("Error del servidor: no se pudo parsear el mensaje de error")
                return False
            
            if rdt_response.is_ack():
                expected_ref_num = connection_state.get_next_sequence_number() + 1
                if rdt_response.get_ref_num() == expected_ref_num:
                    logger.info("ACK recibido para solicitud de download")
                    connection_state.update_reference_number(rdt_response.get_ref_num())
                    connection_state.increment_sequence_number()
                else:
                    logger.error(f"ACK inválido para solicitud de download: {rdt_response.get_ref_num()}, esperado: {expected_ref_num}")
                    return False
            else:
                logger.error("Servidor no envió ACK para solicitud de download")
                return False
        except Exception as e:
            logger.error(f"Error parseando ACK de la solicitud de download: {e}")
            return False
        
        expected_seq_num = 1
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
                    
                    chunk_data = rdt_response.get_data()
                    is_valid, error_msg = validate_prefix(chunk_data, PREFIX_DATA)
                    
                    if is_valid:
                        # Chunk válido de download
                        chunk_data = remove_prefix(chunk_data, PREFIX_DATA)
                        file_data += chunk_data
                    else:
                        logger.error(error_msg)
                        return False
                    
                    ack_msg = RdtMessage(
                        flag=FLAG_ACK,
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
                    # Paquete duplicado - validar y reenviar ACK
                    logger.info(f"Paquete duplicado {rdt_response.get_seq_num()}, reenviando ACK")
                    
                    # Validar prefijo del paquete duplicado
                    chunk_data = rdt_response.get_data()
                    is_valid, error_msg = validate_prefix(chunk_data, PREFIX_DATA)
                    
                    if not is_valid:
                        logger.error(f"Paquete duplicado con prefijo inválido: {error_msg}")
                        return False
                    
                    # Reenviar ACK del paquete duplicado
                    ack_msg = RdtMessage(
                        flag=FLAG_ACK,
                        max_window=connection_state.get_max_window(),
                        seq_num=rdt_response.get_seq_num(),
                        ref_num=rdt_response.get_seq_num() + 1,
                        data=b''
                    )
                    client.send(ack_msg.to_bytes())
                    logger.info(f"ACK reenviado para paquete duplicado seq={rdt_response.get_seq_num()}")
                    
                else:
                    # Paquete fuera de orden - descartar y enviar ACK del último recibido
                    logger.warning(f"Paquete fuera de orden {rdt_response.get_seq_num()}, esperado {expected_seq_num}")
                    
                    # Enviar ACK del último paquete recibido correctamente
                    if expected_seq_num > 0:
                        last_acked_seq = expected_seq_num - 1
                        ack_msg = RdtMessage(
                            flag=FLAG_ACK,
                            max_window=connection_state.get_max_window(),
                            seq_num=last_acked_seq,
                            ref_num=last_acked_seq + 1,
                            data=b''
                        )
                        client.send(ack_msg.to_bytes())
                        logger.info(f"ACK enviado para último paquete correcto seq={last_acked_seq}")
                    
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
