import os
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


    # TODO
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
settings = Settings()