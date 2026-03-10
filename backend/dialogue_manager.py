from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ---------------------------------------------------
# MAIN SYSTEM PROMPT (APPOINTMENT BOOKING)
# ---------------------------------------------------

SYSTEM_PROMPT = """
You are ALVA, an intelligent voice appointment assistant.

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
- Never output JSON.
- Keep responses under 2 sentences.
- Stay friendly and professional.
"""

# ---------------------------------------------------
# FEEDBACK PROMPT
# ---------------------------------------------------

FEEDBACK_PROMPT = """
You are ALVA collecting feedback after a doctor appointment.

Conversation flow:

1. Ask the user about their appointment experience.
2. Encourage the user to speak naturally in a sentence.
3. After receiving feedback, thank the user politely.

Example:

Assistant: How was your appointment today? Please tell us about your experience.

User: The doctor explained everything clearly and was very friendly.

Assistant: Thank you for your feedback. It helps us improve our service.

Rules:
- Keep responses short
- Do not ask booking questions
- Be polite and professional
"""

# ---------------------------------------------------
# APPOINTMENT BOOKING DIALOGUE
# ---------------------------------------------------

def generate_reply(session: dict, last_user_message: str) -> str:

    # Ensure history exists
    if "history" not in session:
        session["history"] = []

    # Save user message
    session["history"].append({
        "role": "user",
        "content": last_user_message
    })

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


# ---------------------------------------------------
# FEEDBACK DIALOGUE FUNCTION
# ---------------------------------------------------

def feedback(session: dict, user_message: str) -> str:

    # Ensure feedback history exists
    if "feedback_history" not in session:
        session["feedback_history"] = []

    # Save user message
    session["feedback_history"].append({
        "role": "user",
        "content": user_message
    })

    messages = [
        {"role": "system", "content": FEEDBACK_PROMPT}
    ]

    messages.extend(session["feedback_history"][-6:])

    try:

        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.4
        )

        reply = completion.choices[0].message.content.strip()

    except Exception as e:

        print("Feedback ERROR:", e)

        reply = "Thank you for your feedback."

    session["feedback_history"].append({
        "role": "assistant",
        "content": reply
    })

    return reply