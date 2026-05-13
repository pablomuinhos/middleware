from fastapi import APIRouter
from datetime import datetime
from services.fhir_client import call_fhir_server
from utils.logging_config import logger
from core.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """
    Verificar el estado del middleware y la conectividad con el servidor FHIR.
    """
    fhir_status = "unknown"
    fhir_error = None
    
    try:
        status_code, _ = await call_fhir_server("GET", "/metadata")
        fhir_status = "ok" if status_code == 200 else "error"
        if status_code != 200:
            fhir_error = f"HTTP {status_code}"
    except Exception as e:
        fhir_status = "error"
        fhir_error = str(e)
    
    return {
        "middleware": {
            "status": "ok",
            "version": settings.API_VERSION,
            "timestamp": datetime.now().isoformat()
        },
        "fhir_server": {
            "status": fhir_status,
            "url": settings.FHIR_SERVER_URL,
            "error": fhir_error if fhir_error else None
        }
    }

@router.get("/ready")
async def readiness_check():
    """
    Endpoint para verificar que el middleware está listo para recibir tráfico.
    """
    return {"status": "ready"}