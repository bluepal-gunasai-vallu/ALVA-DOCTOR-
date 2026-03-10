import mysql.connector
from backend.config import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB


# ---------------- DATABASE CONNECTION ---------------- #

def get_connection():
    return mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB
    )


# ---------------- APPOINTMENTS ---------------- #

def create_appointment(name, email, service, date_time, state, google_event_id=None):

    conn = get_connection()
    cursor = conn.cursor()

    sql = """
    INSERT INTO appointments (name, email, service, date_time, state, google_event_id)
    VALUES (%s,%s,%s,%s,%s,%s)
    """

    cursor.execute(sql, (name, email, service, date_time, state, google_event_id))

    conn.commit()

    cursor.close()
    conn.close()


def get_all_appointments():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM appointments ORDER BY date_time DESC")

    data = cursor.fetchall()

    cursor.close()
    conn.close()

    return data


def get_last_appointment_by_email(email):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM appointments WHERE email=%s ORDER BY date_time DESC LIMIT 1",
        (email,)
    )

    data = cursor.fetchone()

    cursor.close()
    conn.close()

    return data


def update_appointment_status(appointment_id, status):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE appointments SET state=%s WHERE id=%s",
        (status, appointment_id)
    )

    conn.commit()

    cursor.close()
    conn.close()


def update_appointment_datetime(appointment_id, new_datetime):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE appointments SET date_time=%s WHERE id=%s",
        (new_datetime, appointment_id)
    )

    conn.commit()

    cursor.close()
    conn.close()


def update_google_event_id(appointment_id, event_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE appointments SET google_event_id=%s WHERE id=%s",
        (event_id, appointment_id)
    )

    conn.commit()

    cursor.close()
    conn.close()


# ---------------- DOCTOR AVAILABILITY ---------------- #

def set_doctor_availability(date, start_time, end_time, status):

    conn = get_connection()
    cursor = conn.cursor()

    # check if record exists
    cursor.execute(
        "SELECT id FROM doctor_availability WHERE date=%s",
        (date,)
    )

    row = cursor.fetchone()

    if row:
        # update existing record
        cursor.execute("""
            UPDATE doctor_availability
            SET start_time=%s, end_time=%s, status=%s
            WHERE date=%s
        """, (start_time, end_time, status, date))

    else:
        # insert new record
        cursor.execute("""
            INSERT INTO doctor_availability (date,start_time,end_time,status)
            VALUES (%s,%s,%s,%s)
        """, (date, start_time, end_time, status))

    conn.commit()

    cursor.close()
    conn.close()


def get_doctor_availability():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM doctor_availability ORDER BY date ASC")

    data = cursor.fetchall()

    cursor.close()
    conn.close()

    return data


def check_doctor_time_conflict(date, time):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM doctor_availability WHERE date=%s",
        (date,)
    )

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    for r in rows:

        # 🚫 FULL DAY LEAVE
        if r["status"] == "LEAVE":
            return "LEAVE"

        # ⏰ BUSY TIME RANGE
        if r["status"] == "BUSY":

            if r["start_time"] and r["end_time"]:

                if str(r["start_time"]) <= time <= str(r["end_time"]):
                    return "BUSY"

    return None
# ---------------- FEEDBACK ---------------- #

def save_feedback(name, email, message):

    conn = get_connection()
    cursor = conn.cursor()

    sql = """
    INSERT INTO feedback (name, email, message)
    VALUES (%s, %s, %s)
    """

    cursor.execute(sql, (name, email, message))

    conn.commit()

    cursor.close()
    conn.close()
def is_doctor_on_leave(date):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM doctor_availability WHERE date=%s AND status='LEAVE'",
        (date,)
    )

    row = cursor.fetchone()

    cursor.close()
    conn.close()

    return row is not None