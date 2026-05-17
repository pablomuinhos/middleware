# services/observation_builder.py

from typing import Dict, Any, Optional

def build_observation_resource(
    obs_data: Dict[str, Any],
    patient_fhir_id: str,
    encounter_id: Optional[str] = None
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
    
    # añadir Encounter si existe
    if encounter_id:
        resource["encounter"] = {"reference": f"Encounter/{encounter_id}"}
    
    # Añadir fecha/hora
    if obs_data.get("effective_date"):
        # Convertir HL7 YYYYMMDDHHMMSS a ISO
        date_raw = obs_data["effective_date"]
        if len(date_raw) >= 14:
            iso_date = f"{date_raw[0:4]}-{date_raw[4:6]}-{date_raw[6:8]}T{date_raw[8:10]}:{date_raw[10:12]}:{date_raw[12:14]}"
        elif len(date_raw) >= 8:
            iso_date = f"{date_raw[0:4]}-{date_raw[4:6]}-{date_raw[6:8]}"
        else:
            iso_date = date_raw
        resource["effectiveDateTime"] = iso_date
    
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