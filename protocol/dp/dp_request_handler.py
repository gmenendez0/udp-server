class DPRequestHandler:
    def handle_request(request: bytes) -> bytes:
       # Process the incoming request and return a response
        response = f"Handled request: {request}"
        return response