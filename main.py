from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import os

# ========================
# Security
# ========================
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
    target = Column(String)
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

# CORS config (khusus domain WordPress kamu)
origins = [
    "https://super.universitaspertamina.ac.id",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          # bisa juga ["*"] untuk tes
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# Add KPI update (🔒 secure)
@app.post("/kpi/update")
def add_kpi_update(
    kpi_id: int,
    fungsi_slug: str,
    period: str,
    value: str,
    link_evidence: str,
    note: str,
    db: Session = Depends(get_db),
    token: str = Depends(verify_token)
):
    # Pastikan KPI_id yang dipilih memang milik fungsi_slug user
    kpi = db.query(KPIMaster).filter(KPIMaster.kpi_id == kpi_id).first()
    if not kpi:
        raise HTTPException(status_code=404, detail="KPI not found")
    
    if kpi.fungsi_slug != fungsi_slug:
        raise HTTPException(status_code=403, detail="Tidak boleh update KPI milik fungsi lain")

    # Simpan update
    update = KPIUpdates(
        kpi_id=kpi_id,
        fungsi_slug=fungsi_slug,
        period=period,
        value=value,
        link_evidence=link_evidence,
        note=note,
        status="submitted"
    )
    db.add(update)
    db.commit()
    db.refresh(update)
    return {"message": "KPI update berhasil", "id": update.id, "status": update.status}

# Get KPI updates by fungsi
@app.get("/kpi/updates/{fungsi_slug}")
def get_kpi_updates_by_fungsi(fungsi_slug: str, db: Session = Depends(get_db)):
    updates = db.query(KPIUpdates).filter(KPIUpdates.fungsi_slug == fungsi_slug).all()
    return updates

# Get KPI master with detail per fungsi
@app.get("/kpi_master/{fungsi_slug}")
def get_kpi_master_by_fungsi(fungsi_slug: str, db: Session = Depends(get_db)):
    return db.query(KPIMaster).filter(KPIMaster.fungsi_slug == fungsi_slug).all()
