from fastapi import FastAPI, Depends, HTTPException, Header
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import os
from datetime import datetime
from fastapi import Path

API_TOKEN = os.getenv("API_TOKEN")

def verify_token(authorization: str = Header(None)):
    if authorization != f"Bearer {API_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")
        
# ========================
# Database setup
# ========================
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/postgres")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ========================
# Models
# ========================
class KPIMaster(Base):
    __tablename__ = "kpi_master"
    kpi_id = Column(Integer, primary_key=True, index=True)
    fungsi_slug = Column(String, index=True)
    kpi_name = Column(String)
    iku = Column(String)
    program_prioritas = Column(String)
    bobot = Column(Float)
    target = Column(Float)
    unit = Column(String)
    is_active = Column(Boolean)

class KPIUpdates(Base):
    __tablename__ = "kpi_updates"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    kpi_id = Column(Integer)
    fungsi_slug = Column(String, index=True)
    period = Column(String)  # format yyyy-mm
    value = Column(String)   # biar fleksibel, sesuai tabel
    link_evidence = Column(String)
    note = Column(String)
    status = Column(String, default="submitted")  # submitted / approved / rejected
    reviewed_by = Column(String, nullable=True)
    reviewed_at = Column(String, nullable=True)


# ========================
# FastAPI init
# ========================
app = FastAPI()

# Dependency DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ========================
# Routes
# ========================

@app.get("/")
def root():
    return {"message": "Super KPI API running"}

# Get all KPI master
@app.get("/kpi")
def get_kpi(db: Session = Depends(get_db)):
    return db.query(KPIMaster).all()

# Get KPI by fungsi
@app.get("/kpi/{fungsi_slug}")
def get_kpi_by_fungsi(fungsi_slug: str, db: Session = Depends(get_db)):
    return db.query(KPIMaster).filter(KPIMaster.fungsi_slug == fungsi_slug).all()

# Add KPI update
@app.post("/kpi/update")
def add_kpi_update(
    kpi_id: int,
    fungsi_slug: str,
    period: str,
    value: float,
    link_evidence: str,
    note: str,
    token: str = Depends(verify_token)   # ⬅️ taruh dependensinya disini
):
    update = KPIUpdates(
        kpi_id=kpi_id,
        fungsi_slug=fungsi_slug,
        period=period,
        value=value,
        link_evidence=link_evidence,
        note=note
    )
    # simpan ke DB
    session.add(update)
    session.commit()
    return {"message": "KPI update berhasil"}

# Review KPI update (approve/reject)
@app.post("/kpi/review/{update_id}")
def review_kpi_update(
    update_id: int = Path(..., description="ID dari update yang mau direview"),
    status: str = "approved",   # "approved" atau "rejected"
    reviewed_by: str = "manager",
    db: Session = Depends(get_db),
    token: str = Depends(verify_token)   # tetap pakai token biar aman
):
    update = db.query(KPIUpdates).filter(KPIUpdates.id == update_id).first()
    if not update:
        raise HTTPException(status_code=404, detail="KPI update tidak ditemukan")

    if status not in ["approved", "rejected"]:
        raise HTTPException(status_code=400, detail="Status harus 'approved' atau 'rejected'")

    update.status = status
    update.reviewed_by = reviewed_by
    update.reviewed_at = datetime.utcnow().isoformat()

    db.commit()
    return {"message": f"KPI update {update_id} berhasil di-{status}"}
