from abc import ABC, abstractmethod
from typing import Dict, Any, List, Tuple, Optional
from services.hl7_parser import extract_encounter_data
from services.patient_builder import build_patient_resource
from services.encounter_builder import  build_encounter_resource
from services.fhir_client import call_fhir_server
from utils.logging_config import logger

class HL7MessageHandler(ABC):
    """Clase base para todos los handlers de mensajes HL7"""

    PATIENT_PROFILE_URL = "http://middleware.fhir/profile/patient"

    @abstractmethod
    def can_handle(self, message_type: str) -> bool:
        """Verifica si este handler puede procesar el tipo de mensaje"""
        pass
    
    @abstractmethod
    async def process(self, segments: Dict[str, Any], indexes: Dict[str, Any] = None) -> Tuple[Dict[str, Any],Dict[str, int], List[Dict]]:
        """
        Procesa el mensaje y devuelve el resultado de la operación FHIR
            Tuple (result, resources_processed, errors)
            - result: diccionario con detalles adicionales
            - resources_processed: {"ResurceType1": num, ResurceType2": num, ...}
            - errors: lista de errores
        """
        pass
    
    async def execute_fhir_operation(
        self, 
        method: str, 
        path: str, 
        resource: Dict[str, Any] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Dict[str, Any] = None 
    ) -> Tuple[int, Optional[Dict]]:
        """Ejecuta la operación en el servidor FHIR"""
        return await call_fhir_server(method, path, data=resource, params=params, headers=headers)
    
    def log_info(self, message: str):
        logger.info(f"[{self.__class__.__name__}] {message}")
    def log_warning(self, message: str):
        logger.warning(f"[{self.__class__.__name__}] {message}")
    def log_error(self, message: str):
        logger.error(f"[{self.__class__.__name__}] {message}")


    async def find_patient_by_identifier(self, system: str, value: str) -> Tuple[Optional[Dict], Optional[int], Optional[str]]:
        """
        Busca un paciente por identifier (system|value) en FHIR.
        
        Returns:
            Tuple (patient_resource, status_code, error_message)
            - patient_resource: recurso completo del paciente si se encuentra exactamente uno
            - status_code: 200 si ok, 404 si no existe, 406 si hay duplicados
            - error_message: mensaje de error si no es 200
        """
        if not system or not value:
            return None, 400, "Faltan system o value para buscar el paciente"
        
        identifier_param = f"{system}|{value}"
        params = {"identifier": identifier_param}
        
        self.log_info(f"Buscando paciente con identifier: {identifier_param}")
        
        search_status, search_result = await self.execute_fhir_operation(
            "GET", 
            "/Patient", 
            params=params
        )
        
        if search_status != 200:
            return None, search_status, f"Error buscando paciente: {search_result}"
        
        entries = search_result.get("entry", [])
        
        if not entries:
            self.log_error(f"Paciente no encontrado: {identifier_param}")
            return None, 404, f"Paciente con identifier '{value}' no existe"
        
        if len(entries) > 1:
            self.log_error(f"Múltiples pacientes encontrados: {identifier_param}")
            return None, 406, f"Existen varios pacientes con identifier '{value}'"
        
        patient_resource = entries[0]["resource"]
        patient_id = patient_resource.get("id")
        version_id = patient_resource.get("meta", {}).get("versionId")
        
        self.log_info(f"Paciente encontrado: ID={patient_id}, versión={version_id}")
        return patient_resource, 200, None


    async def get_or_create_patient(self, system: str, value: str, patient_data: Dict) -> Optional[str]:
        """Busca paciente por identifier. Si no existe, lo crea."""
        
        # buscar
        patient_resource, status, error = await self.find_patient_by_identifier(system, value)
        
        if patient_resource:
            patient_id = patient_resource.get("id")
            self.log_info(f"Paciente encontrado: ID={patient_id}")
            return patient_id
        
        # si no existe, crear
        self.log_info(f"Paciente {value} no existe. Creando...")
        
        fhir_patient = build_patient_resource(patient_data)
        if_none_exist = f"identifier={system}|{value}"
        headers = {"If-None-Exist": if_none_exist}
        
        create_status, create_result = await self.execute_fhir_operation(
            "POST", "/Patient", resource=fhir_patient, headers=headers
        )
        
        if create_status in [200, 201]:
            patient_id = create_result.get("id")
            self.log_info(f"Paciente creado automáticamente: ID={patient_id}")
            return patient_id
        else:
            self.log_error(f"Error creando paciente: {create_status} - {create_result}")
            return None
        

    async def process_encounter_if_present(self, segments: Dict, patient_fhir_id: str) -> Optional[Dict]:
        """
        Procesa el segmento PV1 si existe en el mensaje.
        Crea o actualiza el Encounter según corresponda.
        """
        pv1 = segments.get("PV1")
        if not pv1:
            return None
        
        self.log_info("Procesando segmento PV1...")
        
        # visita
        encounter_data = extract_encounter_data(pv1)
        fhir_encounter = build_encounter_resource(encounter_data, patient_fhir_id)
        
        # encounter activo
        active_encounter = await self.find_active_encounter(patient_fhir_id)
        
       
        if active_encounter:
            # actualizar
            encounter_id = active_encounter.get("id")
            version_id = active_encounter.get("meta", {}).get("versionId", "1")
            headers = {"If-Match": f'W/"{version_id}"'}
            
            fhir_encounter["id"] = encounter_id
            fhir_encounter["status"] = "in-progress"
            
            status_code, result = await self.execute_fhir_operation(
                "PUT", f"/Encounter/{encounter_id}",
                resource=fhir_encounter,
                headers=headers
            )
            
            self.log_info(f"Encounter actualizado: {encounter_id}")
            return {"action": "updated", "id": encounter_id, "status_code": status_code}
        else:
            # crear encounter
            status_code, result = await self.execute_fhir_operation(
                "POST", "/Encounter", resource=fhir_encounter
            )
            
            self.log_info(f"Encounter creado: {result.get('id') if result else 'unknown'}")
            return {"action": "created", "id": result.get("id") if result else None, "status_code": status_code}


    async def find_active_encounter(self, patient_fhir_id: str) -> Optional[Dict]:
        """Busca un Encounter activo para un paciente."""
        params = {
            "patient": f"Patient/{patient_fhir_id}",
            "status": "in-progress"
        }
        
        status_code, result = await self.execute_fhir_operation("GET", "/Encounter", params=params)
        
        if status_code == 200 and result.get("entry"):
            return result["entry"][0]["resource"]
        
        return None


    async def create_patient_and_encounter_transaction(
        self, 
        patient_data: Dict[str, Any], 
        encounter_data: Dict[str, Any]
        ) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """
        Crea Patient y Encounter en una sola transacción FHIR.
        Args:
            patient_data: Datos extraídos del PID
            encounter_data: Datos extraídos del PV1
        Returns:
            Tuple (success, patient_id, encounter_id, error_message)
        """

        if not patient_data.get("identifier"):
            return False, None, None, "No se encontró identificador para el paciente"

        # patient
        fhir_patient = build_patient_resource(patient_data)
        # Validar paciente contra perfil
        is_valid, error_msg = await self.validate_resource(
            fhir_patient, 
            "Patient", 
            self.PATIENT_PROFILE_URL
        )
        if not is_valid:
            self.log_error(f"Validación de Patient fallida: {error_msg}")
            return {"success": False, "error": f"Validación fallida: {error_msg}"}

        primary_id = patient_data["identifier"][0]
        system = primary_id["system"]
        value = primary_id["value"]

        bundle = {
            "resourceType": "Bundle",
            "type": "transaction",
            "entry": []
        }

        bundle["entry"].append({
            "fullUrl": "urn:uuid:patient-1",
            "resource": fhir_patient,
            "request": {
                "method": "POST",
                "url": "Patient",
                "ifNoneExist": f"identifier={system}|{value}"
            }
        })

        # encounter (referencia por urn:uuid)
        fhir_encounter = build_encounter_resource(encounter_data, "urn:uuid:patient-1")
        bundle["entry"].append({
            "fullUrl": "urn:uuid:encounter-1",
            "resource": fhir_encounter,
            "request": {
                "method": "POST",
                "url": "Encounter"
            }
        })

        self.log_info(f"Enviando Transaction Bundle: Patient={value}, Encounter incluido")

        # enviar Bundle
        status_code, result = await self.execute_fhir_operation(
            "POST", 
            "/",  # root para bundles
            resource=bundle
        )

        if status_code != 200:
            self.log_error(f"Error en transacción: {status_code} - {result}")
            return False, None, None, f"Error HTTP {status_code}: {result}"

        if result.get("type") != "transaction-response":
            self.log_error(f"Respuesta no es transaction-response: {result}")
            return False, None, None, "Formato de respuesta inesperado"

        patient_id = None
        encounter_id = None

        for entry in result.get("entry", []):
            response = entry.get("response", {})
            location = response.get("location", "")
            
            if "Patient" in location:
                patient_id = location.split("/")[-1]
                self.log_info(f"Patient creado/encontrado: ID={patient_id}")
            elif "Encounter" in location:
                encounter_id = location.split("/")[-1]
                self.log_info(f"Encounter creado: ID={encounter_id}")
            
            if response.get("status", "").startswith("4"):
                self.log_error(f"Error en operación: {response}")
                return False, patient_id, encounter_id, f"Error en operación: {response}"

        if not patient_id:
            return False, None, None, "No se pudo obtener el ID del Patient"

        return True, patient_id, encounter_id, None

    def get_required_segment(self, segments: Dict, segment_type: str, handler_name: str) -> Any:
        """Obtiene un único segmento obligatorio (exactamente uno)"""
        seg_list = segments.get(segment_type, [])
        if len(seg_list) != 1:
            raise ValueError(f"{handler_name}: Debe informarse exactamente un segmento {segment_type}")
        return seg_list[0]

    def get_optional_segment(self, segments: Dict, segment_type: str, handler_name: str) -> Optional[Any]:
        """Obtiene un segmento opcional (cero o uno)"""
        return segments.get(segment_type)[0] if segment_type in segments  else None
    


    async def validate_resource(
        self, 
        resource: Dict[str, Any], 
        resource_type: str, 
        profile_url: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Valida un recurso FHIR contra un perfil usando la operación $validate.
        
        Args:
            resource: Recurso FHIR a validar
            resource_type: Tipo de recurso ("Patient", "Encounter", etc.)
            profile_url: URL del perfil contra el que validar
        
        Returns:
            Tuple (is_valid, error_message)
        """

        
        # Añadir perfil si se proporciona
        if profile_url:
            if "meta" not in resource:
                resource["meta"] = {}
            if "profile" not in resource["meta"]:
                resource["meta"]["profile"] = []
            if profile_url not in resource["meta"]["profile"]:
                resource["meta"]["profile"].append(profile_url)
        params = {"profile": profile_url}
        
        self.log_info(f"Validando {resource_type} contra perfil {profile_url}")
        
        try:
            status_code, result = await self.execute_fhir_operation(
                "POST", 
                f"/{resource_type}/$validate",
                resource=resource,
                params=params
            )
            
            if status_code != 200:
                return False, f"Error en validación: HTTP {status_code}"
            
            # verificar si hay errores en OperationOutcome
            error_messages = []
            for issue in result.get("issue", []):
                if issue.get("severity") == "error":
                    diagnostics = issue.get("diagnostics", "")
                    error_code = issue.get("code", "unknown")

                    if diagnostics:
                        error_messages.append(f"{error_code}: {diagnostics}")
                    else:
                        error_messages.append(f"{error_code}")
            
            if error_messages:
                return False, f"Validación fallida ({len(error_messages)} errores): " + "; ".join(error_messages)
            
            
            self.log_info(f"Validación exitosa para {resource_type}")
            return True, None
            
        except Exception as e:
            self.log_error(f"Excepción en validación: {str(e)}")
            return False, f"Error en validación: {str(e)}"