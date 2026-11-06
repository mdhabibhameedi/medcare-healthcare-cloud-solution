
import boto3
import csv
import io
import json
from collections import Counter
from datetime import datetime, timezone

s3 = boto3.client("s3")
BUCKET = "medcare-m7-healthcare-data-habib"


def read_json(key):
    response = s3.get_object(Bucket=BUCKET, Key=key)
    return json.loads(response["Body"].read().decode("utf-8"))


def read_csv(key):
    response = s3.get_object(Bucket=BUCKET, Key=key)
    content = response["Body"].read().decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(content)))


def lambda_handler(event, context):
    patients = read_csv("raw/patients.csv")
    schedules = read_json("raw/doctor_schedules.json")
    vitals = read_json("raw/iot_vitals.json")

    patient_ids = [p["patient_id"] for p in patients]

    if len(set(patient_ids)) != len(patient_ids):
        raise ValueError("Duplicate patient IDs detected")

    patient_lookup = {p["patient_id"]: p for p in patients}
    latest_vitals = {}

    for reading in vitals:
        pid = reading["patient_id"]

        if pid not in patient_lookup:
            raise ValueError(f"Unknown patient ID: {pid}")

        if (
            pid not in latest_vitals
            or reading["timestamp"] > latest_vitals[pid]["timestamp"]
        ):
            latest_vitals[pid] = reading

    integrated = []

    for patient in patients:
        pid = patient["patient_id"]
        reading = latest_vitals.get(pid, {})

        integrated.append({
            "patient_id": pid,
            "age": patient["age"],
            "gender": patient["gender"],
            "diagnosis": patient["diagnosis"],
            "appointment_date": patient["appointment_date"],
            "vitals_timestamp": reading.get("timestamp", ""),
            "heart_rate": reading.get("heart_rate", ""),
            "blood_pressure": reading.get("blood_pressure", ""),
            "oxygen_level": reading.get("oxygen_level", "")
        })

    csv_buffer = io.StringIO()
    writer = csv.DictWriter(
        csv_buffer,
        fieldnames=list(integrated[0].keys())
    )
    writer.writeheader()
    writer.writerows(integrated)

    s3.put_object(
        Bucket=BUCKET,
        Key="processed/integrated_patients.csv",
        Body=csv_buffer.getvalue().encode("utf-8"),
        ContentType="text/csv",
        ServerSideEncryption="AES256"
    )

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_patients": len(patients),
        "total_doctors": len(set(
            s["doctor_id"] for s in schedules
        )),
        "total_consultation_slots": len(schedules),
        "available_slots": sum(
            s["available"] for s in schedules
        ),
        "booked_slots": sum(
            not s["available"] for s in schedules
        ),
        "total_vital_readings": len(vitals),
        "patients_with_vitals": len(latest_vitals),
        "diagnosis_distribution": dict(Counter(
            p["diagnosis"] for p in patients
        )),
        "appointments_by_date": dict(sorted(Counter(
            p["appointment_date"][:10] for p in patients
        ).items()))
    }

    s3.put_object(
        Bucket=BUCKET,
        Key="processed/healthcare_summary.json",
        Body=json.dumps(summary, indent=2).encode("utf-8"),
        ContentType="application/json",
        ServerSideEncryption="AES256"
    )

    print(
        f"SUCCESS: Processed {len(patients)} patients, "
        f"{len(schedules)} consultation slots, "
        f"{len(vitals)} vital readings"
    )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Healthcare ETL completed successfully",
            "patients": len(patients),
            "integrated_records": len(integrated),
            "vital_readings": len(vitals),
            "output_prefix": "processed/"
        })
    }
