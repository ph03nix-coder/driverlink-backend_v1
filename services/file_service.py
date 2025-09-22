import os
import uuid
import filetype
from fastapi import UploadFile, HTTPException
from typing import Optional, Tuple
from config import UPLOAD_DIR, MAX_FILE_SIZE, ALLOWED_DOCUMENT_TYPES

class FileService:
    def __init__(self):
        self.upload_dir = UPLOAD_DIR
        os.makedirs(self.upload_dir, exist_ok=True)
        
    def validate_file(self, file: UploadFile) -> bool:
        """Validate uploaded file"""
        # Check file size
        if file.size and file.size > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail=f"File too large. Maximum size is {MAX_FILE_SIZE / (1024*1024):.1f}MB")
        
        # Check file extension
        if file.filename:
            ext = os.path.splitext(file.filename)[1].lower()
            if ext not in ALLOWED_DOCUMENT_TYPES:
                raise HTTPException(status_code=400, detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_DOCUMENT_TYPES)}")
        
        return True
    
    async def save_file(self, file: UploadFile, prefix: str = "") -> str:
        """Save uploaded file and return the file path"""
        self.validate_file(file)
        
        # Generate unique filename
        file_extension = os.path.splitext(file.filename or "")[1].lower()
        unique_filename = f"{prefix}_{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(self.upload_dir, unique_filename)
        
        # Save file
        try:
            content = await file.read()
            
            # Additional validation using file content
            kind = filetype.guess(content)
            if kind is None and file_extension not in ['.pdf']:
                raise HTTPException(status_code=400, detail="Could not determine file type")
            
            # For images, validate that it's actually an image
            if file_extension in ['.jpg', '.jpeg', '.png'] and kind is not None:
                if not kind.mime.startswith('image/'):
                    raise HTTPException(status_code=400, detail="File is not a valid image")
            
            with open(file_path, 'wb') as f:
                f.write(content)
            
            return unique_filename
            
        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")
    
    def delete_file(self, filename: str) -> bool:
        """Delete a file"""
        try:
            file_path = os.path.join(self.upload_dir, filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception:
            return False
    
    def get_file_path(self, filename: str) -> str:
        """Get absolute path to file"""
        return os.path.join(self.upload_dir, filename)
    
    def file_exists(self, filename: str) -> bool:
        """Check if file exists"""
        file_path = os.path.join(self.upload_dir, filename)
        return os.path.exists(file_path)

# Global file service instance
file_service = FileService()