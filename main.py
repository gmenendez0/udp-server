import udp_server

def echo_upper_handler(data: bytes) -> bytes:
    return b"Echo: " + data.upper()

server = udp_server.UDPServer(host="127.0.0.1", port=9999, buffer_size=1024, handler=echo_upper_handler)

try:
    server.serve()
except KeyboardInterrupt:
    print("Server stopped by user.")

# ? LO QUE VIMOS AYER
{ack flag}{function flag}{sequence number}|{reference number}_{uuid}_{data}

1. Manejar acks, entrega garantiza, entrega en orden, evitar duplicados,

# ? UDP

# ? RDT
{ack flag}{sequence number}|{reference number}_{data [X, HTTP]}
1. Manejar acks, entrega garantiza, entrega en orden, evitar duplicados

# ? Protocolo de datos X
{function flag}_{uuid}_payload
logica de negocio

# 1. Hacer RDTRequest
# 2. Hacer DPRequest (data protocol request)
# 3. DPRequestHandler
# 4. RDTRequestHandler

