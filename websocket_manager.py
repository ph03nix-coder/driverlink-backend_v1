import json
import asyncio
from typing import Dict, List, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from models import Driver, User
from schemas import OrderNotificationWS
from auth import verify_token
from database import SessionLocal

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}  # driver_id: websocket
        self.driver_connections: Dict[WebSocket, int] = {}  # websocket: driver_id
        
    async def connect(self, websocket: WebSocket, driver_id: int):
        """Accept a WebSocket connection for a driver"""
        await websocket.accept()
        self.active_connections[driver_id] = websocket
        self.driver_connections[websocket] = driver_id
        print(f"Driver {driver_id} connected via WebSocket")
        
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if websocket in self.driver_connections:
            driver_id = self.driver_connections[websocket]
            del self.active_connections[driver_id]
            del self.driver_connections[websocket]
            print(f"Driver {driver_id} disconnected from WebSocket")
    
    async def send_personal_message(self, message: dict, driver_id: int):
        """Send a message to a specific driver"""
        if driver_id in self.active_connections:
            websocket = self.active_connections[driver_id]
            try:
                await websocket.send_text(json.dumps(message))
                return True
            except Exception as e:
                print(f"Error sending message to driver {driver_id}: {e}")
                # Remove the connection if it's broken
                self.disconnect(websocket)
                return False
        return False
    
    async def notify_drivers_about_order(self, driver_ids: List[int], order_notification: OrderNotificationWS):
        """Notify multiple drivers about a new order"""
        successful_notifications = []
        
        message = {
            "type": "order_notification",
            "data": order_notification.dict()
        }
        
        for driver_id in driver_ids:
            success = await self.send_personal_message(message, driver_id)
            if success:
                successful_notifications.append(driver_id)
        
        return successful_notifications
    
    async def send_order_status_update(self, driver_id: int, order_id: int, status: str, message: str = ""):
        """Send order status update to a driver"""
        message_data = {
            "type": "order_status_update",
            "data": {
                "order_id": order_id,
                "status": status,
                "message": message
            }
        }
        return await self.send_personal_message(message_data, driver_id)
    
    async def broadcast_to_available_drivers(self, message: dict, driver_ids: List[int] = None):
        """Broadcast a message to all available drivers or specific driver list"""
        if driver_ids is None:
            # Send to all connected drivers
            target_drivers = list(self.active_connections.keys())
        else:
            target_drivers = driver_ids
        
        successful_sends = []
        for driver_id in target_drivers:
            success = await self.send_personal_message(message, driver_id)
            if success:
                successful_sends.append(driver_id)
        
        return successful_sends
    
    def get_connected_drivers(self) -> List[int]:
        """Get list of currently connected driver IDs"""
        return list(self.active_connections.keys())
    
    def is_driver_connected(self, driver_id: int) -> bool:
        """Check if a driver is currently connected"""
        return driver_id in self.active_connections

# Global connection manager instance
manager = ConnectionManager()

async def authenticate_websocket(websocket: WebSocket, token: str) -> Optional[int]:
    """Authenticate WebSocket connection and return driver_id"""
    try:
        # Verify JWT token
        email = verify_token(token)
        if not email:
            await websocket.close(code=1008, reason="Invalid token")
            return None
        
        # Get user and driver information
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == email).first()
            if not user or not bool(user.is_active):
                await websocket.close(code=1008, reason="User not found or inactive")
                return None
            
            if str(user.user_type) != "driver":
                await websocket.close(code=1008, reason="Only drivers can connect via WebSocket")
                return None
            
            driver = db.query(Driver).filter(Driver.user_id == user.id).first()
            if not driver or str(driver.approval_status) != "approved":
                await websocket.close(code=1008, reason="Driver not approved")
                return None
            
            return int(driver.id)
            
        finally:
            db.close()
    
    except Exception as e:
        print(f"WebSocket authentication error: {e}")
        await websocket.close(code=1011, reason="Authentication error")
        return None

async def handle_websocket_connection(websocket: WebSocket, token: str):
    """Handle a WebSocket connection lifecycle"""
    driver_id = await authenticate_websocket(websocket, token)
    
    if driver_id is None:
        return
    
    await manager.connect(websocket, driver_id)
    
    try:
        while True:
            # Listen for messages from the driver
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            await handle_driver_message(driver_id, message)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error for driver {driver_id}: {e}")
        manager.disconnect(websocket)

async def handle_driver_message(driver_id: int, message: dict):
    """Handle messages sent by drivers through WebSocket"""
    message_type = message.get("type")
    
    if message_type == "order_response":
        # Handle order acceptance/rejection
        await handle_order_response(driver_id, message.get("data", {}))
    elif message_type == "status_update":
        # Handle driver status updates
        await handle_driver_status_update(driver_id, message.get("data", {}))
    elif message_type == "location_update":
        # Handle location updates
        await handle_location_update(driver_id, message.get("data", {}))

async def handle_order_response(driver_id: int, data: dict):
    """Handle order acceptance or rejection from driver"""
    # This will be implemented in the main application logic
    # For now, just log the response
    print(f"Driver {driver_id} responded to order: {data}")

async def handle_driver_status_update(driver_id: int, data: dict):
    """Handle driver status updates"""
    # This will be implemented in the main application logic
    print(f"Driver {driver_id} status update: {data}")

async def handle_location_update(driver_id: int, data: dict):
    """Handle driver location updates"""
    # This will be implemented in the main application logic
    print(f"Driver {driver_id} location update: {data}")