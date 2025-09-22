from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from models import Driver, Order, OrderNotification
from osrm_client import osrm_client
from config import MAX_DISTANCE_KM, MAX_DRIVERS_TO_NOTIFY
import config

class DriverAssignmentService:
    def __init__(self):
        self.osrm_client = osrm_client
    
    def find_available_drivers(self, db: Session, vehicle_type: str, pickup_location: Tuple[float, float]) -> List[dict]:
        """
        Find available drivers for an order based on vehicle type and location
        Returns list of driver info with distances
        """
        # Get available approved drivers with the required vehicle type
        from models import DriverStatus, ApprovalStatus, VehicleType
        drivers = db.query(Driver).filter(
            Driver.status == DriverStatus.AVAILABLE,
            Driver.approval_status == ApprovalStatus.APPROVED,
            Driver.vehicle_type == getattr(VehicleType, vehicle_type.upper()),
            Driver.current_latitude.is_not(None),
            Driver.current_longitude.is_not(None)
        ).all()
        
        if not drivers:
            return []
        
        # Prepare driver locations for distance calculation
        driver_locations = []
        for driver in drivers:
            if driver.current_latitude is not None and driver.current_longitude is not None:
                driver_locations.append((
                    float(driver.current_latitude),
                    float(driver.current_longitude), 
                    int(driver.id)
                ))
        
        # Calculate distances using OSRM
        distances = self.osrm_client.calculate_drivers_distances(pickup_location, driver_locations)
        
        # Filter by maximum distance and sort by distance
        suitable_drivers = []
        for distance_info in distances:
            if distance_info["distance_km"] <= MAX_DISTANCE_KM:
                # Get full driver info
                driver = next((d for d in drivers if d.id == distance_info["driver_id"]), None)
                if driver:
                    suitable_drivers.append({
                        "driver_id": driver.id,
                        "driver": driver,
                        "distance_km": distance_info["distance_km"],
                        "duration_minutes": distance_info["duration_minutes"]
                    })
        
        # Sort by distance (closest first) and limit to MAX_DRIVERS_TO_NOTIFY
        suitable_drivers.sort(key=lambda x: x["distance_km"])
        return suitable_drivers[:MAX_DRIVERS_TO_NOTIFY]
    
    def get_best_vehicle_type_for_order(self, weight_kg: Optional[float], value: Optional[float]) -> str:
        """
        Determine the best vehicle type based on order characteristics
        """
        if weight_kg is None:
            weight_kg = 1.0  # Default light weight
        
        if weight_kg <= 5:
            return "motorcycle"
        elif weight_kg <= 50:
            return "car"
        elif weight_kg <= 200:
            return "van"
        else:
            return "truck"
    
    def create_order_notifications(self, db: Session, order_id: int, driver_distances: List[dict]):
        """Create notification records for drivers"""
        for driver_info in driver_distances:
            notification = OrderNotification(
                order_id=order_id,
                driver_id=driver_info["driver_id"],
                distance_km=driver_info["distance_km"]
            )
            db.add(notification)
        db.commit()
    
    def assign_order_to_first_accepter(self, db: Session, order_id: int, driver_id: int) -> bool:
        """
        Assign order to the first driver who accepts with proper concurrency control
        Returns True if assignment successful, False if order already assigned
        """
        from models import OrderStatus, DriverStatus, ApprovalStatus
        from sqlalchemy import func
        from datetime import datetime
        
        try:
            # Use SELECT FOR UPDATE to prevent race conditions
            order = db.query(Order).filter(
                Order.id == order_id,
                Order.status == OrderStatus.PENDING
            ).with_for_update().first()
            
            if not order:
                return False
            
            # Check if driver is still available
            driver = db.query(Driver).filter(
                Driver.id == driver_id,
                Driver.status == DriverStatus.AVAILABLE,
                Driver.approval_status == ApprovalStatus.APPROVED
            ).with_for_update().first()
            
            if not driver:
                return False
            
            # Assign order atomically
            order.driver_id = driver_id
            order.status = OrderStatus.ASSIGNED
            order.assigned_at = datetime.utcnow()
            
            # Update driver status
            driver.status = DriverStatus.BUSY
            
            # Update the notification that this driver accepted
            notification = db.query(OrderNotification).filter(
                OrderNotification.order_id == order_id,
                OrderNotification.driver_id == driver_id
            ).first()
            
            if notification:
                notification.response = "accepted"
                notification.response_at = datetime.utcnow()
            
            # Mark other notifications as expired/rejected
            other_notifications = db.query(OrderNotification).filter(
                OrderNotification.order_id == order_id,
                OrderNotification.driver_id != driver_id,
                OrderNotification.response.is_(None)
            ).all()
            
            for notif in other_notifications:
                notif.response = "expired"
                notif.response_at = datetime.utcnow()
            
            db.commit()
            return True
            
        except Exception as e:
            db.rollback()
            print(f"Error assigning order: {e}")
            return False
    
    def reject_order(self, db: Session, order_id: int, driver_id: int):
        """Mark that a driver rejected an order"""
        from datetime import datetime
        
        notification = db.query(OrderNotification).filter(
            OrderNotification.order_id == order_id,
            OrderNotification.driver_id == driver_id
        ).first()
        
        if notification:
            notification.response = "rejected"
            notification.response_at = datetime.utcnow()
            db.commit()
    
    def get_drivers_for_notification(self, db: Session, order: Order) -> List[dict]:
        """
        Get list of drivers to notify for an order
        """
        pickup_location = (order.pickup_latitude, order.pickup_longitude)
        
        # Determine required vehicle type
        weight = float(order.weight_kg) if order.weight_kg is not None else None
        value = float(order.value) if order.value is not None else None
        vehicle_type = self.get_best_vehicle_type_for_order(weight, value)
        
        # Find available drivers
        suitable_drivers = self.find_available_drivers(db, vehicle_type, pickup_location)
        
        if suitable_drivers:
            # Create notification records
            self.create_order_notifications(db, int(order.id), suitable_drivers)
        
        return suitable_drivers

# Global assignment service instance
assignment_service = DriverAssignmentService()