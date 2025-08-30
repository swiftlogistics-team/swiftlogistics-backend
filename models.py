# models.py - SQLAlchemy models
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum
from sqlalchemy.relationship import relationship
from datetime import datetime
import enum

class UserType(enum.Enum):
    client = "client"
    driver = "driver"
    admin = "admin"

class OrderStatus(enum.Enum):
    submitted = "submitted"
    processing = "processing"
    in_warehouse = "in_warehouse"
    out_for_delivery = "out_for_delivery"
    delivered = "delivered"
    failed = "failed"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    username = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(255))
    user_type = Column(Enum(UserType))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    orders = relationship("Order", back_populates="client")
    assigned_orders = relationship("Order", foreign_keys="Order.assigned_driver_id", back_populates="driver")

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(String(36), primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("users.id"))
    assigned_driver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    pickup_address = Column(Text)
    delivery_address = Column(Text)
    package_details = Column(Text)  # JSON string
    priority = Column(String(20), default="normal")
    status = Column(Enum(OrderStatus), default=OrderStatus.submitted)
    
    # External system references
    cms_reference = Column(String(100), nullable=True)
    wms_reference = Column(String(100), nullable=True)
    ros_reference = Column(String(100), nullable=True)
    
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    client = relationship("User", foreign_keys=[client_id], back_populates="orders")
    driver = relationship("User", foreign_keys=[assigned_driver_id], back_populates="assigned_orders")
    packages = relationship("Package", back_populates="order")
    delivery_updates = relationship("DeliveryUpdate", back_populates="order")

class Package(Base):
    __tablename__ = "packages"
    
    id = Column(String(36), primary_key=True, index=True)
    order_id = Column(String(36), ForeignKey("orders.id"))
    wms_package_id = Column(String(100))
    weight = Column(String(20))
    dimensions = Column(String(100))
    status = Column(String(50), default="received")
    warehouse_location = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    order = relationship("Order", back_populates="packages")

class Route(Base):
    __tablename__ = "routes"
    
    id = Column(String(36), primary_key=True, index=True)
    driver_id = Column(Integer, ForeignKey("users.id"))
    route_data = Column(Text)  # JSON string containing route information
    status = Column(String(50), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DeliveryUpdate(Base):
    __tablename__ = "delivery_updates"
    
    id = Column(String(36), primary_key=True, index=True)
    order_id = Column(String(36), ForeignKey("orders.id"))
    driver_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String(50))
    notes = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)
    proof_of_delivery = Column(String(500), nullable=True)  # File path or URL
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    order = relationship("Order", back_populates="delivery_updates")