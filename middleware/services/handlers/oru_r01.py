# services/handlers/oru_r01.py

from services.handlers.base import HL7MessageHandler
from services.hl7_parser import extract_patient_data, extract_observation_data
from services.observation_builder import build_observation_resource
from typing import Dict, Any, List, Optional, Tuple

class ORU_R01_Handler(HL7MessageHandler):
    
    MESSAGE_TYPE = "ORU^R01"
    
    def can_handle(self, message_type: str) -> bool:
        return message_type == self.MESSAGE_TYPE
    
    async def process(self, segments: Dict[str, Any], indexes: Dict[str, Any] = None) -> Dict[str, Any]:
        self.log_info(f"Procesando {self.MESSAGE_TYPE}: resultados de laboratorio")
        
        # EXTRAER ESTRUCTURA ANIDADA: Pacientes -> Órdenes -> Resultados
        patients_structure = self._extract_patient_orders_structure(segments, indexes)
        if not patients_structure:
            return {"success": False, "error": "No se encontraron datos de pacientes"}
        
        # procesar pacientes -> Órdenes -> Resultados
        results = []
        errors = []
        
        for patient_data in patients_structure:
            result = await self._process_patient(patient_data)
            if result.get("success"):
                results.append(result)
            else:
                errors.append(result)
        
        return {
            "success": len(errors) == 0,
            "patients_processed": len(results),
            "patients_with_errors": len(errors),
            "results": results,
            "errors": errors if errors else None
        }
    
    def _extract_patient_orders_structure(self, segments: Dict, indexes: Dict) -> List[Dict]:
        """
        Extrae la estructura anidada usando el orden global de segmentos.
        Retorna:
        [
            {
                "pid": segment,
                "pv1": segment or None,
                "orders": [
                    {"obr": segment, "obx": [segment1, segment2, ...]},
                    ...
                ]
            },
            ...
        ]
        """
        if not indexes:
            raise ValueError(
                f"{self.MESSAGE_TYPE}: Estructura del mensaje no procesable "
            )
        
        # Construir lista ordenada de segmentos, por index
        all_segments = []
        for seg_type, seg_list in segments.items():
            seg_idxs = indexes.get(seg_type, [])
            for idx, seg in zip(seg_idxs, seg_list):
                all_segments.append((idx, seg_type, seg))
        
        all_segments.sort(key=lambda x: x[0])
        
        # Construir estructura anidada
        patients = []
        current_patient = None
        current_order = None
        
        for idx, seg_type, seg in all_segments:
            if seg_type == "PID":
                if current_patient:
                    patients.append(current_patient)
                current_patient = {"pid": seg, "pv1": None, "orders": []}
                current_order = None
                
            elif seg_type == "PV1" and current_patient:
                current_patient["pv1"] = seg
                
            elif seg_type == "OBR" and current_patient:
                current_order = {"obr": seg, "obx": []}
                current_patient["orders"].append(current_order)
                
            elif seg_type == "OBX" and current_order:
                current_order["obx"].append(seg)
        
        if current_patient:
            patients.append(current_patient)
        
        return patients
    
    async def _process_patient(self, patient_struct: Dict) -> Dict[str, Any]:
        """Procesa un paciente completo (PID, PV1, y todas sus órdenes)"""
        
        pid = patient_struct.get("pid")
        pv1 = patient_struct.get("pv1")
        orders = patient_struct.get("orders", [])
        
        if not pid:
            return {"success": False, "error": "Paciente sin segmento PID"}
        
        # Extraer datos del paciente
        try:
            patient_data = extract_patient_data(pid, None)
        except ValueError as e:
            return {"success": False, "error": str(e)}
        
        if not patient_data.get("identifier"):
            return {"success": False, "error": "No se encontró identificador del paciente"}

        # buscar paciente para obtener id
        patient_resource, status, error = await self.find_patient_by_identifier(
            patient_data['identifier'][0]['system'],
            patient_data['identifier'][0]['value']
        )
        
        if not patient_resource:
            return {"success": False, "error": f"Paciente no encontrado: {patient_data['identifier'][0]['value']}"}
        
        patient_fhir_id = patient_resource.get("id")
        
        # Buscar o crear Encounter
        encounter_id = await self._get_encounter_id(patient_fhir_id, pv1)
        
        # Procesar todas las órdenes del paciente
        all_observations = []
        order_errors = []
        
        for order_idx, order in enumerate(orders):
            obr = order.get("obr")
            obx_list = order.get("obx", [])
            
            if not obr or not obx_list:
                continue
            
            observation_data_list = extract_observation_data(obr, obx_list)

            for obs_data in observation_data_list:
                service_request_id = None
                if obs_data["placer_order_number"]:
                    service_request_id = await self._find_service_request(obs_data["placer_order_number"])
                
                unique_observation_id = obs_data["unique_observation_id"]
                fhir_obs = build_observation_resource(
                    obs_data,
                    patient_fhir_id,
                    encounter_id,
                    service_request_id,
                    unique_observation_id
                )
                
                if unique_observation_id:
                    if_none_exist = f"identifier=http://middleware.fhir/sid/observation-unique|{unique_observation_id}"
                    headers = {"If-None-Exist": if_none_exist}
                else:
                    headers = {}
                
                status_code, result = await self.execute_fhir_operation(
                    "POST", "/Observation", resource=fhir_obs, headers=headers
                )
                
                if status_code in [200, 201]:
                    obs_id = result.get("id")
                    self.log_info(f"Observation creada: {obs_id}")
                    all_observations.append({
                        "id": obs_id,
                        "code": obs_data.get("code"),
                        "value": obs_data.get("value")
                    })
                else:
                    order_errors.append({
                        "order_idx": order_idx,
                        "code": obs_data.get("code"),
                        "error": result,
                        "status_code": status_code
                    })
        
        return {
            "success": len(order_errors) == 0,
            "patient_id": patient_fhir_id,
            "encounter_id": encounter_id,
            "observations_created": len(all_observations),
            "observations": all_observations,
            "errors": order_errors if order_errors else None
        }
    
    async def _get_encounter_id(self, patient_fhir_id: str, pv1_segment: Optional[Any] = None) -> Optional[str]:
        """Obtiene el ID del Encounter: busca activo o crea uno nuevo desde PV1"""
        
        # 1. Buscar Encounter activo
        params = {
            "patient": f"Patient/{patient_fhir_id}",
            "status": "in-progress"
        }
        
        status_code, result = await self.execute_fhir_operation("GET", "/Encounter", params=params)
        
        if status_code == 200 and result.get("entry"):
            encounter = result["entry"][0]["resource"]
            encounter_id = encounter.get("id")
            self.log_info(f"Encounter activo encontrado: {encounter_id}")
            return encounter_id
        
        # 2. Si no hay Encounter activo y tenemos PV1, crear uno nuevo
        if pv1_segment:
            from services.hl7_parser import extract_encounter_data
            from services.encounter_builder import build_encounter_resource
            
            encounter_data = extract_encounter_data(pv1_segment)
            fhir_encounter = build_encounter_resource(encounter_data, patient_fhir_id)
            
            status_code, result = await self.execute_fhir_operation(
                "POST", "/Encounter", resource=fhir_encounter
            )
            
            if status_code in [200, 201]:
                encounter_id = result.get("id")
                self.log_info(f"Encounter creado desde PV1: {encounter_id}")
                return encounter_id
        
        self.log_info(f"No se encontró ni creó Encounter para paciente {patient_fhir_id}")
        return None
    
    async def _find_service_request(self, placer_order_number: str) -> Optional[str]:
        """Busca un ServiceRequest por su número de orden (identificador de negocio)"""
        params = {"identifier": f"http://hospital/order-id|{placer_order_number}"}
        status_code, result = await self.execute_fhir_operation("GET", "/ServiceRequest", params=params)
        
        if status_code == 200 and result.get("total", 0) >= 1:
            sr_id = result["entry"][0]["resource"]["id"]
            self.log_info(f"ServiceRequest encontrado: {sr_id} para orden {placer_order_number}")
            return sr_id
        else:
            self.log_warning(f"No se encontró ServiceRequest para orden {placer_order_number}")
            return None