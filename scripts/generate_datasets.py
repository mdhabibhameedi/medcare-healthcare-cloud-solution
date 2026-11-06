import csv
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "raw"
DATA.mkdir(parents=True, exist_ok=True)

diagnoses = [
    "Hypertension", "Diabetes", "Asthma",
    "Migraine", "Routine Checkup"
]

patients = []
start_date = datetime(2026, 11, 1)

for i in range(1, 101):
    patients.append({
        "patient_id": f"P{i:04d}",
        "age": random.randint(18, 80),
        "gender": random.choice(["Male", "Female"]),
        "diagnosis": random.choice(diagnoses),
        "appointment_date": (
            start_date + timedelta(days=random.randint(0, 29))
        ).strftime("%Y-%m-%d")
    })

with open(DATA / "patients.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=patients[0].keys())
    writer.writeheader()
    writer.writerows(patients)

doctors = [
    {"doctor_id": "D001", "specialty": "Cardiology"},
    {"doctor_id": "D002", "specialty": "General Medicine"},
    {"doctor_id": "D003", "specialty": "Pulmonology"},
    {"doctor_id": "D004", "specialty": "Neurology"},
    {"doctor_id": "D005", "specialty": "Endocrinology"}
]

slots = []
for doctor in doctors:
    for day in range(3):
        for hour in [9, 11]:
            slots.append({
                "doctor_id": doctor["doctor_id"],
                "specialty": doctor["specialty"],
                "slot": (
                    start_date + timedelta(days=day, hours=hour)
                ).isoformat(),
                "available": True
            })

with open(DATA / "doctor_schedules.json", "w", encoding="utf-8") as f:
    json.dump(slots, f, indent=2)

vitals = []
for patient in patients:
    systolic = random.randint(100, 145)
    diastolic = random.randint(60, 95)

    vitals.append({
        "patient_id": patient["patient_id"],
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "heart_rate": random.randint(60, 105),
        "blood_pressure": f"{systolic}/{diastolic}",
        "oxygen_level": random.randint(94, 100)
    })

with open(DATA / "iot_vitals.json", "w", encoding="utf-8") as f:
    json.dump(vitals, f, indent=2)

assert len(patients) == 100
assert len(slots) == 30
assert len(vitals) == 100
assert len({p["patient_id"] for p in patients}) == 100
assert all(
    v["patient_id"] in {p["patient_id"] for p in patients}
    for v in vitals
)

print("SUCCESS: MedCare datasets generated and validated")
print(f"Patients: {len(patients)}")
print(f"Doctor consultation slots: {len(slots)}")
print(f"IoT vital readings: {len(vitals)}")
print(f"Dataset location: {DATA}")
