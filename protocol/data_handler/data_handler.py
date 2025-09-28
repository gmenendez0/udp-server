from abc import ABC, abstractmethod

class DataHandler(ABC):
    @abstractmethod
    def handle_data(self, data: bytes) -> bytes:
        pass