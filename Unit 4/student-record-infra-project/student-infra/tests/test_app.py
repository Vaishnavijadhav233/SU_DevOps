import importlib
import pytest


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    import app as app_module
    importlib.reload(app_module)
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.get_json()["status"] == "UP"


def test_seed_students(client):
    assert client.get("/api/students").get_json()["count"] == 2


def test_add_student_and_duplicate(client):
    body = {"roll_no": "CS201", "name": "Kabir", "course": "IT"}
    assert client.post("/api/students", json=body).status_code == 201
    assert client.post("/api/students", json=body).status_code == 409


def test_add_student_validation(client):
    assert client.post("/api/students", json={"name": "x"}).status_code == 400


def test_marks_flow_and_percentage(client):
    assert client.post("/api/marks", json={"student_id": 1, "subject": "Math", "marks": 80}).status_code == 201
    assert client.post("/api/marks", json={"student_id": 1, "subject": "DevOps", "marks": 90}).status_code == 201
    data = client.get("/api/students/1/marks").get_json()
    assert data["percentage"] == 85.0 and len(data["marks"]) == 2


def test_marks_rejects_bad_input(client):
    assert client.post("/api/marks", json={"student_id": 1, "subject": "Math", "marks": 150}).status_code == 400
    assert client.post("/api/marks", json={"student_id": 99, "subject": "Math", "marks": 50}).status_code == 404
