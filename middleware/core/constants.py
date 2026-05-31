# TIPOS DE IDENTIFICADORES HL7 v2 -> FHIR system
HL7_IDENTIFIER_TYPE_MAP = {
    "CIP": "urn:oid:2.16.724.1.2.2.1.1.1",       # CIP España
    "MR": "https://hospital.example/fhir/sid/mr",       # Historia clínica local
    "SS": "http://hl7.org/fhir/sid/us-ssn",             # SS
    "NI": "https://hospital.example/fhir/sid/nie",      # NIE
    "PN": "https://hospital.example/fhir/sid/pn",       # Interno
    "UNK": "https://hospital.example/fhir/sid/unknown", # Desconocido
}

# TIPOS DE MENSAJE HL7
SUPPORTED_MESSAGE_TYPES = {
    "ADT^A04": "create_patient",
    "ADT^A08": "update_patient",
    "ADT^A01": "create_encounter",
    "ORU^R01": "create_observation",
}

# IDENTIFICADOR PRINCIPAL (PID-3.5)
DEFAULT_IDENTIFIER = "CIP"
DEFAULT_IDENTIFIER_PATTERN = r"^B{8}[A-Z]{2}\d{6}$"

# LISTA DE IDENTIFICADORES CONSIDERADOS PRINCIPALES
PRIMARY_IDENTIFIER_TYPES = ["CIP", "MR", "SS", "NI", DEFAULT_IDENTIFIER]

# OUTROS
FHIR_RESOURCE_TYPES = ["Patient", "Encounter", "Observation", "MedicationRequest"]

class MessageType:
    ADT_A01 = "ADT^A01"
    ADT_A04 = "ADT^A04"
    ADT_A08 = "ADT^A08"
    ORU_R01 = "ORU^R01"
#   RDE_O11 = "RDE^O11"
    ORM_O01 = "ORM^O01"

MULTI_RESOURCE_MESSAGES = {
    MessageType.ORU_R01,      # múltiples observations para múltiples pacientes
    # MessageType.RDE_O11
}
def is_multi_resource_message(message_type: str) -> bool:
    return message_type in MULTI_RESOURCE_MESSAGES