from typing import Dict, Any, Optional

from utils.date_utils import hl7_to_fhir_datetime

def build_service_request_resource(req_data: Dict[str, Any], patient_fhir_id: str, encounter_id: Optional[str] = None) -> Dict[str, Any]:
    """Construye un recurso FHIR ServiceRequest a partir de datos extraídos"""

    resource = {
        "resourceType": "ServiceRequest",
        "status": "active",
        "intent": "order",
        "subject": {"reference": f"Patient/{patient_fhir_id}"}
    }

    if req_data.get("study_code"):
        resource["code"] = {
            "coding": [{
                "system": "http://loinc.org",
                "code": req_data["study_code"],
                "display": req_data.get("study_description", req_data["study_code"])
            }]
        }

    if encounter_id:
        resource["encounter"] = {"reference": f"Encounter/{encounter_id}"}

    if req_data.get("order_date"):
        resource["authoredOn"] = hl7_to_fhir_datetime(req_data["order_date"])

    if req_data.get("order_id"):
        resource["identifier"] = [{
            "system": "http://hospital/order-id",
            "value": req_data["order_id"]
        }]

    return resource