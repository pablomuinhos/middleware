"""
Funciones auxiliares para manejo de fechas entre HL7 v2 y FHIR.
"""
from typing import Optional


def hl7_to_fhir_datetime(hl7_datetime: str) -> str:
    """
    Convierte una fecha/hora en formato HL7 (YYYYMMDDHHMMSS) a formato FHIR (YYYY-MM-DDTHH:MM:SS).
    Args:
        hl7_datetime: String con fecha/hora en formato HL7
    
    Returns:
        String en formato FHIR 
    """
    hl7_datetime = hl7_datetime.strip()
    if  hl7_datetime =="":
        return ""
    
    # YYYYMMDDHHMMSS...
    if len(hl7_datetime) >= 14:
        return f"{hl7_datetime[0:4]}-{hl7_datetime[4:6]}-{hl7_datetime[6:8]}T{hl7_datetime[8:10]}:{hl7_datetime[10:12]}:{hl7_datetime[12:14]}"
    # YYYYMMDDHHMM...
    if len(hl7_datetime) >= 12:
        return f"{hl7_datetime[0:4]}-{hl7_datetime[4:6]}-{hl7_datetime[6:8]}T{hl7_datetime[8:10]}:{hl7_datetime[10:12]}:00"
    #YYYYMMDD...
    elif len(hl7_datetime) >= 8:
        return f"{hl7_datetime[0:4]}-{hl7_datetime[4:6]}-{hl7_datetime[6:8]}"
    # Formato no reconocido, devolver tal cual
    else:
        return hl7_datetime
