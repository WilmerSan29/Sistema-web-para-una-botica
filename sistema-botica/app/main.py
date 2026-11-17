from sqlalchemy.orm import Mapped, mapped_column, relationship
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app import models   # <-- AÑADE ESTA LÍNEA

Base.metadata.create_all(bind=engine)

# Crear tablas (en desarrollo)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Sistema Botica API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/ping")
def ping():
    return {"message": "pong"}

# --- Routers ---
from app.routers import categories, products
app.include_router(categories.router)
app.include_router(products.router)

from app.routers import purchases
app.include_router(purchases.router)

from app.routers import reports
app.include_router(reports.router)

from app.routers import sales
app.include_router(sales.router)


