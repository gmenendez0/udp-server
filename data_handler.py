from abc import ABC, abstractmethod

class DataHandler(ABC):
    @abstractmethod
    def handle_data(self, address: tuple, data: bytes) -> bytes:
        pass

class UbaDataHandler(DataHandler):
    def __init__(self):
        pass

    def handle_data(self, address: tuple, data: bytes) -> bytes | None:
        # 1. Data se espera que llegue en el protocolo UBA. Pero como Data son bytes, no se puede garantizar que "Data" sea una request completa.
        # 2. Es decir, puede pasar que "data" contenga solo una parte de la request y que la otra parte aun no haya sido recibida de la capa de transporte.
        # 3. Por lo tanto:
        # A. Llega data de address X. Chequeamos en la sesion de X si ya tenemos data previa. Si la hay, la concatenamos.
        # B. Con la data resultante de A, chequeamos si tenemos una request completa. TODO: DEFINIR UN CRITERIO PARA ESTO.
        # C. Si la tenemos, la procesamos, limpiamos la sesion de X y devolvemos la response.
        # D. Si no la tenemos, guardamos la data en la sesion de X y devolvemos None, esperando a que llegue mas data.
        pass