def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.get_json()["status"] == "UP"


def test_metrics_endpoint(client):
    client.get("/api/health")
    assert b"http_requests_total" in client.get("/metrics").data


def test_login_wrong_password(client):
    r = client.post("/api/auth/login", json={"email": "admin@hospital.com", "password": "bad"})
    assert r.status_code == 400


def test_booking_requires_token(client):
    assert client.post("/api/appointments", json={}).status_code == 401


def test_only_admin_can_add_doctor(client, patient_headers, admin_headers):
    body = {"name": "Dr. New", "specialization": "ENT"}
    assert client.post("/api/doctors", json=body, headers=patient_headers).status_code == 403
    assert client.post("/api/doctors", json=body, headers=admin_headers).status_code == 201


def test_full_booking_flow(client, patient_headers):
    r = client.post("/api/appointments", json={"doctor_id": 1, "slot": "2099-02-01T09:30"},
                    headers=patient_headers)
    assert r.status_code == 201
    appt_id = r.get_json()["id"]
    assert len(client.get("/api/appointments", headers=patient_headers).get_json()) == 1
    assert client.delete(f"/api/appointments/{appt_id}", headers=patient_headers).get_json()["status"] == "CANCELLED"
