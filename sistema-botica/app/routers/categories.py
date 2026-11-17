from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/categories", tags=["categories"])

@router.post("", response_model=schemas.CategoryOut)
def create_category(payload: schemas.CategoryIn, db: Session = Depends(get_db)):
    # validación única
    if db.query(models.Category).filter(models.Category.name == payload.name).first():
        raise HTTPException(status_code=400, detail="La categoría ya existe.")
    obj = models.Category(name=payload.name)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.get("", response_model=list[schemas.CategoryOut])
def list_categories(
    q: str | None = Query(default=None, description="Buscar por nombre"),
    db: Session = Depends(get_db),
):
    query = db.query(models.Category)
    if q:
        query = query.filter(models.Category.name.ilike(f"%{q}%"))
    return query.order_by(models.Category.name.asc()).all()

@router.get("/{category_id}", response_model=schemas.CategoryOut)
def get_category(category_id: int, db: Session = Depends(get_db)):
    obj = db.get(models.Category, category_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return obj

@router.put("/{category_id}", response_model=schemas.CategoryOut)
def update_category(category_id: int, payload: schemas.CategoryIn, db: Session = Depends(get_db)):
    obj = db.get(models.Category, category_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    # verificar nombre único
    exists = db.query(models.Category).filter(
        models.Category.name == payload.name, models.Category.id != category_id
    ).first()
    if exists:
        raise HTTPException(status_code=400, detail="Ya existe otra categoría con ese nombre.")
    obj.name = payload.name
    db.commit()
    db.refresh(obj)
    return obj

@router.delete("/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db)):
    obj = db.get(models.Category, category_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    db.delete(obj)
    db.commit()
    return {"ok": True}
