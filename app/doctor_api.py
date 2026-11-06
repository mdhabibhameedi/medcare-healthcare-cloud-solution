
from flask import Flask, jsonify, request
from pathlib import Path
from datetime import datetime
import csv
import json
import threading

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parents[1]
SCHEDULE_FILE = BASE_DIR / "data" / "raw" / "doctor_schedules.json"
PATIENT_FILE = BASE_DIR / "data" / "raw" / "patients.csv"

lock = threading.Lock()


def appointment_table():
    import boto3
    return boto3.resource(
        "dynamodb", region_name="eu-north-1"
    ).Table("MedCare-M7-Appointments")


def load_slots():
    with SCHEDULE_FILE.open("r", encoding="utf-8") as file:
        slots = json.load(file)

    table = appointment_table()
    for slot in slots:
        key = f'{slot["doctor_id"]}#{slot["slot"]}'
        result = table.get_item(Key={"booking_key": key})
        booking = result.get("Item")

        slot["available"] = booking is None
        slot.pop("patient_id", None)
        if booking:
            slot["patient_id"] = booking["patient_id"]

    return slots


def save_slots(slots):
    temporary_file = SCHEDULE_FILE.with_suffix(".tmp")
    temporary_file.write_text(
        json.dumps(slots, indent=2),
        encoding="utf-8"
    )
    temporary_file.replace(SCHEDULE_FILE)


def patient_exists(patient_id):
    with PATIENT_FILE.open(
        "r", encoding="utf-8-sig", newline=""
    ) as file:
        return any(
            row["patient_id"] == patient_id
            for row in csv.DictReader(file)
        )



import os
import hmac
from functools import wraps

TOKEN_FILE = "/opt/medcare/.doctor-api-token"

def require_api_token(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            with open(TOKEN_FILE, encoding="utf-8") as file:
                expected = file.read().strip()
        except OSError:
            app.logger.exception("API token unavailable")
            return jsonify({"error": "Authentication unavailable"}), 503

        supplied = request.headers.get("Authorization", "")
        prefix = "Bearer "
        valid = (
            bool(expected)
            and supplied.startswith(prefix)
            and hmac.compare_digest(supplied[len(prefix):], expected)
        )
        if not valid:
            return jsonify({"error": "Unauthorized"}), 401

        return func(*args, **kwargs)
    return wrapper


@app.get("/health")
def health():
    return jsonify({
        "status": "healthy",
        "service": "MedCare Doctor API"
    })


@app.get("/doctors")
@require_api_token
def doctors():
    return jsonify(load_slots())


@app.get("/doctors/<doctor_id>")
@require_api_token
def doctor_schedule(doctor_id):
    slots = [
        slot for slot in load_slots()
        if slot["doctor_id"] == doctor_id
    ]

    if not slots:
        return jsonify({"error": "Doctor not found"}), 404

    return jsonify(slots)


@app.post("/appointments")
@require_api_token
def book_appointment():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON body"}), 400

    doctor_id = data.get("doctor_id")
    requested_slot = data.get("slot")
    patient_id = data.get("patient_id")

    if not all(
        isinstance(value, str) and value.strip()
        for value in (doctor_id, requested_slot, patient_id)
    ):
        return jsonify({"error": "Missing required fields"}), 400

    if not patient_exists(patient_id):
        return jsonify({"error": "Patient ID not registered"}), 404

    try:
        appointment_time = datetime.fromisoformat(requested_slot)
    except ValueError:
        return jsonify({"error": "Invalid appointment date"}), 400

    if appointment_time <= datetime.now():
        return jsonify({"error": "Cannot book past appointments"}), 400

    from botocore.exceptions import ClientError

    with SCHEDULE_FILE.open("r", encoding="utf-8") as file:
        slots = json.load(file)

    slot = next((
        s for s in slots
        if s["doctor_id"] == doctor_id
        and s["slot"] == requested_slot
    ), None)

    if slot is None:
        return jsonify({"error": "Consultation slot not found"}), 404

    key = f"{doctor_id}#{requested_slot}"
    booking = {
        "booking_key": key,
        "doctor_id": doctor_id,
        "slot": requested_slot,
        "patient_id": patient_id,
        "specialty": slot["specialty"],
        "available": False
    }

    try:
        appointment_table().put_item(
            Item=booking,
            ConditionExpression="attribute_not_exists(booking_key)"
        )
    except ClientError as error:
        if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return jsonify({"error": "Slot already booked"}), 409
        app.logger.exception("DynamoDB appointment write failed")
        return jsonify({"error": "Booking service unavailable"}), 503

    slot.update(booking)
    slot.pop("booking_key", None)

    return jsonify({
        "message": "Appointment booked successfully",
        "appointment": slot
    }), 201


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
