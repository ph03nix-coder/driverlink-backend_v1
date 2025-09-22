import requests
import asyncio
from typing import Dict, Optional
from sqlalchemy.orm import Session
from models import Driver, DocumentApproval
from config import APPROVAL_API_URL, APPROVAL_API_KEY

class ExternalAPIService:
    def __init__(self):
        self.approval_api_url = APPROVAL_API_URL
        self.approval_api_key = APPROVAL_API_KEY
    
    def send_documents_for_approval(self, driver: Driver, license_path: str, id_document_path: str) -> Dict:
        """Send driver documents to external API for approval"""
        
        # Prepare data for external API
        payload = {
            "driver_id": driver.id,
            "driver_info": {
                "first_name": driver.first_name,
                "last_name": driver.last_name,
                "phone_number": driver.phone_number,
                "vehicle_type": str(driver.vehicle_type),
                "vehicle_plate": driver.vehicle_plate,
                "vehicle_model": driver.vehicle_model,
                "vehicle_year": driver.vehicle_year
            },
            "documents": {
                "license_document": license_path,
                "id_document": id_document_path
            }
        }
        
        headers = {
            "Authorization": f"Bearer {self.approval_api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(
                f"{self.approval_api_url}/validate-driver",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": "Documents sent successfully for approval",
                    "data": response.json()
                }
            else:
                return {
                    "success": False,
                    "message": f"API error: {response.status_code}",
                    "error": response.text
                }
                
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "message": "Failed to connect to approval service",
                "error": str(e)
            }
    
    async def send_documents_for_approval_async(self, driver: Driver, license_path: str, id_document_path: str) -> Dict:
        """Async version of send_documents_for_approval"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.send_documents_for_approval, driver, license_path, id_document_path)
    
    def record_approval_attempt(self, db: Session, driver_id: int, response: Dict):
        """Record the approval attempt in database"""
        approval_record = DocumentApproval(
            driver_id=driver_id,
            sent_to_external_api=True,
            external_api_response=str(response),
            sent_at=None  # Will be set by SQL
        )
        
        if response.get("success"):
            # If API call was successful, we can update based on response
            data = response.get("data", {})
            approval_record.license_approved = data.get("license_approved")
            approval_record.id_document_approved = data.get("id_document_approved")
            approval_record.notes = data.get("notes", "")
            approval_record.processed_at = None  # Will be set when we get final response
        else:
            approval_record.notes = response.get("message", "API call failed")
        
        db.add(approval_record)
        db.commit()
        
        return approval_record
    
    def process_approval_webhook(self, db: Session, webhook_data: Dict) -> bool:
        """Process webhook response from external approval service"""
        try:
            driver_id = webhook_data.get("driver_id")
            if not driver_id:
                return False
            
            # Update driver approval status
            driver = db.query(Driver).filter(Driver.id == driver_id).first()
            if not driver:
                return False
            
            # Update approval record
            approval_record = db.query(DocumentApproval).filter(
                DocumentApproval.driver_id == driver_id
            ).order_by(DocumentApproval.sent_at.desc()).first()
            
            if approval_record:
                approval_record.license_approved = webhook_data.get("license_approved", False)
                approval_record.id_document_approved = webhook_data.get("id_document_approved", False)
                approval_record.notes = webhook_data.get("notes", "")
                approval_record.processed_at = None  # Will be set by SQL
            
            # Update driver status based on approval
            license_ok = webhook_data.get("license_approved", False)
            id_ok = webhook_data.get("id_document_approved", False)
            
            if license_ok and id_ok:
                driver.approval_status = "approved"
            else:
                driver.approval_status = "rejected"
            
            db.commit()
            return True
            
        except Exception as e:
            print(f"Error processing approval webhook: {e}")
            db.rollback()
            return False

# Global external API service instance
external_api_service = ExternalAPIService()