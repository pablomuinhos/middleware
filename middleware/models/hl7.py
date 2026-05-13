from pydantic import BaseModel, Field
from typing import Optional, Union
"""
class HL7v2RawMessage(BaseModel):
    raw_message: str = Field(..., description="Mensaje HL7 v2 en texto plano")
    mensaje_tipo: Optional[str] = Field(None, description="Opcional: tipo de mensaje (ADT^A01, etc.)")

class HL7v2JsonMessage(BaseModel):
    mensaje_tipo: str = Field("ADT^A01", description="Tipo de mensaje HL7")
    paciente_id: Optional[str] = Field(None, description="ID del paciente en sistema origen")
    nombre: str = Field(..., description="Nombre del paciente")
    apellido: str = Field(..., description="Apellido del paciente")
    fecha_nacimiento: str = Field(..., description="Fecha de nacimiento (YYYY-MM-DD)")
    direccion: Optional[str] = Field(None, description="Dirección")
    telefono: Optional[str] = Field(None, description="Teléfono")
    historia_clinica: Optional[str] = Field(None, description="Número de historia clínica")
    
    class Config:
        json_schema_extra = {
            "example": {
                "mensaje_tipo": "ADT^A01",
                "paciente_id": "P12345",
                "nombre": "Juan",
                "apellido": "Pérez",
                "fecha_nacimiento": "1975-08-23",
                "direccion": "Calle Mayor 1, Madrid",
                "telefono": "+34123456789",
                "historia_clinica": "HC-98765"
            }
        }

"""
class HL7TransformationResult(BaseModel):
    """Resultado de la transformación HL7 v2 -> FHIR"""
    
    original_hl7_type: str
    transformed_to_fhir: bool
    fhir_patient_id: Optional[str] = None
    fhir_resource_url: Optional[str] = None
    fhir_resource_ready: Optional[dict] = None
    #error_sending: Optional[dict] = None
    error_sending: Optional[Union[str, dict]] = None
    warnings: list = []