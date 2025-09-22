from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from enum import Enum
import config

class UserType(str, Enum):
    STORE = "store"
    DRIVER = "driver"

class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved" 
    REJECTED = "rejected"

class DriverStatus(str, Enum):
    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"

class OrderStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class VehicleType(str, Enum):
    MOTORCYCLE = "motorcycle"
    CAR = "car"
    VAN = "van"
    TRUCK = "truck"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    user_type = Column(SQLEnum(UserType), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationship to driver profile
    driver_profile = relationship("Driver", back_populates="user", uselist=False)

class Driver(Base):
    __tablename__ = "drivers"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    
    # Personal information
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    
    # Vehicle information
    vehicle_type = Column(SQLEnum(VehicleType), nullable=False)
    vehicle_plate = Column(String, nullable=False)
    vehicle_model = Column(String, nullable=False)
    vehicle_year = Column(Integer, nullable=False)
    
    # Location
    current_latitude = Column(Float)
    current_longitude = Column(Float)
    last_location_update = Column(DateTime(timezone=True))
    
    # Status
    status = Column(SQLEnum(DriverStatus), default=DriverStatus.OFFLINE)
    approval_status = Column(SQLEnum(ApprovalStatus), default=ApprovalStatus.PENDING)
    
    # Documentation
    license_document = Column(String)  # File path
    id_document = Column(String)  # File path
    documents_submitted_at = Column(DateTime(timezone=True))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="driver_profile")
    orders = relationship("Order", back_populates="driver")

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Store information
    store_id = Column(Integer, ForeignKey("users.id"))
    store_name = Column(String, nullable=False)
    
    # Driver assignment
    driver_id = Column(Integer, ForeignKey("drivers.id"))
    
    # Order details
    order_number = Column(String, unique=True, nullable=False)
    customer_name = Column(String, nullable=False)
    customer_phone = Column(String, nullable=False)
    
    # Pickup location
    pickup_address = Column(Text, nullable=False)
    pickup_latitude = Column(Float, nullable=False)
    pickup_longitude = Column(Float, nullable=False)
    pickup_instructions = Column(Text)
    
    # Delivery location
    delivery_address = Column(Text, nullable=False)
    delivery_latitude = Column(Float, nullable=False)
    delivery_longitude = Column(Float, nullable=False)
    delivery_instructions = Column(Text)
    
    # Order information
    items_description = Column(Text)
    weight_kg = Column(Float)
    value = Column(Float)
    
    # Status and timing
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    assigned_at = Column(DateTime(timezone=True))
    picked_up_at = Column(DateTime(timezone=True))
    delivered_at = Column(DateTime(timezone=True))
    
    # Estimated delivery
    estimated_distance_km = Column(Float)
    estimated_duration_minutes = Column(Integer)
    
    # Relationships
    driver = relationship("Driver", back_populates="orders")
    store = relationship("User")

class OrderNotification(Base):
    __tablename__ = "order_notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    driver_id = Column(Integer, ForeignKey("drivers.id"))
    
    # Notification details
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    response = Column(String)  # "accepted", "rejected", or null if no response
    response_at = Column(DateTime(timezone=True))
    
    # Distance at time of notification
    distance_km = Column(Float)

class DocumentApproval(Base):
    __tablename__ = "document_approvals"
    
    id = Column(Integer, primary_key=True, index=True)
    driver_id = Column(Integer, ForeignKey("drivers.id"))
    
    # Approval details
    sent_to_external_api = Column(Boolean, default=False)
    external_api_response = Column(Text)
    sent_at = Column(DateTime(timezone=True))
    processed_at = Column(DateTime(timezone=True))
    
    # Results
    license_approved = Column(Boolean)
    id_document_approved = Column(Boolean)
    notes = Column(Text)