import os
from typing import Optional
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

# JWT configuration
SECRET_KEY = os.getenv("SESSION_SECRET")
if not SECRET_KEY:
    raise ValueError("SESSION_SECRET environment variable is required")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours default

# File upload configuration
UPLOAD_DIR = "uploads"
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_DOCUMENT_TYPES = [".jpg", ".jpeg", ".png", ".pdf"]

# OSRM configuration
OSRM_BASE_URL = "https://router.project-osrm.org"

# External approval API configuration
APPROVAL_API_URL = os.getenv("APPROVAL_API_URL", "https://example.com/api/approval")
APPROVAL_API_KEY = os.getenv("APPROVAL_API_KEY")

# WebSocket configuration
WEBSOCKET_PATH = "/ws"

# Vehicle types
VEHICLE_TYPES = ["motorcycle", "car", "van", "truck"]

# Driver approval states
APPROVAL_STATES = ["pending", "approved", "rejected"]

# Driver status
DRIVER_STATUS = ["available", "busy", "offline"]

# Order status
ORDER_STATUS = ["pending", "assigned", "in_progress", "delivered", "cancelled"]

# Distance calculation parameters
MAX_DISTANCE_KM = 50  # Maximum distance to consider a driver
MAX_DRIVERS_TO_NOTIFY = 5  # Maximum number of drivers to notify per order