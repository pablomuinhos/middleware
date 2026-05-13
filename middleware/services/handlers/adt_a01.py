from typing import Dict, Any
from services.encounter_builder import build_encounter_resource
from services.handlers.base import HL7MessageHandler
from services.hl7_parser import extract_encounter_data, extract_patient_data
from services.patient_builder import build_patient_resource

class ADT_A01_Handler(HL7MessageHandler):

    def can_handle(self, message_type: str) -> bool:
        return message_type == "ADT^A01"

    async def process(self, segments: Dict[str, Any]) -> Dict[str, Any]:
        self.log_info("Procesando ADT^A01")

        # paciente
        pid = segments.get('PID')
        if not pid:
            raise ValueError("ADT^A01: No se encontró segmento PID")
        
        pd1 = segments.get('PD1')
        patient_resource = extract_patient_data(pid,pd1)
        """
        patient_fhir_id = await self.get_or_create_patient(
            patient_resource['identifier'][0]['system'],
            patient_resource['identifier'][0]['value'],
            patient_resource
        )

        if not patient_fhir_id:
            return {"success": False, "error": "No se pudo obtener/crear el paciente"}
        """

        # encounter
        pv1 = segments.get('PV1')
        encounter_data = extract_encounter_data(pv1)

        success, patient_id, encounter_id, error = await self.create_patient_and_encounter_transaction(
            patient_resource, encounter_data
        )

        if success:
            return {
                "success": True,
                "patient_id": patient_id,
                "encounter_id": encounter_id
            }
        else:
            return {"success": False, "error": error}
        
        """
        fhir_encounter = build_encounter_resource(encounter_data, patient_fhir_id)
        
        status_code, result = await self.execute_fhir_operation(
            "POST", "/Encounter", resource=fhir_encounter
        )
        
        return {"success": status_code in [200, 201], "encounter_id": result.get("id") if result else None}
        """