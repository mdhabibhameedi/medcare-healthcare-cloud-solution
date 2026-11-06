# MedCare — Secure Healthcare Application and Analytics Platform

Modular Assignment 7 | IHC – Cloud Development  
Author: Md Habib Ahmed  
Region: AWS Europe (Stockholm), `eu-north-1`  
Status: Completed academic demonstration using synthetic healthcare data; AWS resources may still incur charges.

MedCare is a Flask-based healthcare analytics and appointment scheduling demonstration deployed on Amazon EC2. Amazon S3 holds synthetic patient, doctor-schedule and IoT-vitals datasets; AWS Lambda integrates the data; DynamoDB persists appointment bookings and prevents double reservations. The dashboard presents processed analytics and live appointment availability. This repository contains application code, Lambda ETL, datasets, architecture, verification screenshots and the university report.

## Project contents

| Location | Purpose |
|---|---|
| [`app/dashboard.py`](app/dashboard.py) | Flask healthcare dashboard with S3 analytics and DynamoDB booking status |
| [`app/doctor_api.py`](app/doctor_api.py) | Protected doctor schedules and appointment booking API |
| [`deployment/lambda/lambda_function.py`](deployment/lambda/lambda_function.py) | AWS Lambda ETL for the three raw S3 datasets |
| [`scripts/generate_datasets.py`](scripts/generate_datasets.py) | Synthetic healthcare dataset generation |
| [`scripts/integrate_healthcare_data.py`](scripts/integrate_healthcare_data.py) | Local healthcare integration script |
| [`data/raw/`](data/raw/) | Synthetic patients, doctor schedules and IoT vital readings |
| [`data/processed/`](data/processed/) | Integrated patient CSV and healthcare summary JSON |
| [`requirements.txt`](requirements.txt) | Python dependencies |
| [`docs/architecture/MedCare-M7-Architecture.png`](docs/architecture/MedCare-M7-Architecture.png) | Implemented AWS architecture diagram |
| [`docs/evidence/`](docs/evidence/) | Eleven deployment, security and testing screenshots (E01–E11) |
| [`docs/Healthcare Solution-M7-Report.docx`](docs/Healthcare%20Solution-M7-Report.docx) | Final university assignment report |

## Architecture and AWS configuration

![MedCare AWS architecture](docs/architecture/MedCare-M7-Architecture.png)

- **Compute:** One Ubuntu 24.04 EC2 instance hosts separate Flask dashboard and scheduling API services, managed by Gunicorn and systemd.
- **Access:** Nginx serves HTTPS on the EC2 loopback address (`127.0.0.1:443`) through an SSH tunnel. The dashboard uses Nginx Basic Authentication; the API uses a bearer token. The certificate is self-signed, not publicly trusted.
- **Storage:** Amazon S3 bucket `medcare-m7-healthcare-data-habib` stores raw inputs and processed ETL outputs, with SSE-S3 (`AES256`) for processed objects.
- **ETL:** Python 3.13 Lambda function `MedCare-M7-Healthcare-ETL` reads S3 inputs, validates and integrates records, and writes processed objects back to S3.
- **Bookings:** DynamoDB table `MedCare-M7-Appointments`, partition key `booking_key`, stores bookings with conditional writes to prevent double booking.
- **IAM:** The EC2 role has scoped S3-read and DynamoDB access. The Lambda role is scoped to S3 input/output access; Lambda does **not** query DynamoDB.

The dashboard reads the S3 summary and obtains current booking counts directly from DynamoDB. No ALB, ASG, multi-AZ failover or publicly trusted HTTPS endpoint was deployed.

## Application endpoints

| Method | Route | Behavior |
|---|---|---|
| `GET` | `/` | Dashboard overview and analytics |
| `GET` | `/health` | Service health check (local access) |
| `GET` | `/doctors` | List doctor schedules and current availability; bearer token required |
| `GET` | `/doctors/<doctor_id>` | View one doctor's schedule; bearer token required |
| `POST` | `/appointments` | Create a booking with conditional DynamoDB write; bearer token required |

The dashboard and API run behind Nginx, with Gunicorn bound to `127.0.0.1:8000` and `127.0.0.1:8001`, respectively. A duplicate booking returns HTTP `409`.

## Recreate the demonstration (optional; AWS charges may apply)

1. Generate the synthetic inputs using [`scripts/generate_datasets.py`](scripts/generate_datasets.py) and upload them to the S3 `raw/` prefix.
2. Deploy [`deployment/lambda/lambda_function.py`](deployment/lambda/lambda_function.py) with the appropriate S3 IAM permissions, then invoke the ETL to generate `processed/` outputs.
3. Create the DynamoDB `MedCare-M7-Appointments` table with string partition key `booking_key`.
4. Configure an Ubuntu 24.04 EC2 instance with scoped IAM permissions, Python dependencies, and the two Flask applications under `/opt/medcare`.
5. Configure separate Gunicorn/systemd services and Nginx localhost HTTPS reverse proxy; provide authentication secrets privately, never through Git.
6. Access the service through an authorized SSH tunnel and repeat functional, concurrency and recovery tests.

The repository records the source and tested behavior, but does not include the deployed Nginx/systemd definitions or authentication secrets. Those must be configured separately for reproduction. Do not upload private keys, certificates, passwords or API tokens.

## Synthetic datasets versus actual measurements

The inputs contain **100 synthetic patient records**, **100 simulated IoT-vitals readings** and **30 doctor consultation slots across five doctors**. They are not real clinical records. Lambda writes `processed/integrated_patients.csv` and `processed/healthcare_summary.json`; the latter is a point-in-time snapshot, not a live DynamoDB booking export.

The results below come from application tests. They are separate from the synthetic input datasets.

## Observed testing results

| Test | Observed result |
|---|---|
| Data integration | 100 patients, 100 simulated vital readings, 30 consultation slots |
| Final booking status | 27 available slots; 3 booked |
| Competing bookings | Five simultaneous attempts: one `201`, four `409` |
| Concurrent workload | 30 requests with 10 workers; 30 succeeded, 0 failed |
| Average response latency | 2.215 seconds |
| Total workload duration | 7.750 seconds |
| Recovery test | Dashboard and API services restarted; 3 bookings remained persisted |

The concurrent workload test exercised one EC2 instance; it did not test automatic infrastructure scaling. The service recovery test verified application restart and persistent DynamoDB state, not cross-zone failover.

## Security and monitoring

Nginx is accessible only through loopback HTTPS and SSH port forwarding. Dashboard Basic Authentication and API bearer-token checks restrict access; DynamoDB conditional writes guard against conflicting bookings. S3 processed objects and DynamoDB records use encryption at rest, and AWS IAM scopes service permissions. The dashboard provides application-level monitoring; no dedicated CloudWatch dashboard is claimed.

The deployment is an educational prototype using synthetic records and is **not** a HIPAA-certified healthcare service.

## Costs and teardown

Costs depend on EC2 uptime and storage, S3 objects and requests, Lambda usage, DynamoDB usage and network transfer. No project-specific monthly billing figure is claimed. Stop or delete unused AWS resources after collecting required evidence and completing submission to avoid ongoing charges. Do not assume that the resources have already been removed.

## Assignment evidence and documentation

- [Formatted Modular Assignment 7 report](docs/Healthcare%20Solution-M7-Report.docx)
- [AWS architecture diagram](docs/architecture/MedCare-M7-Architecture.png)
- [All 11 evidence screenshots](docs/evidence/)
- [E01 — Doctor Scheduling API test](docs/evidence/E01-Doctor-Scheduling-API-Test.png)
- [E02 — Healthcare dashboard overview](docs/evidence/E02-Healthcare-Dashboard-Overview.png)
- [E03 — Healthcare dashboard monitoring](docs/evidence/E03-Healthcare-Dashboard-Monitoring.png)
- [E04 — S3 healthcare bucket](docs/evidence/E04-S3-Healthcare-Bucket.png)
- [E05 — S3 healthcare datasets](docs/evidence/E05-S3-Healthcare-Datasets.png)
- [E06 — Lambda ETL output](docs/evidence/E06-Lambda-ETL-S3-Output.png)
- [E07 — HTTPS authentication security](docs/evidence/E07-HTTPS-Authentication-Security.png)
- [E08 — DynamoDB appointment persistence](docs/evidence/E08-DynamoDB-Appointment-Persistence.png)
- [E09 — Scalability workload test](docs/evidence/E09-Scalability-Workload-Test.png)
- [E10 — Resilience recovery test](docs/evidence/E10-Resilience-Recovery-Test.png)
- [E11 — Final dashboard verification](docs/evidence/E11-Final-Dashboard-Verification.png)

This repository documents a completed academic prototype, not a production-ready healthcare deployment.
