"""
Implementación del protocolo Go Back N para transferencia de archivos.
"""



import logging
from pathlib import Path
from typing import Tuple, Optional
from protocol.rdt.rdt_message import RdtMessage, RdtRequest
from protocol.const import T_DATA, T_ACK, F_LAST, get_error_message, ERR_NOT_FOUND, ERR_TOO_BIG
from .rdt_client import RdtClient, ConnectionState, CHUNK_SIZE, MAX_RETRIES, validate_file_size, MAX_FILE_SIZE_MB

logger = logging.getLogger(__name__)


def handle_upload_go_back_n(path: Path, host: str, port: int, filename: str) -> bool:
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

    client = RdtClient(host, port)
    
    try:
        if not client.connect():
            logger.error("No se pudo establecer conexión con el servidor")
            return False
        
        logger.info("Conexión establecida, iniciando transferencia de archivo con Go-Back-N")
        
        connection_state = ConnectionState(client.get_handshake_info())
        
        # --- Lógica de Go-Back-N ---
        window_size = connection_state.get_max_window()
        base = connection_state.get_next_sequence_number()
        next_seq_num = base
        
        # Buffer para paquetes enviados pero no confirmados (ACKed)
        sent_packets = {} 
        
        total_size = path.stat().st_size
        total_chunks = (total_size // CHUNK_SIZE) + (1 if total_size % CHUNK_SIZE else 0)
        
        # 1. Enviar nombre del archivo (tratado como el primer paquete)
        filename_msg = RdtMessage(
            flag=T_DATA, max_window=window_size,
            seq_num=connection_state.get_next_sequence_number(),
            ref_num=connection_state.get_current_reference_number(),
            data=filename.encode('utf-8')
        )
        client.send(filename_msg.to_bytes())
        logger.info(f"Enviado nombre del archivo: {filename}")
        connection_state.increment_sequence_number()
        base += 1
        next_seq_num += 1

        with open(path, "rb") as file:
            # Bandera para saber si ya leímos todo el archivo
            file_fully_read = False
            
            while not file_fully_read or base < next_seq_num:
                # --- Fase de Envío: Llenar la ventana ---
                while next_seq_num < base + window_size and not file_fully_read:
                    chunk = file.read(CHUNK_SIZE)
                    if not chunk:
                        file_fully_read = True
                        break # Salir del bucle de envío si no hay más data

                    is_last_chunk = file.tell() >= total_size
                    flag = F_LAST if is_last_chunk else T_DATA

                    rdt_msg = RdtMessage(
                        flag=flag, max_window=window_size,
                        seq_num=next_seq_num,
                        ref_num=connection_state.get_current_reference_number(),
                        data=chunk
                    )
                    
                    sent_packets[next_seq_num] = rdt_msg.to_bytes()
                    client.send(sent_packets[next_seq_num])
                    logger.info(f"Enviado chunk seq={next_seq_num} (ventana: [{base}, {base+window_size-1}])")
                    next_seq_num += 1
                
                # --- Fase de Espera/Recepción de ACKs ---
                data, _, close_signal = client.receive()
                
                if close_signal:
                    logger.info("Servidor solicitó cerrar la conexión.")
                    break

                if not data: # Timeout
                    logger.warning(f"Timeout! Retransmitiendo ventana desde base={base}")
                    client.stats['retransmissions'] += 1
                    for i in range(base, next_seq_num):
                        client.send(sent_packets[i])
                    continue # Volver a esperar ACK

                # --- Procesar ACK ---
                try:
                    rdt_response = RdtRequest(address=f"{host}:{port}", request=data)
                    
                    if rdt_response.is_error():
                        error_code = rdt_response.get_error_code()
                        logger.error(f"Error del servidor: {get_error_message(error_code)}")
                        return False
                    
                    if rdt_response.is_ack():
                        ack_num = rdt_response.get_ref_num() - 1
                        logger.info(f"ACK recibido para seq={ack_num}")
                        
                        # Si el ACK es válido (mayor o igual a la base), deslizar la ventana
                        if ack_num >= base:
                            # Eliminar paquetes confirmados del buffer
                            for i in range(base, ack_num + 1):
                                if i in sent_packets:
                                    del sent_packets[i]
                            base = ack_num + 1
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


def handle_download_go_back_n(path: Path, host: str, port: int, filename: str) -> bool:
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
    client = RdtClient(host, port)
    
    try:
        if not client.connect():
            logger.error("No se pudo establecer conexión con el servidor")
            return False
        
        logger.info("Conexión establecida, solicitando descarga con Go-Back-N")
        
        connection_state = ConnectionState(client.get_handshake_info())

        # 1. Solicitar el archivo
        request_msg = RdtMessage(
            flag=T_DATA, max_window=connection_state.get_max_window(),
            seq_num=connection_state.get_next_sequence_number(),
            ref_num=connection_state.get_current_reference_number(),
            data=filename.encode('utf-8')
        )
        
        client.send(request_msg.to_bytes())
        logger.info(f"Solicitando descarga de {filename}...")
        
        # --- Lógica de Go-Back-N (Receptor) ---
        expected_seq_num = 0 # El servidor comenzará a enviar chunks desde seq=0
        file_data = b''
        
        while True:
            data, _, close_signal = client.receive()
            
            if close_signal:
                logger.info("Servidor solicitó cerrar la conexión.")
                break
            
            if not data:
                logger.warning("Timeout esperando datos del servidor")
                # En GBN, el receptor no hace nada en un timeout, solo espera.
                # El emisor se encargará de retransmitir.
                continue
            
            try:
                rdt_response = RdtRequest(address=f"{host}:{port}", request=data)
                
                seq_num = rdt_response.get_seq_num()
                logger.info(f"Recibido chunk con seq={seq_num}. Se esperaba seq={expected_seq_num}.")

                # Si el paquete es el esperado (en orden)
                if seq_num == expected_seq_num:
                    file_data += rdt_response.get_data()
                    
                    # Enviar ACK por el paquete recibido
                    ack_msg = RdtMessage(
                        flag=T_ACK,
                        max_window=connection_state.get_max_window(),
                        seq_num=expected_seq_num, # irrelevante para el ACK en sí
                        ref_num=expected_seq_num + 1, # ACK cumulativo
                        data=b''
                    )
                    client.send(ack_msg.to_bytes())
                    logger.info(f"Enviado ACK para seq={expected_seq_num}")
                    
                    if rdt_response.is_last():
                        logger.info("Recibido último paquete")
                        break
                    
                    expected_seq_num += 1

                # Si el paquete está fuera de orden o es un duplicado
                else:
                    logger.warning(f"Paquete fuera de orden/duplicado (seq={seq_num}). Descartado.")
                    client.stats['errors'] += 1

                    # Reenviar ACK del último paquete recibido correctamente
                    if expected_seq_num > 0:
                        last_acked_seq = expected_seq_num - 1
                        ack_msg = RdtMessage(
                            flag=T_ACK,
                            max_window=connection_state.get_max_window(),
                            seq_num=last_acked_seq,
                            ref_num=last_acked_seq + 1,
                            data=b''
                        )
                        client.send(ack_msg.to_bytes())
                        logger.info(f"Reenviando ACK para el último paquete correcto (seq={last_acked_seq})")
                        
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