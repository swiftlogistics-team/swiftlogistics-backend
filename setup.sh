# setup.sh - Setup script
#!/bin/bash

echo "Setting up SwiftLogistics Backend..."

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Start dependencies using Docker
echo "Starting dependencies..."
docker-compose up -d

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
sleep 10

# Run database migrations
echo "Setting up database..."
python -c "
from database import engine
from models import Base
Base.metadata.create_all(bind=engine)
print('Database tables created successfully!')
"

# Create initial admin user
echo "Creating initial admin user..."
python -c "
from sqlalchemy.orm import sessionmaker
from database import engine
from models import User
from auth import hash_password

SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

# Check if admin exists
admin = db.query(User).filter(User.email == 'admin@swiftlogistics.com').first()
if not admin:
    admin_user = User(
        email='admin@swiftlogistics.com',
        username='admin',
        hashed_password=hash_password('admin123'),
        user_type='admin'
    )
    db.add(admin_user)
    db.commit()
    print('Admin user created: admin@swiftlogistics.com / admin123')
else:
    print('Admin user already exists')

db.close()
"

echo "Setup complete! You can now start the server with: python main.py"