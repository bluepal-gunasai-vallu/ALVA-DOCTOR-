connections = []

async def send_voice_message(message: str):

    for conn in connections:
        await conn.send_json({
            "type": "voice_notification",
            "text": message,
            "mode": "feedback"
        })