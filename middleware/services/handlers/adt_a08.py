from typing import Dict, Any
from services.handlers.base import HL7MessageHandler
from services.hl7_parser import extract_patient_data
from services.patient_builder import build_patient_resource

class ADT_A08_Handler(HL7MessageHandler):
    """
    Handler para mensajes ADT^A08 - Actualización de información.
    Actualiza un paciente existente en el servidor FHIR.
    Se obvia visita
    """
    MESSAGE_TYPE = "ADT^A08"
    def can_handle(self, message_type: str) -> bool:
        return message_type == self.MESSAGE_TYPE
    
    async def process(self, segments: Dict[str, Any]) -> Dict[str, Any]:
        self.log_info(f"Procesando {self.MESSAGE_TYPE}: actualizar paciente")
        
        # paciente
        pid = self.get_required_segment(segments, "PID", self.MESSAGE_TYPE)
        pd1 = self.get_optional_segment(segments, "PD1", self.MESSAGE_TYPE)

        patient_data = extract_patient_data(pid,pd1)

        # buscar paciente para obtener id
        patient_resource, status_code, error_msg = await self.find_patient_by_identifier(
            patient_data['identifier'][0]['system'],
            patient_data['identifier'][0]['value']
        )

        if not patient_resource:
            self.log_error(error_msg)
            return {
                "operation": "UPDATE",
                "success": False,
                "error": error_msg,
                "status_code": status_code
            }
        
        patient_fhir_id = patient_resource.get("id")
        version_id = patient_resource.get("meta", {}).get("versionId", "1")
        
        self.log_info(f"Paciente encontrado: ID={patient_fhir_id}, versión={version_id}")
        
        fhir_resource = build_patient_resource(patient_data, patient_fhir_id=patient_fhir_id)

        headers = {"If-Match": f'W/"{version_id}"'}

        # enviar (PUT)
        update_status, update_result = await self.execute_fhir_operation(
            "PUT",
            f"/Patient/{patient_fhir_id}",
            resource=fhir_resource,
            headers=headers
        )

        if update_status == 200:
            self.log_info(f"Paciente actualizado: {patient_fhir_id}")
            return {
                "operation": "UPDATE",
                "success": True,
                "patient_id": patient_fhir_id,
                "updated": True
            }
        elif update_status == 404:
            return {
                "operation": "UPDATE",
                "success": False,
                "error": "Paciente no encontrado durante actualización",
                "status_code": 404
            }
        elif update_status == 412:
            self.log_error(f"Conflicto de versión para {patient_fhir_id}")
            return {
                "operation": "UPDATE",
                "success": False,
                "error": "El paciente fue modificado por otro proceso (conflicto de versión)",
                "status_code": 412
            }
        else:
            self.log_error(f"Error actualizando: {update_status}")
            return {
                "operation": "UPDATE",
                "success": False,
                "error": update_result,
                "status_code": update_status
            }