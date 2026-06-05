from typing import Dict, Any, List, Tuple
from services.handlers.base import HL7MessageHandler
from services.hl7_parser import extract_encounter_data, extract_patient_data


class ADT_A01_Handler(HL7MessageHandler):
    """
    Handler para mensajes ADT^A01 - Registro de visita (y paciente).
    Crea una nueva visita al paciente en el servidor FHIR.
    Si no hay paciente, se creará.
    """
    MESSAGE_TYPE = "ADT^A01"
    def can_handle(self, message_type: str) -> bool:
        return message_type == self.MESSAGE_TYPE

    async def process(self, segments: Dict[str, Any], indexes: Dict[str, Any] = None) -> Tuple[Dict[str, Any], Dict[str, int], List[str]]:
        self.log_info(f"Procesando {self.MESSAGE_TYPE}")
        resources_processed = {}
        errors = []

        # paciente
        pid = self.get_required_segment(segments, "PID", self.MESSAGE_TYPE)
        pd1 = self.get_optional_segment(segments, "PD1", self.MESSAGE_TYPE)

        patient_data = extract_patient_data(pid,pd1)

        # encounter
        pv1 = self.get_required_segment(segments, "PV1", self.MESSAGE_TYPE)

        encounter_data = extract_encounter_data(pv1)

        success, patient_id, encounter_id, error = await self.create_patient_and_encounter_transaction(
            patient_data, encounter_data
        )

        if success:
            if patient_id:
                resources_processed["Patient"] = resources_processed.get("Patient", 0) + 1
            if encounter_id:
                resources_processed["Encounter"] = resources_processed.get("Encounter", 0) + 1
            
            return {"success": True, "patient_id": patient_id, "encounter_id": encounter_id}, resources_processed, errors
        else:
            errors.append(error)
            return {"success": False}, resources_processed, errors
        