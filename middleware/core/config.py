import os
import re
from dotenv import load_dotenv

load_dotenv()

class Settings:
    """Configuración centralizada de la aplicación"""
    
    # servidor FHIR
    FHIR_SERVER_URL: str = os.getenv("FHIR_SERVER_URL", "http://localhost:8080/fhir")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    
    # timeouts
    TIMEOUT_SECONDS: float = float(os.getenv("TIMEOUT_SECONDS", "30.0"))
    
    # logs
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # versión
    API_VERSION: str = "1.0.0"
    
    # info
    API_TITLE: str = "Middleware FHIR para interoperabilidad sanitaria"
    API_DESCRIPTION: str = """API intermedia que conecta sistemas legacy (HL7 v2) 
    con servidores FHIR modernos. Implementa transformación de mensajes y
    reglas de minimización de datos."""


# SECURITY
    MAX_TIME_DIFF_SECONDS: int = 1800
    
    def _load_secret_keys(self) -> dict:
        """
        Carga las claves secretas del entorno y las organiza en un diccionario
        con estructura: { "APP": { "FACILITY": "clave" } }
        """
        keys = {}
        pattern = re.compile(r"^SECRET_KEY__(.*?)(?:__(.*))?$")

        for key, value in os.environ.items():
            match = pattern.match(key)
            if match:
                app = match.group(1)
                facility = match.group(2) if match.group(2) else "default"
                
                if app not in keys:
                    keys[app] = {}
                keys[app][facility] = value
        
        return keys
    
    @property
    def SECRET_KEYS(self) -> dict:
        #if not hasattr(self, "_secret_keys_cache"):
        #    self._secret_keys_cache = self._load_secret_keys()
        #return self._secret_keys_cache
        return self._load_secret_keys()
    
    def get_secret_key(self, app: str, facility: str = None) -> str:
        """
        Obtiene la clave secreta para una aplicación y facility específicas.
        """
        app_keys = self.SECRET_KEYS.get(app, {})
        
        # Buscar por facility específica
        if facility and facility in app_keys:
            return app_keys[facility]
        
        # Buscar por default de la app
        if "default" in app_keys:
            return app_keys["default"]
        
        return None


    
settings = Settings()