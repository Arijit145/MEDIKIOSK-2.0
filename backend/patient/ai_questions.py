from openai import OpenAI
from pydantic import BaseModel
from typing import List

from config import settings


# ==================================================
# QUESTION MODELS
# ==================================================

class Question(BaseModel):
    question_id: str
    question: str
    input_type: str
    options: List[str]
    allow_multiple: bool


class QuestionResponse(BaseModel):
    questions: List[Question]


# ==================================================
# NVIDIA NEMOTRON CLIENT
# ==================================================

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=settings.NVIDIA_API_KEY
)


MODEL_NAME = "nvidia/nemotron-3-super-120b-a12b"


# ==================================================
# GENERATE FOLLOW-UP QUESTIONS
# ==================================================

def generate_questions(symptoms: str) -> QuestionResponse:

    prompt = f"""
You are an AI assistant used by a medical
history-taking system.

The patient reported these symptoms:

{symptoms}

Your task is ONLY to generate relevant
medical history questions.

DO NOT:
- diagnose the patient
- recommend medicines
- recommend treatment
- provide a final medical conclusion

RULES:

1. Generate only questions relevant to the
   patient's symptoms.

2. Questions must be easy for a normal patient
   to understand.

3. Prefer selectable questions.

4. Use "radio" when only ONE option can be selected.

5. Use "checkbox" when MULTIPLE options can
   be selected.

6. Every selectable question must have clear
   options.

7. When appropriate, ask about:
   - duration
   - severity
   - associated symptoms
   - relevant medical history

8. Do not generate irrelevant questions.

9. If the symptoms could reasonably indicate
   an infectious or household-spreading illness,
   include:

   "Does anyone in your family or household
   have the same or similar symptoms?"

   Options:
   - Yes
   - No

10. If the family/household question is included,
    the application will separately allow the
    patient to specify WHO has the symptoms.

11. Return ONLY valid JSON matching this structure:

{{
    "questions": [
        {{
            "question_id": "q1",
            "question": "Example question",
            "input_type": "radio",
            "options": ["Option 1", "Option 2"],
            "allow_multiple": false
        }}
    ]
}}
"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        response_format={
            "type": "json_object"
        },
        temperature=0.2,
        max_tokens=1500,
        extra_body={
            "chat_template_kwargs": {
                "enable_thinking": False
            }
        }
    )

    result = response.choices[0].message.content

    return QuestionResponse.model_validate_json(result)


# ==================================================
# DETERMINE MEDICAL DEPARTMENT
# ==================================================

def determine_department(symptoms: str) -> str:
    """
    Determines the appropriate clinic department
    from the patient's symptoms.

    The AI must return ONLY a department name.

    It must NOT:
    - choose a doctor
    - choose a room
    - diagnose the patient
    - recommend treatment
    - recommend medicine
    """

    prompt = f"""
You are a medical department routing assistant
for a clinic.

Your ONLY task is to determine which clinic
department should receive the patient.

Patient symptoms:

{symptoms}

Available departments:

- General Medicine
- Gynaecology
- Ophthalmology
- Dermatology
- ENT
- Orthopaedics
- Paediatrics

Return ONLY ONE department name from the
available departments.

The response MUST be exactly one of these:

General Medicine
Gynaecology
Ophthalmology
Dermatology
ENT
Orthopaedics
Paediatrics

Do not provide:
- diagnosis
- treatment
- medicine
- doctor name
- room number
- explanation
- additional text

Department:
"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0,
        max_tokens=50,
        extra_body={
            "chat_template_kwargs": {
                "enable_thinking": False
            }
        }
    )

    department = response.choices[0].message.content.strip()

    # ----------------------------------------------
    # BACKEND VALIDATION
    # ----------------------------------------------

    allowed_departments = {
        "General Medicine",
        "Gynaecology",
        "Ophthalmology",
        "Dermatology",
        "ENT",
        "Orthopaedics",
        "Paediatrics"
    }

    if department not in allowed_departments:
        raise ValueError(
            f"AI returned an invalid department: {department}"
        )

    return department