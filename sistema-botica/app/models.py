from datetime import datetime
from sqlalchemy import String, BigInteger, Boolean, DateTime, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

# --- Usuario mínimo (lo dejamos para más adelante) ---
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

# --- Categorías ---
class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)

# --- Productos ---
class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    unit: Mapped[str] = mapped_column(String(20), default="UND")
    barcode: Mapped[str | None] = mapped_column(String(64), unique=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    min_stock: Mapped[float] = mapped_column(Numeric(10, 3), default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    category: Mapped["Category"] = relationship("Category")


from sqlalchemy import Date, Enum, UniqueConstraint
from decimal import Decimal
import enum
from sqlalchemy.orm import relationship

# --- Proveedores ---
class Supplier(Base):
    __tablename__ = "suppliers"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200))
    ruc: Mapped[str | None] = mapped_column(String(20))
    phone: Mapped[str | None] = mapped_column(String(32))
    email: Mapped[str | None] = mapped_column(String(200))

# --- Lotes (por producto) ---
class Batch(Base):
    __tablename__ = "batches"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    lot_code: Mapped[str] = mapped_column(String(64))
    expiry_date: Mapped[datetime | None] = mapped_column(Date)
    cost: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    product: Mapped["Product"] = relationship("Product")
    __table_args__ = (UniqueConstraint("product_id", "lot_code", name="uq_product_lot"),)

# --- Movimientos de stock ---
class StockType(str, enum.Enum):
    IN = "IN"
    OUT = "OUT"
    ADJ = "ADJ"

class StockMovement(Base):
    __tablename__ = "stock_movements"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("batches.id"))
    type: Mapped[str] = mapped_column(Enum(StockType))
    qty: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    ref_table: Mapped[str] = mapped_column(String(32))   # 'purchases'
    ref_id: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    product: Mapped["Product"] = relationship("Product")
    batch: Mapped["Batch"] = relationship("Batch")

# --- Compras ---
class PurchaseStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    POSTED = "POSTED"
    CANCELLED = "CANCELLED"

class Purchase(Base):
    __tablename__ = "purchases"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"))
    doc_type: Mapped[str] = mapped_column(String(10))   # 'FA','BO','NC'...
    series: Mapped[str] = mapped_column(String(10))
    number: Mapped[str] = mapped_column(String(20))
    date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    tax: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    status: Mapped[str] = mapped_column(String(12), default=PurchaseStatus.DRAFT.value)

    supplier: Mapped["Supplier"] = relationship("Supplier")
    __table_args__ = (UniqueConstraint("doc_type", "series", "number", name="uq_purchase_doc"),)

class PurchaseItem(Base):
    __tablename__ = "purchase_items"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    purchase_id: Mapped[int] = mapped_column(ForeignKey("purchases.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("batches.id"))
    qty: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    cost: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    tax: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2))
# ... imports arriba ...
class SaleStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    POSTED = "POSTED"
    CANCELLED = "CANCELLED"

class Sale(Base):
    __tablename__ = "sales"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    doc_type: Mapped[str] = mapped_column(String(10))
    series: Mapped[str] = mapped_column(String(10))
    number: Mapped[str] = mapped_column(String(20))
    date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    tax: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    status: Mapped[str] = mapped_column(String(12), default=SaleStatus.DRAFT.value)

    __table_args__ = (UniqueConstraint("doc_type", "series", "number", name="uq_sale_doc"),)

class SaleItem(Base):
    __tablename__ = "sale_items"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    qty: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    discount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    tax: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2))
