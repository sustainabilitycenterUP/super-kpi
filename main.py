from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import os
from datetime import datetime

# ========================
# Config
# ========================
API_TOKEN = os.getenv("API_TOKEN")

def verify_token(authorization: str = Header(None)):
    if authorization != f"Bearer {API_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/postgres"
)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ========================
# Models DB
# ========================
class KPIMaster(Base):
    __tablename__ = "kpi_master"
    kpi_id = Column(Integer, primary_key=True, index=True)
    fungsi_slug = Column(String, index=True)
    kpi_name = Column(String)
    iku = Column(String)
    program_prioritas = Column(String)
    bobot = Column(Float)
    target = Column(String)
    unit = Column(String)
    is_active = Column(Boolean)

class KPIUpdates(Base):
    __tablename__ = "kpi_updates"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    kpi_id = Column(Integer)
    fungsi_slug = Column(String, index=True)
    period = Column(String)  # format yyyy-mm
    value = Column(String)
    link_evidence = Column(String)
    note = Column(String)
    status = Column(String, default="submitted")
    reviewed_by = Column(String, nullable=True)
    reviewed_at = Column(String, nullable=True)

# ========================
# FastAPI init
# ========================
app = FastAPI()

# Aktifkan CORS (sebaiknya spesifik domain WP)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://super.universitaspertamina.ac.id"],  # ganti "*" kalo mau bebas
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB session dep
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ========================
# Request Schemas
# ========================
class KPIUpdateRequest(BaseModel):
    kpi_id: int
    fungsi_slug: str
    period: str
    value: str
    link_evidence: str
    note: str

# ========================
# Routes
# ========================
@app.get("/")
def root():
    return {"message": "Super KPI API running"}

@app.get("/kpi")
def get_kpi(db: Session = Depends(get_db)):
    return db.query(KPIMaster).all()

@app.get("/kpi/{fungsi_slug}")
def get_kpi_by_fungsi(fungsi_slug: str, db: Session = Depends(get_db)):
    return db.query(KPIMaster).filter(KPIMaster.fungsi_slug == fungsi_slug).all()

@app.post("/kpi/update")
def add_kpi_update(
    request: KPIUpdateRequest,
    db: Session = Depends(get_db),
    token: str = Depends(verify_token)
):
    # cek apakah KPI valid
    kpi = db.query(KPIMaster).filter(KPIMaster.kpi_id == request.kpi_id).first()
    if not kpi:
        raise HTTPException(status_code=404, detail="KPI not found")

    # cek apakah KPI sesuai fungsi_slug
    if kpi.fungsi_slug != request.fungsi_slug:
        raise HTTPException(status_code=403, detail="Tidak boleh update KPI milik fungsi lain")

    # simpan update
    update = KPIUpdates(
        kpi_id=request.kpi_id,
        fungsi_slug=request.fungsi_slug,
        period=request.period,
        value=request.value,
        link_evidence=request.link_evidence,
        note=request.note,
        status="submitted"
    )
    db.add(update)
    db.commit()
    db.refresh(update)

    return {
        "message": "KPI update berhasil",
        "id": update.id,
        "fungsi_slug": update.fungsi_slug,
        "status": update.status
    }

@app.get("/kpi/updates/{fungsi_slug}")
def get_kpi_updates_by_fungsi(fungsi_slug: str, db: Session = Depends(get_db)):
    return db.query(KPIUpdates).filter(KPIUpdates.fungsi_slug == fungsi_slug).all()

@app.get("/kpi_master/{fungsi_slug}")
def get_kpi_master_by_fungsi(fungsi_slug: str, db: Session = Depends(get_db)):
    return db.query(KPIMaster).filter(KPIMaster.fungsi_slug == fungsi_slug).all()
