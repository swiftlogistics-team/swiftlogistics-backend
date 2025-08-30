# start.sh - Start script
#!/bin/bash

echo "Starting SwiftLogistics Backend Server..."

# Activate virtual environment
source venv/bin/activate

# Start the server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# test_api.py - API testing script
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    response = requests.get(f"{BASE_URL}/health")
    print(f"Health check: {response.status_code} - {response.json()}")

def test_register_and_login():
    """Test user registration and login"""
    # Register a test client
    client_data = {
        "email": "test@client.com",
        "username": "testclient",
        "password": "password123",
        "user_type": "client"
    }
    
    response = requests.post(f"{BASE_URL}/auth/register", json=client_data)
    print(f"Registration: {response.status_code}")
    
    # Login
    login_data = {
        "email": "test@client.com",
        "password": "password123"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    if response.status_code == 200:
        token = response.json()["access_token"]
        print(f"Login successful, token: {token[:20]}...")
        return token
    else:
        print(f"Login failed: {response.status_code}")
        return None

def test_create_order(token):
    """Test order creation"""
    headers = {"Authorization": f"Bearer {token}"}
    
    order_data = {
        "pickup_address": "123 Warehouse Street, Colombo 01",
        "delivery_address": "456 Customer Lane, Kandy",
        "package_details": {
            "weight": "2.5kg",
            "dimensions": "30x20x15cm",
            "fragile": False,
            "value": 15000
        },
        "priority": "high"
    }
    
    response = requests.post(f"{BASE_URL}/orders", json=order_data, headers=headers)
    print(f"Order creation: {response.status_code}")
    
    if response.status_code == 200:
        order = response.json()
        print(f"Order created: {order['id']}")
        return order["id"]
    
    return None

def test_get_orders(token):
    """Test getting orders"""
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(f"{BASE_URL}/orders", headers=headers)
    print(f"Get orders: {response.status_code}")
    
    if response.status_code == 200:
        orders = response.json()
        print(f"Found {len(orders)} orders")
        for order in orders:
            print(f"  Order {order['id']}: {order['status']}")

def run_tests():
    """Run all tests"""
    print("=== SwiftLogistics API Tests ===")
    
    # Test health
    test_health()
    
    # Test authentication
    token = test_register_and_login()
    
    if token:
        # Test order operations
        order_id = test_create_order(token)
        test_get_orders(token)
    
    print("\n=== Tests Complete ===")

if __name__ == "__main__":
    run_tests()