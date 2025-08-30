# services.py - External system integrations
import aiohttp
import json
import xml.etree.ElementTree as ET
from typing import Dict, Any
import asyncio
import socket
import pika
import threading
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class CMSService:
    """Client Management System (SOAP/XML) integration"""
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
    
    async def submit_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit order to CMS via SOAP"""
        soap_body = f"""
        <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
            <soap:Body>
                <SubmitOrder xmlns="http://cms.swiftlogistics.com/">
                    <OrderId>{order_data['order_id']}</OrderId>
                    <ClientId>{order_data['client_id']}</ClientId>
                    <PickupAddress>{order_data['pickup_address']}</PickupAddress>
                    <DeliveryAddress>{order_data['delivery_address']}</DeliveryAddress>
                </SubmitOrder>
            </soap:Body>
        </soap:Envelope>
        """
        
        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': 'http://cms.swiftlogistics.com/SubmitOrder'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/soap",
                    data=soap_body,
                    headers=headers,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        xml_response = await response.text()
                        # Parse XML response
                        root = ET.fromstring(xml_response)
                        reference_id = root.find('.//ReferenceId')
                        return {
                            "reference_id": reference_id.text if reference_id is not None else f"CMS_{order_data['order_id']}",
                            "status": "submitted"
                        }
                    else:
                        raise Exception(f"CMS error: {response.status}")
        except Exception as e:
            # Mock response for development
            print(f"CMS Service Error: {e}")
            return {
                "reference_id": f"CMS_MOCK_{order_data['order_id']}",
                "status": "submitted"
            }
    
    async def get_order_status(self, reference_id: str) -> Dict[str, Any]:
        """Get order status from CMS"""
        # Mock implementation
        return {
            "reference_id": reference_id,
            "status": "processed",
            "billing_status": "invoiced"
        }

class ROSService:
    """Route Optimization System (REST/JSON) integration"""
    
    def __init__(self, base_url: str = "http://localhost:8002"):
        self.base_url = base_url
        self.api_key = "demo_api_key"  # Should be in environment variables
    
    async def add_delivery_point(self, delivery_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add delivery point to route optimization"""
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        
        payload = {
            'delivery_id': delivery_data['order_id'],
            'address': delivery_data['delivery_address'],
            'priority': delivery_data['priority'],
            'time_window': '09:00-18:00',
            'service_time': 5  # minutes
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/v1/delivery-points",
                    json=payload,
                    headers=headers,
                    timeout=30
                ) as response:
                    if response.status == 201:
                        result = await response.json()
                        return {
                            "route_point_id": result.get('id', f"ROS_{delivery_data['order_id']}"),
                            "estimated_delivery_time": result.get('estimated_time'),
                            "route_sequence": result.get('sequence')
                        }
                    else:
                        raise Exception(f"ROS error: {response.status}")
        except Exception as e:
            # Mock response for development
            print(f"ROS Service Error: {e}")
            return {
                "route_point_id": f"ROS_MOCK_{delivery_data['order_id']}",
                "estimated_delivery_time": "14:00",
                "route_sequence": 1
            }
    
    async def get_optimized_route(self, driver_id: int) -> Dict[str, Any]:
        """Get optimized route for driver"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/v1/routes/driver/{driver_id}",
                    headers={'Authorization': f'Bearer {self.api_key}'},
                    timeout=30
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        raise Exception(f"ROS error: {response.status}")
        except Exception as e:
            # Mock response for development
            print(f"ROS Service Error: {e}")
            return {
                "driver_id": driver_id,
                "route": [
                    {
                        "sequence": 1,
                        "address": "123 Main St, Colombo",
                        "estimated_time": "10:30",
                        "order_id": "mock_order_1"
                    }
                ],
                "total_distance": 25.5,
                "estimated_duration": 120
            }

class WMSService:
    """Warehouse Management System (TCP/IP) integration"""
    
    def __init__(self, host: str = "localhost", port: int = 8003):
        self.host = host
        self.port = port
    
    async def add_package(self, package_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add package to warehouse system"""
        message = {
            "action": "ADD_PACKAGE",
            "order_id": package_data['order_id'],
            "package_details": package_data['package_details'],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            # Simulate TCP/IP communication
            response = await self._send_tcp_message(json.dumps(message))
            return json.loads(response)
        except Exception as e:
            # Mock response for development
            print(f"WMS Service Error: {e}")
            return {
                "package_id": f"WMS_MOCK_{package_data['order_id']}",
                "warehouse_location": "A-01-15",
                "status": "received"
            }
    
    async def update_package_status(self, order_id: str, status: str) -> Dict[str, Any]:
        """Update package status in warehouse"""
        message = {
            "action": "UPDATE_STATUS",
            "order_id": order_id,
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            response = await self._send_tcp_message(json.dumps(message))
            return json.loads(response)
        except Exception as e:
            # Mock response for development
            print(f"WMS Service Error: {e}")
            return {
                "order_id": order_id,
                "status": status,
                "updated": True
            }
    
    async def _send_tcp_message(self, message: str) -> str:
        """Send message via TCP/IP"""
        try:
            reader, writer = await asyncio.open_connection(self.host, self.port)
            writer.write(message.encode())
            await writer.drain()
            
            data = await reader.read(1024)
            writer.close()
            await writer.wait_closed()
            
            return data.decode()
        except Exception as e:
            raise Exception(f"TCP communication failed: {e}")

class MessageBroker:
    """RabbitMQ message broker for asynchronous communication"""
    
    def __init__(self, host: str = "localhost", port: int = 5672):
        self.host = host
        self.port = port
        self.credentials = pika.PlainCredentials(
            os.getenv('RABBITMQ_USER', 'guest'),
            os.getenv('RABBITMQ_PASS', 'guest')
        )
        self.connection = None
        self.channel = None
        self._setup_connection()
    
    def _setup_connection(self):
        """Setup RabbitMQ connection"""
        try:
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=self.host,
                    port=self.port,
                    credentials=self.credentials,
                    heartbeat=600
                )
            )
            self.channel = self.connection.channel()
            
            # Declare exchanges and queues
            self.channel.exchange_declare(exchange='swiftlogistics', exchange_type='topic', durable=True)
            
            # Declare queues
            queues = ['order.submitted', 'order.processed', 'order.failed', 'delivery.updated']
            for queue in queues:
                self.channel.queue_declare(queue=queue, durable=True)
                self.channel.queue_bind(exchange='swiftlogistics', queue=queue, routing_key=queue)
            
        except Exception as e:
            print(f"RabbitMQ connection failed: {e}")
            self.connection = None
            self.channel = None
    
    async def publish_message(self, routing_key: str, message: Dict[str, Any]):
        """Publish message to RabbitMQ"""
        if not self.channel:
            print("RabbitMQ not connected - message not sent")
            return
        
        try:
            self.channel.basic_publish(
                exchange='swiftlogistics',
                routing_key=routing_key,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    timestamp=int(datetime.utcnow().timestamp())
                )
            )
            print(f"Message published to {routing_key}: {message}")
        except Exception as e:
            print(f"Failed to publish message: {e}")
    
    def start_consumer(self, queue: str, callback):
        """Start consuming messages from queue"""
        if not self.channel:
            print("RabbitMQ not connected - cannot start consumer")
            return
        
        def wrapper(ch, method, properties, body):
            try:
                message = json.loads(body.decode())
                callback(message)
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                print(f"Error processing message: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        
        self.channel.basic_consume(queue=queue, on_message_callback=wrapper)
        print(f"Started consuming from {queue}")
        
        # Start consuming in a separate thread
        def consume():
            self.channel.start_consuming()
        
        consumer_thread = threading.Thread(target=consume)
        consumer_thread.daemon = True
        consumer_thread.start()
    
    def close_connection(self):
        """Close RabbitMQ connection"""
        if self.connection and not self.connection.is_closed:
            self.connection.close()

class NotificationService:
    """Service for sending notifications"""
    
    def __init__(self):
        pass
    
    async def send_email(self, to: str, subject: str, body: str):
        """Send email notification"""
        # Mock implementation - integrate with email service
        print(f"Email sent to {to}: {subject}")
        return True
    
    async def send_sms(self, phone: str, message: str):
        """Send SMS notification"""
        # Mock implementation - integrate with SMS service
        print(f"SMS sent to {phone}: {message}")
        return True
    
    async def send_push_notification(self, user_id: str, title: str, message: str):
        """Send push notification"""
        # Mock implementation - integrate with push notification service
        print(f"Push notification sent to {user_id}: {title} - {message}")
        return True

# Service instances
cms_service = CMSService()
ros_service = ROSService()
wms_service = WMSService()
message_broker = MessageBroker()
notification_service = NotificationService()

# Message handlers
def handle_order_processed(message: Dict[str, Any]):
    """Handle order processed event"""
    print(f"Order processed: {message}")
    # Send notification to client
    asyncio.create_task(
        notification_service.send_email(
            "client@example.com",
            "Order Processed",
            f"Your order {message['order_id']} is being processed."
        )
    )

def handle_delivery_updated(message: Dict[str, Any]):
    """Handle delivery update event"""
    print(f"Delivery updated: {message}")
    # Send real-time update to client

# Start message consumers
message_broker.start_consumer('order.processed', handle_order_processed)
message_broker.start_consumer('delivery.updated', handle_delivery_updated)