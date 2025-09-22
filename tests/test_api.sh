#!/bin/bash

# Configuración
BASE_URL="http://localhost:8000"
TEST_EMAIL="test_$(date +%s)@example.com"
TEST_PASSWORD="TestPass123!"

# Colores para la salida
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Función para imprimir resultados
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ $2${NC}"
    else
        echo -e "${RED}✗ $2${NC}"
    fi
}

# Función para hacer peticiones HTTP
make_request() {
    local method=$1
    local endpoint=$2
    local data=$3
    local token=$4
    
    local cmd="curl -s -X $method \"$BASE_URL$endpoint\" -H \"accept: application/json\""
    
    if [ ! -z "$data" ]; then
        cmd+=" -H \"Content-Type: application/json\" -d '$data'"
    fi
    
    if [ ! -z "$token" ]; then
        cmd+=" -H \"Authorization: Bearer $token\""
    fi
    
    # Ejecutar el comando y capturar la salida
    eval $cmd
}

# 1. Registrar un nuevo usuario
echo "1. Registrando un nuevo usuario..."
REGISTER_RESPONSE=$(make_request "POST" "/auth/register" "{\"email\": \"$TEST_EMAIL\", \"password\": \"$TEST_PASSWORD\", \"user_type\": \"driver\"}")
USER_ID=$(echo $REGISTER_RESPONSE | jq -r '.id' 2>/dev/null)
if [ ! -z "$USER_ID" ] && [ "$USER_ID" != "null" ]; then
    print_result 0 "Usuario registrado exitosamente"
else
    print_result 1 "Error al registrar usuario: $REGISTER_RESPONSE"
    exit 1
fi

# 2. Iniciar sesión
echo "\n2. Iniciando sesión..."
LOGIN_RESPONSE=$(make_request "POST" "/auth/login" "{\"email\": \"$TEST_EMAIL\", \"password\": \"$TEST_PASSWORD\"}")
ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token' 2>/dev/null)

if [ ! -z "$ACCESS_TOKEN" ] && [ "$ACCESS_TOKEN" != "null" ]; then
    print_result 0 "Inicio de sesión exitoso"
    echo "   Token: ${ACCESS_TOKEN:0:20}..."
else
    print_result 1 "Error al iniciar sesión: $LOGIN_RESPONSE"
    exit 1
fi

# 3. Obtener información del usuario actual
echo "\n3. Obteniendo información del usuario actual..."
USER_INFO=$(make_request "GET" "/auth/me" "" "$ACCESS_TOKEN")
USER_EMAIL=$(echo $USER_INFO | jq -r '.email' 2>/dev/null)

if [ "$USER_EMAIL" = "$TEST_EMAIL" ]; then
    print_result 0 "Información de usuario obtenida correctamente"
else
    print_result 1 "Error al obtener información del usuario: $USER_INFO"
fi

# 4. Registrar perfil de conductor
echo "\n4. Registrando perfil de conductor..."
DRIVER_DATA='{
    "first_name": "Test",
    "last_name": "Driver",
    "phone_number": "1234567890",
    "vehicle_type": "car",
    "vehicle_plate": "ABC123",
    "vehicle_model": "Test Model",
    "vehicle_year": 2020,
    "user_id": 0
}'

DRIVER_RESPONSE=$(make_request "POST" "/drivers/register" "$DRIVER_DATA" "$ACCESS_TOKEN")
DRIVER_ID=$(echo $DRIVER_RESPONSE | jq -r '.id' 2>/dev/null)

if [ ! -z "$DRIVER_ID" ] && [ "$DRIVER_ID" != "null" ]; then
    print_result 0 "Perfil de conductor registrado exitosamente"
else
    print_result 1 "Error al registrar perfil de conductor: $DRIVER_RESPONSE"
    exit 1
fi

# 5. Actualizar ubicación del conductor
echo "\n5. Actualizando ubicación del conductor..."
LOCATION_DATA='{"latitude": 19.4326, "longitude": -99.1332}'
LOCATION_RESPONSE=$(make_request "PUT" "/drivers/location" "$LOCATION_DATA" "$ACCESS_TOKEN")

if echo "$LOCATION_RESPONSE" | grep -q "Location updated"; then
    print_result 0 "Ubicación actualizada correctamente"
else
    print_result 1 "Error al actualizar ubicación: $LOCATION_RESPONSE"
fi

# 6. Crear un pedido (requiere un usuario de tienda)
echo "\n6. Creando un pedido de prueba..."
# Primero necesitamos un token de tienda
STORE_EMAIL="store_$(date +%s)@example.com"
STORE_PASSWORD="StorePass123!"

# Registrar tienda
make_request "POST" "/auth/register" "{\"email\": \"$STORE_EMAIL\", \"password\": \"$STORE_PASSWORD\", \"user_type\": \"store\"}" > /dev/null

# Iniciar sesión como tienda
STORE_LOGIN_RESPONSE=$(make_request "POST" "/auth/login" "{\"email\": \"$STORE_EMAIL\", \"password\": \"$STORE_PASSWORD\"}")
STORE_TOKEN=$(echo $STORE_LOGIN_RESPONSE | jq -r '.access_token' 2>/dev/null)

# Crear pedido
ORDER_DATA='{
    "pickup_address": "Av. Paseo de la Reforma 505, Cuauhtémoc, 06500 Ciudad de México, CDMX",
    "delivery_address": "Av. Insurgentes Sur 253, Roma Nte., 06700 Ciudad de México, CDMX",
    "pickup_latitude": 19.4326,
    "pickup_longitude": -99.1332,
    "delivery_latitude": 19.4194,
    "delivery_longitude": -99.1455,
    "customer_name": "Cliente de Prueba",
    "customer_phone": "5512345678",
    "items_description": "2x Pizza, 1x Refresco",
    "amount": 250.50,
    "order_number": "order_no_1",
    "store_name": "MiRaboStore"
}'

ORDER_RESPONSE=$(make_request "POST" "/orders" "$ORDER_DATA" "$STORE_TOKEN")
ORDER_ID=$(echo $ORDER_RESPONSE | jq -r '.id' 2>/dev/null)

if [ ! -z "$ORDER_ID" ] && [ "$ORDER_ID" != "null" ]; then
    print_result 0 "Pedido creado exitosamente (ID: $ORDER_ID)"
else
    print_result 1 "Error al crear pedido: $ORDER_RESPONSE"
fi

# 7. Listar pedidos disponibles
echo "\n7. Listando pedidos disponibles..."
ORDERS_RESPONSE=$(make_request "GET" "/orders" "" "$ACCESS_TOKEN")
if echo "$ORDERS_RESPONSE" | jq '. | length > 0' 2>/dev/null | grep -q "true"; then
    print_result 0 "Pedidos obtenidos correctamente"
    echo "   Primer pedido: $(echo $ORDERS_RESPONSE | jq '.[0].id' 2>/dev/null)"
else
    print_result 1 "Error al obtener pedidos: $ORDERS_RESPONSE"
fi

# 8. Cerrar sesión (simulado eliminando el token)
echo "\n8. Cerrando sesión..."
ACCESS_TOKEN=""
print_result 0 "Sesión cerrada"

echo "\nPruebas completadas. Revisa los resultados anteriores para verificar el estado de cada prueba."
