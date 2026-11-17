# app/routers/sales.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from decimal import Decimal
from datetime import date
from typing import Optional

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/sales", tags=["sales"])

# ----------------------- Helpers -----------------------
def batch_available_qty(db: Session, batch_id: int) -> Decimal:
    """Retorna stock disponible de un lote = IN - OUT."""
    in_q = db.query(func.coalesce(func.sum(models.StockMovement.qty), 0)).filter(
        models.StockMovement.batch_id == batch_id,
        models.StockMovement.type == models.StockType.IN.value
    ).scalar()
    out_q = db.query(func.coalesce(func.sum(models.StockMovement.qty), 0)).filter(
        models.StockMovement.batch_id == batch_id,
        models.StockMovement.type == models.StockType.OUT.value
    ).scalar()
    return Decimal(in_q) - Decimal(out_q)

def allocate_fifo(db: Session, product_id: int, need_qty: Decimal):
    """
    Asigna cantidad por lotes (FIFO por fecha de vencimiento).
    Devuelve lista de tuplas (batch_id, qty_a_tomar).
    """
    allocations: list[tuple[int, Decimal]] = []
    remaining = Decimal(need_qty)

    # Primero lotes con fecha, luego sin fecha; dentro de con fecha: ASC por vencimiento
    batches = db.execute(
        select(models.Batch)
        .where(models.Batch.product_id == product_id)
        .order_by(models.Batch.expiry_date.is_(None), models.Batch.expiry_date.asc())
    ).scalars().all()

    for b in batches:
        # saltar vencidos
        if b.expiry_date and b.expiry_date < date.today():
            continue
        avail = batch_available_qty(db, b.id)
        if avail <= 0:
            continue
        take = avail if avail < remaining else remaining
        if take > 0:
            allocations.append((b.id, take))
            remaining -= take
        if remaining <= 0:
            break

    if remaining > 0:
        raise HTTPException(
            status_code=400,
            detail="Stock insuficiente o lotes válidos no disponibles."
        )

    return allocations

def next_number_for_series(db: Session, doc_type: str, series: str) -> str:
    """Calcula el siguiente correlativo (6 dígitos) para doc_type/series."""
    rows = db.query(models.Sale.number).filter(
        models.Sale.doc_type == doc_type,
        models.Sale.series == series,
    ).all()
    nums: list[int] = []
    for (n,) in rows:
        s = str(n).strip()
        if s.isdigit():
            nums.append(int(s))
    nxt = (max(nums) + 1) if nums else 1
    return f"{nxt:06d}"

# ----------------------- Endpoints -----------------------
@router.post("", response_model=schemas.SaleOut)
def create_sale(payload: schemas.SaleIn, db: Session = Depends(get_db)):
    """
    Crea la venta en estado DRAFT y sus items. Si el número llega duplicado,
    se recalcula automáticamente el siguiente correlativo.
    """
    # número final a usar
    number = payload.number

    if number:
        dup = db.query(models.Sale).filter(
            models.Sale.doc_type == payload.doc_type,
            models.Sale.series == payload.series,
            models.Sale.number == number,
        ).first()
        if dup:
            number = next_number_for_series(db, payload.doc_type, payload.series)
    else:
        # por si el schema permitiera number opcional
        number = next_number_for_series(db, payload.doc_type, payload.series)

    # crear cabecera
    sale = models.Sale(
        doc_type=payload.doc_type,
        series=payload.series,
        number=number,
        date=payload.date or func.now(),
        status=models.SaleStatus.DRAFT.value,
    )
    db.add(sale)
    db.flush()  # obtenemos sale.id

    # crear items y totales
    subtotal = Decimal("0.00")
    for it in payload.items:
        line_total = (Decimal(it.qty) * Decimal(it.price) - Decimal(it.discount)).quantize(Decimal("0.01"))
        si = models.SaleItem(
            sale_id=sale.id,
            product_id=it.product_id,
            qty=Decimal(it.qty),
            price=Decimal(it.price),
            discount=Decimal(it.discount),
            tax=Decimal("0.00"),
            total=line_total,
        )
        db.add(si)
        subtotal += line_total

    sale.subtotal = subtotal
    sale.tax = Decimal("0.00")     # si luego aplicas IGV, cámbialo aquí
    sale.total = sale.subtotal + sale.tax

    db.commit()
    db.refresh(sale)
    return sale

@router.post("/{sale_id}/post", response_model=schemas.SaleOut)
def post_sale(sale_id: int, db: Session = Depends(get_db)):
    """
    Postea la venta: genera movimientos OUT siguiendo FIFO por vencimiento
    y cambia el estado a POSTED.
    """
    sale = db.get(models.Sale, sale_id)
    if not sale:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    if sale.status != models.SaleStatus.DRAFT.value:
        raise HTTPException(status_code=400, detail="La venta ya fue posteada o cancelada")

    items = db.query(models.SaleItem).filter(models.SaleItem.sale_id == sale_id).all()
    if not items:
        raise HTTPException(status_code=400, detail="Venta sin items")

    try:
        for it in items:
            allocations = allocate_fifo(db, it.product_id, it.qty)
            for batch_id, take in allocations:
                sm = models.StockMovement(
                    product_id=it.product_id,
                    batch_id=batch_id,
                    type=models.StockType.OUT.value,
                    qty=take,
                    ref_table="sales",
                    ref_id=sale_id,
                )
                db.add(sm)
        sale.status = models.SaleStatus.POSTED.value
        db.commit()
        db.refresh(sale)
        return sale
    except HTTPException:
        db.rollback()
        raise
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al postear la venta: {ex}")

@router.get("", response_model=list[schemas.SaleOut])
def list_sales(
    doc_type: Optional[str] = None,
    series: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    q = db.query(models.Sale)
    if doc_type:
        q = q.filter(models.Sale.doc_type == doc_type)
    if series:
        q = q.filter(models.Sale.series == series)
    return q.order_by(models.Sale.id.desc()).limit(limit).all()
