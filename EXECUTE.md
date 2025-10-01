# UDP File Transfer – TP Redes FIUBA

Sistema cliente-servidor para transferencia de archivos sobre UDP con implementación de protocolo RDT.

## Estructura del Proyecto

```
udp-server-feature-capa-presentacion-servidor/
├── client/                  # Módulo cliente
│   ├── __init__.py
│   ├── upload.py           # Cliente para UPLOAD
│   └── download.py         # Cliente para DOWNLOAD
├── server/                 # Módulo servidor
│   ├── __init__.py
│   ├── start_server.py     # Servidor principal
│   ├── udp_server.py       # Implementación servidor UDP
│   ├── server_helpers.py   # Utilidades del servidor
│   └── main.py            # Servidor simple (legacy)
├── tests/                  # Tests unitarios
│   ├── test_client/        # Tests del cliente
│   └── test_server/        # Tests del servidor
├── storage/               # Directorio de archivos del servidor
└── run_tests.py          # Script para ejecutar tests
```

## Requisitos
- Python 3.11 o superior
- Configuración con pyenv recomendada

## Instalación y Configuración

### 1. Configurar Python con pyenv
```bash
# Instalar Python 3.11 si no está disponible
pyenv install 3.11.11

# Configurar versión local para el proyecto
cd /path/to/udp-server-feature-capa-presentacion-servidor
pyenv local 3.11.11

# Verificar versión
python --version
```

## Ejecución

### Servidor
```bash
# Servidor básico
python -m server.start_server -H 127.0.0.1 -p 9999 -v

# Servidor con directorio de almacenamiento personalizado
python -m server.start_server -H 127.0.0.1 -p 9999 -s ./mi_storage -v

# Ver ayuda completa del servidor
python -m server.start_server -h
```

### Cliente Upload
```bash
# Upload básico
python -m client.upload -s archivo.txt -n archivo_remoto.txt -H 127.0.0.1 -p 9999 -v

# Ver ayuda completa del upload
python -m client.upload -h
```

### Cliente Download  
```bash
# Download básico
python -m client.download -n archivo_remoto.txt -d ./descargas/ -H 127.0.0.1 -p 9999 -v

# Ver ayuda completa del download
python -m client.download -h
```

## Testing

### Ejecutar todos los tests
```bash
# Usando script
python run_tests.py

# Usando pytest
pytest tests/
```


### Ejecutar tests específicos
```bash
# Tests del cliente
python -m unittest tests.test_client.test_upload

# Tests del servidor
python -m unittest tests.test_server.test_udp_server
```
