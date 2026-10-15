import os
import sqlite3
import threading
from flask import Flask, jsonify, request

app = Flask(__name__)
DB_PATH = os.environ.get("DB_PATH", "students.db")
_lock = threading.Lock()


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _lock, get_conn() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_no TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            course TEXT NOT NULL)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS marks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL REFERENCES students(id),
            subject TEXT NOT NULL,
            marks REAL NOT NULL)""")
        if conn.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO students (roll_no, name, course) VALUES (?, ?, ?)",
                [("CS101", "Aarav Sharma", "Computer Science"),
                 ("CS102", "Diya Patel", "Computer Science")])


@app.route("/api/health")
def health():
    return jsonify(status="UP", service="Student Record Platform", version="1.0.0")


@app.route("/api/students", methods=["GET"])
def list_students():
    with _lock, get_conn() as conn:
        rows = [dict(r) for r in conn.execute("SELECT * FROM students ORDER BY id")]
    return jsonify(count=len(rows), students=rows)


@app.route("/api/students", methods=["POST"])
def add_student():
    data = request.get_json(silent=True) or {}
    if not all(data.get(k) for k in ("roll_no", "name", "course")):
        return jsonify(error="roll_no, name and course are required"), 400
    try:
        with _lock, get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO students (roll_no, name, course) VALUES (?, ?, ?)",
                (data["roll_no"], data["name"], data["course"]))
        return jsonify(id=cur.lastrowid, message="student created"), 201
    except sqlite3.IntegrityError:
        return jsonify(error="roll_no already exists"), 409


@app.route("/api/marks", methods=["POST"])
def add_marks():
    data = request.get_json(silent=True) or {}
    try:
        student_id = int(data["student_id"])
        marks = float(data["marks"])
        subject = str(data["subject"]).strip()
    except (KeyError, TypeError, ValueError):
        return jsonify(error="student_id, subject and numeric marks are required"), 400
    if not subject or not 0 <= marks <= 100:
        return jsonify(error="subject required and marks must be between 0 and 100"), 400
    with _lock, get_conn() as conn:
        if not conn.execute("SELECT 1 FROM students WHERE id = ?", (student_id,)).fetchone():
            return jsonify(error="student not found"), 404
        conn.execute("INSERT INTO marks (student_id, subject, marks) VALUES (?, ?, ?)",
                     (student_id, subject, marks))
    return jsonify(message="marks recorded"), 201


@app.route("/api/students/<int:student_id>/marks")
def student_marks(student_id):
    with _lock, get_conn() as conn:
        rows = [dict(r) for r in conn.execute(
            "SELECT subject, marks FROM marks WHERE student_id = ?", (student_id,))]
    percentage = round(sum(r["marks"] for r in rows) / len(rows), 2) if rows else 0
    return jsonify(student_id=student_id, marks=rows, percentage=percentage)


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
