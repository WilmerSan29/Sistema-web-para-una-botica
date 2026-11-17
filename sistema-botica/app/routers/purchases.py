from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from decimal import Decimal
from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/purchases", tags=["purchases"])

# ---- Proveedores básicos ----
@router.post("/suppliers", response_model=schemas.SupplierOut)
def create_supplier(payload: schemas.SupplierIn, db: Session = Depends(get_db)):
    s = models.Supplier(**payload.model_dump())
    db.add(s); db.commit(); db.refresh(s)
    return s

@router.get("/suppliers", response_model=list[schemas.SupplierOut])
def list_suppliers(db: Session = Depends(get_db)):
    return db.query(models.Supplier).order_by(models.Supplier.name.asc()).all()

# ---- Compras ----
@router.post("", response_model=schemas.PurchaseOut)
def create_purchase(payload: schemas.PurchaseIn, db: Session = Depends(get_db)):
    # evitar duplicados de documento
    exists = db.query(models.Purchase).filter(
        models.Purchase.doc_type == payload.doc_type,
        models.Purchase.series == payload.series,
        models.Purchase.number == payload.number,
    ).first()
    if exists:
        raise HTTPException(status_code=400, detail="Documento de compra ya existe.")

    purchase = models.Purchase(
        supplier_id=payload.supplier_id,
        doc_type=payload.doc_type,
        series=payload.series,
        number=payload.number,
        date=payload.date or func.now(),
        status=models.PurchaseStatus.DRAFT.value,
    )
    db.add(purchase)
    db.flush()  # obtiene purchase.id

    subtotal = Decimal("0"); tax = Decimal("0"); total = Decimal("0")
    # crear/usar lotes e ítems (sin afectar stock aún)
    for it in payload.items:
        # crear o reutilizar lote único por producto+lot_code
        batch = db.query(models.Batch).filter(
            models.Batch.product_id == it.product_id,
            models.Batch.lot_code == it.lot_code,
        ).first()
        if not batch:
            batch = models.Batch(
                product_id=it.product_id,
                lot_code=it.lot_code,
                expiry_date=it.expiry_date,
                cost=it.cost,
            )
            db.add(batch)
            db.flush()

        line_total = (Decimal(it.qty) * Decimal(it.cost)).quantize(Decimal("0.01"))
        pi = models.PurchaseItem(
            purchase_id=purchase.id,
            product_id=it.product_id,
            batch_id=batch.id,
            qty=Decimal(it.qty),
            cost=Decimal(it.cost),
            tax=Decimal("0.00"),
            total=line_total,
        )
        db.add(pi)
        subtotal += line_total

    total = subtotal  # sin IGV por ahora; luego puedes calcular IGV si quieres
    purchase.subtotal = subtotal
    purchase.tax = tax
    purchase.total = total

    db.commit()
    db.refresh(purchase)
    return purchase

@router.post("/{purchase_id}/post", response_model=schemas.PurchaseOut)
def post_purchase(purchase_id: int, db: Session = Depends(get_db)):
    purchase = db.get(models.Purchase, purchase_id)
    if not purchase:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    if purchase.status != models.PurchaseStatus.DRAFT.value:
        raise HTTPException(status_code=400, detail="La compra ya fue posteada o cancelada")

    # transacción: crear movimientos IN por cada item
    items = db.query(models.PurchaseItem).filter(models.PurchaseItem.purchase_id == purchase_id).all()
    if not items:
        raise HTTPException(status_code=400, detail="Compra sin items")

    try:
        for it in items:
            sm = models.StockMovement(
                product_id=it.product_id,
                batch_id=it.batch_id,
                type=models.StockType.IN.value,
                qty=it.qty,
                ref_table="purchases",
                ref_id=purchase_id,
            )
            db.add(sm)
        purchase.status = models.PurchaseStatus.POSTED.value
        db.commit()
        db.refresh(purchase)
        return purchase
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al postear la compra")



# ---- Listar Compras (faltaba) ----
@router.get("", response_model=list[schemas.PurchaseOut])
def list_purchases(db: Session = Depends(get_db)):
    return db.query(models.Purchase).order_by(models.Purchase.id.desc()).all()

@router.get("/{purchase_id}", response_model=schemas.PurchaseOut)
def get_purchase(purchase_id: int, db: Session = Depends(get_db)):
    purchase = db.get(models.Purchase, purchase_id)
    if not purchase:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    return purchase
