from typing import Dict, Any, Optional
from utils.date_utils import hl7_to_fhir_datetime


def build_observation_resource(
    obs_data: Dict[str, Any],
    patient_fhir_id: str,
    encounter_id: Optional[str] = None,
    service_request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Construye un recurso FHIR Observation a partir de datos extraídos.
    """
    resource = {
        "resourceType": "Observation",
        "status": "final",
        "code": {
            "coding": [{
                "code": obs_data.get("code", "unknown"),
                "display": obs_data.get("code", "Unknown")
            }]
        },
        "subject": {
            "reference": f"Patient/{patient_fhir_id}"
        }
    }
    
    # Añadir basedOn si tenemos ServiceRequest
    if service_request_id:
        resource["basedOn"] = [{"reference": f"ServiceRequest/{service_request_id}"}]
    
    # añadir Encounter si existe
    if encounter_id:
        resource["encounter"] = {"reference": f"Encounter/{encounter_id}"}
    
    # Añadir fecha/hora
    if obs_data.get("effective_date"):
        resource["effectiveDateTime"] = hl7_to_fhir_datetime(obs_data["effective_date"])
    
    # Añadir valor y unidades
    if obs_data.get("value"):
        value_num = _to_number(obs_data["value"])
        if value_num is not None:
            resource["valueQuantity"] = {
                "value": value_num,
                "unit": obs_data.get("unit", ""),
                "system": "http://unitsofmeasure.org",
                "code": obs_data.get("unit", "")
            }
        else:
            resource["valueString"] = obs_data["value"]
    
    # Añadir rango de referencia
    if obs_data.get("reference_range"):
        resource["referenceRange"] = [{
            "text": obs_data["reference_range"]
        }]
    
    return resource

def _to_number(value: str) -> Optional[float]:
    """Convierte un string a número si es posible"""
    try:
        return float(value)
    except ValueError:
        return None