from groq import Groq
import json
import os
from dotenv import load_dotenv
import re
load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

SYSTEM_PROMPT = """
You are an advanced NLU engine for a voice appointment assistant.

Your task:
1. Detect the user's intent.
2. Extract relevant structured entities.
3. Handle partial, ambiguous, or conversational inputs.
4. Never hallucinate missing data.
5. If uncertain, return null for that field.

INTENTS (choose exactly one):
- schedule
- reschedule
- cancel
- confirm
- check_availability
- greeting
- unknown
- feedback

ENTITIES TO EXTRACT:
- date (natural language format if provided, e.g., "tomorrow", "March 5")
- time (exact time if provided, e.g., "5 PM", "14:30")
- time_period (morning, afternoon, evening, night)
- service (type of appointment)
- name (person name if mentioned)
- email (email address if mentioned)

RULES:
- Return ONLY valid JSON.
- Do NOT include explanations.
- If a value is missing, return null.
- If input is unclear but suggests booking context, choose the most logical intent.
- Never fabricate information.
- Always return all keys.

CONFIRM INTENT RULES:
Classify as "confirm" if the user expresses agreement, approval, or readiness to proceed,
even if they do not explicitly say the word "confirm".

Examples of confirm intent include (but are not limited to):
- yes
- yes please
- okay
- okay go ahead
- that’s correct
- everything is correct
- looks good
- proceed
- book it
- fine
- alright
- sure
- sounds good
- do it
- as everything correct
- as everything current
- correct

If the user shows clear agreement to finalize the booking, choose intent = "confirm".

JSON FORMAT (strict):

{
  "intent": "",
  "date": "",
  "time": "",
  "time_period": "",
  "service": "",
  "name": "",
  "email": ""
}
"""
def detect_time_regex(text: str):

    text = text.lower()

    # detect: 11, 11 am, 11 pm, 11:00, 11:00 am, 11 o'clock
    pattern = r'(\d{1,2})(:\d{2})?\s*(am|pm|o\'?clock)?'

    match = re.search(pattern, text)

    if match:

        hour = int(match.group(1))
        minute = match.group(2) if match.group(2) else ":00"
        suffix = match.group(3)

        if suffix and "pm" in suffix and hour != 12:
            hour += 12

        if suffix and "am" in suffix and hour == 12:
            hour = 0

        return f"{hour:02d}{minute}"

    return None


def extract_nlu(text: str) -> dict:
    regex_time = detect_time_regex(text)
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text}
            ],
            temperature=0,
            max_completion_tokens=300,
            top_p=1,
            stream=False
        )

        response_text = completion.choices[0].message.content.strip()

        # Parse JSON safely
        parsed = json.loads(response_text)

        # Ensure all required keys exist
        required_keys = [
            "intent",
            "date",
            "time",
            "time_period",
            "service",
            "name",
            "email"
        ]

        for key in required_keys:
            if key not in parsed:
                parsed[key] = None

         # ---------- FIX 1: REGEX TIME ----------
        if parsed["time"] is None and regex_time:
            parsed["time"] = regex_time

        # ---------- FIX 2: TIME PERIOD ----------
        if parsed["time"] is None and parsed.get("time_period"):

            period = parsed["time_period"].lower()

            if period == "morning":
                parsed["time"] = "09:00"
            elif period == "afternoon":
                parsed["time"] = "14:00"
            elif period == "evening":
                parsed["time"] = "17:00"
            elif period == "night":
                parsed["time"] = "19:00"

        return parsed


    except Exception as e:
        print("NLU ERROR:", e)

        # Safe fallback
        return {
            "intent": "unknown",
            "date": None,
            "time": None,
            "time_period": None,
            "service": None,
            "name": None,
            "email": None
        }