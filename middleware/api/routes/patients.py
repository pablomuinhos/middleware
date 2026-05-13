from fastapi import APIRouter, HTTPException, Query, status
from typing import Optional
from models.patient import PatientInput
from services.fhir_client import call_fhir_server

from utils.logging_config import logger


router = APIRouter(prefix="/patient", tags=["Pacientes"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_patient(patient: PatientInput):

    fhir_resource = {
        "resourceType": "Patient",
        "name": [{"family": patient.apellido, "given": [patient.nombre]}],
        "birthDate": patient.fecha_nacimiento,
        "gender": patient.genero
    }
    
    status_code, result = await call_fhir_server("POST", "/Patient", data=fhir_resource)
    
    if status_code == 201:
        return result
    else:
        raise HTTPException(status_code=status_code, detail=result)



@router.get("/{patient_id}")
async def get_patient(patient_id: str):
    """Obtiene un paciente por ID"""
    status_code, result = await call_fhir_server("GET", f"/Patient/{patient_id}")
    
    if status_code == 200:
        return result
    elif status_code == 404:
        raise HTTPException(status_code=404, detail=f"Paciente {patient_id} no encontrado")
    else:
        raise HTTPException(status_code=status_code, detail=result)



@router.get("/")
async def search_patients(
    family: Optional[str] = Query(None, description="Apellido del paciente"),
    given: Optional[str] = Query(None, description="Nombre del paciente"),
    gender: Optional[str] = Query(None, description="male, female, other, unknown"),
    birthdate: Optional[str] = Query(None, description="Fecha de nacimiento (YYYY-MM-DD)")
):
    """
    Busca pacientes en el servidor FHIR según criterios opcionales.
    """
    # Construir parámetros de búsqueda FHIR
    params = {}
    if family:
        params["family"] = family
    if given:
        params["given"] = given
    if gender:
        params["gender"] = gender
    if birthdate:
        params["birthdate"] = birthdate
    
    # Si no hay parámetros, devolver error
    if not params:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe proporcionar al menos un criterio de búsqueda"
        )
    
    status_code_fhir, result = await call_fhir_server("GET", "/Patient", params=params)
    
    if status_code_fhir == 200:
        # Añadir metadatos útiles a la respuesta
        result["_middleware_info"] = {
            "search_criteria": params,
            "total_results": len(result.get("entry", []))
        }
        return result
    else:
        raise HTTPException(status_code=status_code_fhir, detail=result)


@router.put("/{patient_id}")
async def update_patient(patient_id: str, patient: PatientInput):
    """
    Actualiza un paciente existente.
    """
    # 1. Obtener el paciente actual
    status_code_fhir, existing = await call_fhir_server("GET", f"/Patient/{patient_id}")
    
    if status_code_fhir != 200:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paciente con ID {patient_id} no encontrado"
        )
    
    # 2. Actualizar los campos modificables
    existing["name"] = [{"family": patient.apellido, "given": [patient.nombre]}]
    existing["birthDate"] = patient.fecha_nacimiento
    existing["gender"] = patient.genero
    
    # 3. Enviar actualización al servidor FHIR
    status_code_fhir, result = await call_fhir_server(
        "PUT", 
        f"/Patient/{patient_id}", 
        data=existing
    )
    
    if status_code_fhir == 200:
        logger.info(f"Paciente {patient_id} actualizado correctamente")
        return result
    else:
        raise HTTPException(status_code=status_code_fhir, detail=result)


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(patient_id: str):
    """
    Elimina un paciente (borrado lógico en FHIR).
    """
    status_code_fhir, _ = await call_fhir_server("DELETE", f"/Patient/{patient_id}")
    
    if status_code_fhir == 204:
        logger.info(f"Paciente {patient_id} eliminado (borrado lógico)")
        return None
    elif status_code_fhir == 404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paciente con ID {patient_id} no encontrado"
        )
    else:
        raise HTTPException(
            status_code=status_code_fhir, 
            detail=f"Error al eliminar paciente {patient_id}"
        )