# Simple in-memory session storage

sessions = {}

def get_session(session_id):
    if session_id not in sessions:
        sessions[session_id] = {
            "fsm_state": "INQUIRY",
            "slots": {}
        }
    return sessions[session_id]


def save_session(session_id, data):
    sessions[session_id] = data


def clear_session(session_id):
    if session_id in sessions:
        del sessions[session_id]