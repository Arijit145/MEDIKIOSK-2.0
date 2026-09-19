from pydantic import BaseModel, Field


class PatientCreate(BaseModel):
    serial_number: int
    name: str
    age: int
    gender: str
    weight: float
    phone: str


class SymptomsCreate(BaseModel):
    patient_id: str
    symptoms: str


class QuestionAnswer(BaseModel):
    question_id: str
    selected_options: list[str] = Field(default_factory=list)
    free_text: str | None = None


class PatientAnswersCreate(BaseModel):
    patient_id: str
    answers: list[QuestionAnswer]
    family_history: str | None = None
    previous_medication: bool