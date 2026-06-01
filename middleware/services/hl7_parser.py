from datetime import datetime, timezone, timedelta
import hl7
import logging
from typing import Dict, Any, Tuple, List
from core.constants import DEFAULT_IDENTIFIER, HL7_IDENTIFIER_TYPE_MAP, PRIMARY_IDENTIFIER_TYPES, DEFAULT_IDENTIFIER_PATTERN
import re
import hashlib
from core.config import settings

logger = logging.getLogger(__name__)

def normalize_hl7_message(raw_message: str) -> str:
    return raw_message.replace('\r\n', '\r').replace('\n', '\r')

def parse_hl7_segments(raw_message: str) -> Tuple[Dict[str, Any],Dict[str, Any]]:
    """Parsea un mensaje HL7 y devuelve un diccionario de segmentos"""
    normalized = normalize_hl7_message(raw_message)
    parsed = hl7.parse(normalized)
    
    segments = {}
    indexes = {}
    for idx,segment in enumerate(parsed):
        segment_type = segment[0][0]

        if segment_type not in segments:
            segments[segment_type] = []
            indexes[segment_type] = []

        segments[segment_type].append(segment)
        indexes[segment_type].append(idx)

    return segments, indexes



def check_token_and_date_and_get_message_type(segments: Dict[str, Any]) -> str:
    """Extrae el tipo de mensaje del segmento MSH"""
    msh_list = segments.get('MSH', [])
    if not msh_list:
        raise ValueError("No se encontró segmento MSH")
    msh = msh_list[0]

    if len(msh) <= 9:
        raise ValueError("No se ha podido obtener el tipo de mensaje")
    
    # COMPROBAR TOKEN
    secret = settings.get_secret_key(str(msh[3]), str(msh[4])).encode('utf-8')
    if not secret:
        raise ValueError(f"No hay clave secreta configurada para {str(msh[3])}/{str(msh[4])}")
    
    # se hace hash de la fecha y el secreto
    msh_datetime = str(msh[7])
    key = hashlib.sha256(f"{msh_datetime}".encode('utf-8') + secret).hexdigest()
    if key != str(msh[8]):
        raise ValueError("No se ha podido autenticar el mensaje")
    
    ## COMPROBAR TIEMPO
    if not msh_datetime:
        raise ValueError("No se encontró fecha/hora en el mensaje (MSH-7)")
    
    try:
        msg_time = datetime.strptime(msh_datetime, "%Y%m%d%H%M%S")
    except ValueError:
        try:
            msg_time = datetime.strptime(msh_datetime, "%Y%m%d")
        except ValueError:
            raise ValueError(f"Formato de fecha no reconocido: {msh_datetime}")
    msg_time = msg_time.replace(tzinfo=timezone.utc)    
    now = datetime.now(timezone.utc)
    time_diff = abs((now - msg_time).total_seconds())
    
    MAX_TIME_DIFF_SECONDS = settings.MAX_TIME_DIFF_SECONDS
    
    #if time_diff > MAX_TIME_DIFF_SECONDS:
    #    raise ValueError(f"El mensaje tiene una antigüedad de {time_diff/60:.1f} minutos, excede el límite de 30 minutos")
    

    
    return str(msh[9])


def flatten_hl7_field(field):
    """
    Simplifica los anidamientos excesivos de la librería hl7
    """
    result = []
    
    if isinstance(field, (list, tuple)):
        for item in field:
            if isinstance(item, (list, tuple)):
                for subitem in item:
                    if isinstance(subitem, (list, tuple)) and len(subitem) > 0:
                        result.append(str(subitem[0]) if subitem[0] else "")
                    else:
                        result.append(str(subitem) if subitem else "")
            else:
                result.append(str(item) if item else "")
    else:
        result.append(str(field) if field else "")
    
    return result

###################
## RESOURCES
###################

## PATIENT
def extract_patient_data(pid_segment, pd1_segment=None) -> Dict[str, Any]:
    """Extrae datos del paciente"""

    ### PID

    # PID-2
    default_identifier = None
    identifiers = []
    if len(pid_segment) > 2 and pid_segment[2]:
        pid2_value = str(pid_segment[2]).strip()
        if pid2_value and re.match(DEFAULT_IDENTIFIER_PATTERN, pid2_value):
            default_identifier = pid2_value

    # PID-3: Patient IDs list
    if len(pid_segment) > 3:
        for identifier in pid_segment[3]:
            if len(identifier) > 4 and str(identifier[4]) in HL7_IDENTIFIER_TYPE_MAP:
                key = str(identifier[4])
                value = str(identifier[0]).strip()
                if key == DEFAULT_IDENTIFIER:
                    if re.match(DEFAULT_IDENTIFIER_PATTERN, value):
                        default_identifier = value
                else:
                    identifiers.append( { "system": HL7_IDENTIFIER_TYPE_MAP.get(key),"value": value})
    if default_identifier is not None:
        identifiers.insert(
            0,
            { "system": HL7_IDENTIFIER_TYPE_MAP.get(DEFAULT_IDENTIFIER),"value": default_identifier}
        )
    else:
        raise ValueError("No se encontró identificador principal de paciente o no cumple el formato requerido")

    # PID-5: Patient Name
    apellido = ""
    nombre = ""
    if len(pid_segment) > 5 and pid_segment[5]:
        name_parts = flatten_hl7_field(pid_segment[5])
        apellido = name_parts[0] if len(name_parts) > 0 else ""
        nombre = name_parts[1] if len(name_parts) > 1 else ""

    # PID-6: Patient Name
    apellido2 = ""
    if len(pid_segment) > 6 and pid_segment[6]:
        name_parts = flatten_hl7_field(pid_segment[6])
        apellido2 = name_parts[0] if len(name_parts) > 0 else ""

    # PID-7: Date of Birth
    fecha_raw = str(pid_segment[7]) if len(pid_segment) > 7 else ""
    fecha_nacimiento = ""
    if len(fecha_raw) >= 8:
        fecha_nacimiento = f"{fecha_raw[0:4]}-{fecha_raw[4:6]}-{fecha_raw[6:8]}"
    
    # PID-8: Gender
    genero_raw = str(pid_segment[8]) if len(pid_segment) > 8 else ""
    genero = "male" if genero_raw.upper() == "M" else "female" if genero_raw.upper() == "F" else "unknown"

    # PID-11: street^^city^state or province^zip^country
    address = None
    if len(pid_segment) > 11 and pid_segment[11]:
        addr_parts = flatten_hl7_field(pid_segment[11])
        # limpiar
        while len(addr_parts) < 6:
            addr_parts.append("")
        
        # construir direccion si hay algo
        if any(addr_parts[:5]):
            address = {
                "line": [addr_parts[0]] if addr_parts[0] else [],
                "city": addr_parts[2] if addr_parts[2] else None,
                "state": addr_parts[3] if addr_parts[3] else None,
                "postalCode": addr_parts[4] if addr_parts[4] else None,
                "country": addr_parts[5] if addr_parts[5] else None,
            }

            address = {k: v for k, v in address.items() if v not in (None, [])}
    # PID-13 PID14:
    telecom = []
    if len(pid_segment) > 13 and pid_segment[13]:
        phone_home = str(pid_segment[13]).strip()
        if phone_home:
            telecom.append({
                "system": "phone",
                "value": phone_home,
                "use": "home"
            })
    
    if len(pid_segment) > 14 and pid_segment[14]:
        phone_business = str(pid_segment[14]).strip()
        if phone_business:
            telecom.append({
                "system": "phone",
                "value": phone_business,
                "use": "work"
            })

    # PID-15
    language = None
    if len(pid_segment) > 15 and pid_segment[15]:
        lang_raw = str(pid_segment[15]).strip().upper()
        if lang_raw:
            # TODO: mapear según system
            lang_map = {
                "ENG": "en", "SPA": "es", "FRE": "fr", "GER": "de",
                "ITA": "it", "POR": "pt", "RUS": "ru", "CHI": "zh"
            }
            language = lang_map.get(lang_raw, lang_raw.lower())

    # PID-16
    marital_status = None
    if len(pid_segment) > 16 and pid_segment[16]:
        marital_raw = str(pid_segment[16]).strip().upper()
        marital_map = { # TODO: mapear según system
            "M": "M",
            "S": "S",
            "D": "D",
            "W": "W",
            "A": "A",
            "P": "P",
            "U": "U",
            "T": "U",
        }
        marital_status = marital_map.get(marital_raw, "U")

    ### PD1

    disability = None
    living_arrangement = None
    living_dependency = None
    
    if pd1_segment:
        # PD1-7
        if len(pd1_segment) > 7 and pd1_segment[7]:
            living_arrangement = str(pd1_segment[7]).strip()
        
        # PD1-8
        if len(pd1_segment) > 8 and pd1_segment[8]:
            living_dependency = str(pd1_segment[8]).strip()

        # PD1-11
        if len(pd1_segment) > 11 and pd1_segment[11]:
            disability_parts = flatten_hl7_field(pd1_segment[11])
            if len(disability_parts) >= 1:
                disability = {
                    "code": disability_parts[0] if len(disability_parts) > 0 else "",
                    "description": disability_parts[1] if len(disability_parts) > 1 else "",
                    "system": disability_parts[2] if len(disability_parts) > 2 else ""
                }

    return {
        "identifier":identifiers,
        "nombre": nombre,
        "apellido": apellido,
        "apellido2":apellido2,
        "birthDate": fecha_nacimiento,
        "gender": genero,
        "address":address,
        "telecom": telecom,
        "language":language,
        "marital_status":marital_status,
        "disability": disability,
        "living_arrangement": living_arrangement,
        "living_dependency": living_dependency,  
    }

## ENCOUTER

def extract_encounter_data(pv1_segment) -> Dict[str, Any]:
    """
    Extrae datos del segmento PV1 (Patient Visit) para construir un Encounter de FHIR.
    """
    if not pv1_segment or len(pv1_segment) < 2:
        return {}

    class_map = { # TODO: crear mapeo
        "O": "AMB",  # Ambulatory
        "I": "IMP",  # Inpatient
        "E": "EMER", # Emergency
        "U": "URG",  # Urgent
    }
    patient_class_code = str(pv1_segment[2]).strip() if len(pv1_segment) > 2 else "AMB"
    encounter_class = class_map.get(patient_class_code, "AMB")

    # PV1-3:'Consultorio^^^Médico^A'
    location = None
    if len(pv1_segment) > 3 and pv1_segment[3]:
        loc_parts = flatten_hl7_field(pv1_segment[3])
        if loc_parts:
            location = {
                "location": {"display": loc_parts[0] if loc_parts[0] else "Unknown Location"}
            }

    # PV1-7: ID^Name
    practitioner_id = None
    practitioner_name = None
    if len(pv1_segment) > 7 and pv1_segment[7]:
        doc_parts = flatten_hl7_field(pv1_segment[7])
        if len(doc_parts) >= 2:
            practitioner_id = doc_parts[0]  # ID del médico
            practitioner_name = doc_parts[1]  # Nombre del médico

    # PV1-44
    admit_time = None
    if len(pv1_segment) > 44 and pv1_segment[44]:
        admit_time = str(pv1_segment[44])  # Formato HL7: YYYYMMDDHHMMSS
        # TODO revisar formatos

    return {
        "class": encounter_class,
        "location": location,
        "practitioner_id": practitioner_id,
        "practitioner_name": practitioner_name,
        "admit_time": admit_time,
        "raw_pv1": pv1_segment
    }


## OBSERVATION

def extract_observation_data(obr_segment, obx_segments: list) -> List[Dict[str, Any]]:
    """
    Extrae datos de observación de los segmentos OBR y OBX.
    Retorna una lista de observaciones (una por cada OBX).
    """
    observations = []
    
    # OBR-2: orden
    placer_order_number = str(obr_segment[2]) if len(obr_segment) > 2 else ""

    # OBR-4: código
    study_code = ""
    if len(obr_segment) > 4 and obr_segment[4]:
        obr4 = flatten_hl7_field(obr_segment[4])
        study_code = obr4[0] if len(obr4) > 0 else ""
    
    # OBR-7: fecha
    effective_date = ""
    if len(obr_segment) > 7 and obr_segment[7]:
        effective_date = str(obr_segment[7])
    
    for idx, obx in enumerate(obx_segments):
        set_id = str(obx[1]) if len(obx) > 1 and len(obx[1]) > 1 else str(idx + 1)
        unique_observation_id = f"{placer_order_number}-{set_id}"
        # OBX-3: código 
        code = ""
        if len(obx) > 3 and obx[3]:
            code_parts = flatten_hl7_field(obx[3])
            code = code_parts[0] if code_parts else ""
        
        # OBX-5: valor
        value = ""
        if len(obx) > 5 and obx[5]:
            value = str(obx[5])
        
        # OBX-6: unidades
        unit = ""
        if len(obx) > 6 and obx[6]:
            unit_parts = flatten_hl7_field(obx[6])
            unit = unit_parts[0] if unit_parts else ""
        
        # OBX-7: rango
        reference_range = ""
        if len(obx) > 7 and obx[7]:
            reference_range = str(obx[7])
        
        # OBX-8: f(N=Normal, L=Low, H=High)
        abnormal_flag = ""
        if len(obx) > 8 and obx[8]:
            abnormal_flag = str(obx[8])
        
        observations.append({
            "unique_observation_id":unique_observation_id,
            "placer_order_number": placer_order_number,
            "study_code": study_code,
            "code": code,
            "value": value,
            "unit": unit,
            "reference_range": reference_range,
            "abnormal_flag": abnormal_flag,
            "effective_date": effective_date
        })
    
    return observations


## SERVICE REQUEST

def extract_service_request_data(orc_segment, obr_segment) -> Dict[str, Any]:
    """Extrae datos de ORC y OBR para construir un ServiceRequest"""

    # Datos desde ORC (Order Common)
    order_status = "active"
    order_date = ""

    order_status = str(orc_segment[1]) if len(orc_segment) > 1 else "NW"  
    order_date = str(orc_segment[9]) if len(orc_segment) > 9 else ""      

    # Datos desde OBR (Observation Request)
    study_code = ""
    study_description = ""
    study_date = ""
    order_id = ""

    order_id = str(obr_segment[2]) if len(obr_segment) > 2 else ""        

    if len(obr_segment) > 4:
        obr4 = flatten_hl7_field(obr_segment[4])
        study_code = obr4[0] if len(obr4) > 0 else ""
        study_description = obr4[1] if len(obr4) > 1 else ""

    if len(obr_segment) > 7:
        study_date = str(obr_segment[7])  # OBR-7: Observation Date/Time

    return {
        "order_id": order_id,
        "order_status": order_status,
        "order_date": order_date,
        "study_code": study_code,
        "study_description": study_description,
        "study_date": study_date
    }
