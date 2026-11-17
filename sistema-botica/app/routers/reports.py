from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app import models
from datetime import date
from sqlalchemy import func, case

router = APIRouter(prefix="/reports", tags=["reports"])

# --- Reporte de Ventas ---
@router.get("/sales")
def report_sales(db: Session = Depends(get_db)):
    data = (
        db.query(
            func.date(models.Sale.date).label("fecha"),
            func.count(models.Sale.id).label("num_ventas"),
            func.sum(models.Sale.total).label("total_vendido"),
        )
        .filter(models.Sale.status == models.SaleStatus.POSTED.value)
        .group_by(func.date(models.Sale.date))
        .order_by(func.date(models.Sale.date))
        .all()
    )

    # Convertir a formato legible
    result = [
        {
            "fecha": str(r.fecha),
            "num_ventas": r.num_ventas,
            "total_vendido": float(r.total_vendido or 0),
        }
        for r in data
    ]
    return result


# reporte de inventario 

@router.get("/inventory")
def report_inventory(db: Session = Depends(get_db)):
    qty_in = func.sum(case((models.StockMovement.type == "IN", models.StockMovement.qty), else_=0))
    qty_out = func.sum(case((models.StockMovement.type == "OUT", models.StockMovement.qty), else_=0))
    stock_expr = (qty_in - qty_out).label("stock_disponible")

    rows = (
        db.query(
            models.Product.name.label("producto"),
            models.Batch.lot_code.label("lote"),
            models.Batch.expiry_date.label("vencimiento"),
            stock_expr,
        )
        .select_from(models.StockMovement)
        .join(models.Batch, models.StockMovement.batch_id == models.Batch.id)
        .join(models.Product, models.Batch.product_id == models.Product.id)
        .group_by(models.Product.name, models.Batch.lot_code, models.Batch.expiry_date)
        .having(stock_expr > 0)
        .order_by(models.Product.name.asc(), models.Batch.expiry_date.asc())
        .all()
    )

    return [
        {
            "producto": r.producto,
            "lote": r.lote,
            "vencimiento": r.vencimiento,
            "stock_disponible": float(r.stock_disponible or 0),
        }
        for r in rows
    ]


# --- Reporte de Vencimientos ---
@router.get("/alerts/expirations")
def alert_expirations(db: Session = Depends(get_db)):
    hoy = date.today()
    proximos = hoy.replace(day=1).replace(month=hoy.month + 1)  # próximos 30 días
    data = (
        db.query(
            models.Product.name,
            models.Batch.lot_code,
            models.Batch.expiry_date,
        )
        .filter(models.Batch.expiry_date <= proximos)
        .all()
    )
    return [
        {"producto": d.name, "lote": d.lot_code, "vencimiento": d.expiry_date}
        for d in data
    ]



# --- Reporte simple de productos vendidos por día ---
@router.get("/sales_by_product")
def report_sales_by_product(db: Session = Depends(get_db)):
    data = (
        db.query(
            func.date(models.Sale.date).label("fecha"),
            models.Product.name.label("producto"),
            func.sum(models.SaleItem.qty).label("cantidad_vendida"),
            func.sum(models.SaleItem.total).label("total_vendido"),
        )
        .join(models.SaleItem, models.Sale.id == models.SaleItem.sale_id)
        .join(models.Product, models.SaleItem.product_id == models.Product.id)
        .filter(models.Sale.status == models.SaleStatus.POSTED.value)
        .group_by(func.date(models.Sale.date), models.Product.name)
        .order_by(func.date(models.Sale.date).desc())
        .all()
    )

    return [
        {
            "fecha": str(r.fecha),
            "producto": r.producto,
            "cantidad_vendida": float(r.cantidad_vendida or 0),
            "total_vendido": float(r.total_vendido or 0),
        }
        for r in data
    ]

