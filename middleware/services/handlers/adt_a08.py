from typing import Dict, Any, List, Tuple
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
    
    async def process(self, segments: Dict[str, Any], indexes: Dict[str, Any] = None) -> Tuple[Dict[str, Any], Dict[str, int], List[str]]:
        self.log_info(f"Procesando {self.MESSAGE_TYPE}: actualizar paciente")
        resources_processed = {}
        errors = []

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
            }, resources_processed, [error_msg]
        
        patient_fhir_id = patient_resource.get("id")
        version_id = patient_resource.get("meta", {}).get("versionId", "1")
        
        self.log_info(f"Paciente encontrado: ID={patient_fhir_id}, versión={version_id}")
        
        fhir_resource = build_patient_resource(patient_data, patient_fhir_id=patient_fhir_id)

        # Validar paciente contra perfil
        is_valid, error_msg = await self.validate_resource(
            fhir_resource, 
            "Patient", 
            self.PATIENT_PROFILE_URL
        )
        if not is_valid:
            error = f"Validación de Patient fallida: {error_msg}"
            self.log_error(error)
            return {"success": False}, resources_processed, [error]

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
            resources_processed["Patient"] = resources_processed.get("Patient", 0) + 1
            return {
                "operation": "UPDATE",
                "success": True,
                "patient_id": patient_fhir_id,
                "updated": True
            }, resources_processed, errors
        elif update_status == 404:
            return {
                "operation": "UPDATE",
                "success": False,
                "status_code": 404
            }, resources_processed, ["Paciente no encontrado durante actualización"]
        elif update_status == 412:
            self.log_error(f"Conflicto de versión para {patient_fhir_id}")
            return {
                "operation": "UPDATE",
                "success": False,
                "status_code": 412
            }, resources_processed, ["El paciente fue modificado por otro proceso (conflicto de versión)"]
        else:
            self.log_error(f"Error actualizando: {update_status}")
            return {
                "operation": "UPDATE",
                "success": False,
                "error": update_result,
                "status_code": update_status
            }, resources_processed, [update_result]