# 🏥 Smart Hospital Appointment Platform

A REST API for managing hospital doctors and patient appointments. It is built with Flask and PostgreSQL, uses JWT for authentication, exports Prometheus metrics, and includes Docker, Kubernetes, and Jenkins deployment files.

## ✨ What it does

- **Patient accounts:** Register and sign in to receive a JWT.
- **Doctor directory:** List doctors without signing in; only admins can add doctors.
- **Appointment booking:** Authenticated patients can book, view, and cancel their own appointments.
- **Booking rules:** Appointments must be in the future, a doctor cannot have two bookings for the same time, and each patient can have up to three active bookings.
- **Health and metrics:** Health-check endpoint for the API and Prometheus-compatible request and latency metrics.
- **Automated delivery:** Jenkins runs lint and tests, builds and scans a Docker image, then deploys it to Minikube.

## 🧰 Technology

| Area | Technology |
| --- | --- |
| API | Python 3.11, Flask |
| Data access and database | Flask-SQLAlchemy, PostgreSQL; SQLite is the local fallback |
| Authentication | PyJWT |
| Monitoring | Prometheus client and Prometheus server |
| Testing and linting | pytest, pytest-cov, Flake8 |
| Packaging and deployment | Docker, Docker Compose, Kubernetes, Minikube, Jenkins, Trivy |

## 🚀 Run locally with Docker Compose

### Prerequisites

- Docker Desktop with Docker Compose enabled
- Ports `5000` (API) and `9090` (Prometheus) available

### Start the services

From the project root, run:

```bash
docker compose up --build
```

This starts:

1. **PostgreSQL** on the internal Compose network. The API waits for its health check before starting.
2. **The Flask API** at `http://localhost:5000`.
3. **Prometheus** at `http://localhost:9090`, configured to scrape the API.

The database uses a named Docker volume, so its data is retained when the containers stop. To stop the services, press `Ctrl+C`; to stop and remove the containers, run `docker compose down`. To also delete the database volume and its data, run `docker compose down -v`.

### Check that it is running

```bash
curl http://localhost:5000/api/health
curl http://localhost:5000/metrics
```

The health endpoint should return JSON with `"status": "UP"`. The metrics endpoint returns Prometheus text-format metrics.

## 🐍 Run without Docker

The application defaults to a local SQLite database if `DATABASE_URL` is not set. For PostgreSQL, set `DATABASE_URL` to a SQLAlchemy-compatible PostgreSQL connection URL before starting the app.

### 1. Create and activate a virtual environment

**Windows PowerShell**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies and start the API

```bash
python -m pip install -r requirements.txt
python run.py
```

The API listens on `http://localhost:5000` by default. Set `PORT` to change the port. For a local run, `SECRET_KEY` can be set to choose the JWT signing key; never use the development default for a deployed service.

## 📡 API reference

All application routes are prefixed with `/api`. JSON request bodies are expected where noted. Routes requiring authentication use:

```http
Authorization: Bearer <token>
```

| Method | Endpoint | Authentication | Purpose |
| --- | --- | --- | --- |
| `GET` | `/api/health` | None | Report API health and version |
| `POST` | `/api/auth/register` | None | Register a patient |
| `POST` | `/api/auth/login` | None | Sign in and receive a JWT |
| `GET` | `/api/doctors` | None | List doctors |
| `POST` | `/api/doctors` | Admin | Add a doctor |
| `POST` | `/api/appointments` | Signed-in user | Book an appointment |
| `GET` | `/api/appointments` | Signed-in user | List the signed-in patient's appointments |
| `DELETE` | `/api/appointments/<id>` | Signed-in user | Cancel one of that patient's appointments |
| `GET` | `/metrics` | None | Expose Prometheus metrics |

### Example workflow

Register a patient:

```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"patient@example.com","password":"change-this-password"}'
```

Sign in and copy the returned `token`:

```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"patient@example.com","password":"change-this-password"}'
```

Book an appointment using a doctor ID from `GET /api/doctors` and a future ISO-8601 time:

```bash
curl -X POST http://localhost:5000/api/appointments \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"doctor_id":1,"slot":"2099-02-01T09:30"}'
```

List appointments with `GET /api/appointments`, or cancel one with `DELETE /api/appointments/<id>`, using the same bearer-token header.

### Authentication and account notes

- Patient registration requires an email and a password of at least six characters.
- Login tokens expire after two hours.
- The application seeds two sample doctors and an admin account when the database is empty.
- The seeded admin email is `admin@hospital.com`. Its password defaults to `admin123` unless the application receives an `ADMIN_PASSWORD` environment variable when the admin is first created.
- Errors caused by invalid requests or business rules are returned as JSON with HTTP `400`; missing or invalid tokens return `401`, and insufficient permissions return `403`.

## 🧪 Tests and code quality

Install the dependencies first, then run:

```bash
python -m pytest -v
python -m flake8 app/ --max-line-length=120 --count --statistics
```

To run tests with coverage and enforce the same 80% minimum used by Jenkins:

```bash
python -m pytest -v --cov=app --cov-fail-under=80
```

## 📈 Monitoring

- **Application health:** `GET /api/health`
- **Metrics:** `GET /metrics`; includes total HTTP requests and request-latency histograms by endpoint.
- **Prometheus UI:** `http://localhost:9090` when using Docker Compose. The scrape configuration is in [`monitoring/prometheus.yml`](monitoring/prometheus.yml).

## ☸️ Kubernetes and Jenkins

The [`k8s/`](k8s/) directory contains manifests for the API Deployment and NodePort Service, PostgreSQL with a persistent volume claim, application configuration and Secret, and a CPU-based Horizontal Pod Autoscaler.

To deploy manually to an already configured Kubernetes cluster:

```bash
kubectl apply -f k8s/
kubectl get deployments,pods,services
```

The API Service uses NodePort `30100`. With Minikube, retrieve its accessible URL with:

```bash
minikube service hospital-service --url
```

The [`Jenkinsfile`](Jenkinsfile) describes the automated pipeline:

1. Check out the source and install Python dependencies.
2. Run Flake8 and pytest with an 80% coverage threshold in parallel.
3. Build a versioned Docker image and tag it as `latest`.
4. Scan the image with Trivy for HIGH and CRITICAL vulnerabilities. The current pipeline reports these findings but does not fail the build solely because of them.
5. Load the image into Minikube, apply the Kubernetes manifests, update the API image, and wait for rollout.
6. Publish JUnit test results and clean the Jenkins workspace.

The Jenkins deployment stage currently uses Windows-specific Minikube, Docker, and kubeconfig paths. Update those paths and configure Jenkins credentials and environment variables for your own agent before using the pipeline.

## 🔐 Deployment security

- Replace all sample passwords, database credentials, and JWT signing keys before deployment.
- Configure a strong `SECRET_KEY` and `ADMIN_PASSWORD` in the application environment. The checked-in development Compose and Kubernetes configuration contains sample values and does not provide a production secret-management setup.
- Do not expose the development database credentials or seeded admin password on a public service.
- Store production credentials in a secret manager or deployment platform's protected secret store; do not commit real secrets to this repository.

## 🗂️ Project layout

```text
app/                 Flask application, API routes, models, services, metrics
k8s/                 Kubernetes API, PostgreSQL, configuration, and Secret manifests
monitoring/          Prometheus scrape configuration
tests/               API and service tests
Dockerfile           Container image definition
docker-compose.yml   Local API, PostgreSQL, and Prometheus stack
Jenkinsfile          CI/CD pipeline for Minikube
requirements.txt     Python dependencies
run.py               Application entry point
```
