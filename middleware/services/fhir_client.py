import httpx
import logging
from fastapi import HTTPException, status
from typing import Optional, Dict, Any, Tuple
from core.config import settings

logger = logging.getLogger(__name__)


async def call_fhir_server(
    method: str, 
    path: str, 
    data: Optional[Dict] = None, 
    params: Optional[Dict] = None,
    headers: Optional[Dict] = None
) -> Tuple[int, Optional[Dict]]:
    """
    Función genérica para llamar al servidor FHIR.
    
    Args:
        method: HTTP method (GET, POST, PUT, DELETE)
        path: Path del endpoint FHIR (ej: "/Patient")
        data: Datos para POST/PUT (recurso FHIR)
        params: Parámetros de query para GET
        headers: Headers adicionales para la petición
    
    Returns:
        Tuple (status_code, response_json)
    """
    url = f"{settings.FHIR_SERVER_URL}{path}"
    default_headers = {"Content-Type": "application/fhir+json"}
    if headers:
        default_headers.update(headers)
    try:
        async with httpx.AsyncClient(timeout=settings.TIMEOUT_SECONDS) as client:
            match method.upper():
                case "GET":
                    response = await client.get(url, params=params, headers=default_headers)
                case "POST":
                    response = await client.post(url, json=data, headers=default_headers)
                case "PUT":
                    response = await client.put(url, json=data, headers=default_headers)
                case "DELETE":
                    response = await client.delete(url, headers=default_headers)
                case _:
                    raise ValueError(f"Método HTTP no soportado: {method}")
            
            logger.info(f"FHIR call: {method} {url} -> Status: {response.status_code}")
            
            response_json = response.json() if response.text else None
            return response.status_code, response_json
            
    except httpx.TimeoutException:
        logger.error(f"Timeout calling FHIR server: {url}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="El servidor FHIR no respondió a tiempo"
        )
    except httpx.ConnectError:
        logger.error(f"Cannot connect to FHIR server: {url}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo conectar al servidor FHIR"
        )
    except Exception as e:
        logger.error(f"Error calling FHIR server: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno: {str(e)}"
        )


def get_patient_url(patient_id: str) -> str:
    """Construye la URL completa de un recurso Patient en el servidor FHIR"""
    return f"{settings.FHIR_SERVER_URL}/Patient/{patient_id}"