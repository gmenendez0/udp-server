#!/usr/bin/env python3
"""
Implementación del protocolo Go Back N para transferencia de archivos.
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def handle_upload_go_back_n(path: Path, host: str, port: int, filename: str, max_window: int = 5) -> bool:
    """
    Maneja la subida de un archivo usando Go-Back-N con handshake.

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
        
        logger.info("Conexión establecida, iniciando transferencia de archivo con Go-Back-N")
        
        connection_state = client.get_connection_state()
        
        window_size = connection_state.get_max_window()
        base = connection_state.get_next_sequence_number()
        next_seq_num = base
        
        sent_packets = {} 
        
        total_size = path.stat().st_size
        total_chunks = (total_size // CHUNK_SIZE) + (1 if total_size % CHUNK_SIZE else 0)
        
        file_info = format_upload_request(filename, total_size)
        file_info_msg = RdtMessage(
            flag=FLAG_DATA,
            max_window=window_size,
            seq_num=connection_state.get_next_sequence_number(),
            ref_num=connection_state.get_current_reference_number(),
            data=file_info.encode('latin-1')
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
                    error_text = response_data.decode('latin-1', errors='ignore')
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
                    logger.info("ACK recibido para mensaje inicial")
                    connection_state.update_reference_number(rdt_response.get_ref_num())
                    connection_state.increment_sequence_number()
                    # Actualizar la base después del mensaje inicial
                    base = connection_state.get_next_sequence_number()
                    next_seq_num = base
                    logger.info(f"Base actualizada después del mensaje inicial: base={base}")
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
                    response_text = response_data.decode('latin-1', errors='ignore')
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
        
        file_fully_read = False
        current_chunk_index = 0
        
        while not file_fully_read or base < next_seq_num:
            
            while next_seq_num < base + window_size and not file_fully_read:
                if current_chunk_index >= total_chunks:
                    file_fully_read = True
                    break
                    
                chunk = file_chunks[current_chunk_index]
                is_last_chunk = current_chunk_index == total_chunks - 1
                flag = FLAG_LAST if is_last_chunk else FLAG_DATA

                chunk_with_prefix = format_chunk_data(PREFIX_DATA, chunk)
                current_seq = next_seq_num
                rdt_msg = RdtMessage(
                    flag=flag, max_window=window_size,
                    seq_num=current_seq,
                    ref_num=connection_state.get_current_reference_number(),
                    data=chunk_with_prefix
                )
                
                sent_packets[current_seq] = rdt_msg.to_bytes()
                client.send(sent_packets[current_seq])
                logger.info(f"Enviado chunk seq={current_seq} (ventana: [{base}, {base+window_size-1}])")
                next_seq_num += 1
                current_chunk_index += 1
                
                data, _, close_signal = client.receive()
                
                if close_signal:
                    logger.info("Servidor solicitó cerrar la conexión.")
                    break

                if not data:
                    logger.warning(f"Timeout! Retransmitiendo ventana desde base={base}")
                    client.stats['retransmissions'] += 1
                    for i in range(base, next_seq_num):
                        if i in sent_packets:
                            client.send(sent_packets[i])
                    continue

                try:
                    rdt_response = RdtRequest(address=f"{host}:{port}", request=data)
                    
                    if rdt_response.is_error():
                        error_code = rdt_response.get_error_code()
                        logger.error(f"Error del servidor: {get_error_message(error_code)}")
                        return False
                    
                    if rdt_response.is_ack():
                        ack_num = rdt_response.get_ref_num()
                        logger.info(f"ACK recibido con ref_num={ack_num}")
                        
                        if ack_num >= base:
                            # El servidor confirma el paquete ack_num, entonces la nueva base es ack_num + 1
                            for i in range(base, ack_num + 1):
                                if i in sent_packets:
                                    del sent_packets[i]
                            base = ack_num 
                            connection_state.update_reference_number(ack_num + 1)
                            logger.info(f"Ventana deslizada. Nueva base={base}")
                            
                except Exception as e:
                    logger.error(f"Error parseando ACK: {e}")
                    client.stats['errors'] += 1

        stats = client.get_stats()
        logger.info(f"Upload completado. Estadísticas: {stats}")
        return True
        
    except Exception as e:
        logger.error(f"Upload falló: {e}")
        return False
    finally:
        client.close()


def handle_download_go_back_n(path: Path, host: str, port: int, filename: str, max_window: int = 5) -> bool:
    """
    Maneja la descarga de un archivo usando Go-Back-N con handshake.

    Args:
        path (Path): Ruta donde guardar el archivo.
        host (str): IP del servidor.
        port (int): Puerto del servidor.
        filename (str): Nombre del archivo a descargar.

    Returns:
        bool: True si se completó con éxito, False si falló.
    """
    client = RdtClient(host, port, max_window)
    print("aquii")
    try:
        if not client.connect():
            logger.error("No se pudo establecer conexión con el servidor")
            return False
        
        logger.info("Conexión establecida, solicitando descarga con Go-Back-N")
        
        connection_state = client.get_connection_state()

        download_request = format_download_request(filename)
        request_msg = RdtMessage(
            flag=FLAG_DATA, 
            max_window=connection_state.get_max_window(),
            seq_num=connection_state.get_next_sequence_number(),
            ref_num=connection_state.get_current_reference_number(),
            data=download_request.encode('latin-1')
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
            
            response_data = rdt_response.get_data()
            
            if response_data and not response_data.startswith(b'D_'):
                try:
                    error_text = response_data.decode('latin-1', errors='ignore')
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
        received_packets = {}  # Buffer para paquetes fuera de orden
        window_size = connection_state.get_max_window()
        
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
                seq_num = rdt_response.get_seq_num()
                logger.info(f"Recibido chunk con seq={seq_num}. Se esperaba seq={expected_seq_num}.")

                # Verificar si el paquete está en la ventana de recepción
                if expected_seq_num <= seq_num < expected_seq_num + window_size:
                    chunk_data = rdt_response.get_data()
                    is_valid, error_msg = validate_prefix(chunk_data, PREFIX_DATA)
                    
                    if is_valid:
                        chunk_data = remove_prefix(chunk_data, PREFIX_DATA)
                        received_packets[seq_num] = chunk_data
                        
                        # Procesar paquetes en orden
                        is_last = False
                        while expected_seq_num in received_packets:
                            file_data += received_packets[expected_seq_num]
                            del received_packets[expected_seq_num]
                            
                            if rdt_response.is_last() and seq_num == expected_seq_num:
                                logger.info("Recibido último paquete")
                                is_last = True
                            
                            expected_seq_num += 1
                        
                        if is_last:
                            ack_msg = RdtMessage(
                                flag=FLAG_ACK,
                                max_window=connection_state.get_max_window(),
                                seq_num=expected_seq_num - 1,
                                ref_num=expected_seq_num,
                                data=b''
                            )
                            client.send(ack_msg.to_bytes())
                            logger.info(f"Enviado ACK acumulativo para seq={expected_seq_num - 1}")
                            break
                        
                        # Enviar ACK acumulativo
                        ack_msg = RdtMessage(
                            flag=FLAG_ACK,
                            max_window=connection_state.get_max_window(),
                            seq_num=expected_seq_num - 1,
                            ref_num=expected_seq_num,
                            data=b''
                        )
                        client.send(ack_msg.to_bytes())
                        logger.info(f"Enviado ACK acumulativo para seq={expected_seq_num - 1}")
                        
                    else:
                        logger.error(error_msg)
                        return False
                else:
                    logger.warning(f"Paquete fuera de ventana (seq={seq_num}, ventana=[{expected_seq_num}, {expected_seq_num + window_size - 1}]). Descartado.")
                    client.stats['errors'] += 1
                        
            except Exception as e:
                logger.error(f"Error parseando paquete: {e}")
                client.stats['errors'] += 1
                continue
        
        if file_data:
            with open(path, "wb") as file:
                file.write(file_data)
            logger.info(f"Archivo guardado exitosamente en {path}")
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