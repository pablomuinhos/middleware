from fastapi import APIRouter, HTTPException, status, Request
from services.transformer import process_hl7_message
from utils.logging_config import logger
from models.hl7 import HL7TransformationResult
from core.constants import is_multi_resource_message

#router = APIRouter(prefix="/transform", tags=["Transformación HL7 v2 -> FHIR"])
router = APIRouter(prefix="/hl7", tags=["Transformación HL7 v2 -> FHIR"])

@router.post("/", response_model=HL7TransformationResult)
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
        result, message_type, patient_id = await process_hl7_message(raw_message)

        # para ORU^R01 (estructura diferente)
        if is_multi_resource_message(message_type):
            if result.get("success"):
                return HL7TransformationResult(
                    original_hl7_type=f"HL7 v2 ({message_type})",
                    transformed_to_fhir=True,
                    fhir_patient_id=None,
                    warnings=[]
                )
            else:
                # construir mensaje de error
                error_messages = []
                for err in result.get("errors", []):
                    error_messages.append(err.get("error", str(err)))
                
                return HL7TransformationResult(
                    original_hl7_type=f"HL7 v2 ({message_type})",
                    transformed_to_fhir=False,
                    error_sending="; ".join(error_messages),
                    warnings=[f"Pacientes con error: {result.get('patients_with_errors', 0)}"]
                )
        
        if result.get("success"):
            return HL7TransformationResult(
                original_hl7_type=f"HL7 v2 ({message_type})",
                transformed_to_fhir=True,
                fhir_patient_id=patient_id,
                warnings=[]
            )
        else:
            return HL7TransformationResult(
                original_hl7_type=f"HL7 v2 ({message_type})",
                transformed_to_fhir=False,
                error_sending=result.get("error"),
                warnings=[f"Operación fallida: {result.get('operation')}"]
            )
            
    except Exception as e:
        logger.error(f"Error procesando mensaje: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Error procesando mensaje HL7 v2: {str(e)}"
        )