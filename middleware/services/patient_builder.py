from typing import Dict, Any, Optional

def build_patient_resource(patient_data: Dict[str, Any], patient_fhir_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Construye un recurso FHIR Patient
    Args:
        patient_data: Diccionario con datos del paciente
        patient_fhir_id: ID de FHIR
    Returns:
        Diccionario con el recurso FHIR Patient
    """
    fhir_resource = {
        "resourceType": "Patient",
        "name": [{"family": patient_data["apellido"], "given": [patient_data["nombre"]]}]
    }
    
    # añadir ID para actualización
    if patient_fhir_id:
        fhir_resource["id"] = patient_fhir_id
    
    if patient_data.get("identifier"):
        fhir_resource["identifier"] = patient_data["identifier"]
    
    if patient_data.get("birthDate"):
        fhir_resource["birthDate"] = patient_data["birthDate"]
    
    if patient_data.get("gender"):
        fhir_resource["gender"] = patient_data["gender"]
    
    if patient_data.get("address"):
        fhir_resource["address"] = [patient_data["address"]]
    
    if patient_data.get("telecom"):
        fhir_resource["telecom"] = patient_data["telecom"]
    
    if patient_data.get("language"):
        fhir_resource["communication"] = [{
            "language": {
                "coding": [{
                    "system": "http://hl7.org/fhir/ValueSet/languages",
                    "code": patient_data["language"]
                }]
            },
            "preferred": True
        }]
    
    if patient_data.get("marital_status"):
        fhir_resource["maritalStatus"] = {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-MaritalStatus",
                "code": patient_data["marital_status"]
            }]
        }
    
    extensions = []

    if patient_data.get("disability"):
        disability = patient_data["disability"]
        extensions.append({
            "url": "http://hl7.org/fhir/StructureDefinition/patient-disability",
            "valueCodeableConcept": {
                "coding": [{
                    "system": disability.get("system") or "http://terminology.hl7.org/CodeSystem/disability",
                    "code": disability.get("code"),
                    "display": disability.get("description")
                }]
            }
        })
    if patient_data.get("living_arrangement"):
        extensions.append({
            "url": "http://hl7.org/fhir/StructureDefinition/patient-livingArrangement",
            "valueCodeableConcept": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/living-arrangement",
                    "code": patient_data["living_arrangement"]
                }]
            }
        })
    if patient_data.get("living_dependency"):
        extensions.append({
            "url": "http://hl7.org/fhir/StructureDefinition/patient-livingDependency",
            "valueCodeableConcept": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/living-dependency",
                    "code": patient_data["living_dependency"]
                }]
            }
        })
    
    if extensions:
        fhir_resource["extension"] = extensions

    return fhir_resource