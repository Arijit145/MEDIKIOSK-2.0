from pydantic import BaseModel, EmailStr


class DoctorRegister(BaseModel):
    name: str
    registration_number: str
    phone: str
    email: EmailStr
    department: str


class DoctorLogin(BaseModel):
    name: str
    registration_number: str
    phone: str
    email: EmailStr
    department: str