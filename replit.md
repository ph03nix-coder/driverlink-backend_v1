# Sistema de Gestión de Envíos

## Descripción General
Sistema backend completo desarrollado en FastAPI para gestión de envíos con asignación inteligente de choferes, notificaciones en tiempo real y cálculo de rutas optimizadas.

## Características Implementadas

### ✅ Funcionalidades Principales
- **API REST con FastAPI**: Documentación automática disponible en `/docs`
- **Autenticación JWT**: Sistema seguro para choferes y tiendas
- **Registro de Choferes**: Con validación de documentos (licencia y cédula)
- **Sistema de Aprobación**: Integración con API externa para aprobar choferes
- **Gestión de Órdenes**: CRUD completo para órdenes de envío
- **Cálculo de Rutas**: Integración con OSRM para distancias y tiempos
- **Asignación Inteligente**: Basada en ubicación y tipo de vehículo
- **Primer Chofer que Acepta**: Sistema de asignación automática
- **Notificaciones en Tiempo Real**: WebSockets para comunicación instantánea
- **Estados de Seguimiento**: Para órdenes y choferes

### 🔧 Arquitectura Técnica
- **Backend**: FastAPI con Python 3.11
- **Base de Datos**: PostgreSQL con SQLAlchemy ORM
- **Autenticación**: JWT con tokens seguros
- **Tiempo Real**: WebSockets nativos de FastAPI
- **Archivos**: Sistema de subida con validación
- **Rutas**: Integración OSRM para cálculo de distancias

## Estructura del Proyecto

```
├── main.py                     # Aplicación principal FastAPI
├── models.py                   # Modelos de base de datos
├── schemas.py                  # Esquemas Pydantic para validación
├── auth.py                     # Sistema de autenticación JWT
├── config.py                   # Configuración del sistema
├── database.py                 # Conexión a base de datos
├── websocket_manager.py        # Gestor de conexiones WebSocket
├── osrm_client.py             # Cliente para cálculo de rutas
├── services/
│   ├── file_service.py        # Gestión de archivos
│   ├── assignment_service.py   # Asignación de choferes
│   └── external_api_service.py # Integración API externa
└── uploads/                   # Archivos subidos
```

## Endpoints Principales

### Autenticación
- `POST /auth/register` - Registro de usuarios
- `POST /auth/login` - Login con JWT
- `GET /auth/me` - Información del usuario actual

### Choferes
- `POST /drivers/register` - Completar perfil de chofer
- `POST /drivers/upload-documents` - Subir documentos
- `PUT /drivers/location` - Actualizar ubicación
- `PUT /drivers/status` - Cambiar estado (disponible/ocupado)
- `GET /drivers/me` - Perfil del chofer

### Órdenes
- `POST /orders` - Crear orden de envío
- `GET /orders` - Listar órdenes
- `GET /orders/{id}` - Detalles de orden
- `POST /orders/{id}/accept` - Aceptar orden (chofer)
- `POST /orders/{id}/reject` - Rechazar orden (chofer)
- `PUT /orders/{id}/status` - Actualizar estado de orden

### WebSocket
- `WS /ws?token={jwt}` - Conexión para notificaciones en tiempo real

### Utilidades
- `GET /health` - Estado del sistema
- `POST /webhooks/approval` - Webhook de aprobación externa

## Configuración

### Variables de Entorno Requeridas
```bash
DATABASE_URL=postgresql://user:pass@host:port/dbname
SESSION_SECRET=tu-clave-secreta-segura
ACCESS_TOKEN_EXPIRE_MINUTES=1440  # Opcional, default 24h
APPROVAL_API_URL=https://api-externa.com/approval  # Opcional
APPROVAL_API_KEY=clave-api-externa  # Opcional
```

### Tipos de Vehículos Soportados
- `motorcycle` - Motocicleta (hasta 5kg)
- `car` - Automóvil (hasta 50kg)
- `van` - Furgoneta (hasta 200kg)
- `truck` - Camión (más de 200kg)

## Estados del Sistema

### Estados de Choferes
- `pending` - Pendiente de aprobación
- `approved` - Aprobado para trabajar
- `rejected` - Rechazado

### Estados de Disponibilidad
- `available` - Disponible para órdenes
- `busy` - Ocupado con una orden
- `offline` - Desconectado

### Estados de Órdenes
- `pending` - Pendiente de asignación
- `assigned` - Asignada a un chofer
- `in_progress` - En camino
- `delivered` - Entregada
- `cancelled` - Cancelada

## Flujo de Trabajo

1. **Registro**: Tienda/chofer se registra en el sistema
2. **Documentación**: Chofer sube documentos para aprobación
3. **Aprobación**: Sistema externo aprueba/rechaza chofer
4. **Disponibilidad**: Chofer aprobado se marca como disponible
5. **Orden**: Tienda crea orden de envío
6. **Asignación**: Sistema encuentra choferes cercanos adecuados
7. **Notificación**: WebSocket notifica a choferes seleccionados
8. **Aceptación**: Primer chofer que acepta obtiene la orden
9. **Entrega**: Chofer actualiza estados hasta completar entrega

## Seguridad Implementada
- JWT con expiración configurable
- Validación de archivos subidos
- Variables de entorno obligatorias para secretos
- Transacciones atómicas para prevenir condiciones de carrera
- Validación de permisos por tipo de usuario

## Estado del Desarrollo
- ✅ Sistema funcionando en puerto 5000
- ✅ Documentación API disponible en `/docs`
- ✅ Endpoints principales implementados
- ✅ WebSocket para notificaciones funcionando
- ✅ Integración OSRM para rutas
- ⚠️ Algunos errores menores de tipos (no afectan funcionalidad)

## Próximos Pasos Recomendados
1. Implementar tests unitarios e integración
2. Agregar sistema de métricas y monitoreo
3. Implementar caché para consultas frecuentes
4. Agregar sistema de calificaciones para choferes
5. Implementar dashboard administrativo

## Tecnologías Utilizadas
- FastAPI 0.117.1
- SQLAlchemy 2.0.43
- PostgreSQL
- WebSockets 15.0.1
- OSRM API
- JWT Authentication
- Pydantic validation
- Uvicorn ASGI server