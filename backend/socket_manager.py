connections = []

async def send_voice_message(message: str, email: str = None):

    for conn in connections:
        await conn.send_json({
            "type": "voice_notification",
            "text": message,
            "mode": "feedback",
            "email": email
        })