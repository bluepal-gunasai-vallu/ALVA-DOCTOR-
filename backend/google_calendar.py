from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import datetime
import os
import pickle

SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():

    creds = None

    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)

        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)

    return service



def create_event(start_datetime, end_datetime, summary, description, attendee_email):

    service = get_calendar_service()

    event = {
        'summary': summary,
        'description': description,
        'start': {
            'dateTime': start_datetime,
            'timeZone': 'Asia/Kolkata',
        },
        'end': {
            'dateTime': end_datetime,
            'timeZone': 'Asia/Kolkata',
        },
        'attendees': [
            {'email': attendee_email},
        ],
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 1440},  # 24 hours
                {'method': 'popup', 'minutes': 30},    # 30 minutes
            ],
        },
    }

    event = service.events().insert(calendarId='primary', body=event).execute()

    return event['id']


def get_busy_slots(date):

    service = get_calendar_service()

    start_of_day = f"{date}T00:00:00+05:30"
    end_of_day = f"{date}T23:59:59+05:30"

    body = {
        "timeMin": start_of_day,
        "timeMax": end_of_day,
        "timeZone": "Asia/Kolkata",
        "items": [{"id": "primary"}]
    }

    events_result = service.freebusy().query(body=body).execute()

    busy_times = events_result['calendars']['primary']['busy']

    return busy_times


def generate_available_slots(date):

    busy_times = get_busy_slots(date)

    working_hours = range(9, 18)  # 9 AM to 5 PM

    available = []

    for hour in working_hours:
        slot_start = f"{date}T{hour:02d}:00:00+05:30"

        conflict = False
        for busy in busy_times:
            if busy['start'] <= slot_start < busy['end']:
                conflict = True
                break

        if not conflict:
            available.append(f"{hour}:00")

    return available
def delete_event(event_id):

    service = get_calendar_service()

    service.events().delete(
        calendarId="primary",
        eventId=event_id
    ).execute()

    return True
def create_doctor_block(date, start_time, end_time, status):

    service = get_calendar_service()

    start_datetime = f"{date}T{start_time}:00+05:30"
    end_datetime = f"{date}T{end_time}:00+05:30"

    event = {
        "summary": f"Doctor {status}",
        "description": "Blocked via ALVA Doctor Dashboard",
        "start": {
            "dateTime": start_datetime,
            "timeZone": "Asia/Kolkata"
        },
        "end": {
            "dateTime": end_datetime,
            "timeZone": "Asia/Kolkata"
        }
    }

    event = service.events().insert(
        calendarId="primary",
        body=event
    ).execute()

    return event["id"]