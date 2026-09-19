import json
from pathlib import Path
from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    HTTPException
)

from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import get_db

from patient.models import Patient
from patient.symptoms import PatientSymptoms

from patient.schemas import (
    PatientCreate,
    SymptomsCreate,
    PatientAnswersCreate
)

from patient.ai_questions import (
    generate_questions,
    determine_department
)

from patient.summary import create_patient_summary
from patient.receipt import create_registration_receipt

from clinic.models import Department, Room
from doctor.models import Doctor


router = APIRouter(
    prefix="/patients",
    tags=["Patients"]
)


# =========================================================
# PATIENT REGISTRATION
# =========================================================

@router.post("/register")
def register_patient(
    patient: PatientCreate,
    db: Session = Depends(get_db)
):
    current_time = datetime.now()
    current_year = current_time.year

    # -----------------------------------------------------
    # Generate Patient ID
    # Example: 15/2026
    # -----------------------------------------------------

    patient_id = f"{patient.serial_number}/{current_year}"

    # -----------------------------------------------------
    # Check whether Patient ID already exists
    # -----------------------------------------------------

    existing_patient = db.query(Patient).filter(
        Patient.patient_id == patient_id
    ).first()

    if existing_patient:
        raise HTTPException(
            status_code=409,
            detail=f"Patient ID {patient_id} already exists"
        )

    # -----------------------------------------------------
    # Create patient
    # -----------------------------------------------------

    new_patient = Patient(
        serial_number=patient.serial_number,
        patient_id=patient_id,
        name=patient.name,
        age=patient.age,
        gender=patient.gender,
        weight=patient.weight,
        phone=patient.phone
    )

    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)

    # -----------------------------------------------------
    # IMPORTANT:
    #
    # No receipt is generated here.
    #
    # Department and room are not known until the patient
    # submits symptoms.
    # -----------------------------------------------------

    return {
        "message": "Patient registered successfully",
        "patient_id": patient_id,
        "next_step": "Submit symptoms for department and room assignment"
    }


# =========================================================
# REGISTRATION RECEIPT
# =========================================================

@router.get("/receipt")
def get_registration_receipt(
    patient_id: str,
    db: Session = Depends(get_db)
):
    # -----------------------------------------------------
    # Find patient
    # -----------------------------------------------------

    patient = db.query(Patient).filter(
        Patient.patient_id == patient_id
    ).first()

    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    # -----------------------------------------------------
    # Receipt is NOT available until symptoms have been
    # submitted and a department has been assigned.
    # -----------------------------------------------------

    if patient.department_id is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Registration receipt is not available yet. "
                "Please submit symptoms first."
            )
        )

    # -----------------------------------------------------
    # Find department
    # -----------------------------------------------------

    department = db.query(Department).filter(
        Department.id == patient.department_id
    ).first()

    if not department:
        raise HTTPException(
            status_code=500,
            detail="Patient department could not be found"
        )

    # -----------------------------------------------------
    # Find room assigned to department
    # -----------------------------------------------------

    room = db.query(Room).filter(
        Room.department_id == patient.department_id
    ).first()

    if not room:
        raise HTTPException(
            status_code=500,
            detail=(
                f"No room is configured for "
                f"{department.name}"
            )
        )

    # -----------------------------------------------------
    # Registration time
    # -----------------------------------------------------

    registration_time = patient.created_at

    if registration_time is None:
        registration_time = datetime.now()

    # -----------------------------------------------------
    # Generate receipt
    # -----------------------------------------------------

    receipt_path = create_registration_receipt(
        patient_id=patient.patient_id,
        patient_name=patient.name,
        registration_time=registration_time,
        department_name=department.name,
        room_number=room.room_number
    )

    # -----------------------------------------------------
    # Return PDF
    # -----------------------------------------------------

    return FileResponse(
        path=receipt_path,
        media_type="application/pdf",
        filename=receipt_path.name
    )


# =========================================================
# SUBMIT SYMPTOMS
# =========================================================

@router.post("/symptoms")
def submit_symptoms(
    data: SymptomsCreate,
    db: Session = Depends(get_db)
):
    # -----------------------------------------------------
    # Find patient
    # -----------------------------------------------------

    patient = db.query(Patient).filter(
        Patient.patient_id == data.patient_id
    ).first()

    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    # -----------------------------------------------------
    # Validate symptoms
    # -----------------------------------------------------

    symptoms_text = data.symptoms.strip()

    if not symptoms_text:
        raise HTTPException(
            status_code=400,
            detail="Symptoms cannot be empty"
        )

    # -----------------------------------------------------
    # Ask Nemotron to determine ONLY the department
    # -----------------------------------------------------

    try:
        department_name = determine_department(
            symptoms_text
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Department routing failed: {str(e)}"
            )
        )

    # -----------------------------------------------------
    # Find department in PostgreSQL
    # -----------------------------------------------------

    department = db.query(Department).filter(
        Department.name == department_name
    ).first()

    if not department:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Department '{department_name}' "
                "does not exist in the database"
            )
        )

    # -----------------------------------------------------
    # Find doctor assigned to this department
    # -----------------------------------------------------

    doctor = db.query(Doctor).filter(
        Doctor.department_id == department.id
    ).first()

    if not doctor:
        raise HTTPException(
            status_code=503,
            detail=(
                f"No doctor is currently assigned "
                f"to the {department.name} department"
            )
        )

    # -----------------------------------------------------
    # Find room assigned to this department
    # -----------------------------------------------------

    room = db.query(Room).filter(
        Room.department_id == department.id
    ).first()

    if not room:
        raise HTTPException(
            status_code=503,
            detail=(
                f"No room is configured for "
                f"the {department.name} department"
            )
        )

    # -----------------------------------------------------
    # Save patient symptoms
    # -----------------------------------------------------

    new_symptoms = PatientSymptoms(
        patient_id=data.patient_id,
        symptoms=symptoms_text
    )

    db.add(new_symptoms)

    # -----------------------------------------------------
    # Assign department to patient
    # -----------------------------------------------------

    patient.department_id = department.id

    # -----------------------------------------------------
    # Save changes
    # -----------------------------------------------------

    db.commit()
    db.refresh(new_symptoms)
    db.refresh(patient)

    # -----------------------------------------------------
    # NOW generate the registration receipt.
    #
    # At this point we know:
    # - Patient
    # - Department
    # - Doctor
    # - Room
    # -----------------------------------------------------

    registration_time = patient.created_at

    if registration_time is None:
        registration_time = datetime.now()

    create_registration_receipt(
        patient_id=patient.patient_id,
        patient_name=patient.name,
        registration_time=registration_time,
        department_name=department.name,
        room_number=room.room_number
    )

    # -----------------------------------------------------
    # Return routing result
    # -----------------------------------------------------

    return {
        "message": "Symptoms submitted successfully",
        "patient_id": patient.patient_id,
        "symptoms": symptoms_text,
        "department": department.name,
        "doctor": doctor.name,
        "room": room.room_number,
        "receipt": (
            f"/patients/receipt"
            f"?patient_id={patient.patient_id}"
        )
    }


# =========================================================
# GENERATE FOLLOW-UP QUESTIONS
# =========================================================

@router.post("/generate-questions")
def generate_patient_questions(
    patient_id: str,
    db: Session = Depends(get_db)
):
    # -----------------------------------------------------
    # Find latest symptom record
    # -----------------------------------------------------

    record = db.query(PatientSymptoms).filter(
        PatientSymptoms.patient_id == patient_id
    ).order_by(
        PatientSymptoms.id.desc()
    ).first()

    if not record:
        raise HTTPException(
            status_code=404,
            detail="Symptoms not found for this patient"
        )

    # -----------------------------------------------------
    # Generate questions using Nemotron
    # -----------------------------------------------------

    try:
        result = generate_questions(
            record.symptoms
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Nemotron question generation failed: {str(e)}"
            )
        )

    # -----------------------------------------------------
    # Store questions as JSON
    # -----------------------------------------------------

    record.generated_questions = json.dumps(
        result.model_dump()
    )

    db.commit()

    return result


# =========================================================
# SUBMIT PATIENT ANSWERS
# =========================================================

@router.post("/answers")
def submit_patient_answers(
    data: PatientAnswersCreate,
    db: Session = Depends(get_db)
):
    # -----------------------------------------------------
    # Find latest symptom record
    # -----------------------------------------------------

    record = db.query(PatientSymptoms).filter(
        PatientSymptoms.patient_id == data.patient_id
    ).order_by(
        PatientSymptoms.id.desc()
    ).first()

    if not record:
        raise HTTPException(
            status_code=404,
            detail="Patient symptom record not found"
        )

    # -----------------------------------------------------
    # Save answers
    # -----------------------------------------------------

    record.answers = json.dumps(
        [
            answer.model_dump()
            for answer in data.answers
        ]
    )

    # -----------------------------------------------------
    # Save family history
    # -----------------------------------------------------

    record.family_history = data.family_history

    # -----------------------------------------------------
    # Save previous medication information
    # -----------------------------------------------------

    record.previous_medication = (
        data.previous_medication
    )

    db.commit()

    return {
        "message": "Patient answers saved successfully",
        "patient_id": data.patient_id
    }


# =========================================================
# UPLOAD PREVIOUS PRESCRIPTION
# =========================================================

@router.post("/prescription")
async def upload_previous_prescription(
    patient_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # -----------------------------------------------------
    # Find latest symptom record
    # -----------------------------------------------------

    record = db.query(PatientSymptoms).filter(
        PatientSymptoms.patient_id == patient_id
    ).order_by(
        PatientSymptoms.id.desc()
    ).first()

    if not record:
        raise HTTPException(
            status_code=404,
            detail="Patient symptom record not found"
        )

    # -----------------------------------------------------
    # Create upload directory
    # -----------------------------------------------------

    upload_directory = Path(
        "uploads/prescriptions"
    )

    upload_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    # -----------------------------------------------------
    # Get original filename
    # -----------------------------------------------------

    original_name = file.filename or "prescription"

    # -----------------------------------------------------
    # Create safe filename
    # -----------------------------------------------------

    timestamp = datetime.now().strftime(
        "%Y%m%d%H%M%S%f"
    )

    safe_patient_id = patient_id.replace(
        "/",
        "_"
    )

    safe_original_name = Path(
        original_name
    ).name

    filename = (
        f"{safe_patient_id}_"
        f"{timestamp}_"
        f"{safe_original_name}"
    )

    file_path = upload_directory / filename

    # -----------------------------------------------------
    # Preserve uploaded file unchanged
    # -----------------------------------------------------

    contents = await file.read()

    with open(file_path, "wb") as buffer:
        buffer.write(contents)

    # -----------------------------------------------------
    # Store file information
    # -----------------------------------------------------

    record.prescription_path = str(
        file_path
    )

    record.prescription_original_name = (
        original_name
    )

    db.commit()

    return {
        "message": (
            "Previous prescription uploaded "
            "successfully"
        ),
        "patient_id": patient_id,
        "original_filename": original_name
    }


# =========================================================
# GENERATE PATIENT SUMMARY
# =========================================================

@router.post("/summary")
def generate_patient_summary(
    patient_id: str,
    db: Session = Depends(get_db)
):
    # -----------------------------------------------------
    # Find patient
    # -----------------------------------------------------

    patient = db.query(Patient).filter(
        Patient.patient_id == patient_id
    ).first()

    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    # -----------------------------------------------------
    # Find latest symptom record
    # -----------------------------------------------------

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
            detail="Patient symptom record not found"
        )

    # -----------------------------------------------------
    # Generate DOCX summary
    # -----------------------------------------------------

    try:
        summary_path = create_patient_summary(
            patient,
            symptom_record
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Summary generation failed: {str(e)}"
            )
        )

    # -----------------------------------------------------
    # Store summary information
    # -----------------------------------------------------

    symptom_record.summary_path = str(
        summary_path
    )

    symptom_record.summary_original_name = (
        summary_path.name
    )

    db.commit()

    return {
        "message": "Patient summary generated successfully",
        "patient_id": patient_id,
        "summary_filename": summary_path.name,
        "download_url": (
            "/patients/summary/download"
            f"?patient_id={patient_id}"
        )
    }


# =========================================================
# DOWNLOAD PATIENT SUMMARY
# =========================================================

@router.get("/summary/download")
def download_patient_summary(
    patient_id: str,
    db: Session = Depends(get_db)
):
    # -----------------------------------------------------
    # Find latest symptom record
    # -----------------------------------------------------

    record = db.query(
        PatientSymptoms
    ).filter(
        PatientSymptoms.patient_id == patient_id
    ).order_by(
        PatientSymptoms.id.desc()
    ).first()

    if not record:
        raise HTTPException(
            status_code=404,
            detail="Patient symptom record not found"
        )

    # -----------------------------------------------------
    # Check summary path
    # -----------------------------------------------------

    if not record.summary_path:
        raise HTTPException(
            status_code=404,
            detail=(
                "Patient summary has not been generated"
            )
        )

    # -----------------------------------------------------
    # Check file exists
    # -----------------------------------------------------

    summary_path = Path(
        record.summary_path
    )

    if not summary_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Summary file not found"
        )

    # -----------------------------------------------------
    # Return DOCX
    # -----------------------------------------------------

    return FileResponse(
        path=summary_path,
        media_type=(
            "application/vnd.openxmlformats-"
            "officedocument.wordprocessingml.document"
        ),
        filename=summary_path.name
    )