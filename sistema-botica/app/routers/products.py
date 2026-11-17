from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/products", tags=["products"])

@router.post("", response_model=schemas.ProductOut)
def create_product(payload: schemas.ProductIn, db: Session = Depends(get_db)):
    # únicos: sku y (si viene) barcode
    if db.query(models.Product).filter(models.Product.sku == payload.sku).first():
        raise HTTPException(status_code=400, detail="El SKU ya existe.")
    if payload.barcode and db.query(models.Product).filter(models.Product.barcode == payload.barcode).first():
        raise HTTPException(status_code=400, detail="El código de barras ya existe.")
    obj = models.Product(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.get("", response_model=list[schemas.ProductOut])
def list_products(
    q: str | None = Query(default=None, description="Buscar por nombre, SKU o código de barras"),
    only_active: bool = True,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = db.query(models.Product)
    if only_active:
        query = query.filter(models.Product.is_active == True)  # noqa: E712
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                models.Product.name.ilike(like),
                models.Product.sku.ilike(like),
                models.Product.barcode.ilike(like),
            )
        )
    return query.order_by(models.Product.name.asc()).offset(offset).limit(limit).all()

@router.get("/{product_id}", response_model=schemas.ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    obj = db.get(models.Product, product_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return obj

@router.put("/{product_id}", response_model=schemas.ProductOut)
def update_product(product_id: int, payload: schemas.ProductIn, db: Session = Depends(get_db)):
    obj = db.get(models.Product, product_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    # validar unicidad de sku/barcode
    if db.query(models.Product).filter(models.Product.sku == payload.sku, models.Product.id != product_id).first():
        raise HTTPException(status_code=400, detail="SKU en uso por otro producto.")
    if payload.barcode and db.query(models.Product).filter(models.Product.barcode == payload.barcode, models.Product.id != product_id).first():
        raise HTTPException(status_code=400, detail="Código de barras en uso por otro producto.")

    for k, v in payload.model_dump().items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj

@router.delete("/{product_id}")
def delete_product(product_id: int, hard: bool = False, db: Session = Depends(get_db)):
    obj = db.get(models.Product, product_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    if hard:
        db.delete(obj)
    else:
        obj.is_active = False  # baja lógica
    db.commit()
    return {"ok": True}
