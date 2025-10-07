#!/usr/bin/env python3
"""
Script de prueba para verificar la integración cliente-servidor.
"""

import subprocess
import time
import os
import sys
import threading
from pathlib import Path

def start_server():
    """Inicia el servidor en un hilo separado"""
    try:
        result = subprocess.run([
            sys.executable, "-m", "server.start_server", 
            "--host", "127.0.0.1", 
            "--port", "9999",
            "--verbose"
        ], capture_output=True, text=True, timeout=10)
        return result
    except subprocess.TimeoutExpired:
        return None

def test_handshake():
    """Prueba el handshake básico"""
    print("=== Probando handshake ===")
    
    # Crear un archivo de prueba pequeño
    test_file = Path("test_file.txt")
    test_file.write_text("Hola mundo! Este es un archivo de prueba.")
    
    try:
        # Probar upload con stop-and-wait
        print("Probando upload con stop-and-wait...")
        result = subprocess.run([
            sys.executable, "-m", "client.upload",
            "--host", "127.0.0.1",
            "--port", "9999", 
            "--src", str(test_file),
            "--name", "test_upload.txt",
            "--protocol", "stop-and-wait",
            "--verbose"
        ], capture_output=True, text=True, timeout=30)
        
        print(f"Upload resultado: {result.returncode}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        
        # Probar download
        print("\nProbando download...")
        result = subprocess.run([
            sys.executable, "-m", "client.download",
            "--host", "127.0.0.1",
            "--port", "9999",
            "--dst", ".",
            "--name", "test_upload.txt", 
            "--protocol", "stop-and-wait",
            "--verbose"
        ], capture_output=True, text=True, timeout=30)
        
        print(f"Download resultado: {result.returncode}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        
        # Verificar que el archivo se descargó
        downloaded_file = Path("test_upload.txt")
        if downloaded_file.exists():
            print(f"✓ Archivo descargado exitosamente: {downloaded_file.stat().st_size} bytes")
            downloaded_file.unlink()  # Limpiar
        else:
            print("✗ Archivo no se descargó")
            
    except subprocess.TimeoutExpired:
        print("✗ Timeout en las pruebas")
    except Exception as e:
        print(f"✗ Error en las pruebas: {e}")
    finally:
        # Limpiar archivo de prueba
        if test_file.exists():
            test_file.unlink()

def main():
    """Función principal de prueba"""
    print("Iniciando pruebas de integración cliente-servidor...")
    
    # Iniciar servidor en hilo separado
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # Esperar un poco para que el servidor se inicie
    time.sleep(2)
    
    try:
        test_handshake()
    except KeyboardInterrupt:
        print("\nPruebas interrumpidas por el usuario")
    except Exception as e:
        print(f"Error en las pruebas: {e}")
    
    print("\nPruebas completadas")

if __name__ == "__main__":
    main()
