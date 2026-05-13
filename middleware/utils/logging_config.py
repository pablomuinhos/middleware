import logging
import sys
from core.config import settings

def setup_logging():
    """Configura el sistema de logging de la aplicación"""
    
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            # logging.FileHandler('middleware.log')
        ]
    )
    
    # reducir logs de librerías externas
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)

logger = setup_logging()