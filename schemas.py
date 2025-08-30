# schemas.py - Pydantic schemas for API
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any, List
from datetime import datetime

# User schemas
class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    user_type: str

class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    user_type: str
    
    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

# Order schemas
class OrderCreate(BaseModel):
    pickup_address: str
    delivery_address: str
    package_details: Dict[str, Any]
    priority: str = "normal"

class OrderResponse(BaseModel):
    id: str
    status: str
    pickup_address: str
    delivery_address: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# Package schemas
class PackageResponse(BaseModel):
    id: str
    wms_package_id: str
    weight: str
    dimensions: str
    status: str
    
    class Config:
        from_attributes = True

# Route schemas
class RouteResponse(BaseModel):
    id: str
    driver_id: int
    route_data: Dict[str, Any]
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# Delivery update schemas
class DeliveryUpdateCreate(BaseModel):
    status: str
    notes: Optional[str] = None
    location: Optional[str] = None
    proof_of_delivery: Optional[str] = None

class DeliveryUpdateResponse(BaseModel):
    id: str
    order_id: str
    driver_id: int
    status: str
    notes: Optional[str]
    location: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True