# main.py - Main FastAPI application
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import json
import asyncio
from datetime import datetime, timedelta
import uuid
import os
from dotenv import load_dotenv

# Import our modules
from database import get_db, engine
from models import Base, User, Order, Package, Route, DeliveryUpdate
from schemas import (
    OrderCreate, OrderResponse, UserCreate, UserResponse, 
    PackageResponse, RouteResponse, DeliveryUpdateCreate,
    LoginRequest, TokenResponse
)
from auth import create_access_token, verify_token, get_current_user, hash_password, verify_password
from services import (
    cms_service, ros_service, wms_service, 
    message_broker, notification_service
)

load_dotenv()

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SwiftLogistics Middleware API",
    description="Backend middleware for SwiftLogistics delivery platform",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# WebSocket connection manager for real-time updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
    
    async def send_message(self, client_id: str, message: dict):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(json.dumps(message))
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections.values():
            await connection.send_text(json.dumps(message))

manager = ConnectionManager()

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

# Authentication endpoints
@app.post("/auth/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    hashed_password = hash_password(user_data.password)
    user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password,
        user_type=user_data.user_type
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        user_type=user.user_type
    )

@app.post("/auth/login", response_model=TokenResponse)
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user.email, "user_id": user.id})
    return TokenResponse(access_token=access_token, token_type="bearer")

# Order management endpoints
@app.post("/orders", response_model=OrderResponse)
async def create_order(
    order_data: OrderCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Create order in database
    order = Order(
        id=str(uuid.uuid4()),
        client_id=current_user.id,
        pickup_address=order_data.pickup_address,
        delivery_address=order_data.delivery_address,
        package_details=json.dumps(order_data.package_details),
        priority=order_data.priority,
        status="submitted"
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    
    # Process order asynchronously
    background_tasks.add_task(process_order, order.id, db)
    
    return OrderResponse(
        id=order.id,
        status=order.status,
        pickup_address=order.pickup_address,
        delivery_address=order.delivery_address,
        created_at=order.created_at
    )

@app.get("/orders", response_model=List[OrderResponse])
async def get_orders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.user_type == "client":
        orders = db.query(Order).filter(Order.client_id == current_user.id).all()
    else:  # driver can see assigned orders
        orders = db.query(Order).filter(Order.assigned_driver_id == current_user.id).all()
    
    return [
        OrderResponse(
            id=order.id,
            status=order.status,
            pickup_address=order.pickup_address,
            delivery_address=order.delivery_address,
            created_at=order.created_at
        ) for order in orders
    ]

@app.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check permission
    if current_user.user_type == "client" and order.client_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return OrderResponse(
        id=order.id,
        status=order.status,
        pickup_address=order.pickup_address,
        delivery_address=order.delivery_address,
        created_at=order.created_at
    )

# Driver endpoints
@app.post("/orders/{order_id}/update-status")
async def update_delivery_status(
    order_id: str,
    update_data: DeliveryUpdateCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.user_type != "driver":
        raise HTTPException(status_code=403, detail="Only drivers can update delivery status")
    
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Update order status
    order.status = update_data.status
    order.updated_at = datetime.utcnow()
    
    # Create delivery update record
    delivery_update = DeliveryUpdate(
        id=str(uuid.uuid4()),
        order_id=order_id,
        driver_id=current_user.id,
        status=update_data.status,
        notes=update_data.notes,
        location=update_data.location
    )
    
    db.add(delivery_update)
    db.commit()
    
    # Send real-time notification to client
    await manager.send_message(
        str(order.client_id),
        {
            "type": "delivery_update",
            "order_id": order_id,
            "status": update_data.status,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    
    # Notify WMS about status change
    await wms_service.update_package_status(order_id, update_data.status)
    
    return {"message": "Status updated successfully"}

@app.get("/driver/routes", response_model=List[RouteResponse])
async def get_driver_routes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.user_type != "driver":
        raise HTTPException(status_code=403, detail="Access denied")
    
    routes = db.query(Route).filter(Route.driver_id == current_user.id).all()
    return [
        RouteResponse(
            id=route.id,
            driver_id=route.driver_id,
            route_data=json.loads(route.route_data),
            status=route.status,
            created_at=route.created_at
        ) for route in routes
    ]

# WebSocket endpoint for real-time updates
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming WebSocket messages if needed
            await manager.send_message(client_id, {"echo": data})
    except WebSocketDisconnect:
        manager.disconnect(client_id)

# Background task for order processing
async def process_order(order_id: str, db: Session):
    """Process order through CMS, WMS, and ROS systems"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return
    
    try:
        # 1. Submit to CMS (Client Management System)
        cms_response = await cms_service.submit_order({
            "order_id": order_id,
            "client_id": order.client_id,
            "pickup_address": order.pickup_address,
            "delivery_address": order.delivery_address
        })
        
        # 2. Add to WMS (Warehouse Management System)
        wms_response = await wms_service.add_package({
            "order_id": order_id,
            "package_details": json.loads(order.package_details)
        })
        
        # 3. Add to ROS (Route Optimization System)
        ros_response = await ros_service.add_delivery_point({
            "order_id": order_id,
            "delivery_address": order.delivery_address,
            "priority": order.priority
        })
        
        # Update order status
        order.status = "processing"
        order.cms_reference = cms_response.get("reference_id")
        order.wms_reference = wms_response.get("package_id")
        order.ros_reference = ros_response.get("route_point_id")
        
        db.commit()
        
        # Send notification via message broker
        await message_broker.publish_message("order.processed", {
            "order_id": order_id,
            "status": "processing"
        })
        
    except Exception as e:
        # Handle transaction failure
        order.status = "failed"
        order.error_message = str(e)
        db.commit()
        
        # Send failure notification
        await message_broker.publish_message("order.failed", {
            "order_id": order_id,
            "error": str(e)
        })

# Admin endpoints
@app.get("/admin/stats")
async def get_admin_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.user_type != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    total_orders = db.query(Order).count()
    pending_orders = db.query(Order).filter(Order.status == "submitted").count()
    delivered_orders = db.query(Order).filter(Order.status == "delivered").count()
    
    return {
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "delivered_orders": delivered_orders,
        "delivery_rate": (delivered_orders / total_orders * 100) if total_orders > 0 else 0
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)