from app.database import SessionLocal, engine
from app import models
from app.models import Product

# 🔹 Create all tables in the database
models.Base.metadata.create_all(bind=engine)

# 🔹 Create DB session
db = SessionLocal()

# 🔹 Seed sample products
products = [
    Product(name="Pen", stock=100, price=10, tax=5),
    Product(name="Book", stock=50, price=50, tax=12),
    Product(name="Bag", stock=20, price=500, tax=18)
]

db.add_all(products)
db.commit()

print("✅ Products inserted successfully!")