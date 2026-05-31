from services.handlers.base import HL7MessageHandler
from services.hl7_parser import extract_patient_data, extract_service_request_data
from services.service_request_builder import build_service_request_resource
from typing import Dict, Any, List, Optional

class ORM_O01_Handler(HL7MessageHandler):
    """
    Handler para mensajes ORM^O01 - Solicitud de laboratorio / pruebas.
    Crea uno o más recursos ServiceRequest en FHIR (uno por cada par ORC+OBR).
    """

    MESSAGE_TYPE = "ORM^O01"

    def can_handle(self, message_type: str) -> bool:
        return message_type == self.MESSAGE_TYPE

    async def process(self, segments: Dict[str, Any], indexes: Dict[str, Any] = None) -> Dict[str, Any]:
        self.log_info(f"Procesando {self.MESSAGE_TYPE}: solicitud de pruebas")

        pid = self.get_required_segment(segments, "PID", self.MESSAGE_TYPE) # lo tratamos como requerido

        # comprobar existencia de paciente
        patient_data = extract_patient_data(pid)

        patient_resource, status_code, error_msg = await self.find_patient_by_identifier(
            patient_data['identifier'][0]['system'],
            patient_data['identifier'][0]['value']
        )

        if not patient_resource:
            return {"success": False, "error": "Paciente no encontrado"}

        patient_fhir_id = patient_resource.get("id")

        service_requests_pairs = self._extract_service_request_estructure(segments, indexes)
        if len(service_requests_pairs) == 0:
            return {"success": False, "error": "No se encontraron ordenes"}

        # Buscar o crear Encounter (si hay PV1)
        encounter_id = None
        pv1 = self.get_optional_segment(segments, "PV1", self.MESSAGE_TYPE)

        if pv1 and len(pv1) > 0:
            from services.hl7_parser import extract_encounter_data
            from services.encounter_builder import build_encounter_resource

            encounter_data = extract_encounter_data(pv1)
            fhir_encounter = build_encounter_resource(encounter_data, patient_fhir_id)

            enc_status, enc_result = await self.execute_fhir_operation(
                "POST", "/Encounter", resource=fhir_encounter
            )
            if enc_status in [200, 201]:
                encounter_id = enc_result.get("id")

        # Procesar cada par ORC-OBR
        created_requests = []
        cancelled_requests = []
        errors = []
        for request_pair in service_requests_pairs:
            orc = request_pair.get("orc")
            obr = request_pair.get("obr")
            order_control = str(orc[1]) if len(orc) > 1 else "NW"


            if order_control == "NW":
                # Extraer datos de la solicitud (ORC + OBR)
                request_data = extract_service_request_data(orc, obr)
                # Construir recurso ServiceRequest
                fhir_service_request = build_service_request_resource(
                    request_data,
                    patient_fhir_id,
                    encounter_id
                )

                # evitar repetir ordenes
                order_id = request_data.get("order_id")
                if order_id:
                    if_none_exist = f"identifier=http://hospital/order-id|{order_id}"
                    headers = {"If-None-Exist": if_none_exist}
                else:
                    headers = {}

                # Enviar a FHIR
                status_code, result = await self.execute_fhir_operation(
                    "POST", "/ServiceRequest",
                    resource=fhir_service_request,
                    headers=headers
                )

                if status_code in [200, 201]:
                    sr_id = result.get("id")
                    self.log_info(f"ServiceRequest creado: ID={sr_id}")
                    created_requests.append({
                        "service_request_id": sr_id,
                        "order_id": request_data.get("order_id"),
                        "study_code": request_data.get("study_code")
                    })
                else:
                    self.log_error(f"Error creando ServiceRequest: {status_code}")
                    errors.append({
                        "order_id": request_data.get("order_id"),
                        "error": result,
                        "status_code": status_code
                    })
            elif order_control == "CA":  # Cancelar orden
                # Obtener el número de orden (OBR-2)
                order_id = str(obr[2]) if len(obr) > 2 else ""
                
                if not order_id:
                    self.log_error("Cancelación sin número de orden (OBR-2)")
                    errors.append({"error": "Cancelación sin número de orden"})
                    continue
                
                # Buscar ServiceRequest por identifier
                service_request_id = await self._find_service_request_by_order_id(order_id)
                
                if service_request_id:
                    # Actualizar status a "revoked"
                    update_result = await self._cancel_service_request(service_request_id)
                    if update_result:
                        cancelled_requests.append({
                            "service_request_id": service_request_id,
                            "order_id": order_id,
                            "action": "cancelled"
                        })
                    else:
                        errors.append({
                            "order_id": order_id,
                            "error": "No se pudo cancelar la orden"
                        })
                else:
                    errors.append({
                        "order_id": order_id,
                        "error": "Orden no encontrada"
                    })



        # Respuesta final
        return {
            "success": len(errors) == 0,
            "patient_id": patient_fhir_id,
            "encounter_id": encounter_id,
            "service_requests_created": len(created_requests),
            "service_requests": created_requests,
            "cancelled_requests": cancelled_requests,
            "errors": errors if errors else None
        }
        
    def _extract_service_request_estructure(self, segments: Dict, indexes: Dict) -> List[Dict]:
        """
        Extrae pares de orc y obr cuando estoss egmentos son consecutivos.
        Retorna:
        [
            {
                "orc": segment,
                "obr": segment ,
            },
            ...
        ]
        """
        if not indexes:
            raise ValueError(
                f"{self.MESSAGE_TYPE}: Estructura del mensaje no procesable "
            )
        
        obrs = dict(zip(indexes.get("OBR", []), segments.get("OBR", [])))
        orcs = dict(zip(indexes.get("ORC", []), segments.get("ORC", [])))
        segments_couples = []

        for idx, seg in obrs.items():
            if idx - 1 in orcs:
                segments_couples.append({"orc": orcs[idx - 1], "obr": seg})
            else:
                self.log_warning(f"OBR en índice {idx} no tiene ORC inmediatamente anterior. Se ignora.")

        return segments_couples


    async def _find_service_request_by_order_id(self, order_id: str) -> Optional[str]:
        """Busca un ServiceRequest por su número de orden (identifier)"""
        params = {"identifier": f"http://hospital/order-id|{order_id}"}
        status_code, result = await self.execute_fhir_operation("GET", "/ServiceRequest", params=params)
        
        if status_code == 200 and result.get("total", 0) >= 1:
            return result["entry"][0]["resource"]["id"]
        return None

    async def _cancel_service_request(self, service_request_id: str) -> bool:
        """
        Actualiza el status a 'revoked' usando Patch.
        """
        patch = [
            {
                "op": "replace",
                "path": "/status",
                "value": "revoked"
            }
        ]
        
        status_code, result = await self.execute_fhir_operation(
            "PATCH", 
            f"/ServiceRequest/{service_request_id}", 
            resource=patch,
            headers={"Content-Type": "application/json-patch+json"}
        )
        
        return status_code in [200, 201]