from pathlib import Path
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A5
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import mm


def create_registration_receipt(
    patient_id: str,
    patient_name: str,
    registration_time: datetime,
    department_name: str = "Pending symptom assessment",
    room_number: str = "Pending"
) -> Path:
    """
    Create the MediKiosk patient registration receipt.

    The receipt contains:
    - Patient name
    - Registration date
    - Exact registration time
    - Patient ID
    - Assigned department
    - Assigned room

    Returns:
        Path: Path to the generated PDF receipt.
    """

    # ---------------------------------------------------------
    # Create receipt directory
    # ---------------------------------------------------------

    receipt_directory = Path("uploads/receipts")
    receipt_directory.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------
    # Create a safe filename
    # Example:
    # Patient ID: 18/2026
    # File: receipt_18_2026.pdf
    # ---------------------------------------------------------

    safe_patient_id = patient_id.replace("/", "_")

    receipt_path = receipt_directory / f"receipt_{safe_patient_id}.pdf"

    # ---------------------------------------------------------
    # Escape text before putting it inside ReportLab Paragraphs
    # ---------------------------------------------------------

    safe_patient_name = escape(str(patient_name))
    safe_patient_id_text = escape(str(patient_id))
    safe_department = escape(str(department_name))
    safe_room = escape(str(room_number))

    # ---------------------------------------------------------
    # Styles
    # ---------------------------------------------------------

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReceiptTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=18,
        leading=22,
        spaceAfter=8
    )

    subtitle_style = ParagraphStyle(
        "ReceiptSubtitle",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=11,
        leading=16
    )

    normal_center_style = ParagraphStyle(
        "ReceiptNormal",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=11,
        leading=16
    )

    patient_id_style = ParagraphStyle(
        "PatientID",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=18,
        leading=22
    )

    department_style = ParagraphStyle(
        "Department",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=13,
        leading=18
    )

    # ---------------------------------------------------------
    # Create PDF document
    # ---------------------------------------------------------

    document = SimpleDocTemplate(
        str(receipt_path),
        pagesize=A5,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm
    )

    content = []

    # ---------------------------------------------------------
    # Header
    # ---------------------------------------------------------

    content.append(
        Paragraph(
            "MEDIKIOSK",
            title_style
        )
    )

    content.append(
        Paragraph(
            "Patient Registration Receipt",
            subtitle_style
        )
    )

    content.append(
        Spacer(1, 10)
    )

    # ---------------------------------------------------------
    # Patient details
    # ---------------------------------------------------------

    content.append(
        Paragraph(
            f"<b>Patient Name:</b> {safe_patient_name}",
            normal_center_style
        )
    )

    content.append(
        Paragraph(
            f"<b>Date:</b> {registration_time.strftime('%d/%m/%Y')}",
            normal_center_style
        )
    )

    content.append(
        Paragraph(
            f"<b>Time:</b> {registration_time.strftime('%H:%M:%S')}",
            normal_center_style
        )
    )

    content.append(
        Spacer(1, 10)
    )

    # ---------------------------------------------------------
    # Patient ID
    # ---------------------------------------------------------

    content.append(
        Paragraph(
            "<b>Patient ID</b>",
            normal_center_style
        )
    )

    content.append(
        Spacer(1, 4)
    )

    content.append(
        Paragraph(
            f"<b>{safe_patient_id_text}</b>",
            patient_id_style
        )
    )

    content.append(
        Spacer(1, 12)
    )

    # ---------------------------------------------------------
    # Department
    # ---------------------------------------------------------

    content.append(
        Paragraph(
            f"<b>Department:</b><br/>{safe_department}",
            department_style
        )
    )

    content.append(
        Spacer(1, 8)
    )

    # ---------------------------------------------------------
    # Room
    # ---------------------------------------------------------

    content.append(
        Paragraph(
            f"<b>Room:</b> {safe_room}",
            department_style
        )
    )

    content.append(
        Spacer(1, 15)
    )

    # ---------------------------------------------------------
    # Instructions
    # ---------------------------------------------------------

    content.append(
        Paragraph(
            "Please keep this receipt safely.",
            normal_center_style
        )
    )

    content.append(
        Paragraph(
            "Your Patient ID will be required for future visits.",
            normal_center_style
        )
    )

    # ---------------------------------------------------------
    # Build PDF
    # ---------------------------------------------------------

    document.build(content)

    return receipt_path