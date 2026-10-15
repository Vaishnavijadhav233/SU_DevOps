import pytest
from app import create_app, db


@pytest.fixture
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def patient_headers(client):
    client.post("/api/auth/register", json={"email": "p@x.com", "password": "secret1"})
    token = client.post("/api/auth/login", json={"email": "p@x.com", "password": "secret1"}).get_json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(client):
    token = client.post("/api/auth/login", json={"email": "admin@hospital.com", "password": "admin123"}).get_json()["token"]
    return {"Authorization": f"Bearer {token}"}
