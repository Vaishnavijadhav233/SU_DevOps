# Library Management Platform

A web-based library circulation system built with Flask and SQLite. It provides
a searchable public catalogue and a librarian interface for managing books,
members, loans, returns, renewals, and overdue fines.

## 1. Project Overview

The application supports the everyday workflow of a small library:

1. Search the catalogue and check whether a book is available.
2. Sign in as a librarian to add books and members.
3. Issue an available book to a registered member for 14 days.
4. Renew an active loan or return the book and calculate any late fine.
5. Review catalogue, overdue loans, fines, and recent circulation activity on
   the dashboard.

The project uses server-rendered HTML pages, a SQLite database, a small JSON
books API, and a Docker image for deployment.

## 2. Engineering Objectives

- **Reliable circulation rules:** Prevent issuing an unavailable book or
  deleting a book or member with an active loan.
- **Protected librarian actions:** Require a librarian session and a valid CSRF
  token for form submissions that modify data.
- **Persistent data:** Store catalogue, members, and loan history in SQLite;
  migrate legacy `books.due` data into the loans table at startup.
- **Testable application:** Use an application factory and isolated temporary
  databases in the automated test suite.
- **Repeatable delivery:** Run tests in GitHub Actions and package the app in a
  Docker container.

## 3. Technology Stack

| Layer | Technology | Version / constraint | Purpose |
|---|---|---|---|
| Runtime | Python | 3.12 in Docker and CI | Application runtime |
| Web framework | Flask | `>=3.0,<4` | Routes, sessions, templates |
| Database | SQLite | Python standard library | Catalogue, members, and loans |
| Production server | Gunicorn | `>=22.0` | WSGI server in the container |
| Tests | pytest | `>=8.0` | Application and route tests |
| Container | Docker | Dockerfile and Compose | Build and run the application |
| CI | GitHub Actions | GitHub-hosted Ubuntu runner | Test and build verification |

Dependency constraints are declared in [`requirements.txt`](requirements.txt).

## 4. Application Architecture

The application is intentionally a compact Flask application rather than a
multi-service system:

| Component | Responsibility |
|---|---|
| `app.py` | Application factory, SQLite setup and migration, routes, and business rules |
| `templates/` | Jinja-rendered catalogue, login, members, and dashboard pages |
| `static/` | Shared application stylesheet |
| `tests/` | Flask test-client tests using temporary SQLite databases |
| Docker Compose | Runs one web service and mounts a persistent data volume |
| GitHub Actions | Runs pytest and builds the Docker image |

### Data model

- **Book:** title, author, category, ISBN, and legacy due-date field used during
  migration.
- **Member:** name and unique email address.
- **Loan:** book, optional member reference, issue date, due date, return date,
  and final fine. An unreturned loan represents an active issue.

### Circulation rules

- New loans are due 14 days after issue.
- Renewing an active loan adds 14 days to its current due date.
- A returned book incurs Rs 5 per day late, calculated and stored when it is
  returned. The dashboard shows a running estimate for books that are still
  overdue.
- A book with an active loan cannot be issued again or deleted.
- A member with an active loan cannot be deleted.
- Member emails must be unique.
- Existing databases are initialized and migrated when the application starts.

## 5. Project Structure

```text
library/
├── .github/
│   └── workflows/
│       └── ci.yml             # Test and Docker build workflow
├── static/
│   └── style.css              # Application styles
├── templates/
│   ├── base.html               # Shared layout
│   ├── dashboard.html          # Librarian dashboard
│   ├── index.html              # Public catalogue and book actions
│   ├── login.html              # Librarian login
│   └── members.html            # Member management
├── tests/
│   ├── conftest.py             # Test setup
│   └── test_app.py             # Route and circulation tests
├── app.py                      # Flask application and SQLite logic
├── docker-compose.yml          # Local container deployment
├── Dockerfile                  # Production container image
├── requirements.txt            # Python dependencies
└── README.md
```

## 6. Pages and HTTP Endpoints

### Browser pages

| Method | Path | Access | Description |
|---|---|---|---|
| `GET` | `/` | Public | Search and filter the book catalogue |
| `GET`, `POST` | `/login` | Public | Librarian sign-in |
| `POST` | `/logout` | Librarian | Sign out |
| `GET`, `POST` | `/members` | Librarian | List and add members |
| `GET` | `/dashboard` | Librarian | View totals, overdue books, and recent activity |

### Book actions

These actions require a librarian session and a CSRF token:

| Method | Path | Description |
|---|---|---|
| `POST` | `/books/add` | Add a book |
| `POST` | `/books/<id>/delete` | Delete a book if it has no active loan |
| `POST` | `/issue/<id>` | Issue an available book to a member |
| `POST` | `/renew/<id>` | Renew an active loan |
| `POST` | `/return/<id>` | Return an active loan and record its fine |
| `POST` | `/members/<id>/delete` | Delete a member if they have no active loan |

### JSON endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/books?q=<text>` | Return books whose titles match the optional query |
| `GET` | `/health` | Return `{"status":"ok"}` when the database is reachable |

The catalogue page supports searching by title, author, ISBN, and category, and
filtering by available or issued status.

## 7. Local Setup

### Windows PowerShell

From the project directory:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

$env:DATABASE = "library.db"
$env:SECRET_KEY = "replace-with-a-long-random-value"
$env:ADMIN_USER = "admin"
$env:ADMIN_PASSWORD = "replace-this-password"
python -m flask --app app run --host 0.0.0.0 --port 8000
```

Open <http://localhost:8000>. To run the tests, open another terminal in the
project directory, activate the virtual environment, and run:

```powershell
python -m pytest -q
```

### Linux / macOS / WSL

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

export DATABASE=library.db
export SECRET_KEY='replace-with-a-long-random-value'
export ADMIN_USER=admin
export ADMIN_PASSWORD='replace-this-password'
python -m flask --app app run --host 0.0.0.0 --port 8000
```

Run the test suite with:

```bash
python -m pytest -q
```

If `ADMIN_PASSWORD` is not set, the app generates a password for that run and
writes it to the application logger. Set an explicit password for local use and
always configure a strong password for deployment.

## 8. Configuration

| Variable | Default | Description |
|---|---|---|
| `DATABASE` | `/data/library.db` | SQLite database path |
| `SECRET_KEY` | Generated at startup | Flask session signing key; set a stable secret for deployments |
| `ADMIN_USER` | `admin` | Librarian login name |
| `ADMIN_PASSWORD` | Generated at startup if unset | Librarian login password |
| `COOKIE_SECURE` | `0` | Set to `1` when served over HTTPS |
| `PORT` | `8000` in Docker | Port Gunicorn listens on in the container |

For local runs, set `DATABASE` to a writable file path. In Docker Compose, the
database is stored in the persistent `library-data` volume at
`/data/library.db`.

## 9. Tests and Continuous Integration

The tests cover public catalogue search and health checks, login and CSRF
requirements, issuing and returning books, late-fine calculation, book
management, and the dashboard.

Run locally:

```bash
python -m pytest -q
```

The workflow in `.github/workflows/ci.yml` runs the test suite for pushes and
pull requests, then builds the Docker image after tests pass.

## 10. Docker Deployment

### Docker Compose

1. Copy the example environment file and edit the values:

   ```powershell
   Copy-Item .env.example .env
   ```

2. Set a strong `SECRET_KEY` and `ADMIN_PASSWORD` in `.env`, then build and
   start the service:

   ```powershell
   docker compose up -d --build
   ```

The app is available at <http://localhost:8000>. Compose persists the database
in the `library-data` volume. View logs or stop the service with:

```powershell
docker compose logs -f
docker compose down
```

### Build and run the image directly

```bash
docker build -t library .
docker run --detach --name library \
  --publish 8000:8000 \
  --env SECRET_KEY='replace-with-a-long-random-value' \
  --env ADMIN_USER=admin \
  --env ADMIN_PASSWORD='replace-this-password' \
  --volume library-data:/data \
  library
```

The container runs Gunicorn as a non-root user and includes a `/health`
container health check. It uses one Gunicorn worker with four threads because
the application uses SQLite. For production, keep one application instance,
use a persistent writable disk, configure stable secrets, and serve traffic
through an HTTPS reverse proxy with `COOKIE_SECURE=1`.

## 11. Deployment Notes

- The Docker image is built from `python:3.12-slim`.
- SQLite is intended here for a small, single-instance deployment. Do not run
  multiple application replicas against the same SQLite file.
- Platforms that support Docker can deploy the included `Dockerfile`; configure
  `SECRET_KEY`, `ADMIN_USER`, and `ADMIN_PASSWORD`, mount persistent storage at
  `/data`, and use `/health` as the health check.
- This repository currently provides Docker deployment and GitHub Actions CI;
  it does not include Jenkins or Kubernetes configuration.
