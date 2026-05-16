# TIPOS DE IDENTIFICADORES HL7 v2 -> FHIR system
HL7_IDENTIFIER_TYPE_MAP = {
    "CIP": "urn:oid:2.16.724.1.2.2.1.1.1",       # CIP España
    "MR": "urn:oid:hospital/medical-record",     # historia clínica local
    "SS": "http://hl7.org/fhir/sid/us-ssn",      # SS
    "NI": "urn:oid:es:nie",                      # NIE
    "PN": "urn:oid:hospital/person-number",      # interno
    "UNK": "urn:oid:hospital/unknown",           # Desconocido
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