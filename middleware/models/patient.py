from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional

class PatientInput(BaseModel):
    """Modelo para recibir datos de paciente (simula entrada HL7 v2)"""
    
    nombre: str = Field(..., min_length=1, max_length=100, description="Nombre del paciente")
    apellido: str = Field(..., min_length=1, max_length=100, description="Apellido del paciente")
    fecha_nacimiento: str = Field(..., description="Fecha en formato YYYY-MM-DD")
    genero: Optional[str] = Field("unknown", description="male, female, other, unknown")
    telefono: Optional[str] = Field(None, description="Número de teléfono")
    email: Optional[str] = Field(None, description="Correo electrónico")
    direccion: Optional[str] = Field(None, description="Dirección postal")
    
    @validator('fecha_nacimiento')
    def validate_date(cls, v: str) -> str:
        """Validar formato de fecha YYYY-MM-DD"""
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('Formato de fecha inválido. Use YYYY-MM-DD')
    
    @validator('genero')
    def validate_gender(cls, v: str) -> str:
        """Validar valores de género FHIR"""
        allowed = ['male', 'female', 'other', 'unknown']
        if v not in allowed:
            raise ValueError(f'Género debe ser uno de: {allowed}')
        return v
    
    @validator('email')
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Validar formato de email si se proporciona"""
        if v is not None and '@' not in v:
            raise ValueError('Email inválido')
        return v


class PatientResponse(BaseModel):
    """Modelo para respuesta de paciente (simplificado)"""
    id: str
    nombre_completo: str
    fecha_nacimiento: str
    genero: str
    fhir_resource_url: str