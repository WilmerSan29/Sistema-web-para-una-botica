from pydantic import BaseModel, Field
from typing import Optional

# -------- Categorías --------
class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)

class CategoryOut(CategoryIn):
    id: int
    class Config:
        from_attributes = True

# -------- Productos --------
class ProductIn(BaseModel):
    sku: str = Field(min_length=1, max_length=32)
    name: str
    category_id: Optional[int] = None
    unit: str = "UND"
    barcode: Optional[str] = None
    price: float = 0
    min_stock: float = 0
    is_active: bool = True

class ProductOut(ProductIn):
    id: int
    class Config:
        from_attributes = True

from datetime import date, datetime
from decimal import Decimal

# -------- Proveedores --------
class SupplierIn(BaseModel):
    name: str
    ruc: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

class SupplierOut(SupplierIn):
    id: int
    class Config:
        from_attributes = True

# -------- Lotes --------
class BatchIn(BaseModel):
    product_id: int
    lot_code: str
    expiry_date: Optional[date] = None
    cost: Decimal
    qty: Decimal  # cantidad del lote para esta compra

class BatchOut(BaseModel):
    id: int
    product_id: int
    lot_code: str
    expiry_date: Optional[date] = None
    cost: Decimal
    class Config:
        from_attributes = True

# -------- Compras --------
class PurchaseItemIn(BaseModel):
    product_id: int
    lot_code: str
    expiry_date: Optional[date] = None
    qty: Decimal
    cost: Decimal

class PurchaseIn(BaseModel):
    supplier_id: int
    doc_type: str
    series: str
    number: str
    date: Optional[datetime] = None
    items: list[PurchaseItemIn]

class PurchaseOut(BaseModel):
    id: int
    supplier_id: int
    doc_type: str
    series: str
    number: str
    date: datetime
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    status: str
    class Config:
        from_attributes = True

# --- ESQUEMAS DE VENTAS ---
from typing import Optional, List
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel

class SaleItemIn(BaseModel):
    product_id: int
    qty: Decimal
    price: Decimal
    discount: Decimal = Decimal("0")

class SaleIn(BaseModel):
    doc_type: str
    series: str
    number: str
    date: Optional[datetime] = None
    items: List[SaleItemIn]

class SaleOut(BaseModel):
    id: int
    doc_type: str
    series: str
    number: str
    date: datetime
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    status: str

    class Config:
        from_attributes = True
