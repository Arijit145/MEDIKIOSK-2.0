from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)

from fastapi.responses import FileResponse

from sqlalchemy.orm import Session

from database import get_db

from doctor.models import Doctor
from doctor.schemas import (
    DoctorRegister,
    DoctorLogin
)

from clinic.models import Department

from patient.models import Patient
from patient.symptoms import PatientSymptoms


router = APIRouter(
    prefix="/doctors",
    tags=["Doctors"]
)


# ==================================================
# DOCTOR REGISTRATION
# ==================================================

@router.post("/register")
def register_doctor(
    doctor: DoctorRegister,
    db: Session = Depends(get_db)
):

    # ----------------------------------------------
    # FIND DEPARTMENT
    # ----------------------------------------------

    department = db.query(
        Department
    ).filter(
        Department.name == doctor.department.strip()
    ).first()

    if not department:

        raise HTTPException(
            status_code=400,
            detail=(
                f"Department '{doctor.department}' "
                "does not exist"
            )
        )

    # ----------------------------------------------
    # CHECK REGISTRATION NUMBER
    # ----------------------------------------------

    existing_doctor = db.query(
        Doctor
    ).filter(
        Doctor.registration_number
        == doctor.registration_number
    ).first()

    if existing_doctor:

        raise HTTPException(
            status_code=409,
            detail=(
                "Doctor with this registration "
                "number already exists"
            )
        )

    # ----------------------------------------------
    # CHECK PHONE
    # ----------------------------------------------

    existing_phone = db.query(
        Doctor
    ).filter(
        Doctor.phone == doctor.phone
    ).first()

    if existing_phone:

        raise HTTPException(
            status_code=409,
            detail=(
                "This phone number is already registered"
            )
        )

    # ----------------------------------------------
    # CHECK EMAIL
    # ----------------------------------------------

    existing_email = db.query(
        Doctor
    ).filter(
        Doctor.email == doctor.email
    ).first()

    if existing_email:

        raise HTTPException(
            status_code=409,
            detail=(
                "This email is already registered"
            )
        )

    # ----------------------------------------------
    # CREATE DOCTOR
    # ----------------------------------------------

    new_doctor = Doctor(
        name=doctor.name,
        registration_number=doctor.registration_number,
        phone=doctor.phone,
        email=doctor.email,
        department_id=department.id
    )

    db.add(new_doctor)

    db.commit()

    db.refresh(new_doctor)

    return {
        "message": "Doctor registered successfully",
        "doctor_id": new_doctor.id,
        "name": new_doctor.name,
        "registration_number":
            new_doctor.registration_number,
        "department_id": department.id,
        "department": department.name
    }


# ==================================================
# DOCTOR LOGIN
# ==================================================

@router.post("/login")
def doctor_login(
    doctor: DoctorLogin,
    db: Session = Depends(get_db)
):

    # ----------------------------------------------
    # FIND DEPARTMENT
    # ----------------------------------------------

    department = db.query(
        Department
    ).filter(
        Department.name == doctor.department.strip()
    ).first()

    if not department:

        raise HTTPException(
            status_code=400,
            detail="Department does not exist"
        )

    # ----------------------------------------------
    # FIND DOCTOR
    # ----------------------------------------------

    existing_doctor = db.query(
        Doctor
    ).filter(
        Doctor.registration_number
        == doctor.registration_number,

        Doctor.phone
        == doctor.phone,

        Doctor.email
        == doctor.email,

        Doctor.name
        == doctor.name,

        Doctor.department_id
        == department.id
    ).first()

    if not existing_doctor:

        raise HTTPException(
            status_code=401,
            detail="Doctor credentials are incorrect"
        )

    return {
        "message": "Doctor login successful",

        "doctor_id": existing_doctor.id,

        "name": existing_doctor.name,

        "registration_number":
            existing_doctor.registration_number,

        "email": existing_doctor.email,

        "department_id":
            existing_doctor.department_id,

        "department":
            department.name
    }


# ==================================================
# GET PATIENT CASE FOR DOCTOR
# ==================================================

@router.get("/patient-summary")
def get_patient_summary_for_doctor(
    patient_id: str,
    doctor_id: int,
    db: Session = Depends(get_db)
):

    # ----------------------------------------------
    # FIND DOCTOR
    # ----------------------------------------------

    doctor = db.query(
        Doctor
    ).filter(
        Doctor.id == doctor_id
    ).first()

    if not doctor:

        raise HTTPException(
            status_code=404,
            detail="Doctor not found"
        )

    # ----------------------------------------------
    # MAKE SURE DOCTOR HAS A DEPARTMENT
    # ----------------------------------------------

    if doctor.department_id is None:

        raise HTTPException(
            status_code=409,
            detail=(
                "Doctor is not assigned to a department"
            )
        )

    # ----------------------------------------------
    # FIND PATIENT
    # ----------------------------------------------

    patient = db.query(
        Patient
    ).filter(
        Patient.patient_id == patient_id
    ).first()

    if not patient:

        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    # ----------------------------------------------
    # MAKE SURE PATIENT HAS A DEPARTMENT
    # ----------------------------------------------

    if patient.department_id is None:

        raise HTTPException(
            status_code=409,
            detail=(
                "Patient has not been assigned "
                "to a department yet"
            )
        )

    # ----------------------------------------------
    # DEPARTMENT AUTHORIZATION
    # ----------------------------------------------

    if doctor.department_id != patient.department_id:

        raise HTTPException(
            status_code=403,
            detail=(
                "Access denied. This patient is "
                "assigned to another department."
            )
        )

    # ----------------------------------------------
    # FIND LATEST PATIENT CASE
    # ----------------------------------------------

    symptom_record = db.query(
        PatientSymptoms
    ).filter(
        PatientSymptoms.patient_id == patient_id
    ).order_by(
        PatientSymptoms.id.desc()
    ).first()

    if not symptom_record:

        raise HTTPException(
            status_code=404,
            detail="Patient case record not found"
        )

    # ----------------------------------------------
    # CHECK DOCX
    # ----------------------------------------------

    if not symptom_record.summary_path:

        raise HTTPException(
            status_code=404,
            detail=(
                "Patient summary has not been "
                "generated yet"
            )
        )

    # ----------------------------------------------
    # CHECK FILE EXISTS
    # ----------------------------------------------

    summary_path = Path(
        symptom_record.summary_path
    )

    if not summary_path.exists():

        raise HTTPException(
            status_code=404,
            detail="Patient summary file not found"
        )

    # ----------------------------------------------
    # RETURN DOCX
    # ----------------------------------------------

    return FileResponse(
        path=summary_path,

        media_type=(
            "application/vnd.openxmlformats-"
            "officedocument.wordprocessingml.document"
        ),

        filename=summary_path.name
    )