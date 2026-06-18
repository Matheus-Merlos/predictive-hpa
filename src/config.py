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

        #for kubernetes discovery
        self.namespace = os.getenv('NAMESPACE')
        if not self.namespace:
            raise ValueError('NAMESPACE env var is invalid.')
        
        self.label_str = os.getenv('SELECTOR_LABELS')
        if not self.label_str:
            raise ValueError('SELECTOR_LABELS env var is invalid.')
        
        #for reactive hpa
        self.reactive_hpa_target_cpu_utilization_percentage = os.getenv('REACTIVE_TARGET_CPU_UTILIZATION_PERCENTAGE', None)
        self.reactive_hpa_target_mem_utilization_percentage = os.getenv('REACTIVE_TARGET_MEMORY_UTILIZATION_PERCENTAGE', None)
        try:
            self.reactive_hpa_min_replicas = int(os.getenv('REACTIVE_TARGET_MIN_REPLICAS'))
        except TypeError:
            raise ValueError('REACTIVE_TARGET_MIN_REPLICAS env var is invalid.')
        
        try:
            self.reactive_hpa_max_replicas = int(os.getenv('REACTIVE_TARGET_MAX_REPLICAS'))
        except TypeError:
            raise ValueError('REACTIVE_TARGET_MAX_REPLICAS env var is invalid.')
        
        #for duckdb
        self.duckdb_file_path = os.getenv('DUCKDB_FILE_PATH')
        if not self.duckdb_file_path:
            raise ValueError('DUCKDB_FILE_PATH env var is invalid.')