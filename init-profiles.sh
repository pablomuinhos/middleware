#!/bin/bash
set -e  # Detener el script si hay error
echo "Inicialización de perfiles FHIR"

FHIR_URL="http://localhost:8080/fhir"
PROFILES_DIR="./middleware/profiles"
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s -f "http://localhost:8080/fhir/metadata" > /dev/null 2>&1; then
        echo " Servidor FHIR operativo"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT+1))
    echo " Esperando... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo " Error: El servidor FHIR no respondió después de $MAX_RETRIES intentos"
    exit 1
fi

echo "Cargando perfiles..."

for profile_file in "$PROFILES_DIR"/*.json; do
    # Verifica si el archivo existe (por si la carpeta está vacía)
    if [ ! -f "$profile_file" ]; then
        echo "  No se encontraron archivos .json en $PROFILES_DIR"
        break
    fi

    file_count=$((file_count+1))
    echo "  ($file_count) Procesando: $(basename "$profile_file")"

    PROFILE_URL=$(jq -r '.url' "$profile_file")
    HTTP_CODE=$(curl -s -o "$PROFILES_DIR"/tmp.log -w "%{http_code}" \
        -X POST "$FHIR_URL/StructureDefinition" \
        -H "Content-Type: application/fhir+json" \
        -H "If-None-Exist: url=$PROFILE_URL" \
        -d @"$profile_file")

    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
        echo "    Perfil cargado correctamente (HTTP $HTTP_CODE)"
    elif [ "$HTTP_CODE" = "409" ] || [ "$HTTP_CODE" = "412" ]; then
        echo "    El perfil ya existe (HTTP $HTTP_CODE). Se omite."
    else
        echo "    Error al cargar el perfil (HTTP $HTTP_CODE)"
        echo "    --- Respuesta del servidor: ---"
        cat "$PROFILES_DIR"/tmp.log
        echo "    ------------------------------"
    fi
done
echo "Inicialización completada"