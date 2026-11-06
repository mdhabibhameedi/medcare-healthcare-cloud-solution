
import csv
import json
from pathlib import Path
from datetime import datetime
from collections import Counter

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw"
PROCESSED = BASE / "data" / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)

with (RAW / "patients.csv").open(
    "r", encoding="utf-8-sig", newline=""
) as f:
    patients = list(csv.DictReader(f))

with (RAW / "doctor_schedules.json").open(
    "r", encoding="utf-8"
) as f:
    schedules = json.load(f)

with (RAW / "iot_vitals.json").open(
    "r", encoding="utf-8"
) as f:
    vitals = json.load(f)

assert len(patients) == 100, "Patient count mismatch"
assert len(schedules) == 30, "Schedule count mismatch"
assert len(vitals) == 100, "Vitals count mismatch"

patient_ids = [p["patient_id"] for p in patients]
assert len(set(patient_ids)) == len(patient_ids), "Duplicate patient IDs"

patient_lookup = {p["patient_id"]: p for p in patients}

latest_vitals = {}
for reading in vitals:
    pid = reading["patient_id"]
    assert pid in patient_lookup, f"Unknown patient: {pid}"

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

output_csv = PROCESSED / "integrated_patients.csv"

with output_csv.open(
    "w", encoding="utf-8", newline=""
) as f:
    writer = csv.DictWriter(
        f, fieldnames=list(integrated[0].keys())
    )
    writer.writeheader()
    writer.writerows(integrated)

booked = sum(not s["available"] for s in schedules)
available = sum(s["available"] for s in schedules)

diagnosis_counts = Counter(
    p["diagnosis"] for p in patients
)

appointment_counts = Counter(
    p["appointment_date"][:10] for p in patients
)

summary = {
    "generated_at": datetime.now().isoformat(timespec="seconds"),
    "total_patients": len(patients),
    "total_doctors": len(set(s["doctor_id"] for s in schedules)),
    "total_consultation_slots": len(schedules),
    "available_slots": available,
    "booked_slots": booked,
    "total_vital_readings": len(vitals),
    "patients_with_vitals": len(latest_vitals),
    "diagnosis_distribution": dict(diagnosis_counts),
    "appointments_by_date": dict(sorted(appointment_counts.items()))
}

output_json = PROCESSED / "healthcare_summary.json"
output_json.write_text(
    json.dumps(summary, indent=2),
    encoding="utf-8"
)

print("SUCCESS: Healthcare data integration completed")
print("Patients:", len(patients))
print("Doctors:", summary["total_doctors"])
print("Consultation slots:", len(schedules))
print("Vital readings:", len(vitals))
print("Integrated records:", len(integrated))
print("Available slots:", available)
print("Booked slots:", booked)
print("Output: data/processed/integrated_patients.csv")
print("Output: data/processed/healthcare_summary.json")
