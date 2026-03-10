from fastapi import APIRouter
from backend.db import (
    get_all_appointments,
    update_appointment_status,
    set_doctor_availability,
    get_doctor_availability
)

from backend.socket_manager import send_voice_message
from backend.google_calendar import create_doctor_block

router = APIRouter()


# ---------------- APPOINTMENTS ---------------- #

@router.get("/doctor/appointments")
def fetch_all():
    return get_all_appointments()


@router.put("/doctor/appointments/{appointment_id}")
def change_status(appointment_id: int, status: str):

    update_appointment_status(appointment_id, status)

    return {"message": "Status updated"}


# ---------------- DOCTOR SCHEDULE ---------------- #

@router.post("/doctor/availability")
def update_availability(date: str, start_time: str, end_time: str, status: str):

    # save in database
    set_doctor_availability(date, start_time, end_time, status)

    # create block in Google Calendar
    create_doctor_block(date, start_time, end_time, status)

    return {"message": "Schedule updated in DB and Google Calendar"}


@router.get("/doctor/availability")
def get_availability():
    return get_doctor_availability()


# ---------------- REMINDER ---------------- #

@router.post("/doctor/reminder")
async def send_reminder():

    await send_voice_message(
        "Reminder. Your appointment is scheduled soon."
    )

    return {"message": "Reminder sent"}


# ---------------- FEEDBACK ---------------- #

@router.post("/doctor/feedback")
async def ask_feedback(id:int,email:str):

    from backend.socket_manager import send_voice_message

    await send_voice_message(
    f"Hello {email}. How was your appointment today? Please tell us about your experience.",
    email
)

    return {"message": "Feedback request sent"}
