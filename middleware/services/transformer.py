from typing import Dict, Any, List, Tuple, Optional
from services.hl7_parser import parse_hl7_segments, check_token_and_date_and_get_message_type
from services.handlers import get_handler
from utils.logging_config import logger

async def process_hl7_message(raw_message: str) -> Tuple[Dict[str, Any], str, Dict[str, int], List[str]]:
    """
    Procesa un mensaje HL7 v2 y devuelve un recurso FHIR.
    - result: resultado del handler (puede contener detalles adicionales)
    - message_type: tipo de mensaje detectado
    - resources_processed: diccionario con contadores de recursos creados
    - errors: lista de errores ocurridos
    """
    segments, indexes = parse_hl7_segments(raw_message)

    # aplicar handler segun tipo de mensaje
    message_type = check_token_and_date_and_get_message_type(segments)
    logger.info(f"Mensaje HL7 detectado: {message_type}")

    handler = get_handler(message_type)
    if not handler:
        logger.warning(f"Tipo de mensaje no soportado: {message_type}")
        return (
            {"operation": "UNSUPPORTED","success": False}, 
            message_type, 
            {},
            [f"Tipo de mensaje no soportado: {message_type}"])
    
    result, resources_processed, errors = await handler.process(segments, indexes)
    return result, message_type, resources_processed, errors