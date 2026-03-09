from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """
You are ALVA, an intelligent voice appointment assistant.

You handle two conversation modes:

1. APPOINTMENT BOOKING
2. FEEDBACK COLLECTION

----------------------
APPOINTMENT MODE
----------------------

You help users book doctor appointments.

Required information:
- service
- date
- time
- name
- email

Rules:
- Ask for only ONE missing detail at a time.
- Keep responses short and voice-friendly.
- Do not repeat questions if the information is already known.

----------------------
FEEDBACK MODE
----------------------

If the user is giving feedback about the doctor, appointment, or service:

- Thank the user for the feedback.
- Do NOT ask booking questions.
- End the conversation politely.

Example responses:
"Thank you for your feedback. We appreciate it."
"Thanks for sharing your experience."

----------------------
GENERAL RULES
----------------------

- Never output JSON.
- Keep responses under 2 sentences.
- Stay friendly and professional.
"""


def generate_reply(session: dict, last_user_message: str) -> str:

    # Ensure history exists
    if "history" not in session:
        session["history"] = []

    # Save user message
    session["history"].append({
        "role": "user",
        "content": last_user_message
    })

    # Detect feedback mode
    if session.get("feedback_mode"):

        reply = "Thank you for your feedback. We appreciate your response."

        session["history"].append({
            "role": "assistant",
            "content": reply
        })

        return reply

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "system",
            "content": f"Current collected slots: {session.get('slots', {})}"
        }
    ]

    messages.extend(session["history"][-10:])

    try:

        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.4
        )

        reply = completion.choices[0].message.content.strip()

    except Exception as e:

        print("Groq ERROR:", e)

        reply = "Sorry, something went wrong. Could you please repeat that?"

    session["history"].append({
        "role": "assistant",
        "content": reply
    })

    return reply