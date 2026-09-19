from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text,
    ForeignKey
)

from datetime import datetime

from database import Base


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    name = Column(
        String,
        nullable=False
    )

    registration_number = Column(
        String,
        unique=True,
        nullable=False,
        index=True
    )

    phone = Column(
        String,
        unique=True,
        nullable=False
    )

    email = Column(
        String,
        unique=True,
        nullable=False
    )

    department_id = Column(
        Integer,
        ForeignKey("departments.id"),
        nullable=False,
        index=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


class PrescriptionVersion(Base):
    __tablename__ = "prescription_versions"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    patient_id = Column(
        String,
        nullable=False,
        index=True
    )

    doctor_id = Column(
        Integer,
        ForeignKey("doctors.id"),
        nullable=False,
        index=True
    )

    version_number = Column(
        Integer,
        nullable=False
    )

    status = Column(
        String,
        nullable=False,
        default="DRAFT"
    )

    draft_path = Column(
        String,
        nullable=True
    )

    final_path = Column(
        String,
        nullable=True
    )

    document_hash = Column(
        String,
        nullable=True
    )

    doctor_finalized_at = Column(
        DateTime,
        nullable=True
    )

    patient_acknowledged_at = Column(
        DateTime,
        nullable=True
    )

    patient_acknowledgement_method = Column(
        String,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    patient_id = Column(
        String,
        nullable=True,
        index=True
    )

    prescription_version_id = Column(
        Integer,
        ForeignKey("prescription_versions.id"),
        nullable=True,
        index=True
    )

    actor_type = Column(
        String,
        nullable=False
    )

    actor_id = Column(
        String,
        nullable=False
    )

    action = Column(
        String,
        nullable=False
    )

    details = Column(
        Text,
        nullable=True
    )

    ip_address = Column(
        String,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )