# 🧪 Comandos de Prueba - Sistema UDP File Transfer

## 📋 Resumen del Sistema

**Protocolos soportados:**
- `stop-and-wait`: Protocolo de ventana deslizante con ventana de tamaño 1
- `go-back-n`: Protocolo de ventana deslizante con ventana de tamaño 5

**Operaciones:**
- `upload`: Subir archivo del cliente al servidor
- `download`: Descargar archivo del servidor al cliente

**Archivos de prueba creados:**
- `files/test_pequeno.txt` - Archivo pequeño (3 líneas)
- `files/test_medio.txt` - Archivo mediano (10 líneas)
- `files/test_grande.txt` - Archivo grande (20 líneas)
- `files/test_binario.dat` - Archivo con contenido especial
- `files/test_archivo.txt` - Archivo existente (grande)
- `files/test_post_archivo.txt` - Archivo existente (pequeño)

---

## 🚀 Comandos de Prueba

### 1. Iniciar el Servidor

```bash
# Servidor básico con verbose
python -m server.start_server -H 127.0.0.1 -p 9999 -v

# Servidor con directorio de almacenamiento personalizado
python -m server.start_server -H 127.0.0.1 -p 9999 -s ./storage -v

# Servidor en modo silencioso
python -m server.start_server -H 127.0.0.1 -p 9999 -q

# Ver ayuda del servidor
python -m server.start_server -h
```

### 2. Pruebas de Upload

#### Upload con Stop-and-Wait
```bash
# Archivo pequeño
python -m client.upload -s files/test_pequeno.txt -n uploaded_pequeno.txt -H 127.0.0.1 -p 9999 -r stop-and-wait -v

# Archivo mediano
python -m client.upload -s files/test_medio.txt -n uploaded_medio.txt -H 127.0.0.1 -p 9999 -r stop-and-wait -v

# Archivo grande
python -m client.upload -s files/test_grande.txt -n uploaded_grande.txt -H 127.0.0.1 -p 9999 -r stop-and-wait -v

# Archivo binario
python -m client.upload -s files/test_binario.dat -n uploaded_binario.dat -H 127.0.0.1 -p 9999 -r stop-and-wait -v
```

#### Upload con Go-Back-N
```bash
# Archivo pequeño
python -m client.upload -s files/test_pequeno.txt -n uploaded_pequeno_gbn.txt -H 127.0.0.1 -p 9999 -r go-back-n -v

# Archivo mediano
python -m client.upload -s files/test_medio.txt -n uploaded_medio_gbn.txt -H 127.0.0.1 -p 9999 -r go-back-n -v

# Archivo grande
python -m client.upload -s files/test_grande.txt -n uploaded_grande_gbn.txt -H 127.0.0.1 -p 9999 -r go-back-n -v

# Archivo binario
python -m client.upload -s files/test_binario.dat -n uploaded_binario_gbn.dat -H 127.0.0.1 -p 9999 -r go-back-n -v
```

### 3. Pruebas de Download

#### Download con Stop-and-Wait
```bash
# Descargar archivo subido con stop-and-wait
python -m client.download -n uploaded_pequeno.txt -d descargas/ -H 127.0.0.1 -p 9999 -r stop-and-wait -v

python -m client.download -n uploaded_medio.txt -d descargas/ -H 127.0.0.1 -p 9999 -r stop-and-wait -v

python -m client.download -n uploaded_grande.txt -d descargas/ -H 127.0.0.1 -p 9999 -r stop-and-wait -v

python -m client.download -n uploaded_binario.dat -d descargas/ -H 127.0.0.1 -p 9999 -r stop-and-wait -v
```

#### Download con Go-Back-N
```bash
# Descargar archivo subido con go-back-n
python -m client.download -n uploaded_pequeno_gbn.txt -d descargas/ -H 127.0.0.1 -p 9999 -r go-back-n -v

python -m client.download -n uploaded_medio_gbn.txt -d descargas/ -H 127.0.0.1 -p 9999 -r go-back-n -v

python -m client.download -n uploaded_grande_gbn.txt -d descargas/ -H 127.0.0.1 -p 9999 -r go-back-n -v

python -m client.download -n uploaded_binario_gbn.dat -d descargas/ -H 127.0.0.1 -p 9999 -r go-back-n -v
```

### 4. Pruebas de Error

```bash
# Intentar descargar archivo inexistente
python -m client.download -n archivo_inexistente.txt -d descargas/ -H 127.0.0.1 -p 9999 -r stop-and-wait -v

# Intentar subir archivo inexistente
python -m client.upload -s archivo_inexistente.txt -n test.txt -H 127.0.0.1 -p 9999 -r stop-and-wait -v

# Conectar a servidor inexistente
python -m client.upload -s files/test_pequeno.txt -n test.txt -H 127.0.0.1 -p 8888 -r stop-and-wait -v

# Probar archivo duplicado (subir el mismo archivo dos veces)
python -m client.upload -s files/test_pequeno.txt -n archivo_duplicado.txt -H 127.0.0.1 -p 9999 -r stop-and-wait -v
python -m client.upload -s files/test_pequeno.txt -n archivo_duplicado.txt -H 127.0.0.1 -p 9999 -r stop-and-wait -v
```

### 4.1. Pruebas Automatizadas de Errores

```bash
# Ejecutar todas las pruebas de error
python test_errores.py
```

### 5. Pruebas con Archivos Existentes

```bash
# Usar archivos que ya existen en el proyecto
python -m client.upload -s files/test_archivo.txt -n uploaded_test_archivo.txt -H 127.0.0.1 -p 9999 -r stop-and-wait -v

python -m client.upload -s files/test_post_archivo.txt -n uploaded_test_post.txt -H 127.0.0.1 -p 9999 -r go-back-n -v

# Descargar archivos existentes
python -m client.download -n uploaded_test_archivo.txt -d descargas/ -H 127.0.0.1 -p 9999 -r stop-and-wait -v
```

---

## 🤖 Pruebas Automatizadas

### Ejecutar todas las pruebas automáticamente
```bash
# Ejecutar script de pruebas completo
python test_completo.py
```

### Ejecutar tests unitarios
```bash
# Todos los tests
python run_tests.py

# Tests específicos del cliente
python -m unittest tests.test_client.test_upload
python -m unittest tests.test_client.test_download

# Tests específicos del servidor
python -m unittest tests.test_server

# Con pytest (si está instalado)
pytest tests/
```

---

## 📊 Secuencia de Pruebas Recomendada

### 1. Prueba Básica (Terminal 1)
```bash
# Iniciar servidor
python -m server.start_server -H 127.0.0.1 -p 9999 -v
```

### 2. Prueba Básica (Terminal 2)
```bash
# Upload simple
python -m client.upload -s files/test_pequeno.txt -n test_upload.txt -H 127.0.0.1 -p 9999 -r stop-and-wait -v

# Download simple
python -m client.download -n test_upload.txt -d descargas/ -H 127.0.0.1 -p 9999 -r stop-and-wait -v
```

### 3. Prueba de Protocolos (Terminal 2)
```bash
# Comparar protocolos con el mismo archivo
python -m client.upload -s files/test_medio.txt -n test_sw.txt -H 127.0.0.1 -p 9999 -r stop-and-wait -v
python -m client.upload -s files/test_medio.txt -n test_gbn.txt -H 127.0.0.1 -p 9999 -r go-back-n -v

# Descargar ambos
python -m client.download -n test_sw.txt -d descargas/ -H 127.0.0.1 -p 9999 -r stop-and-wait -v
python -m client.download -n test_gbn.txt -d descargas/ -H 127.0.0.1 -p 9999 -r go-back-n -v
```

### 4. Prueba de Archivos Grandes (Terminal 2)
```bash
# Archivo grande con go-back-n (más eficiente)
python -m client.upload -s files/test_archivo.txt -n archivo_grande.txt -H 127.0.0.1 -p 9999 -r go-back-n -v
python -m client.download -n archivo_grande.txt -d descargas/ -H 127.0.0.1 -p 9999 -r go-back-n -v
```

---

## 🔧 Opciones de Configuración

### Cliente Upload
- `-s, --src`: Archivo fuente (requerido)
- `-n, --name`: Nombre del archivo en el servidor
- `-H, --host`: IP del servidor (default: 127.0.0.1)
- `-p, --port`: Puerto del servidor (default: 9999)
- `-r, --protocol`: Protocolo (stop-and-wait, go-back-n)
- `-v, --verbose`: Modo verbose
- `-q, --quiet`: Modo silencioso

### Cliente Download
- `-n, --name`: Nombre del archivo en el servidor (requerido)
- `-d, --dst`: Directorio de destino (requerido)
- `-H, --host`: IP del servidor (default: 127.0.0.1)
- `-p, --port`: Puerto del servidor (default: 9999)
- `-r, --protocol`: Protocolo (stop-and-wait, go-back-n)
- `-v, --verbose`: Modo verbose
- `-q, --quiet`: Modo silencioso

### Servidor
- `-H, --host`: IP de escucha (default: 127.0.0.1)
- `-p, --port`: Puerto de escucha (default: 9999)
- `-s, --storage`: Directorio de almacenamiento
- `-v, --verbose`: Modo verbose
- `-q, --quiet`: Modo silencioso

---

## 📝 Notas Importantes

1. **Siempre iniciar el servidor antes que el cliente**
2. **Usar diferentes nombres de archivo para evitar conflictos**
3. **El directorio `descargas/` se crea automáticamente**
4. **Los archivos se almacenan en el directorio del servidor**
5. **Go-back-n es más eficiente para archivos grandes**
6. **Stop-and-wait es más simple pero más lento**
7. **Usar `-v` para ver detalles de la transferencia**
8. **Usar `Ctrl+C` para detener el servidor**

---

## 🎯 Casos de Prueba Específicos

### Prueba de Integridad
```bash
# Subir y descargar el mismo archivo, luego comparar
python -m client.upload -s files/test_medio.txt -n integridad.txt -H 127.0.0.1 -p 9999 -r go-back-n -v
python -m client.download -n integridad.txt -d descargas/ -H 127.0.0.1 -p 9999 -r go-back-n -v

# Comparar archivos
diff files/test_medio.txt descargas/integridad.txt
```

### Prueba de Múltiples Clientes
```bash
# Terminal 1: Servidor
python -m server.start_server -H 127.0.0.1 -p 9999 -v

# Terminal 2: Cliente 1
python -m client.upload -s files/test_pequeno.txt -n cliente1.txt -H 127.0.0.1 -p 9999 -r stop-and-wait -v

# Terminal 3: Cliente 2 (simultáneo)
python -m client.upload -s files/test_medio.txt -n cliente2.txt -H 127.0.0.1 -p 9999 -r go-back-n -v
```

### Prueba de Rendimiento
```bash
# Medir tiempo de transferencia
time python -m client.upload -s files/test_archivo.txt -n rendimiento.txt -H 127.0.0.1 -p 9999 -r go-back-n -v
time python -m client.download -n rendimiento.txt -d descargas/ -H 127.0.0.1 -p 9999 -r go-back-n -v
```
