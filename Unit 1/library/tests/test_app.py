import datetime
import re

import pytest

import app as library


@pytest.fixture
def client(tmp_path):
    a = library.create_app({"DATABASE": str(tmp_path / "t.db"), "ADMIN_PASSWORD": "pw", "SECRET_KEY": "k"})
    return a.test_client()


def token(c, path="/login"):
    html = c.get(path).get_data(as_text=True)
    return re.search(r'name="csrf" value="(\w+)"', html).group(1)


def login(c):
    r = c.post("/login", data={"username": "admin", "password": "pw", "csrf": token(c)})
    assert r.status_code == 302


def post(c, url, **data):
    return c.post(url, data={"csrf": token(c, "/"), **data}, follow_redirects=True)


def test_public_search_and_health(client):
    assert client.get("/health").json == {"status": "ok"}
    assert b"Clean Code" in client.get("/?q=clean").data
    assert b"Operating System" not in client.get("/?q=clean").data
    assert len(client.get("/api/books").json) == 4


def test_mutations_require_login_and_csrf(client):
    assert client.post("/issue/1", data={"csrf": "x"}).status_code == 400
    assert client.get("/members").status_code == 302
    assert client.post("/login", data={"username": "admin", "password": "bad", "csrf": token(client)}).status_code == 200


def test_issue_return_with_fine(client, monkeypatch):
    login(client)
    post(client, "/members", name="Asha", email="a@x.com")
    assert b"Issued, due" in post(client, "/issue/1", member_id=1).data
    assert b"not available" in post(client, "/issue/1", member_id=1).data
    future = datetime.date.today() + datetime.timedelta(days=20)  # 6 days overdue
    monkeypatch.setattr(library, "today", lambda: future)
    assert b"Fine: Rs 30" in post(client, "/return/1").data


def test_add_delete_book_and_dashboard(client):
    login(client)
    assert b"New Book" in post(client, "/books/add", title="New Book", author="Me").data
    assert b"Book deleted" in post(client, "/books/5/delete").data
    assert b"Dashboard" in client.get("/dashboard").data
