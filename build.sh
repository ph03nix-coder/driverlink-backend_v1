#!/bin/bash
# Exit on error
set -e

# Instalar dependencias
echo "Instalando dependencias..."
pip install -r requirements.txt

# Verificar si DATABASE_URL está configurada
if [ -z "$DATABASE_URL" ]; then
    echo "Error: La variable de entorno DATABASE_URL no está configurada"
    exit 1
fi

# Instalar psql para ejecutar comandos SQL
if ! command -v psql &> /dev/null; then
    echo "Instalando PostgreSQL client..."
    apt-get update && apt-get install -y postgresql-client
fi

# Extraer información de conexión de DATABASE_URL
# Formato esperado: postgresql://user:password@host:port/dbname
DB_USER=$(echo $DATABASE_URL | grep -oP 'postgresql://\K[^:]+')
DB_PASS=$(echo $DATABASE_URL | grep -oP ':[^:]+@' | cut -d: -f2 | cut -d@ -f1)
DB_HOST=$(echo $DATABASE_URL | grep -oP '@[^:]+' | cut -d@ -f2)
DB_PORT=$(echo $DATABASE_URL | grep -oP ':[0-9]+' | cut -d: -f2 | head -1)
DB_NAME=$(echo $DATABASE_URL | grep -oP '/([^/]+)$' | cut -d/ -f2 | cut -d? -f1)

# Verificar si la base de datos existe
echo "Verificando base de datos..."
if PGPASSWORD=$DB_PASS psql -h $DB_HOST -U $DB_USER -p $DB_PORT -lqt | cut -d \| -f 1 | grep -qw $DB_NAME; then
    echo "La base de datos $DB_NAME ya existe"
else
    echo "Creando base de datos $DB_NAME..."
    PGPASSWORD=$DB_PASS createdb -h $DB_HOST -U $DB_USER -p $DB_PORT $DB_NAME
fi

# Ejecutar migraciones si existen
echo "Verificando migraciones..."
if [ -d "migrations" ]; then
    echo "Ejecutando migraciones..."
    alembic upgrade head
else
    echo "No se encontraron migraciones. Creando migraciones iniciales..."
    alembic init migrations
    # Aquí deberías editar el archivo de configuración de alembic.ini y el script de migración
    # según sea necesario antes de crear la migración inicial
    # alembic revision --autogenerate -m "Initial migration"
    # alembic upgrade head
fi

echo "¡Construcción completada con éxito!"
