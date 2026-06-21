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
Product(id=1, name="Jim Beam Apple 32,5 %1,0L  США", volumeInfo="32,5", price=2000.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=2, name="Jim Beam Black Extra-Aged Bourbon 43% 0.7L", volumeInfo="0.7L", price=2200.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=3, name="Jim Beam Honey 32,5 %1,0L  США", volumeInfo="32,5", price=2000.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=4, name="Jim Beam Peach 32.5% 0.7L", volumeInfo="32.5", price=1850.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=5, name="Jim Beam Red Stag 32,5% 1.0 l", volumeInfo="32,5", price=2000.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=6, name="Jim Beam RYE 40% 0.7L", volumeInfo="0.7L", price=2150.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=7, name="Jim Beam White 0,2L  США", volumeInfo="0,2L", price=630.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=8, name="Jim Beam White 0,500 L  США", volumeInfo="0,500 L", price=1270.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=9, name="Jim Beam White 0,7L  США", volumeInfo="0,7L", price=1720.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=10, name="Jim Beam White 1,0L  США", volumeInfo="1,0L", price=2000.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=11, name="Бурбон  Blanton's Original Special  0,750L США", volumeInfo="0,750L", price=6330.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=12, name="Бурбон Buffalo Trace Kentucky Bourbon 40% 0.7L", volumeInfo="0.7L", price=2150.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=13, name="Бурбон Four roses 1.0 L США", volumeInfo="1.0 L", price=2700.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=14, name="Бурбон Maker's Mark  0,7l  45%", volumeInfo="0,7l", price=2960.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=15, name="Бурбон Old Forester 1,0L США", volumeInfo="1,0L", price=3000.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=16, name="Бренди Metaxa 7* +GB 40% 1 L", volumeInfo="1.0L", price=2310.00, providerName="Мастер и Ко", category="Other"),
    Product(id=17, name="Бренди St. Remy Authentic XO + GB 40% 1L", volumeInfo="1.0L", price=2250.00, providerName="Мастер и Ко", category="Other"),
    Product(id=18, name="Вино Porto Valdouro Rubi Port 19% 0.75 кр", volumeInfo="0.75", price=1220.00, providerName="Мастер и Ко", category="Wine"),
    Product(id=19, name="Вино Porto Valdouro TawnyPort 19% 0.75", volumeInfo="0.75", price=1220.00, providerName="Мастер и Ко", category="Wine"),
    Product(id=20, name="Вино Porto Valdouro White Port 19% 0.75", volumeInfo="0.75", price=1220.00, providerName="Мастер и Ко", category="Wine"),
    Product(id=21, name="Вино JP Chenet Blanc Colombard/Sauvignon 12% 0,75 l", volumeInfo="0,75 l", price=590.00, providerName="Мастер и Ко", category="Wine"),
    Product(id=22, name="Вино JP Chenet Cabemet Syrah 12.5% 0.75L", volumeInfo="12.5", price=590.00, providerName="Мастер и Ко", category="Wine"),
    Product(id=23, name="Вино JP Chenet Medium Sweet  белое 11,5% 0,75 l", volumeInfo="11,5", price=590.00, providerName="Мастер и Ко", category="Wine"),
    Product(id=24, name="Вино JP Chenet Medium Sweet Moelleux 11.5% 0.75L (Rose)", volumeInfo="11.5", price=650.00, providerName="Мастер и Ко", category="Wine"),
    Product(id=25, name="Вино JP Chenet Medium Sweet Rouge кр 12% 0,75 l", volumeInfo="0,75 l", price=590.00, providerName="Мастер и Ко", category="Wine"),
    Product(id=26, name="Вино JP Chenet Merlot 13.5% 0.25L", volumeInfo="13.5", price=350.00, providerName="Мастер и Ко", category="Wine"),
    Product(id=27, name="Вино JP Chenet Merlot 13.5% 0.75L", volumeInfo="13.5", price=590.00, providerName="Мастер и Ко", category="Wine"),
    Product(id=28, name="Биттер Angostura Cocoa 48% 0.100 L", volumeInfo="0.100 L", price=1500.00, providerName="Мастер и Ко", category="Other"),
    Product(id=29, name="Биттер Angostura Dr. Siegert 0,200L", volumeInfo="0,200L", price=1830.00, providerName="Мастер и Ко", category="Other"),
    Product(id=30, name="Биттер Angostura Orange 28% 0.100 L", volumeInfo="0.100 L", price=1650.00, providerName="Мастер и Ко", category="Other"),
    Product(id=31, name="Биттер FERNET-BRANCA 1L", volumeInfo="1.0L", price=2160.00, providerName="Мастер и Ко", category="Other"),
    Product(id=32, name="Биттер Bitter-Fernet Branca Menta 28% 0.7L", volumeInfo="0.7L", price=2160.00, providerName="Мастер и Ко", category="Other"),
    Product(id=33, name="Биттер The Bitter Truth Chocolate  44% 0.2L", volumeInfo="0.2L", price=1650.00, providerName="Мастер и Ко", category="Other"),
    Product(id=34, name="Биттер The Bitter Truth Grapefrut 44% 0.2L", volumeInfo="0.2L", price=1650.00, providerName="Мастер и Ко", category="Other"),
    Product(id=35, name="Биттер The Bitter Truth Orange  39% 0.2L", volumeInfo="0.2L", price=1650.00, providerName="Мастер и Ко", category="Other"),
    Product(id=36, name="Виски AUCHENTOSHAN AMERICAN OAK RESERVE 40% 1 L +GB", volumeInfo="1.0L", price=5020.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=37, name="Виски Black & White 40% 1L", volumeInfo="1.0L", price=1760.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=38, name="Виски Black Velvet  Toasted CARAMEL  35% 1,0L", volumeInfo="1,0L", price=1780.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=39, name="Виски Black Velvet Cndn Whisky 0,7", volumeInfo="0,7", price=1610.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=40, name="Виски Black Velvet Cndn Whisky 1,0", volumeInfo="1,0", price=1850.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=41, name="Виски Black Velvet 8 years 1,0L Канада купаж", volumeInfo="1,0L", price=2150.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=42, name="Виски Black Velvet Cndn Reserve Whisky (10YO)", volumeInfo="1.0L", price=2150.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=43, name="Виски Burn MacKenzie 1,0L Шотландия.Купаж", volumeInfo="1,0L", price=1340.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=44, name="Виски Canadian Club 1,0L Канада", volumeInfo="1,0L", price=2050.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=45, name="Виски Clansman  0,05L", volumeInfo="0,05L", price=200.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=46, name="Виски Clansman 0,350  LШотландия.Купаж.", volumeInfo="0,350  L", price=645.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=47, name="Виски Clansman 0.7LШотландия.Купаж", volumeInfo="0.7L", price=855.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=48, name="Виски Clansman 1.0 LШотландия.Купаж.", volumeInfo="1.0 L", price=1195.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=49, name="Виски Clansman 1.5 LШотландия.Купаж.", volumeInfo="1.5 L", price=1745.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=50, name="Виски Crown Royal 1.0L Канада.Купажированный", volumeInfo="1.0L", price=3000.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=51, name="Виски Dalmore 12 yo GB 0,7l Шотландия Односолодовый Single Malt", volumeInfo="0,7l", price=9450.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=52, name="Виски Dalmore 15 yo GB 0.7l Шотландия Single Malt", volumeInfo="0.7l", price=11940.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=53, name="Виски Dalmore 18 yo 0.7 l Шотландия Single Malt", volumeInfo="0.7 l", price=14610.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=54, name="Виски Glen Scotia Double Cask Single Malt Scotch Whisky 0.7L", volumeInfo="0.7L", price=4940.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=55, name="Виски Glen Scotia Viktoriana Single Malt Scotch Whisky 0.7L", volumeInfo="0.7L", price=6820.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=56, name="Виски High Commissiner  Blended 0.05 L", volumeInfo="0.05 L", price=200.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=57, name="Виски High Commissiner  Blended 0.350 .LШотландия.Купаж.", volumeInfo="0.350", price=695.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=58, name="Виски High Commissiner  Blended 0.7.LШотландия.Купаж.", volumeInfo="0.7", price=925.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=59, name="Виски High Commissiner  Blended 1,5 .LШотландия.Купаж.", volumeInfo="1,5", price=2000.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=60, name="Виски High Commissiner  Blended 1.LШотландия.Купаж.", volumeInfo="1.0L", price=1345.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=61, name="Виски HIGH COMMISSIONER 7 YEAR OLD BLENDED SCOTCH WHISKY 0,7", volumeInfo="0,7", price=1445.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=62, name="Виски HIGHLAND BARON BLENDED SCOTCH WHISKY 1л", volumeInfo="1.0L", price=1255.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=63, name="Виски Highland Park 12 yo 0.7L Шотландия.Односолодовый", volumeInfo="0.7L", price=4100.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=64, name="Виски Inchmoan 12 YO 0.7l", volumeInfo="0.7l", price=3800.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=65, name="Виски Inchmurrin 12 YO Single Malt Scotch Whisky 0,7l", volumeInfo="0,7l", price=5320.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=66, name="Виски Inchmoan 12 YO 0.05l", volumeInfo="0.05l", price=240.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=67, name="Виски Inchmurrin 12 YO Single Malt Scotch Whisky 0,05l", volumeInfo="0,05l", price=240.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=68, name="Виски Kilbeggan 0.7L", volumeInfo="0.7L", price=1500.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=69, name="Виски Kilbeggan 1L", volumeInfo="1.0L", price=2040.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=70, name="Виски Laphroaig 10 yo 0.7l", volumeInfo="0.7l", price=6500.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=71, name="Виски Laphroaig 25 yo Cask Strength 0,7L Шотландия.Односолодовый", volumeInfo="0,7L", price=82000.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=72, name="Виски Laphroaig Quarter Cask 0,7L Шотландия.Односолодовый", volumeInfo="0,7L", price=4490.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=73, name="Виски Laphroaig Select 0,7L Шотландия.Односолодовый", volumeInfo="0,7L", price=3570.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=74, name="Виски Loch Lomond  12 летний 0,7 +2 стакана", volumeInfo="0,7", price=4225.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=75, name="Виски LOCH LOMOND  12YO,+ NOSING GLASS   20cl", volumeInfo="1.0L", price=2325.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=76, name="Виски Loch Lomond 12 Y.O Single malt 0.05 l 46%", volumeInfo="0.05 l", price=300.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=77, name="Виски Loch Lomond 12 Y.O Single malt 0.7l 46%", volumeInfo="0.7l", price=3600.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=78, name="Виски LOCH LOMOND 12 YEAR OLD+2x 5cl SINGLE MALT SCOTCH WHISKY", volumeInfo="1.0L", price=4180.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=79, name="Виски Loch Lomond 18 Y.O Single malt 0.7l 46%", volumeInfo="0.7l", price=6330.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=80, name="Виски Loch Lomond Organik 17 YEAR OLD 0.7L", volumeInfo="0.7L", price=7590.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=81, name="Виски Loch Lomond Original Single Malt Scotch Whisky 0.05l", volumeInfo="0.05l", price=250.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=82, name="Виски Loch Lomond Original Single Malt Scotch Whisky 0.7l", volumeInfo="0.7l", price=2455.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=83, name="Виски Loch Lomond Original Single Malt Scotch Whisky 1l", volumeInfo="1.0L", price=3475.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=84, name="Виски Loch Lomond Reserve 0,7l", volumeInfo="0,7l", price=1445.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=85, name="Виски Loch Lomond Reserve 1l", volumeInfo="1.0L", price=1780.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=86, name="Виски Loch Lomond Signature 0,7", volumeInfo="0,7", price=1695.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=87, name="Виски Loch Lomond Signature 1.0L", volumeInfo="1.0L", price=2135.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=88, name="Виски Loch Lomond Single Grain Scotch Whisky 0.05 L", volumeInfo="0.05 L", price=200.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=89, name="Виски Loch Lomond Single Grain Scotch Whisky 0.7 Тубус", volumeInfo="0.7", price=2205.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=90, name="Виски Loch Lomond Single Molt Scotch Whisky-The OPEN special edition 0,7L", volumeInfo="0,7L", price=4050.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=91, name="Виски lsle of Jura The Sound 42.5% 1 L + GB", volumeInfo="42.5", price=4050.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=92, name="Виски Monkey Shoulder 0.7L", volumeInfo="0.7L", price=3370.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=93, name="Виски Monkey Shoulder Smokey Monkey 0.7 L (Шотландия)", volumeInfo="0.7 L", price=3500.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=94, name="Виски Nikka Coffey Malt 45% 0.7L + GB", volumeInfo="0.7L", price=5940.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=95, name="Виски Suntory Hibiki Japanese Harmony  0,7L Япония", volumeInfo="0,7L", price=14200.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=96, name="Виски Oban 14 yo 0,7L Шотландия.Односолодовый", volumeInfo="0,7L", price=7100.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=97, name="Виски Proper Twelve 0,7 л", volumeInfo="0,7 л", price=4180.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=98, name="Виски Teachers 0.5 L Шотландия.Купаж", volumeInfo="0.5 L", price=900.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=99, name="Виски Teachers 0.75 L Шотландия.Купаж", volumeInfo="0.75 L", price=1150.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=100, name="Виски Teachers 1,0L Шотландия.Купаж", volumeInfo="1,0L", price=1950.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=101, name="Виски Tullamore Dew 0.7 L", volumeInfo="0.7 L", price=1900.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=102, name="Виски Tullamore Dew 1L", volumeInfo="1.0L", price=2500.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=103, name="Виски VAT 69 1,0L Шотландия.Купаж", volumeInfo="1,0L", price=1400.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=104, name="Виски WILLIAM LAWSONS 1.0 L Великобритания", volumeInfo="1.0 L", price=1750.00, providerName="Мастер и Ко", category="Whiskey"),
    Product(id=105, name="Вермут Martini Bianco 1,0л", volumeInfo="1,0л", price=1160.00, providerName="Мастер и Ко", category="Other"),
    Product(id=106, name="Вермут Martini Rosato 1,0л.", volumeInfo="1,0л", price=1160.00, providerName="Мастер и Ко", category="Other"),
    Product(id=107, name="Вермут Martini Rosso 1,0л.", volumeInfo="1,0л", price=1160.00, providerName="Мастер и Ко", category="Other"),
    Product(id=108, name="Вермут Martini Extra Dry 1,0л", volumeInfo="1,0л", price=1160.00, providerName="Мастер и Ко", category="Other"),
    Product(id=109, name="Вермут Martini Fiero 1,0л.", volumeInfo="1,0л", price=1390.00, providerName="Мастер и Ко", category="Other"),
    Product(id=110, name="Vodka-Beluga Noble 40% 0.7L", volumeInfo="0.7L", price=3000.00, providerName="Мастер и Ко", category="Vodka"),
    Product(id=111, name="Vodka-Beluga Noble 40% 1 L", volumeInfo="1.0L", price=4100.00, providerName="Мастер и Ко", category="Vodka"),
    Product(id=112, name="Водка Grey Goose 40% 0,7L", volumeInfo="0,7L", price=3500.00, providerName="Мастер и Ко", category="Vodka"),
    Product(id=113, name="Водка Grey Goose 40% 1L", volumeInfo="1.0L", price=4950.00, providerName="Мастер и Ко", category="Vodka"),
    Product(id=114, name="Водка Crystal Head 0.7L", volumeInfo="0.7L", price=5960.00, providerName="Мастер и Ко", category="Vodka"),
    Product(id=115, name="Водка Glen's 0,05L", volumeInfo="0,05L", price=160.00, providerName="Мастер и Ко", category="Vodka"),
    Product(id=116, name="Водка Glens Platinum 0.7L 40%", volumeInfo="0.7L", price=995.00, providerName="Мастер и Ко", category="Vodka"),
    Product(id=117, name="Водка Glens Platinum 1L 40%", volumeInfo="1.0L", price=1255.00, providerName="Мастер и Ко", category="Vodka"),
    Product(id=118, name="Водка Glens Vodka 0.35 L37.5%(кр)", volumeInfo="0.35 L", price=525.00, providerName="Мастер и Ко", category="Vodka"),
    Product(id=119, name="Водка Koskenkorva Original 1,0л", volumeInfo="1,0л", price=1430.00, providerName="Мастер и Ко", category="Vodka"),
    Product(id=120, name="Водка Glens Vodka 0.7 l 37.5%(кр)", volumeInfo="0.7 l", price=665.00, providerName="Мастер и Ко", category="Vodka"),
    Product(id=121, name="Водка Glens Vodka 1.0 l 37.5%(кр)", volumeInfo="1.0 l", price=850.00, providerName="Мастер и Ко", category="Vodka"),
    Product(id=122, name="Водка Neft Barrel Black 40% 0.7L", volumeInfo="0.7L", price=3300.00, providerName="Мастер и Ко", category="Vodka"),
    Product(id=123, name="Водка Neft Barrel White 40% 0.7L", volumeInfo="0.7L", price=3300.00, providerName="Мастер и Ко", category="Vodka"),
    Product(id=124, name="Водка Raki Yeni 1,0L", volumeInfo="1,0L", price=2250.00, providerName="Мастер и Ко", category="Vodka"),
    Product(id=125, name="Джин BEN LOMOND BLACKBERRY & GOOSEBERRY GIN 0.7l", volumeInfo="0.7l", price=2200.00, providerName="Мастер и Ко", category="Gin"),
    Product(id=126, name="Джин BEN LOMOND CITRUS BLOOD ORANGE & PINK GRAPEFRUIT  GIN 70cI", volumeInfo="1.0L", price=2200.00, providerName="Мастер и Ко", category="Gin"),
    Product(id=127, name="Джин BEN LOMOND GIN 0.7L", volumeInfo="0.7L", price=2200.00, providerName="Мастер и Ко", category="Gin"),
    Product(id=128, name="Джин BEN LOMOND RASPBERRY & ELDERFLOWER GIN 0.7l", volumeInfo="0.7l", price=2200.00, providerName="Мастер и Ко", category="Gin"),
    Product(id=129, name="Джин BOMBAY Saphire 1 л.", volumeInfo="1.0L", price=2655.00, providerName="Мастер и Ко", category="Gin"),
    Product(id=130, name="Джин HENDRICKS  0,7л", volumeInfo="0,7л", price=3300.00, providerName="Мастер и Ко", category="Gin"),
    Product(id=131, name="Джин Glens 1L", volumeInfo="1.0L", price=1195.00, providerName="Мастер и Ко", category="Gin"),
    Product(id=132, name="Джин Finsbury 1L", volumeInfo="1.0L", price=1430.00, providerName="Мастер и Ко", category="Gin"),
    Product(id=133, name="Джин Finsbury Wild Strawberry 37,5% 0,7 L", volumeInfo="37,5", price=1175.00, providerName="Мастер и Ко", category="Gin"),
    Product(id=134, name="Джин Glens GIN 1.5L", volumeInfo="1.5L", price=1695.00, providerName="Мастер и Ко", category="Gin"),
    Product(id=135, name="Джин Tanqueray 1L", volumeInfo="1.0L", price=2500.00, providerName="Мастер и Ко", category="Gin"),
    Product(id=136, name="Джин Tanqueray Malacca 41.3% 1L", volumeInfo="41.3", price=2350.00, providerName="Мастер и Ко", category="Gin"),
    Product(id=137, name="Джин Tanqueray Rangpur 41/3 % 1L", volumeInfo="1.0L", price=2350.00, providerName="Мастер и Ко", category="Gin"),
    Product(id=138, name="Джин Tanqueray Sevilla 41.3% 1L", volumeInfo="41.3", price=2350.00, providerName="Мастер и Ко", category="Gin"),
    Product(id=139, name="Джин Tanqueray TEN 47.3 % 1L", volumeInfo="47.3", price=3520.00, providerName="Мастер и Ко", category="Gin"),
    Product(id=140, name="Коньяк Courvoisier V.S 0.5L", volumeInfo="0.5L", price=2280.00, providerName="Мастер и Ко", category="Other"),
    Product(id=141, name="Коньяк Courvoisier V.S 0.7L", volumeInfo="0.7L", price=3900.00, providerName="Мастер и Ко", category="Other"),
    Product(id=142, name="Коньяк Courvoisier V.S 1,0L", volumeInfo="1,0L", price=4500.00, providerName="Мастер и Ко", category="Other"),
    Product(id=143, name="Коньяк Courvoisier VSOP 0.05L", volumeInfo="0.05L", price=430.00, providerName="Мастер и Ко", category="Other"),
    Product(id=144, name="Коньяк Courvoisier VSOP 0.5L", volumeInfo="0.5L", price=2920.00, providerName="Мастер и Ко", category="Other"),
    Product(id=145, name="Коньяк Courvoisier VSOP 0.7L", volumeInfo="0.7L", price=4900.00, providerName="Мастер и Ко", category="Other"),
    Product(id=146, name="Коньяк Courvoisier VSOP 1,0L", volumeInfo="1,0L", price=6000.00, providerName="Мастер и Ко", category="Other"),
    Product(id=147, name="Коньяк Courvoisier XO 0.7+GB", volumeInfo="0.7", price=16500.00, providerName="Мастер и Ко", category="Other"),
    Product(id=148, name="Коньяк Meukow black panther V.S 0.7+ GB", volumeInfo="0.7", price=3450.00, providerName="Мастер и Ко", category="Other"),
    Product(id=149, name="Коньяк Meukow  V.S.O.P 0.7", volumeInfo="0.7", price=4600.00, providerName="Мастер и Ко", category="Other"),
    Product(id=150, name="Коньяк Meukow XO 0.7", volumeInfo="0.7", price=14500.00, providerName="Мастер и Ко", category="Other"),
    Product(id=151, name="Коньяк CAMUS VS 0.7 L", volumeInfo="0.7 L", price=3700.00, providerName="Мастер и Ко", category="Other"),
    Product(id=152, name="Коньяк CAMUS VSOP 0.7 L", volumeInfo="0.7 L", price=5500.00, providerName="Мастер и Ко", category="Other"),
    Product(id=153, name="Коньяк CAMUS XO 0.7 L", volumeInfo="0.7 L", price=18500.00, providerName="Мастер и Ко", category="Other"),
    Product(id=154, name="Коньяк Remy Martin XO 0,7+GB", volumeInfo="0,7", price=18500.00, providerName="Мастер и Ко", category="Other"),
    Product(id=155, name="Коньяк Remy Martin VSOP 0,7", volumeInfo="0,7", price=6000.00, providerName="Мастер и Ко", category="Other"),
    Product(id=156, name="Коньяк Godet Antarctica 40% 0.5L +GB", volumeInfo="0.5L", price=3520.00, providerName="Мастер и Ко", category="Other"),
    Product(id=157, name="Ликер Absinth \"Mr.Jekyll\" 0.7L", volumeInfo="0.7L", price=1320.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=158, name="Ликер Agwa de Bolivia 0.7 L", volumeInfo="0.7 L", price=2410.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=159, name="Ликер Amaretto di Amore 1L", volumeInfo="1.0L", price=2010.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=160, name="Ликер Amaretto Di Saronno 28% 1l", volumeInfo="1.0L", price=2150.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=161, name="Ликер Amarula Cream Liquer 1,0L", volumeInfo="1,0L", price=2090.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=162, name="Ликер Aperol 1л.", volumeInfo="1.0L", price=2360.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=163, name="Ликер Aperitif-Luxardo Aperitivo 11% 1l", volumeInfo="1.0L", price=2150.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=164, name="Ликер ARCHERS  Peach Snapps 18% 0.7 L", volumeInfo="0.7 L", price=1950.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=165, name="Ликер BECHEROVKA 1 л", volumeInfo="1.0L", price=1900.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=166, name="Ликер Bols Elderflower 17% 0.7 L", volumeInfo="0.7 L", price=1410.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=167, name="Ликер Bols Apricot Brandy 24% 0.7 L", volumeInfo="0.7 L", price=1410.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=168, name="Ликер Bols Lychee 17% 0.70 l", volumeInfo="0.70 l", price=1410.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=169, name="Ликер Bols Marashino 0.7l", volumeInfo="0.7l", price=1410.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=170, name="Ликер Bols Triple sec 38% 0.70 l", volumeInfo="0.70 l", price=1410.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=171, name="Ликер Bols Peach  0.7 L", volumeInfo="0.7 L", price=1410.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=172, name="Ликер Bols Creme de Casis 17% 0.7 L", volumeInfo="0.7 L", price=1410.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=173, name="Ликер Bols Coconut 17% 0.7 L", volumeInfo="0.7 L", price=1410.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=174, name="Ликер Bols Coffee 24% 0.7 L", volumeInfo="0.7 L", price=1410.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=175, name="Ликер Campari Bitter  1 L", volumeInfo="1.0L", price=2600.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=176, name="Ликер Carolans Irish Cream 1 л", volumeInfo="1.0L", price=2000.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=177, name="Ликер Cointreau 1.0 L", volumeInfo="1.0 L", price=2500.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=178, name="Ликер De cuyper  Citron 1,0L", volumeInfo="1,0L", price=1520.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=179, name="Ликер De cuyper  Green Mente  1,0L", volumeInfo="1,0L", price=1780.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=180, name="Ликер De cuyper  Melon 0,7л", volumeInfo="0,7л", price=1680.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=181, name="Ликер De cuyper  Melon 1,0L", volumeInfo="1,0L", price=1780.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=182, name="Ликер De cuyper  Razzmatazz 1,0L", volumeInfo="1,0L", price=1520.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=183, name="Ликер De cuyper Apricot Brandy 0,7л", volumeInfo="0,7л", price=1680.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=184, name="Ликер De cuyper Apricot Brandy 1,0L", volumeInfo="1,0L", price=1780.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=185, name="Ликер De cuyper Blue Curacao 0,7L", volumeInfo="0,7L", price=1680.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=186, name="Ликер De cuyper Triple Sec 1,0L", volumeInfo="1,0L", price=1780.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=187, name="Ликер De cuyper Watermelon 1,0L", volumeInfo="1,0L", price=1520.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=188, name="Ликер De Kuyper Creme de Cacao Brown 20% 0.7L", volumeInfo="0.7L", price=1680.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=189, name="Ликер De Kuyper Creme de Cacao White 24% 0.7L", volumeInfo="0.7L", price=1680.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=190, name="Ликер De Kuyper Orange 15% 0.7L", volumeInfo="0.7L", price=1680.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=191, name="Ликер De Kuyper Pina Colada 14.5% 0.7L", volumeInfo="14.5", price=1680.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=192, name="Ликер Dom Benedictine 0.7 L", volumeInfo="0.7 L", price=2410.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=193, name="Ликер Dom Benedictine 1,0L", volumeInfo="1,0L", price=2670.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=194, name="Ликер Drambuie 0,750L", volumeInfo="0,750L", price=2360.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=195, name="Ликер Frangelico 0,7L", volumeInfo="0,7L", price=2150.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=196, name="Ликер Frangelico 1,0L", volumeInfo="1,0L", price=2480.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=197, name="Ликер Galliano L'autentico Liquor 0,7L", volumeInfo="0,7L", price=2030.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=198, name="Ликер Grand Marnier  1,0L", volumeInfo="1,0L", price=4050.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=199, name="Ликер Jagermeister 35% 0,5 л", volumeInfo="0,5 л", price=1520.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=200, name="Ликер Jagermeister 35% 0,7 л", volumeInfo="0,7 л", price=2050.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=201, name="Ликер Jagermeister 35% 1.0 л", volumeInfo="1.0 л", price=2730.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=202, name="Ликер Jagermeister Orange 1,0 л", volumeInfo="1,0 л", price=2900.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=203, name="Ликер Jagermeister Manifest 1,0 л", volumeInfo="1,0 л", price=4050.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=204, name="Ликер Jagermeister Scharf Spised Ginger 33% 0,7 л", volumeInfo="0,7 л", price=2150.00, providerName="Мастер и Ко", category="Gin"),
    Product(id=205, name="Ликер Limoncello Palini 1l", volumeInfo="1.0L", price=2350.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=206, name="Ликер Midori Melon 20% 1,0 L", volumeInfo="1,0 L", price=2530.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=207, name="Ликер Passoa 1,0L", volumeInfo="1,0L", price=1880.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=208, name="Ликер Safari 1l", volumeInfo="1.0L", price=1720.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=209, name="Ликер Sambuca di Amore 1L", volumeInfo="1.0L", price=2050.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=210, name="Ликер Sambuca Molinari  1,0L", volumeInfo="1,0L", price=2050.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=211, name="Ликер Schwartzhog 1L", volumeInfo="1.0L", price=2030.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=212, name="Ликер Southern Comfort 35% 1L", volumeInfo="1.0L", price=1650.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=213, name="Ликер St. Germain Elderflower Liqueur 0,7L", volumeInfo="0,7L", price=4940.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=214, name="Ликер Xenta Absinth 1,0L", volumeInfo="1,0L", price=2450.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=215, name="Ликер XuXu 1,0L", volumeInfo="1,0L", price=2030.00, providerName="Мастер и Ко", category="Liqueurs"),
    Product(id=216, name="пиво Ceska pinta №1 Nefitrovane Svetly Pivo 5,0% 0,568l", volumeInfo="5,0", price=128.00, providerName="Мастер и Ко", category="Beer"),
    Product(id=217, name="пиво Ceska pinta в ж.б банке 0.568 ml", volumeInfo="0.568", price=128.00, providerName="Мастер и Ко", category="Beer"),
    Product(id=218, name="пиво Ceska pinta N1 MONASTYRSKE 5,9 %", volumeInfo="5,9", price=128.00, providerName="Мастер и Ко", category="Beer"),
    Product(id=219, name="пиво Corona Extra 4.5% 0.355 L (стекло)", volumeInfo="4.5", price=150.00, providerName="Мастер и Ко", category="Beer"),
    Product(id=220, name="Пиво Kralovice Tradicni 10 Svetly Lezak 4,7% 0,5l", volumeInfo="4,7", price=105.00, providerName="Мастер и Ко", category="Beer"),
    Product(id=221, name="Пиво Kralovice Tradicni Premium 5,0% 0,5l ст.бут", volumeInfo="5,0", price=105.00, providerName="Мастер и Ко", category="Beer"),
    Product(id=222, name="Пиво Kralovice Non Filtered 5.4% 0.5L", volumeInfo="5.4", price=105.00, providerName="Мастер и Ко", category="Beer"),
    Product(id=223, name="Пиво Line Brew Pomergranate  0,568l, 4,5 %", volumeInfo="0,568l", price=135.00, providerName="Мастер и Ко", category="Beer"),
    Product(id=224, name="Пиво Line Brew Raspberry -Lime 0,568l, 4,5 %", volumeInfo="0,568l", price=135.00, providerName="Мастер и Ко", category="Beer"),
    Product(id=225, name="Пиво Line Brew Wild Strawberry  0,568l, 4,5 %", volumeInfo="0,568l", price=135.00, providerName="Мастер и Ко", category="Beer"),
    Product(id=226, name="Ром Bacardi Carta Blanca 1.0л", volumeInfo="1.0л", price=2035.00, providerName="Мастер и Ко", category="Rum"),
    Product(id=227, name="Ром Bacardi Carta Negra 1.0л", volumeInfo="1.0л", price=2030.00, providerName="Мастер и Ко", category="Rum"),
    Product(id=228, name="Ром Bacardi Spiced 1.0л", volumeInfo="1.0л", price=2030.00, providerName="Мастер и Ко", category="Rum"),
    Product(id=229, name="Ром Cachaca 51 1L(Бразилия)", volumeInfo="1.0L", price=1970.00, providerName="Мастер и Ко", category="Rum"),
    Product(id=230, name="Ром Glens Black 1,0L", volumeInfo="1,0L", price=1195.00, providerName="Мастер и Ко", category="Rum"),
    Product(id=231, name="Ром Glens White 1,0L", volumeInfo="1,0L", price=1195.00, providerName="Мастер и Ко", category="Rum"),
    Product(id=232, name="Саке́ Choya 0.75 L", volumeInfo="0.75 L", price=1820.00, providerName="Мастер и Ко", category="Other"),
    Product(id=233, name="Текила JUAREZ GOLD  1.0L", volumeInfo="1.0L", price=1750.00, providerName="Мастер и Ко", category="Tequila"),
    Product(id=234, name="Текила JUAREZ SILVER  1.0L", volumeInfo="1.0L", price=1750.00, providerName="Мастер и Ко", category="Tequila"),
    Product(id=235, name="Текила Meskals 0.75L", volumeInfo="0.75L", price=2920.00, providerName="Мастер и Ко", category="Tequila"),
    Product(id=236, name="Текила Montelobos Espadin Mezcal Joven 43.2% 0.7L", volumeInfo="43.2", price=3650.00, providerName="Мастер и Ко", category="Tequila"),
    Product(id=237, name="Текила Sierra gold 1.0 l", volumeInfo="1.0 l", price=2500.00, providerName="Мастер и Ко", category="Tequila"),
    Product(id=238, name="Текила Sierra silver 1.0 l", volumeInfo="1.0 l", price=2400.00, providerName="Мастер и Ко", category="Tequila"),
    Product(id=239, name="Текила Patron Reposado 0,75л.", volumeInfo="0,75л", price=4700.00, providerName="Мастер и Ко", category="Tequila"),
    Product(id=240, name="Текила Patron Anejo 0,75л.", volumeInfo="0,75л", price=6000.00, providerName="Мастер и Ко", category="Tequila"),
    Product(id=241, name="Текила Patron  Silver  0.7 L", volumeInfo="0.7 L", price=4210.00, providerName="Мастер и Ко", category="Tequila"),
    Product(id=242, name="Шампанское Cornaro Prosecco Treviso Brut DOC 11% 0.75l", volumeInfo="0.75l", price=1100.00, providerName="Мастер и Ко", category="Wine"),
    Product(id=243, name="Шампанское Cornaro Prosecco Treviso extra Dry 11% 0.75l", volumeInfo="0.75l", price=1100.00, providerName="Мастер и Ко", category="Wine"),
    Product(id=244, name="Шампанское MonteIIiana Prosecco Treviso Extra Dry 11% 0,75л", volumeInfo="0,75л", price=1100.00, providerName="Мастер и Ко", category="Wine"),
    Product(id=245, name="Шампанское MonteIIiana Prosecco treviso Extra Dry 11% 0,2l", volumeInfo="0,2l", price=500.00, providerName="Мастер и Ко", category="Wine"),
    Product(id=246, name="Шампанское Manfredi Asti docg 7.5% 0.75l", volumeInfo="7.5", price=850.00, providerName="Мастер и Ко", category="Wine"),
    Product(id=247, name="Шампанское Manfredi Moscato 6.5% 0.75l", volumeInfo="6.5", price=850.00, providerName="Мастер и Ко", category="Wine"),
    Product(id=248, name="Шампанское Martini Prosecco", volumeInfo="1.0L", price=1370.00, providerName="Мастер и Ко", category="Wine"),
    Product(id=249, name="Шампанское Martini Brut Sparkling", volumeInfo="1.0L", price=1370.00, providerName="Мастер и Ко", category="Wine"),
    Product(id=250, name="Шампанское Martini Asti Spumante", volumeInfo="1.0L", price=1370.00, providerName="Мастер и Ко", category="Wine"),
    Product(id=251, name="ШампанскоеLouis Roederer Cristal Brut 2007 GB 0,750L", volumeInfo="0,750L", price=37000.00, providerName="Мастер и Ко", category="Wine"),
    Product(id=252, name="Водка Stolichnaya Excellent 0,5 л", volumeInfo="0,5 л", price=510.00, providerName="Кронатрэйд", category="Vodka"),
    Product(id=253, name="Stolichnaya Excellent 0,7 л Водка", volumeInfo="0,7 л", price=700.00, providerName="Кронатрэйд", category="Vodka"),
    Product(id=254, name="Stolichnaya Excellent 0,7 л ПУ", volumeInfo="0,7 л", price=800.00, providerName="Кронатрэйд", category="Other"),
    Product(id=255, name="Sever 0,5 л Водка", volumeInfo="0,5 л", price=440.00, providerName="Кронатрэйд", category="Vodka"),
    Product(id=256, name="Stolichnaya Водка Sever 0,25 л", volumeInfo="0,25 л", price=245.00, providerName="Кронатрэйд", category="Vodka"),
    Product(id=257, name="Sever 0,7 л Водка", volumeInfo="0,7 л", price=600.00, providerName="Кронатрэйд", category="Vodka"),
    Product(id=258, name="Stolichnaya Sever 1,0 л", volumeInfo="1,0 л", price=835.00, providerName="Кронатрэйд", category="Other"),
    Product(id=259, name="Водка Stolichnaya 0,25 л", volumeInfo="0,25 л", price=245.00, providerName="Кронатрэйд", category="Vodka"),
    Product(id=260, name="Stolichnaya 0,5 л Водка", volumeInfo="0,5 л", price=435.00, providerName="Кронатрэйд", category="Vodka"),
    Product(id=261, name="Stolichnaya 0,7 л Водка", volumeInfo="0,7 л", price=595.00, providerName="Кронатрэйд", category="Vodka"),
    Product(id=262, name="Stolichnaya 1,0 л", volumeInfo="1,0 л", price=830.00, providerName="Кронатрэйд", category="Other"),
    Product(id=263, name="Водка Moskovskaya Osobaya 0,5 л", volumeInfo="0,5 л", price=435.00, providerName="Кронатрэйд", category="Vodka"),
    Product(id=264, name="Moskovskaya Osobaya 0,7 л", volumeInfo="0,7 л", price=595.00, providerName="Кронатрэйд", category="Other"),
    Product(id=265, name="Premium 0,25 л Водка Русская", volumeInfo="0,25 л", price=230.00, providerName="Кронатрэйд", category="Vodka"),
    Product(id=266, name="Premium 0,5 л Водка Русская", volumeInfo="0,5 л", price=395.00, providerName="Кронатрэйд", category="Vodka"),
    Product(id=267, name="Alpha Spirit 0,5 л Водка Русская", volumeInfo="0,5 л", price=400.00, providerName="Кронатрэйд", category="Vodka"),
    Product(id=268, name="Premium 0,7 л", volumeInfo="0,7 л", price=535.00, providerName="Кронатрэйд", category="Other"),
    Product(id=269, name="Водка Koskenkorva Original 0,5 л", volumeInfo="0,5 л", price=820.00, providerName="Кронатрэйд", category="Vodka"),
    Product(id=270, name="Водка Koskenkorva Original 1,0 л", volumeInfo="1,0 л", price=1430.00, providerName="Кронатрэйд", category="Vodka"),
    Product(id=271, name="Водка Koskenkorva Original 0,7 л", volumeInfo="0,7 л", price=1115.00, providerName="Кронатрэйд", category="Vodka"),
    Product(id=272, name="ArnozanBordeaux Superieur ArnozanBordeauxвино ArnozanBordeauxвино ArnozanBordeaux вино вино красное сухое 0,75 л Белое сухое 0,75 л красное сухое 0,75 л розовое сухое 0,75 л", volumeInfo="0,75 л", price=750.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=273, name="ArnozanMedocвино Chateau De Laborde Chateau Haut Mirambet Chateau La Grave Medoc красное сухое 0,75 л Boise Bordeaux вино Bordeaux вино красное вино красное сухое 0,75 л", volumeInfo="0,75 л", price=1100.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=274, name="белое полусладкое 0,75 л Sauvignon вино белое сухое 0,75 л красное сухое 0,75 л", volumeInfo="0,75 л", price=670.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=275, name="Rafale Cabernet Sauvignon вино Rafale Syrah вино красное Rafale Merlot вино красное полусухое 0,75 л полусухое 0,75 л красное полусухое 0,75 л", volumeInfo="0,75 л", price=600.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=276, name="Rafale Muscat вино белое сухое 0,75 л Rafale Cabernet", volumeInfo="0,75 л", price=650.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=277, name="вино белое сухое 0,75 л Chablis 1er Cru", volumeInfo="0,75 л", price=2200.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=278, name="Les Valery вино белое сухое 0,75 л", volumeInfo="0,75 л", price=3100.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=279, name="полусладкое 0,75 л Cabernet", volumeInfo="0,75 л", price=820.00, providerName="Кронатрэйд", category="Other"),
    Product(id=280, name="полусладкое 0,75 л Petit Chablis Chateau De Malignyвино", volumeInfo="0,75 л", price=820.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=281, name="белое сухое 0,75 л", volumeInfo="0,75 л", price=1820.00, providerName="Кронатрэйд", category="Other"),
    Product(id=282, name="белое полусладкое 0,75 л Victor", volumeInfo="0,75 л", price=1099.00, providerName="Кронатрэйд", category="Other"),
    Product(id=283, name="белое сухое 0,75 л Victor", volumeInfo="0,75 л", price=1099.00, providerName="Кронатрэйд", category="Other"),
    Product(id=284, name="Dravigny шампанское розовое сухое 0,75 л", volumeInfo="0,75 л", price=1099.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=285, name="шампанское белое сухое 0,75 л Абрау", volumeInfo="0,75 л", price=665.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=286, name="Дюрсо Резерв шампанское розовое сухое 0,75 л", volumeInfo="0,75 л", price=665.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=287, name="белое полусладкое 0,2 л Абрау", volumeInfo="0,2 л", price=225.00, providerName="Кронатрэйд", category="Other"),
    Product(id=288, name="Дюрсо шампанское белое полусладкое 0,75 л", volumeInfo="0,75 л", price=570.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=289, name="белое сухое 0,2 л Абрау", volumeInfo="0,2 л", price=225.00, providerName="Кронатрэйд", category="Other"),
    Product(id=290, name="Дюрсо шампанское белое сухое 0,75 л", volumeInfo="0,75 л", price=570.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=291, name="розовое полусухое 0,75 л Абрау", volumeInfo="0,75 л", price=570.00, providerName="Кронатрэйд", category="Other"),
    Product(id=292, name="Дюрсо шампанское белое полусухое 0,75 л", volumeInfo="0,75 л", price=570.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=293, name="белое сухое 0,75 л Абрау", volumeInfo="0,75 л", price=535.00, providerName="Кронатрэйд", category="Other"),
    Product(id=294, name="Эстейтс вино красное сухое 0,75 л", volumeInfo="0,75 л", price=535.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=295, name="полусладкое 0,75 л Купаж", volumeInfo="0,75 л", price=425.00, providerName="Кронатрэйд", category="Other"),
    Product(id=296, name="Абрау вино белое сухое 0,75 л", volumeInfo="0,75 л", price=425.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=297, name="Абрау вино красное сухое 0,75 л", volumeInfo="0,75 л", price=425.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=298, name="Водка Абрау Дюрсо Настойка 7 злаков 0,5 л", volumeInfo="0,5 л", price=580.00, providerName="Кронатрэйд", category="Vodka"),
    Product(id=299, name="горькая Абрау Дюрсо 7 овощей 0,5 л", volumeInfo="0,5 л", price=660.00, providerName="Кронатрэйд", category="Other"),
    Product(id=300, name="Hans GreylSauvignon NZ вино белое сухое 0,75 л", volumeInfo="0,75 л", price=950.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=301, name="красное полусухое 0,75 л 770", volumeInfo="0,75 л", price=690.00, providerName="Кронатрэйд", category="Other"),
    Product(id=302, name="Miles Zinfandel вино розовое полусухое 0,75 л", volumeInfo="0,75 л", price=690.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=303, name="Fuego Garnacha вино красное Fuego полусладкое 0,75 л", volumeInfo="0,75 л", price=565.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=304, name="красное сухое 0,75 л Fuego", volumeInfo="0,75 л", price=565.00, providerName="Кронатрэйд", category="Other"),
    Product(id=305, name="Verdejo вино белое сухое 0,75 л", volumeInfo="0,75 л", price=565.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=306, name="розовое сухое 0,75 л Te", volumeInfo="0,75 л", price=630.00, providerName="Кронатрэйд", category="Other"),
    Product(id=307, name="Toa Sauvignon вино белое сухое 0,75 л", volumeInfo="0,75 л", price=630.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=308, name="белое полусухое 0,75 л Just for you Malbec", volumeInfo="0,75 л", price=565.00, providerName="Кронатрэйд", category="Other"),
    Product(id=309, name="красное сухое 0,75 л Just", volumeInfo="0,75 л", price=565.00, providerName="Кронатрэйд", category="Other"),
    Product(id=310, name="for you Merlot вино красное полусухое 0,75 л", volumeInfo="0,75 л", price=565.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=311, name="вино розовое сухое 0,75 л Just for you Pinot", volumeInfo="0,75 л", price=565.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=312, name="Grigio вино белое сухое 0,75 л", volumeInfo="0,75 л", price=565.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=313, name="вино белое Montmeyrac сухое 0,75 л", volumeInfo="0,75 л", price=480.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=314, name="Montmeyrac вино красное сухое 0,75 л Montmeyrac", volumeInfo="0,75 л", price=480.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=315, name="вино розовое сухое 0,75 л", volumeInfo="0,75 л", price=480.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=316, name="LouisEschenauer Bordeux вино Louis белое полусладкое 0,75 л", volumeInfo="0,75 л", price=700.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=317, name="сом вино красное сухое 0,75 л", volumeInfo="0,75 л", price=700.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=318, name="Louis Eschenauer Medoc Louis Eschenauer Bordeux Superiour вино красное сухое 0,75 л", volumeInfo="0,75 л", price=750.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=319, name="вино красное сухое 0,75 л", volumeInfo="0,75 л", price=750.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=320, name="Le Grand Filou вино розовое полусухое 0,75 л", volumeInfo="0,75 л", price=550.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=321, name="Le Grand Filou вино красное полусухое 0,75 л", volumeInfo="0,75 л", price=550.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=322, name="Le Sweet Filou вино красное сладкое 0,75 л", volumeInfo="0,75 л", price=550.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=323, name="Le Sweet Filou вино розовое сладкое 0,75 л", volumeInfo="0,75 л", price=550.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=324, name="Le Sweet Filou вино белое сладкое 0,75 л", volumeInfo="0,75 л", price=550.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=325, name="Xenta Absenta Lime Xenta Absenta XentaAbsenta XentaAbsenta Ginger абсент 0,7 л Orange абсент 0,7 л абсент 0,7 л абсент 1,0 л", volumeInfo="0,7 л", price=1800.00, providerName="Кронатрэйд", category="Gin"),
    Product(id=326, name="Xeven Limoncello Xenta Superior абсент 0,7 л ПУ", volumeInfo="0,7 л", price=3200.00, providerName="Кронатрэйд", category="Other"),
    Product(id=327, name="Цена 1230 сом Виски Cutty Sark 1,0 л", volumeInfo="1,0 л", price=1730.00, providerName="Кронатрэйд", category="Other"),
    Product(id=328, name="Виски Glen Turner 12 YO 0,7 л Виски", volumeInfo="0,7 л", price=3360.00, providerName="Кронатрэйд", category="Other"),
    Product(id=329, name="Glen Turner heritage 0,7 л Виски", volumeInfo="0,7 л", price=2050.00, providerName="Кронатрэйд", category="Other"),
    Product(id=330, name="Old Virginia 0,7 л", volumeInfo="0,7 л", price=1450.00, providerName="Кронатрэйд", category="Gin"),
    Product(id=331, name="Виски Label 5 classic 0,5 л Виски Label 5 classic 0,7 л", volumeInfo="0,5 л", price=885.00, providerName="Кронатрэйд", category="Other"),
    Product(id=332, name="Виски Label 5 classic 1,0 л", volumeInfo="1,0 л", price=1120.00, providerName="Кронатрэйд", category="Other"),
    Product(id=333, name="вино белое сухое 0,75 л Ventiterre", volumeInfo="0,75 л", price=780.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=334, name="красное сухое 0,75 л Ventiterre", volumeInfo="0,75 л", price=970.00, providerName="Кронатрэйд", category="Other"),
    Product(id=335, name="Ventiterre Pinot Grigio сухое 0,75 л", volumeInfo="0,75 л", price=780.00, providerName="Кронатрэйд", category="Other"),
    Product(id=336, name="вино белое сухое 0,75 л", volumeInfo="0,75 л", price=780.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=337, name="белое сухое 0,75 л Zonin", volumeInfo="0,75 л", price=900.00, providerName="Кронатрэйд", category="Other"),
    Product(id=338, name="красное сухое 0,75 л Zonin", volumeInfo="0,75 л", price=1000.00, providerName="Кронатрэйд", category="Other"),
    Product(id=339, name="вино красное сухое 0,75 л Zonin", volumeInfo="0,75 л", price=900.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=340, name="Pinot Grigio вино белое сухое 0,75 л", volumeInfo="0,75 л", price=900.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=341, name="полусладкое 0,75 л Zonin", volumeInfo="0,75 л", price=780.00, providerName="Кронатрэйд", category="Other"),
    Product(id=342, name="сладкое 0,75 л Zonin", volumeInfo="0,75 л", price=990.00, providerName="Кронатрэйд", category="Other"),
    Product(id=343, name="Zonin белое сухое 0,75 л", volumeInfo="0,75 л", price=1150.00, providerName="Кронатрэйд", category="Other"),
    Product(id=344, name="полусладкое 0,75 л белое сухое 0,75 л", volumeInfo="0,75 л", price=410.00, providerName="Кронатрэйд", category="Other"),
    Product(id=345, name="Baron Simon вино красное Baron Simon вино полусладкое 0,75 л красное сухое 0,75 л", volumeInfo="0,75 л", price=410.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=346, name="Baron Romero вино белое полусладкое 0,75 л", volumeInfo="0,75 л", price=410.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=347, name="Baron Romero вино красное полусладкое 0,75 л", volumeInfo="0,75 л", price=410.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=348, name="Inkermanвино белое Inkermanвино красное InkermanМерло-Каберне InkermanМускатное вино полусухое 0,75 л полусухое 0,75 л вино красное сухое 0,75 л белое полусладкое 0,7 л", volumeInfo="0,75 л", price=420.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=349, name="InkermanПинновино InkermanСкалистая Бухта InkermanСкалистая Бухта InkermanСовиньон вино красное полусладкое 0,7 л вино белое сухое 0,75 л вино красное сухое 0,75 л белое сухое 0,75 л", volumeInfo="0,7 л", price=320.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=350, name="InkermanШардонеКачинское InkermanШато Блан вино InkermanШато Руж вино вино белое сухое 0,75 л белое полусухое 0,7 л красное полусухое 0,7 л", volumeInfo="0,75 л", price=420.00, providerName="Кронатрэйд", category="Wine"),
    Product(id=351, name="Stella Artois", volumeInfo="0,44 ж/б", price=145.00, providerName="САН ИнБев", category="Beer"),
    Product(id=352, name="Alcohol Free", volumeInfo="0,45 ж/б", price=95.00, providerName="САН ИнБев", category="Beer"),
    Product(id=353, name="BUD", volumeInfo="0,45 ж/б", price=118.00, providerName="САН ИнБев", category="Beer"),
    Product(id=354, name="Hoegaarden", volumeInfo="0,44с/б", price=155.00, providerName="САН ИнБев", category="Beer"),
    Product(id=355, name="Brahma", volumeInfo="0,45 c/б", price=130.00, providerName="САН ИнБев", category="Beer"),
    Product(id=356, name="Lowenbrau", volumeInfo="0,45с/б", price=105.00, providerName="САН ИнБев", category="Beer"),
    Product(id=357, name="Золотистое", volumeInfo="0,45с/б", price=44.00, providerName="САН ИнБев", category="Beer"),
    Product(id=358, name="Hoegaarden  Грейпфрут", volumeInfo="0,44 с/б", price=166.00, providerName="САН ИнБев", category="Beer"),
    Product(id=359, name="Corona Extra", volumeInfo="0,33 c/б", price=175.00, providerName="САН ИнБев", category="Beer"),
    Product(id=360, name="EL Capulco", volumeInfo="0,4 c/б", price=121.00, providerName="САН ИнБев", category="Beer"),
    Product(id=361, name="Без сахара", volumeInfo="0,45 ж/б", price=95.00, providerName="САН ИнБев", category="Beer"),
    Product(id=362, name="Volt", volumeInfo="0,45 ж/б", price=95.00, providerName="САН ИнБев", category="Soft Drinks"),
    Product(id=363, name="Amsterdam", volumeInfo="0,45 с/б", price=108.00, providerName="САН ИнБев", category="Beer"),
    Product(id=364, name="Kozel", volumeInfo="светлое 0,45с/б", price=107.00, providerName="САН ИнБев", category="Beer"),
    Product(id=365, name="Старый мельник", volumeInfo="из бочонка 0,45 с/б", price=104.00, providerName="САН ИнБев", category="Beer"),
    Product(id=366, name="ESSA ананас и грейпфрут", volumeInfo="0,4 с/б", price=108.00, providerName="САН ИнБев", category="Beer"),
    Product(id=367, name="ESSA", volumeInfo="дыня и клубника 0,4 с/б", price=108.00, providerName="САН ИнБев", category="Beer"),
    Product(id=368, name="Corona Core", volumeInfo="0,33 c/б", price=190.00, providerName="САН ИнБев", category="Beer"),
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
        # Clear database to ensure it matches the current seeding exactly and avoids foreign key issues
        db.query(OrderItemDB).delete()
        db.query(OrderDB).delete()
        db.query(ProductDB).delete()
        db.commit()
        for p in INITIAL_PRODUCTS:
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
