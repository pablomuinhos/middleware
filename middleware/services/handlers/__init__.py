from services.handlers.adt_a01 import ADT_A01_Handler
from services.handlers.adt_a04 import ADT_A04_Handler
from services.handlers.adt_a08 import ADT_A08_Handler
from services.handlers.oru_r01 import ORU_R01_Handler

HANDLERS = [
    ADT_A01_Handler(),
    ADT_A04_Handler(),
    ADT_A08_Handler(),
    ORU_R01_Handler(),
]

def get_handler(message_type: str):
    """Devuelve el handler adecuado para el tipo de mensaje"""
    for handler in HANDLERS:
        if handler.can_handle(message_type):
            return handler
    return None