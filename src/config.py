import os
import dotenv

class Config:
    _instance = None
    _initialized: bool = False

    def __new__(cls) -> "Config":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        
        return cls._instance

    def __init__(self) -> None:
        dotenv.load_dotenv('.env')
        if not hasattr(self, '_initialized'):
            self._initialized = True

        self.prometheus_url: str | None = os.getenv('PROMETHEUS_CONNECTION_STRING')
        prometheus_secure_connection_raw: str | None = os.getenv('PROMETHEUS_SECURE_CONNECTION')

        if not self.prometheus_url:
            raise ValueError('PROMETHEUS_CONNECTION_STRING value is invalid.')
        
        self.prometheus_secure_connection: bool = True if prometheus_secure_connection_raw == "true" else False
        