from typing import Dict, Any
from services.encounter_builder import build_encounter_resource
from services.handlers.base import HL7MessageHandler
from services.hl7_parser import extract_encounter_data, extract_patient_data
from services.patient_builder import build_patient_resource


class ADT_A04_Handler(HL7MessageHandler):
    """
    Handler para mensajes ADT^A04 - Registro de paciente.
    Crea un nuevo paciente en el servidor FHIR.
    """
    MESSAGE_TYPE = "ADT^A04"
    def can_handle(self, message_type: str) -> bool:
        return message_type == self.MESSAGE_TYPE
    
    async def process(self, segments: Dict[str, Any], indexes: Dict[str, Any] = None) -> Dict[str, Any]:
        self.log_info(f"Procesando {self.MESSAGE_TYPE}: crear paciente")
        
        # paciente
        pid = self.get_required_segment(segments, "PID", self.MESSAGE_TYPE)
        pd1 = self.get_optional_segment(segments, "PD1", self.MESSAGE_TYPE)

        patient_data = extract_patient_data(pid,pd1)
        fhir_resource = build_patient_resource(patient_data)

        # Validar paciente contra perfil
        is_valid, error_msg = await self.validate_resource(
            fhir_resource, 
            "Patient", 
            self.PATIENT_PROFILE_URL
        )
        if not is_valid:
            self.log_error(f"Validación de Patient fallida: {error_msg}")
            return {"success": False, "error": f"Validación fallida: {error_msg}"}

        if_none_exist = f"identifier={patient_data['identifier'][0]['system']}|{patient_data['identifier'][0]['value']}"
        headers = { "If-None-Exist": if_none_exist }

        # enviar
        patient_status, patient_result = await self.execute_fhir_operation(
            "POST", 
            "/Patient", 
            resource=fhir_resource,
            headers=headers
        )

        if patient_status not in [200, 201]:
            self.log_error(f"Error creando/actualizando Patient: {patient_status}")
            return {
                "success": False,
                "error": patient_result,
                "status_code": patient_status
            }
        
        patient_fhir_id = patient_result.get("id")
        self.log_info(f"Patient creado: ID={patient_fhir_id}")

        # encounter
        encounter_result = None
        pv1 = self.get_required_segment(segments, "PV1", self.MESSAGE_TYPE)
            
        try:
            encounter_data = extract_encounter_data(pv1)
            fhir_encounter = build_encounter_resource(encounter_data, patient_fhir_id)

            enc_status, enc_result = await self.execute_fhir_operation(
                "POST", "/Encounter", 
                resource=fhir_encounter
            )

            if enc_status in [200, 201]:
                encounter_id = enc_result.get("id")
                self.log_info(f"Encounter creado: ID={encounter_id}")
                encounter_result = {
                    "success": True,
                    "id": encounter_id,
                    "status_code": enc_status
                }
            else:
                self.log_error(f"Error creando Encounter: {enc_status} - {enc_result}")
                encounter_result = {
                    "success": False,
                    "error": enc_result,
                    "status_code": enc_status
                }
        except Exception as e:
            self.log_error(f"Excepción creando Encounter: {str(e)}")
            encounter_result = {
                "success": False,
                "error": str(e),
                "status_code": None
            }
            
        return {
            "success": True,
            "patient_id": patient_fhir_id,
            "encounter": encounter_result,
            "warning": "Encounter no creado" if encounter_result and not encounter_result.get("success") else None
        }
