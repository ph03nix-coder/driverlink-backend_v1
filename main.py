import os
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, WebSocket, WebSocketDisconnect, Query, Form

# Cargar variables de entorno
load_dotenv()
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_, true, false
from datetime import datetime, timedelta
from typing import List, Optional

# Import all modules
from database import engine, get_db, Base
from models import User as UserModel, Driver as DriverModel, Order as OrderModel, OrderNotification as OrderNotificationModel, UserType, DriverStatus, OrderStatus, ApprovalStatus, Driver
import schemas
from auth import get_password_hash, authenticate_user, create_access_token, verify_token, get_current_active_user
from websocket_manager import manager, handle_websocket_connection
from services.file_service import file_service
from services.assignment_service import assignment_service  
from services.external_api_service import external_api_service
from osrm_client import osrm_client
import config

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="DriverLink Delivery Management System",
    description="Backend API for delivery management with driver assignment and real-time notifications",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on your frontend domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Dependency to get current user from token
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    return get_current_active_user(db, token)

# Dependency to check if user is a store
def get_current_store(current_user: UserModel = Depends(get_current_user)):
    if current_user.user_type != UserType.STORE:
        raise HTTPException(status_code=403, detail="Access denied. Store account required.")
    return current_user

# Dependency to check if user is a driver
def get_current_driver_user(current_user: UserModel = Depends(get_current_user)):
    if current_user.user_type != UserType.DRIVER:
        raise HTTPException(status_code=403, detail="Access denied. Driver account required.")
    return current_user

# Dependency to get driver profile
def get_current_driver(current_user: UserModel = Depends(get_current_driver_user), db: Session = Depends(get_db)):
    driver = db.query(DriverModel).filter(DriverModel.user_id == current_user.id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")
    return driver

# Authentication endpoints
@app.post("/auth/register", response_model=schemas.User)
async def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Register a new user (store or driver)"""
    # Check if user already exists
    db_user = db.query(UserModel).filter(UserModel.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = UserModel(
        email=user.email,
        hashed_password=hashed_password,
        user_type=user.user_type
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

@app.post("/auth/login", response_model=schemas.Token)
async def login_user(user_login: schemas.UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return JWT token"""
    user = authenticate_user(db, user_login.email, user_login.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/auth/me", response_model=schemas.User)
async def get_current_user_info(current_user: UserModel = Depends(get_current_user)):
    """Get current user information"""
    return current_user

# Driver registration and management endpoints
@app.post("/drivers/register", response_model=schemas.Driver)
async def register_driver(
    driver_data: schemas.DriverCreate, 
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Complete driver profile registration
    
    This endpoint allows any authenticated user to register as a driver.
    The user must be authenticated but doesn't need to have the driver role yet.
    After successful registration, the user's role will be updated to DRIVER.
    """
    # Check if driver profile already exists
    existing_driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()
    if existing_driver:
        raise HTTPException(status_code=400, detail="Driver profile already exists")
    
    # Update user type to DRIVER if not already set
    if current_user.user_type != UserType.DRIVER:
        current_user.user_type = UserType.DRIVER
        db.commit()
    
    # Create driver profile
    driver_dict = driver_data.dict()
    # Remove user_id from the data since we'll set it from current_user
    driver_dict.pop('user_id', None)
    
    db_driver = Driver(**driver_dict, user_id=current_user.id)
    db.add(db_driver)
    db.commit()
    db.refresh(db_driver)
    
    return db_driver

@app.post("/drivers/upload-documents")
async def upload_driver_documents(
    license_file: UploadFile = File(...),
    id_document_file: UploadFile = File(...),
    current_user: UserModel = Depends(get_current_driver_user),
    db: Session = Depends(get_db)
):
    """Upload driver license and ID documents"""
    driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found. Please register first.")
    
    # Save files
    license_filename = await file_service.save_file(license_file, f"license_{driver.id}")
    id_filename = await file_service.save_file(id_document_file, f"id_{driver.id}")
    
    # Update driver record
    driver.license_document = license_filename
    driver.id_document = id_filename
    driver.documents_submitted_at = datetime.utcnow()
    
    # Send to external API for approval
    response = await external_api_service.send_documents_for_approval_async(
        driver, license_filename, id_filename
    )
    
    # Record the approval attempt
    external_api_service.record_approval_attempt(db, driver.id, response)
    
    db.commit()
    
    return {
        "message": "Documents uploaded successfully and sent for approval",
        "license_document": license_filename,
        "id_document": id_filename,
        "external_api_status": response.get("message", "Unknown")
    }

@app.put("/drivers/location")
async def update_driver_location(
    location: schemas.DriverLocationUpdate,
    current_driver: DriverModel = Depends(get_current_driver),
    db: Session = Depends(get_db)
):
    """Update driver's current location"""
    current_driver.current_latitude = location.latitude
    current_driver.current_longitude = location.longitude
    current_driver.last_location_update = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Location updated successfully"}

@app.put("/drivers/status")
async def update_driver_status(
    status_update: schemas.DriverStatusUpdate,
    current_driver: DriverModel = Depends(get_current_driver),
    db: Session = Depends(get_db)
):
    """Update driver's availability status"""
    if current_driver.approval_status != ApprovalStatus.APPROVED:
        raise HTTPException(status_code=403, detail="Only approved drivers can change status")
    
    current_driver.status = status_update.status
    db.commit()
    
    return {"message": f"Status updated to {status_update.status}"}

@app.get("/drivers/me", response_model=schemas.Driver)
async def get_my_driver_profile(current_driver: DriverModel = Depends(get_current_driver)):
    """Get current driver's profile"""
    return current_driver

# Order management endpoints
@app.post("/orders", response_model=schemas.Order)
async def create_order(
    order: schemas.OrderCreate,
    current_store: UserModel = Depends(get_current_store),
    db: Session = Depends(get_db)
):
    """Create a new delivery order
    
    This endpoint creates a new delivery order and notifies available drivers in real-time.
    
    ## Flow
    1. Creates the order in the database
    2. Calculates the optimal route using OSRM
    3. Finds suitable drivers based on location and availability
    4. Sends real-time notifications to available drivers via WebSocket
    
    ## Notifications
    - Available drivers within the service area will receive a WebSocket notification
    - The first driver to accept the order will be assigned
    - Other drivers will receive a notification that the order was taken
    
    ## Response
    Returns the created order with estimated distance and duration
    
    ## Example Notification to Drivers
    ```json
    {
        "type": "order_notification",
        "data": {
            "order_id": 123,
            "pickup_address": "123 Main St",
            "delivery_address": "456 Oak Ave",
            "distance_km": 5.2,
            "estimated_duration_minutes": 15,
            "customer_name": "John Doe",
            "items_description": "2x Pizza, 1x Soda"
        }
    }
    """
    # Calculate estimated distance and duration
    pickup_location = (order.pickup_latitude, order.pickup_longitude)
    delivery_location = (order.delivery_latitude, order.delivery_longitude)
    
    route_info = osrm_client.get_distance_and_duration(pickup_location, delivery_location)
    
    # Create order
    db_order = OrderModel(
        **order.dict(),
        store_id=current_store.id,
        estimated_distance_km=route_info["distance_km"] if route_info else None,
        estimated_duration_minutes=route_info["duration_minutes"] if route_info else None
    )
    
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    
    # Find and notify suitable drivers
    suitable_drivers = assignment_service.get_drivers_for_notification(db, db_order)
    
    if suitable_drivers:
        # Create WebSocket notification
        order_notification = schemas.OrderNotificationWS(
            order_id=db_order.id,
            pickup_address=db_order.pickup_address,
            delivery_address=db_order.delivery_address,
            distance_km=route_info["distance_km"] if route_info else 0,
            estimated_duration_minutes=route_info["duration_minutes"] if route_info else None,
            customer_name=db_order.customer_name,
            items_description=db_order.items_description
        )
        
        # Notify drivers via WebSocket
        driver_ids = [d["driver_id"] for d in suitable_drivers]
        await manager.notify_drivers_about_order(driver_ids, order_notification)
    
    return db_order

@app.get("/orders", response_model=schemas.OrderListResponse)
async def get_orders(
    status: Optional[OrderStatus] = None,
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get orders (filtered by current user type)"""
    query = db.query(OrderModel)
    
    if current_user.user_type == UserType.STORE:
        query = query.filter(OrderModel.store_id == current_user.id)
    elif current_user.user_type == UserType.DRIVER:
        driver = db.query(DriverModel).filter(DriverModel.user_id == current_user.id).first()
        if driver:
            query = query.filter(OrderModel.driver_id == driver.id)
        else:
            return schemas.OrderListResponse(orders=[], total=0)
    
    if status:
        query = query.filter(Order.status == status)
    
    total = query.count()
    orders = query.offset(offset).limit(limit).all()
    
    return schemas.OrderListResponse(orders=orders, total=total)

@app.get("/orders/{order_id}", response_model=schemas.Order)
async def get_order(
    order_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific order details"""
    order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check permissions
    if current_user.user_type == UserType.STORE and order.store_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    elif current_user.user_type == UserType.DRIVER:
        driver = db.query(DriverModel).filter(DriverModel.user_id == current_user.id).first()
        if not driver or order.driver_id != driver.id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    return order

@app.post("/orders/{order_id}/accept")
async def accept_order(
    order_id: int,
    current_driver: DriverModel = Depends(get_current_driver),
    db: Session = Depends(get_db)
):
    """Accept a delivery order (first-come-first-served)"""
    if current_driver.approval_status != ApprovalStatus.APPROVED:
        raise HTTPException(status_code=403, detail="Only approved drivers can accept orders")
    
    if current_driver.status != DriverStatus.AVAILABLE:
        raise HTTPException(status_code=400, detail="Driver must be available to accept orders")
    
    # Try to assign order
    success = assignment_service.assign_order_to_first_accepter(db, order_id, current_driver.id)
    
    if success:
        # Notify the driver about successful assignment
        await manager.send_order_status_update(
            current_driver.id, 
            order_id, 
            "assigned",
            "Order assigned successfully"
        )
        
        return {"message": "Order accepted successfully"}
    else:
        return {"message": "Order no longer available"}

@app.post("/orders/{order_id}/reject")
async def reject_order(
    order_id: int,
    current_driver: DriverModel = Depends(get_current_driver),
    db: Session = Depends(get_db)
):
    """Reject a delivery order"""
    assignment_service.reject_order(db, order_id, current_driver.id)
    return {"message": "Order rejected"}

@app.put("/orders/{order_id}/status")
async def update_order_status(
    order_id: int,
    status_update: schemas.OrderStatusUpdate,
    current_driver: DriverModel = Depends(get_current_driver),
    db: Session = Depends(get_db)
):
    """Update order status (pickup, delivered, etc.)"""
    order = db.query(OrderModel).filter(
        OrderModel.id == order_id,
        OrderModel.driver_id == current_driver.id
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found or not assigned to you")
    
    old_status = order.status
    order.status = status_update.status
    
    # Update timestamps based on status
    now = datetime.utcnow()
    if status_update.status == OrderStatus.IN_PROGRESS:
        order.picked_up_at = now
    elif status_update.status == OrderStatus.DELIVERED:
        order.delivered_at = now
        # Driver becomes available again
        current_driver.status = DriverStatus.AVAILABLE
    
    db.commit()
    
    return {"message": f"Order status updated from {old_status} to {status_update.status}"}

# WebSocket endpoint for real-time notifications
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(..., description="JWT token for authentication")):
    """WebSocket endpoint for real-time driver notifications
    
    This endpoint establishes a persistent WebSocket connection for receiving real-time updates.
    
    ## Authentication
    - Requires a valid JWT token as a query parameter
    - The token must be from an active driver account
    
    ## Message Format (Server → Client)
    
    ### New Order Notification
    ```json
    {
        "type": "order_notification",
        "data": {
            "order_id": 123,
            "pickup_address": "123 Main St",
            "delivery_address": "456 Oak Ave",
            "distance_km": 5.2,
            "estimated_duration_minutes": 15,
            "customer_name": "John Doe",
            "items_description": "2x Pizza, 1x Soda"
        }
    }
    ```
    
    ### Order Status Update
    ```json
    {
        "type": "order_status_update",
        "data": {
            "order_id": 123,
            "status": "picked_up",
            "message": "Order has been picked up"
        }
    }
    ```
    
    ## Sending Messages (Client → Server)
    
    ### Accept Order
    ```json
    {
        "action": "accept_order",
        "order_id": 123
    }
    ```
    
    ### Reject Order
    ```json
    {
        "action": "reject_order",
        "order_id": 123,
        "reason": "Too far away"
    }
    ```
    
    ### Update Status
    ```json
    {
        "action": "update_status",
        "status": "available"
    }
    ```
    
    ## Error Responses
    
    ### Authentication Failed
    ```json
    {
        "type": "error",
        "code": "authentication_failed",
        "message": "Invalid or expired token"
    }
    ```
    
    ### Invalid Message Format
    ```json
    {
        "type": "error",
        "code": "invalid_message_format",
        "message": "Invalid message format"
    }
    """
    await handle_websocket_connection(websocket, token)

# External webhook endpoint for document approval
@app.post("/webhooks/approval")
async def approval_webhook(approval_data: dict, db: Session = Depends(get_db)):
    """Webhook to receive approval status from external service"""
    success = external_api_service.process_approval_webhook(db, approval_data)
    
    if success:
        return {"message": "Approval processed successfully"}
    else:
        raise HTTPException(status_code=400, detail="Failed to process approval")

# Statistics endpoints
@app.get("/stats/drivers")
async def get_driver_stats(
    current_driver: DriverModel = Depends(get_current_driver),
    db: Session = Depends(get_db)
):
    """Get driver statistics"""
    total_deliveries = db.query(OrderModel).filter(
        OrderModel.driver_id == current_driver.id,
        OrderModel.status == OrderStatus.DELIVERED
    ).count()
    
    pending_deliveries = db.query(OrderModel).filter(
        OrderModel.driver_id == current_driver.id,
        OrderModel.status.in_([OrderStatus.ASSIGNED.value, OrderStatus.IN_PROGRESS.value])
    ).count()
    
    return {
        "total_deliveries": total_deliveries,
        "pending_deliveries": pending_deliveries,
        "approval_status": current_driver.approval_status,
        "current_status": current_driver.status
    }

@app.get("/stats/orders")
async def get_order_stats(
    current_store: UserModel = Depends(get_current_store),
    db: Session = Depends(get_db)
):
    """Get order statistics for stores"""
    base_query = db.query(OrderModel).filter(OrderModel.store_id == current_store.id)
    
    stats = {
        "pending_orders": base_query.filter(OrderModel.status == OrderStatus.PENDING).count(),
        "assigned_orders": base_query.filter(OrderModel.status == OrderStatus.ASSIGNED).count(),
        "in_progress_orders": base_query.filter(OrderModel.status == OrderStatus.IN_PROGRESS).count(),
        "completed_orders": base_query.filter(OrderModel.status == OrderStatus.DELIVERED).count()
    }
    
    return stats

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

if __name__ == "__main__":
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=5000,
        reload=True
    )