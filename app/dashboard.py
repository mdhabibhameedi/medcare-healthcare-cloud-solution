
from flask import Flask, render_template_string, jsonify
from pathlib import Path
from collections import Counter
import csv
import json

app = Flask(__name__)
BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw"
PROCESSED = BASE / "data" / "processed"

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MedCare | Healthcare Dashboard</title>
<style>
* { box-sizing: border-box; }
body {
    margin: 0; font-family: Arial, sans-serif;
    background: #f3f6fb; color: #172b4d;
}
header {
    background: #123a63; color: white;
    padding: 25px 6%;
}
header h1 { margin: 0; }
header p { margin-bottom: 0; color: #cbdcec; }
main { max-width: 1250px; margin: 30px auto; padding: 0 20px; }
.cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px;
}
.card, .panel {
    background: white; border-radius: 12px;
    padding: 22px; box-shadow: 0 2px 9px #152d4512;
}
.card span { color: #60748b; font-size: 14px; }
.card strong {
    display: block; font-size: 32px;
    margin-top: 12px; color: #123a63;
}
.grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 20px; margin-top: 24px;
}
h2 { font-size: 19px; margin-top: 0; }
.bar-row { margin: 14px 0; }
.bar-label {
    display: flex; justify-content: space-between;
    font-size: 13px; margin-bottom: 6px;
}
.track { background: #e8edf5; border-radius: 6px; height: 11px; }
.fill { background: #1688a7; height: 11px; border-radius: 6px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td {
    padding: 11px; border-bottom: 1px solid #e8edf3;
    text-align: left;
}
th { color: #526780; }
.table-wrap { overflow-x: auto; }
footer {
    text-align: center; color: #66798e;
    font-size: 12px; padding: 30px;
}
</style>
</head>
<body>
<header>
<h1>MedCare Health Services</h1>
<p>Healthcare Operations & Patient Monitoring Dashboard</p>
</header>
<main>
<section class="cards">
<div class="card"><span>Total Patients</span><strong>{{ s.total_patients }}</strong></div>
<div class="card"><span>Doctors</span><strong>{{ s.total_doctors }}</strong></div>
<div class="card"><span>Available Slots</span><strong>{{ s.available_slots }}</strong></div>
<div class="card"><span>Booked Slots</span><strong>{{ s.booked_slots }}</strong></div>
<div class="card"><span>Vital Readings</span><strong>{{ s.total_vital_readings }}</strong></div>
</section>

<section class="grid">
<div class="panel">
<h2>Diagnosis Distribution</h2>
{% for name, count in diagnoses.items() %}
<div class="bar-row">
<div class="bar-label"><span>{{ name }}</span><b>{{ count }}</b></div>
<div class="track">
<div class="fill" style="width: {{ count / max_diagnosis * 100 }}%"></div>
</div>
</div>
{% endfor %}
</div>

<div class="panel">
<h2>Appointment Activity by Date</h2>
{% for date, count in appointments.items() %}
<div class="bar-row">
<div class="bar-label"><span>{{ date }}</span><b>{{ count }}</b></div>
<div class="track">
<div class="fill" style="width: {{ count / max_appointments * 100 }}%"></div>
</div>
</div>
{% endfor %}
</div>
</section>

<section class="grid">
<div class="panel">
<h2>Doctor Consultation Availability</h2>
<div class="table-wrap">
<table>
<tr><th>Doctor</th><th>Specialty</th><th>Available</th><th>Booked</th></tr>
{% for doctor in doctors %}
<tr>
<td>{{ doctor.id }}</td>
<td>{{ doctor.specialty }}</td>
<td>{{ doctor.available }}</td>
<td>{{ doctor.booked }}</td>
</tr>
{% endfor %}
</table>
</div>
</div>

<div class="panel">
<h2>Recent IoT Vital Readings</h2>
<div class="table-wrap">
<table>
<tr><th>Patient</th><th>Heart Rate</th><th>Blood Pressure</th><th>SpO2</th></tr>
{% for v in vitals %}
<tr>
<td>{{ v.patient_id }}</td>
<td>{{ v.heart_rate }}</td>
<td>{{ v.blood_pressure }}</td>
<td>{{ v.oxygen_level }}</td>
</tr>
{% endfor %}
</table>
</div>
</div>
</section>
</main>
<footer>Synthetic demonstration data | MedCare M7 Academic Project</footer>
</body>
</html>
"""


def read_data():
    import boto3

    s3 = boto3.client("s3", region_name="eu-north-1")
    response = s3.get_object(
        Bucket="medcare-m7-healthcare-data-habib",
        Key="processed/healthcare_summary.json"
    )
    summary = json.loads(response["Body"].read())

    with (RAW / "doctor_schedules.json").open(
        encoding="utf-8"
    ) as file:
        schedules = json.load(file)

    with (RAW / "iot_vitals.json").open(
        encoding="utf-8"
    ) as file:
        vitals = json.load(file)

    import boto3

    table = boto3.resource(
        "dynamodb", region_name="eu-north-1"
    ).Table("MedCare-M7-Appointments")

    for slot in schedules:
        booking_key = f'{slot["doctor_id"]}#{slot["slot"]}'
        response = table.get_item(
            Key={"booking_key": booking_key},
            ConsistentRead=True
        )
        booking = response.get("Item")
        slot["available"] = booking is None

    summary["available_slots"] = sum(
        slot["available"] for slot in schedules
    )
    summary["booked_slots"] = sum(
        not slot["available"] for slot in schedules
    )

    doctor_data = {}
    for slot in schedules:
        did = slot["doctor_id"]
        if did not in doctor_data:
            doctor_data[did] = {
                "id": did,
                "specialty": slot["specialty"],
                "available": 0,
                "booked": 0
            }
        key = "available" if slot["available"] else "booked"
        doctor_data[did][key] += 1

    return summary, list(doctor_data.values()), vitals


@app.get("/")
def dashboard():
    summary, doctors, vitals = read_data()
    diagnoses = summary["diagnosis_distribution"]
    appointments = summary["appointments_by_date"]

    return render_template_string(
        HTML,
        s=summary,
        doctors=doctors,
        vitals=vitals[-10:][::-1],
        diagnoses=diagnoses,
        appointments=appointments,
        max_diagnosis=max(diagnoses.values(), default=1),
        max_appointments=max(appointments.values(), default=1)
    )


@app.get("/api/summary")
def api_summary():
    summary, _, _ = read_data()
    return jsonify(summary)


@app.get("/health")
def health():
    return jsonify({"status": "healthy", "service": "MedCare Dashboard"})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=False)
