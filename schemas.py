from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from models import UserType, ApprovalStatus, DriverStatus, OrderStatus, VehicleType

# Base schemas
class UserBase(BaseModel):
    email: EmailStr
    user_type: UserType

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Driver schemas
class DriverBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone_number: str = Field(..., min_length=10, max_length=15)
    vehicle_type: VehicleType
    vehicle_plate: str = Field(..., min_length=1, max_length=20)
    vehicle_model: str = Field(..., min_length=1, max_length=100)
    vehicle_year: int = Field(..., ge=1950, le=2030)

class DriverCreate(DriverBase):
    user_id: int

class DriverLocationUpdate(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)

class DriverStatusUpdate(BaseModel):
    status: DriverStatus

class Driver(DriverBase):
    id: int
    user_id: int
    status: DriverStatus
    approval_status: ApprovalStatus
    current_latitude: Optional[float]
    current_longitude: Optional[float]
    last_location_update: Optional[datetime]
    license_document: Optional[str]
    id_document: Optional[str]
    documents_submitted_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

# Order schemas
class OrderBase(BaseModel):
    order_number: str = Field(..., min_length=1, max_length=50)
    customer_name: str = Field(..., min_length=1, max_length=200)
    customer_phone: str = Field(..., min_length=10, max_length=15)
    pickup_address: str = Field(..., min_length=1)
    pickup_latitude: float = Field(..., ge=-90, le=90)
    pickup_longitude: float = Field(..., ge=-180, le=180)
    pickup_instructions: Optional[str] = None
    delivery_address: str = Field(..., min_length=1)
    delivery_latitude: float = Field(..., ge=-90, le=90)
    delivery_longitude: float = Field(..., ge=-180, le=180)
    delivery_instructions: Optional[str] = None
    items_description: Optional[str] = None
    weight_kg: Optional[float] = Field(None, ge=0)
    value: Optional[float] = Field(None, ge=0)

class OrderCreate(OrderBase):
    store_name: str = Field(..., min_length=1, max_length=200)

class OrderStatusUpdate(BaseModel):
    status: OrderStatus

class Order(OrderBase):
    id: int
    store_id: int
    store_name: str
    driver_id: Optional[int]
    status: OrderStatus
    created_at: datetime
    assigned_at: Optional[datetime]
    picked_up_at: Optional[datetime]
    delivered_at: Optional[datetime]
    estimated_distance_km: Optional[float]
    estimated_duration_minutes: Optional[int]
    
    class Config:
        from_attributes = True

# Authentication schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

# WebSocket message schemas
class WebSocketMessage(BaseModel):
    type: str
    data: dict

class OrderNotificationWS(BaseModel):
    type: str = "order_notification"
    order_id: int
    pickup_address: str
    delivery_address: str
    distance_km: float
    estimated_duration_minutes: Optional[int]
    customer_name: str
    items_description: Optional[str]

class OrderAcceptance(BaseModel):
    order_id: int
    action: str = Field(..., pattern="^(accept|reject)$")

# Document upload schemas
class DocumentUploadResponse(BaseModel):
    message: str
    license_document: Optional[str] = None
    id_document: Optional[str] = None

# External API schemas
class DocumentApprovalRequest(BaseModel):
    driver_id: int
    license_document_path: str
    id_document_path: str
    driver_info: dict

class ApprovalStatusResponse(BaseModel):
    status: ApprovalStatus
    message: str

# Response schemas
class MessageResponse(BaseModel):
    message: str

class DriverListResponse(BaseModel):
    drivers: List[Driver]
    total: int

class OrderListResponse(BaseModel):
    orders: List[Order]
    total: int

# Statistics schemas
class DriverStats(BaseModel):
    total_deliveries: int
    pending_deliveries: int
    average_rating: Optional[float]
    
class OrderStats(BaseModel):
    pending_orders: int
    assigned_orders: int
    in_progress_orders: int
    completed_orders: int