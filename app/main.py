import os
import datetime
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime, event, inspect, text
from sqlalchemy.orm import Session, sessionmaker, declarative_base, relationship

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./barbot.db")

# Render/Heroku dynamic postgres protocol replacement
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

# Enable foreign keys for SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Pydantic schemas
class Product(BaseModel):
    id: int
    name: str
    volumeInfo: Optional[str] = None
    price: float
    providerName: str
    category: str

class CartItem(BaseModel):
    productId: int
    quantity: int

class CheckoutResponse(BaseModel):
    order_id: int
    status: str
    total_price: float

# SQLAlchemy models
class ProductDB(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    volume_info = Column(String, nullable=True)
    price = Column(Float, nullable=False)
    provider_name = Column(String, nullable=False)
    category = Column(String, nullable=False, default="Other")

class OrderDB(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    total_price = Column(Float, nullable=False)
    status = Column(String, default="pending", nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    
    items = relationship("OrderItemDB", back_populates="order", cascade="all, delete-orphan")

class OrderItemDB(Base):
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    
    order = relationship("OrderDB", back_populates="items")

# Non-destructive migration: add category column if missing
inspector = inspect(engine)
if inspector.has_table("products"):
    columns = [c['name'] for c in inspector.get_columns('products')]
    if 'category' not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE products ADD COLUMN category VARCHAR NOT NULL DEFAULT 'Other'"))

# Create tables (no-op for tables that already exist)
Base.metadata.create_all(bind=engine)

# In-memory definitions for initial seeding
INITIAL_PRODUCTS = [
    Product(id=1, name="Jack Daniel's Tennessee Whiskey", volumeInfo="1.0L", price=29.99, providerName="AlcoTrade Global", category="Whiskey"),
    Product(id=2, name="Jameson Irish Whiskey", volumeInfo="0.7L", price=24.99, providerName="AlcoTrade Global", category="Whiskey"),
    Product(id=3, name="Grey Goose Vodka", volumeInfo="1.0L", price=39.99, providerName="AlcoTrade Global", category="Vodka"),
    Product(id=4, name="Hendrick's Gin", volumeInfo="0.7L", price=34.99, providerName="Premium Spirits Ltd", category="Gin"),
    Product(id=5, name="Bombay Sapphire Gin", volumeInfo="1.0L", price=27.99, providerName="Premium Spirits Ltd", category="Gin"),
    Product(id=6, name="Patrón Silver Tequila", volumeInfo="0.75L", price=45.99, providerName="Premium Spirits Ltd", category="Tequila"),
    Product(id=7, name="Bacardi Carta Blanca Rum", volumeInfo="1.0L", price=19.99, providerName="Bacardi-Martini Group", category="Rum"),
    Product(id=8, name="Campari Bitter", volumeInfo="1.0L", price=22.99, providerName="Milano Imports", category="Liqueurs"),
    Product(id=9, name="Aperol Aperitivo", volumeInfo="1.0L", price=18.99, providerName="Milano Imports", category="Liqueurs"),
    Product(id=10, name="Cointreau Liqueur", volumeInfo="0.7L", price=26.99, providerName="Milano Imports", category="Liqueurs"),
    Product(id=11, name="Coca-Cola Classic", volumeInfo="0.33L", price=2.50, providerName="SoftBeverage Co", category="Soft Drinks"),
    Product(id=12, name="Still Mineral Water", volumeInfo="0.5L", price=1.50, providerName="SoftBeverage Co", category="Soft Drinks"),
    Product(id=13, name="Virgin Mojito Mocktail", volumeInfo="0.4L", price=6.50, providerName="BarBot Signature", category="Mocktails"),
    Product(id=14, name="Lavazza Super Cream Beans", volumeInfo="1.0kg", price=18.50, providerName="Coffee & Tea Co", category="Coffee"),
    Product(id=15, name="UHT Barista Milk 3.2%", volumeInfo="1.0L", price=2.20, providerName="Dairy Fields", category="Milk"),
    Product(id=16, name="Monin Vanilla Syrup", volumeInfo="0.7L", price=9.99, providerName="Premium Spirits Ltd", category="Syrups"),
    Product(id=17, name="Monin Caramel Syrup", volumeInfo="0.7L", price=9.99, providerName="Premium Spirits Ltd", category="Syrups"),
    Product(id=18, name="Chardonnay White Wine", volumeInfo="0.75L", price=14.50, providerName="Milano Imports", category="Wine"),
    Product(id=19, name="Cabernet Sauvignon Red Wine", volumeInfo="0.75L", price=16.00, providerName="Milano Imports", category="Wine"),
    Product(id=20, name="Cocktail Ice Cubes (Bag)", volumeInfo="5.0kg", price=4.50, providerName="IceCold Logistics", category="Ice"),
    Product(id=21, name="Crushed Ice (Bag)", volumeInfo="5.0kg", price=5.00, providerName="IceCold Logistics", category="Ice"),
    Product(id=22, name="Corona Extra Beer Case", volumeInfo="24x0.33L", price=32.99, providerName="AlcoTrade Global", category="Beer"),
    Product(id=23, name="Heineken Premium Lager", volumeInfo="0.5L", price=2.80, providerName="AlcoTrade Global", category="Beer"),
    Product(id=24, name="Aberfeldy 12YO Single Malt", volumeInfo="0.7L", price=49.99, providerName="Forester.kg", category="Whiskey"),
    Product(id=25, name="Ardbeg 10YO Single Malt", volumeInfo="0.7L", price=59.99, providerName="Forester.kg", category="Whiskey"),
    Product(id=26, name="Beluga Noble Russian Vodka", volumeInfo="1.0L", price=34.99, providerName="Forester.kg", category="Vodka"),
    Product(id=27, name="Belvedere Pure Vodka", volumeInfo="0.7L", price=39.99, providerName="Forester.kg", category="Vodka"),
    Product(id=28, name="Dewar's White Label", volumeInfo="1.0L", price=19.99, providerName="Forester.kg", category="Whiskey"),
    Product(id=29, name="Espolón Tequila Blanco", volumeInfo="0.75L", price=29.99, providerName="Forester.kg", category="Tequila"),
    Product(id=30, name="Finlandia Classic Vodka", volumeInfo="1.0L", price=17.99, providerName="Forester.kg", category="Vodka"),
    Product(id=31, name="Glenfiddich 12YO Single Malt", volumeInfo="0.7L", price=44.99, providerName="Forester.kg", category="Whiskey"),
    Product(id=32, name="Glenmorangie The Original", volumeInfo="0.7L", price=47.99, providerName="Forester.kg", category="Whiskey"),
    Product(id=33, name="Hennessy VS Cognac", volumeInfo="0.7L", price=54.99, providerName="Forester.kg", category="Liqueurs"),
    Product(id=34, name="Jägermeister Liqueur", volumeInfo="1.0L", price=23.99, providerName="Forester.kg", category="Liqueurs"),
    Product(id=35, name="Jim Beam Bourbon", volumeInfo="1.0L", price=18.99, providerName="Forester.kg", category="Whiskey"),
    Product(id=36, name="Wild Turkey 81 Bourbon", volumeInfo="0.7L", price=22.99, providerName="Forester.kg", category="Whiskey"),
    Product(id=37, name="Woodford Reserve Bourbon", volumeInfo="0.7L", price=38.99, providerName="Forester.kg", category="Whiskey"),
    Product(id=38, name="Moët & Chandon Brut Imperial", volumeInfo="0.75L", price=59.99, providerName="Forester.kg", category="Wine"),
    Product(id=39, name="Carlsberg Pilsner", volumeInfo="0.5L", price=2.50, providerName="Forester.kg", category="Beer"),
    Product(id=40, name="Guinness Extra Stout", volumeInfo="0.45L", price=3.50, providerName="Forester.kg", category="Beer"),
    Product(id=41, name="Stella Artois Lager", volumeInfo="0.5L", price=2.80, providerName="Forester.kg", category="Beer"),
    Product(id=42, name="Martini Bianco Vermouth", volumeInfo="1.0L", price=15.99, providerName="Forester.kg", category="Wine"),
    Product(id=43, name="Santo Stefano Bianco", volumeInfo="0.75L", price=6.99, providerName="Forester.kg", category="Wine")
]

# Build a lookup for updating existing rows after ALTER TABLE migration
_CATEGORY_BY_ID = {p.id: p.category for p in INITIAL_PRODUCTS}

# Update existing products that still have the default 'Other' category after migration
if inspector.has_table("products"):
    with engine.begin() as conn:
        for pid, cat in _CATEGORY_BY_ID.items():
            conn.execute(
                text("UPDATE products SET category = :cat WHERE id = :pid AND category = 'Other'"),
                {"cat": cat, "pid": pid},
            )


# Dependency: DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Lifespan: seed data on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: seed missing products individually
    db = SessionLocal()
    try:
        for p in INITIAL_PRODUCTS:
            exists = db.query(ProductDB).filter(ProductDB.id == p.id).first()
            if not exists:
                db_p = ProductDB(
                    id=p.id,
                    name=p.name,
                    volume_info=p.volumeInfo,
                    price=p.price,
                    provider_name=p.providerName,
                    category=p.category,
                )
                db.add(db_p)
        db.commit()
    finally:
        db.close()
    yield

    # Shutdown: nothing to clean up


app = FastAPI(lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/products", response_model=List[Product])
def get_products(db: Session = Depends(get_db)):
    db_products = db.query(ProductDB).all()
    return [
        Product(
            id=p.id,
            name=p.name,
            volumeInfo=p.volume_info,
            price=p.price,
            providerName=p.provider_name,
            category=p.category,
        )
        for p in db_products
    ]


@app.post("/checkout", response_model=CheckoutResponse)
def checkout(items: List[CartItem], db: Session = Depends(get_db)):
    total = 0.0
    # Calculate total price using database product prices
    for item in items:
        prod = db.query(ProductDB).filter(ProductDB.id == item.productId).first()
        if not prod:
            raise HTTPException(status_code=400, detail=f"Product with ID {item.productId} not found")
        total += prod.price * item.quantity

    # Save order
    new_order = OrderDB(
        total_price=round(total, 2),
        status="Order successfully placed!",
    )
    db.add(new_order)
    db.flush()

    # Save order items
    for item in items:
        order_item = OrderItemDB(
            order_id=new_order.id,
            product_id=item.productId,
            quantity=item.quantity,
        )
        db.add(order_item)

    db.commit()

    return CheckoutResponse(
        order_id=new_order.id,
        status=new_order.status,
        total_price=new_order.total_price,
    )


@app.get("/orders/{order_id}/formatted_text")
def get_order_formatted_text(order_id: int, db: Session = Depends(get_db)):
    order = db.query(OrderDB).filter(OrderDB.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    items = db.query(OrderItemDB, ProductDB).join(
        ProductDB, OrderItemDB.product_id == ProductDB.id
    ).filter(OrderItemDB.order_id == order_id).all()

    grouped = {}
    for item, prod in items:
        provider = prod.provider_name
        if provider not in grouped:
            grouped[provider] = []
        grouped[provider].append((prod.name, item.quantity))

    formatted = {}
    for provider, prod_list in grouped.items():
        lines = [f"Order for {provider}:"]
        for name, qty in prod_list:
            lines.append(f"- {name} x{qty}")
        formatted[provider] = "\n".join(lines)

    return formatted


if __name__ == "__main__":
    import os
    import uvicorn
    # Платформа сама передаст нужный порт через переменную PORT
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
