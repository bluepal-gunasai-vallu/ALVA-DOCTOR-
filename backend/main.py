from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.socket_manager import connections
from backend.session_store import get_session, save_session
from backend.nlu import extract_nlu
from backend.dialogue_manager import generate_reply, feedback
from backend.db import get_last_appointment_by_email

from backend.db import (
    create_appointment,
    check_doctor_time_conflict,
    update_appointment_status,
    get_all_appointments,
    update_appointment_datetime,
    update_google_event_id,
    is_doctor_on_leave,
    save_feedback
)

from backend.fsm import AppointmentStateMachine
from backend.google_calendar import (
    create_event,
    delete_event,
    generate_available_slots
)

from backend.doctor_routes import router as doctor_router
import uuid
import dateparser
from datetime import datetime, timedelta


app = FastAPI()

app.mount("/static", StaticFiles(directory="frontend"), name="frontend")
app.include_router(doctor_router)


@app.get("/")
def home():
    return FileResponse("frontend/index.html")

# @app.get("/")
# def home():
#     return FileResponse("frontend/doctor_dashboard.html")    


# -----------------------------
# Normalize datetime
# -----------------------------
def normalize_datetime(date_str, time_str):

    if not date_str or not time_str:
        return None

    combined = f"{date_str} {time_str}"
    parsed = dateparser.parse(combined)

    if not parsed:
        return None

    return parsed.strftime("%Y-%m-%d %H:%M:%S")


# -----------------------------
# WebSocket Assistant
# -----------------------------
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):

    await websocket.accept()
    connections.append(websocket)

    appointment_id = str(uuid.uuid4())

    state_machine = AppointmentStateMachine(
        appointment_id=appointment_id,
        current_state="INQUIRY"
    )

    try:

        while True:

            text = await websocket.receive_text()

            session = get_session(session_id)

            # -------------------------------------------------
            # RECEIVE EMAIL FROM FRONTEND (FEEDBACK FIX)
            # -------------------------------------------------
            if text.startswith("__feedback_email__:"):
                email = text.replace("__feedback_email__:", "")
                session["feedback_email"] = email
                save_session(session_id, session)
                continue


            # ---------------------------
            # ACTIVATE FEEDBACK MODE
            # ---------------------------
            if text == "__feedback_mode__":

                session["feedback_mode"] = True

                # email already sent from frontend
                save_session(session_id, session)

                # DO NOT call AI here
                continue


            # ---------------------------
            # FEEDBACK MODE HANDLING
            # ---------------------------

            if session.get("feedback_mode"):

                user_feedback = text.strip()

                email = session.get("feedback_email")

                name = None

                # fetch name from appointment
                if email:
                    appointment = get_last_appointment_by_email(email)
                    if appointment:
                        name = appointment["name"]

                save_feedback(
                    name,
                    email,
                    user_feedback
                )

                # sess
                # on["feedback_mode"] = False
                # save_session(session_id, session)

                reply = "Thank you for sharing your experience. Your feedback helps us improve."

                await websocket.send_json({
                    "type": "assistant_reply",
                    "text": reply,
                    "state": state_machine.get_state()
                })

                continue
            # ---------------------------
            # NORMAL NLU PROCESSING
            # ---------------------------

            nlu = extract_nlu(text)

            # update slots
            for key, value in nlu.items():
                if value:
                    session["slots"][key] = value

            save_session(session_id, session)

            required = ["service", "date", "time", "name", "email"]


            # ---------------------------
            # CHECK AVAILABILITY
            # ---------------------------

            if nlu.get("intent") == "check_availability":

                date = session["slots"].get("date")

                parsed_date = dateparser.parse(date)
                formatted_date = parsed_date.strftime("%Y-%m-%d")

                if is_doctor_on_leave(formatted_date):

                    reply = "Doctor is on leave that day. Please choose another date."

                else:

                    slots = generate_available_slots(formatted_date)

                    if not slots:
                        reply = "No slots available that day."
                    else:
                        reply = f"Available slots are {', '.join(slots)}"

                await websocket.send_json({
                    "type": "assistant_reply",
                    "text": reply,
                    "state": state_machine.get_state()
                })

                continue


            # ---------------------------
            # MOVE TO TENTATIVE
            # ---------------------------

            if state_machine.get_state() == "INQUIRY":

                if any(session["slots"].get(k) for k in required):

                    state_machine.transition(
                        "TENTATIVE",
                        metadata={"reason": "user_provided_details"}
                    )


            # ---------------------------
            # CONFIRM BOOKING
            # ---------------------------

            if nlu.get("intent") == "confirm":

                if all(session["slots"].get(k) for k in required):

                    state_machine.transition(
                        "CONFIRMED",
                        metadata={"reason": "user_confirmed"}
                    )


            # ---------------------------
            # SAVE APPOINTMENT
            # ---------------------------

            if state_machine.get_state() == "CONFIRMED" and not session.get("appointment_saved"):

                name = session["slots"].get("name")
                email = session["slots"].get("email")
                service = session["slots"].get("service")
                date = session["slots"].get("date")
                time = session["slots"].get("time")

                parsed_date = dateparser.parse(date)
                formatted_date = parsed_date.strftime("%Y-%m-%d")

                parsed_time = dateparser.parse(time).strftime("%H:%M:%S")

                if is_doctor_on_leave(formatted_date):

                    await websocket.send_json({
                        "type": "assistant_reply",
                        "text": "Doctor is on leave that day. Please choose another date.",
                        "state": state_machine.get_state()
                    })

                    continue

                conflict = check_doctor_time_conflict(
                    formatted_date,
                    parsed_time
                )

                if conflict == "BUSY":

                    slots = generate_available_slots(formatted_date)

                    reply = f"Doctor is busy at that time. Available slots are {', '.join(slots)}"

                    await websocket.send_json({
                        "type": "assistant_reply",
                        "text": reply,
                        "state": state_machine.get_state()
                    })

                    continue


                normalized_datetime = normalize_datetime(date, time)

                start_dt = datetime.strptime(
                    normalized_datetime,
                    "%Y-%m-%d %H:%M:%S"
                )

                end_dt = start_dt + timedelta(hours=1)

                event_id = create_event(
                    start_datetime=start_dt.isoformat(),
                    end_datetime=end_dt.isoformat(),
                    summary=f"{service}-{name}",
                    description="Booked via ALVA",
                    attendee_email=email
                )

                create_appointment(
                    name=name,
                    email=email,
                    service=service,
                    date_time=normalized_datetime,
                    state="CONFIRMED",
                    google_event_id=event_id
                )

                session["appointment_saved"] = True
                save_session(session_id, session)

                reply = "Your appointment has been booked successfully."

                await websocket.send_json({
                    "type": "assistant_reply",
                    "text": reply,
                    "state": state_machine.get_state()
                })

                continue


            # ---------------------------
            # CANCEL APPOINTMENT
            # ---------------------------

            if nlu.get("intent") == "cancel":

                email = session["slots"].get("email")

                appointments = get_all_appointments()

                found = False

                for a in appointments:

                    if a["email"] == email and a["state"] in ["CONFIRMED", "MODIFIED"]:

                        found = True

                        if a.get("google_event_id"):
                            try:
                                delete_event(a["google_event_id"])
                            except Exception as e:
                                print("Calendar delete skipped:", e)

                        update_appointment_status(a["id"], "CANCELLED")

                        state_machine.transition(
                            "CANCELLED",
                            metadata={"reason": "user_cancelled"}
                        )

                        await websocket.send_json({
                            "type": "assistant_reply",
                            "text": "Your appointment has been cancelled.",
                            "state": state_machine.get_state()
                        })

                        break

                if not found:

                    await websocket.send_json({
                        "type": "assistant_reply",
                        "text": "No active appointment found to cancel.",
                        "state": state_machine.get_state()
                    })

                continue


            # ---------------------------
            # RESCHEDULE REQUEST
            # ---------------------------

            if nlu.get("intent") == "reschedule":

                session["reschedule_mode"] = True

                session["slots"].pop("date", None)
                session["slots"].pop("time", None)

                save_session(session_id, session)

                await websocket.send_json({
                    "type": "assistant_reply",
                    "text": "Sure. What new date would you like?",
                    "state": state_machine.get_state()
                })

                continue


            # ---------------------------
            # RESCHEDULE FLOW
            # ---------------------------

            if session.get("reschedule_mode"):

                date = session["slots"].get("date")
                time = session["slots"].get("time")

                if not date:

                    reply = "What new date would you like?"

                elif not time:

                    reply = "What time works for you?"

                else:

                    email = session["slots"].get("email")

                    appointments = get_all_appointments()

                    for a in appointments:

                        if a["email"] == email and a["state"] in ["CONFIRMED", "MODIFIED"]:

                            normalized_datetime = normalize_datetime(date, time)

                            start_dt = datetime.strptime(
                                normalized_datetime,
                                "%Y-%m-%d %H:%M:%S"
                            )

                            end_dt = start_dt + timedelta(hours=1)

                            if a.get("google_event_id"):
                                try:
                                    delete_event(a["google_event_id"])
                                except Exception as e:
                                    print("Calendar delete skipped:", e)

                            event_id = create_event(
                                start_datetime=start_dt.isoformat(),
                                end_datetime=end_dt.isoformat(),
                                summary=f"{a['service']}-{a['name']}",
                                description="Rescheduled via ALVA",
                                attendee_email=email
                            )

                            update_appointment_datetime(a["id"], normalized_datetime)
                            update_google_event_id(a["id"], event_id)
                            update_appointment_status(a["id"], "MODIFIED")

                            state_machine.transition(
                                "MODIFIED",
                                metadata={"reason": "user_rescheduled"}
                            )

                            session["reschedule_mode"] = False
                            save_session(session_id, session)

                            reply = "Your appointment has been rescheduled."

                            break

                await websocket.send_json({
                    "type": "assistant_reply",
                    "text": reply,
                    "state": state_machine.get_state()
                })

                continue


            # ---------------------------
            # DEFAULT AI REPLY
            # ---------------------------

            reply = generate_reply(session, text)

            await websocket.send_json({
                "type": "assistant_reply",
                "text": reply,
                "state": state_machine.get_state()
            })


    except WebSocketDisconnect:
         if websocket in connections:
            connections.remove(websocket)

         print("Client disconnected:", session_id)