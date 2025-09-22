from dotenv import load_dotenv
import os

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# Verificar que las variables requeridas estén configuradas
required_vars = ["DATABASE_URL", "SESSION_SECRET"]
for var in required_vars:
    if not os.getenv(var):
        raise ValueError(f"La variable de entorno {var} es requerida pero no está configurada")
