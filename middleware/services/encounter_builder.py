from typing import Dict, Any, Optional

from utils.date_utils import hl7_to_fhir_datetime

def build_encounter_resource(encounter_data: Dict[str, Any], patient_fhir_id: str, patient_identifier: Dict = None) -> Dict[str, Any]:
    """
    Construye un recurso FHIR Encounter.
    """
    if not patient_fhir_id:
        raise ValueError("Se necesita el patient_fhir_id para crear el Encounter")

    resource = {
        "resourceType": "Encounter",
        "status": "in-progress",
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": encounter_data.get("class", "AMB")
        },
        "subject": {
            "reference": f"Patient/{patient_fhir_id}"
        }
    }

    # location
    if encounter_data.get("location"):
        resource["location"] = [encounter_data["location"]]

    # médico
    if encounter_data.get("practitioner_id"):
        resource["participant"] = [{
            "type": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/v3-ParticipationType",
                    "code": "ATND"
                }]
            }],
            "individual": {
                "reference": f"Practitioner/{encounter_data['practitioner_id']}",
                "display": encounter_data.get("practitioner_name", "Unknown")
            }
        }]

    # admit_time
    if encounter_data.get("admit_time"):
        admit_str = str(encounter_data["admit_time"])
        iso_date = hl7_to_fhir_datetime(admit_str)
   
        resource["period"] = {"start": iso_date}

    return resource