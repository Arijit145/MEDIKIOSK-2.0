from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey
)

from database import Base


class Department(Base):
    __tablename__ = "departments"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    name = Column(
        String,
        unique=True,
        nullable=False,
        index=True
    )


class Room(Base):
    __tablename__ = "rooms"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    room_number = Column(
        String,
        unique=True,
        nullable=False
    )

    department_id = Column(
        Integer,
        ForeignKey("departments.id"),
        unique=True,
        nullable=False
    )