from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import Base, engine, get_db

# Patient models
from patient.models import Patient
from patient.symptoms import PatientSymptoms

# Patient routes
from patient.routes import router as patient_router

# Doctor models
from doctor.models import (
    Doctor,
    PrescriptionVersion,
    AuditLog
)

# Doctor routes
from doctor.routes import router as doctor_router

# Clinic models
from clinic.models import (
    Department,
    Room
)


# --------------------------------------------------
# FastAPI Application
# --------------------------------------------------

app = FastAPI(
    title="MediKiosk API",
    description="Backend API for the MediKiosk healthcare platform",
    version="1.0.0"
)


# --------------------------------------------------
# Database Table Creation
# --------------------------------------------------

Base.metadata.create_all(
    bind=engine
)


# --------------------------------------------------
# Routers
# --------------------------------------------------

app.include_router(
    patient_router
)

app.include_router(
    doctor_router
)


# --------------------------------------------------
# Root Endpoint
# --------------------------------------------------

@app.get("/")
def home():

    return {
        "message": "MediKiosk backend is running"
    }


# --------------------------------------------------
# Database Health Check
# --------------------------------------------------

@app.get("/health/database")
def database_health(
    db: Session = Depends(get_db)
):

    db.execute(
        text("SELECT 1")
    )

    return {
        "database": "connected"
    }