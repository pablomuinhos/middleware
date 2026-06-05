from fastapi import APIRouter, HTTPException, status, Request
from services.transformer import process_hl7_message
from utils.logging_config import logger


#router = APIRouter(prefix="/transform", tags=["Transformación HL7 v2 -> FHIR"])

router = APIRouter(prefix="/hl7", tags=["Transformación HL7 v2 -> FHIR"])
@router.post("/")
async def transform_hl7_to_fhir(request: Request):
    """
    Recibe un mensaje HL7 v2 en texto plano y actúa según el tipo:
    """

    body_bytes = await request.body()
    raw_message = body_bytes.decode("utf-8").strip()
    
    # comprobar que tenga encabezado MSH
    if not raw_message.startswith("MSH"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El mensaje debe empezar por 'MSH'"
        )
    
    try:
        result, message_type, resources_processed, errors = await process_hl7_message(raw_message)

        return {
            "success": result.get("success", False),
            "message_type": message_type,
            "resources_processed": resources_processed,
            "errors": errors
        }

    except Exception as e:
        logger.error(f"Error procesando mensaje: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Error procesando mensaje HL7 v2: {str(e)}"
        )