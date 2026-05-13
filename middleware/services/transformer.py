from typing import Dict, Any, Tuple, Optional
from services.hl7_parser import parse_hl7_segments, get_message_type
from services.handlers import get_handler
from utils.logging_config import logger

async def process_hl7_message(raw_message: str) -> Tuple[Dict[str, Any], str, Optional[str]]:
    """
    Procesa un mensaje HL7 v2 y devuelve un recurso FHIR.
    """
    segments = parse_hl7_segments(raw_message)
    
    # aplicar handler segun tipo de mensaje
    message_type = get_message_type(segments)
    logger.info(f"Mensaje HL7 detectado: {message_type}")
    handler = get_handler(message_type)
    if handler:
        result = await handler.process(segments)
        return result, message_type, result.get("patient_id")
    else:
        logger.warning(f"Tipo de mensaje no soportado: {message_type}")
        return {
            "operation": "UNSUPPORTED",
            "success": False,
            "error": f"Tipo de mensaje '{message_type}' no soportado"
        }, message_type, None