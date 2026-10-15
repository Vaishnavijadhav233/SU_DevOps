import datetime
import logging
import os
import secrets
import sqlite3
from functools import wraps

from flask import (Flask, abort, flash, g, jsonify, redirect, render_template,
                   request, session, url_for)

LOAN_DAYS = 14
FINE_PER_DAY = 5

SEED_BOOKS = [
    ("Operating System Concepts", "Silberschatz", "Computer Science"),
    ("Clean Code", "Robert Martin", "Software Engineering"),
    ("Database System Concepts", "Korth", "Computer Science"),
    ("The Phoenix Project", "Gene Kim", "DevOps"),
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS books(
    id INTEGER PRIMARY KEY, title TEXT NOT NULL, author TEXT NOT NULL,
    category TEXT DEFAULT '', isbn TEXT DEFAULT '', due TEXT);
CREATE TABLE IF NOT EXISTS members(
    id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL);
CREATE TABLE IF NOT EXISTS loans(
    id INTEGER PRIMARY KEY,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    member_id INTEGER REFERENCES members(id) ON DELETE SET NULL,
    issued TEXT NOT NULL, due TEXT NOT NULL, returned TEXT, fine INTEGER DEFAULT 0);
CREATE INDEX IF NOT EXISTS idx_loans_book ON loans(book_id, returned);
"""

# One row per book, joined with its active (unreturned) loan if any.
BOOK_QUERY = """
SELECT b.*, l.id AS loan_id, l.due AS loan_due, m.name AS member
FROM books b
LEFT JOIN loans l ON l.book_id = b.id AND l.returned IS NULL
LEFT JOIN members m ON m.id = l.member_id
"""


def today():
    return datetime.date.today()


def init_db(path):
    c = sqlite3.connect(path)
    c.executescript(SCHEMA)
    cols = {r[1] for r in c.execute("PRAGMA table_info(books)")}
    for col in ("category", "isbn"):
        if col not in cols:
            c.execute(f"ALTER TABLE books ADD COLUMN {col} TEXT DEFAULT ''")
    # Migrate legacy "books.due" issues into the loans table.
    c.execute("""INSERT INTO loans(book_id, issued, due)
                 SELECT id, date(due, '-%d days'), due FROM books
                 WHERE due IS NOT NULL
                   AND id NOT IN (SELECT book_id FROM loans WHERE returned IS NULL)""" % LOAN_DAYS)
    c.execute("UPDATE books SET due = NULL")
    if c.execute("SELECT COUNT(*) FROM books").fetchone()[0] == 0:
        c.executemany("INSERT INTO books(title,author,category) VALUES(?,?,?)", SEED_BOOKS)
    c.commit()
    c.close()


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        DATABASE=os.environ.get("DATABASE", "/data/library.db"),
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        ADMIN_USER=os.environ.get("ADMIN_USER", "admin"),
        ADMIN_PASSWORD=os.environ.get("ADMIN_PASSWORD"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "0") == "1",
    )
    if config:
        app.config.update(config)
    if not app.config["ADMIN_PASSWORD"]:
        app.config["ADMIN_PASSWORD"] = secrets.token_urlsafe(10)
        logging.getLogger("gunicorn.error").warning(
            "ADMIN_PASSWORD not set; generated one for this run: %s", app.config["ADMIN_PASSWORD"])

    os.makedirs(os.path.dirname(os.path.abspath(app.config["DATABASE"])), exist_ok=True)
    init_db(app.config["DATABASE"])

    def db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
        return g.db

    @app.teardown_appcontext
    def close_db(_):
        c = g.pop("db", None)
        if c:
            c.close()

    def csrf_token():
        if "csrf" not in session:
            session["csrf"] = secrets.token_hex(16)
        return session["csrf"]

    app.jinja_env.globals["csrf_token"] = csrf_token
    app.jinja_env.globals["fine_per_day"] = FINE_PER_DAY

    @app.before_request
    def check_csrf():
        if request.method == "POST":
            expected = session.get("csrf")
            if not expected or not secrets.compare_digest(request.form.get("csrf", ""), expected):
                abort(400, "Invalid CSRF token")

    @app.after_request
    def headers(resp):
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "same-origin"
        return resp

    def admin_required(f):
        @wraps(f)
        def wrapper(*a, **kw):
            if not session.get("admin"):
                return redirect(url_for("login", next=request.path))
            return f(*a, **kw)
        return wrapper

    def overdue_fine(due_iso):
        return max(0, (today() - datetime.date.fromisoformat(due_iso)).days) * FINE_PER_DAY

    @app.route("/")
    def home():
        q = request.args.get("q", "").strip()
        status = request.args.get("status", "")
        sql = BOOK_QUERY + " WHERE (b.title LIKE ? OR b.author LIKE ? OR b.isbn LIKE ? OR b.category LIKE ?)"
        if status == "available":
            sql += " AND l.id IS NULL"
        elif status == "issued":
            sql += " AND l.id IS NOT NULL"
        rows = db().execute(sql + " ORDER BY b.title", [f"%{q}%"] * 4).fetchall()
        members = db().execute("SELECT * FROM members ORDER BY name").fetchall()
        return render_template("index.html", books=rows, members=members, q=q, status=status,
                               today=today().isoformat())

    @app.route("/health")
    def health():
        db().execute("SELECT 1")
        return jsonify(status="ok")

    @app.route("/api/books")
    def api_books():
        q = request.args.get("q", "")
        rows = db().execute(BOOK_QUERY + " WHERE b.title LIKE ? ORDER BY b.title", (f"%{q}%",)).fetchall()
        return jsonify([{"id": r["id"], "title": r["title"], "author": r["author"],
                         "category": r["category"], "isbn": r["isbn"],
                         "available": r["loan_id"] is None, "due": r["loan_due"]} for r in rows])

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            ok_user = secrets.compare_digest(request.form.get("username", ""), app.config["ADMIN_USER"])
            ok_pw = secrets.compare_digest(request.form.get("password", ""), app.config["ADMIN_PASSWORD"])
            if ok_user and ok_pw:
                session.clear()
                session["admin"] = True
                nxt = request.args.get("next", "/")
                return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else "/")
            flash("Invalid credentials", "error")
        return render_template("login.html")

    @app.route("/logout", methods=["POST"])
    def logout():
        session.clear()
        return redirect(url_for("home"))

    @app.route("/issue/<int:i>", methods=["POST"])
    @admin_required
    def issue(i):
        c = db()
        member_id = request.form.get("member_id", type=int)
        if not member_id or not c.execute("SELECT 1 FROM members WHERE id=?", (member_id,)).fetchone():
            flash("Select a member to issue the book to.", "error")
            return redirect(url_for("home"))
        busy = c.execute("SELECT 1 FROM loans WHERE book_id=? AND returned IS NULL", (i,)).fetchone()
        if busy or not c.execute("SELECT 1 FROM books WHERE id=?", (i,)).fetchone():
            flash("Book is not available.", "error")
        else:
            due = today() + datetime.timedelta(days=LOAN_DAYS)
            c.execute("INSERT INTO loans(book_id,member_id,issued,due) VALUES(?,?,?,?)",
                      (i, member_id, today().isoformat(), due.isoformat()))
            c.commit()
            flash(f"Book issued. Due on {due.isoformat()}.", "ok")
        return redirect(url_for("home"))

    @app.route("/return/<int:i>", methods=["POST"])
    @admin_required
    def ret(i):
        c = db()
        loan = c.execute("SELECT * FROM loans WHERE book_id=? AND returned IS NULL", (i,)).fetchone()
        if not loan:
            flash("Book is not currently issued.", "error")
            return redirect(url_for("home"))
        fine = overdue_fine(loan["due"])
        c.execute("UPDATE loans SET returned=?, fine=? WHERE id=?", (today().isoformat(), fine, loan["id"]))
        c.commit()
        flash(f"Book returned. Fine: Rs {fine}", "ok")
        return redirect(url_for("home"))

    @app.route("/renew/<int:i>", methods=["POST"])
    @admin_required
    def renew(i):
        c = db()
        loan = c.execute("SELECT * FROM loans WHERE book_id=? AND returned IS NULL", (i,)).fetchone()
        if loan:
            new_due = (datetime.date.fromisoformat(loan["due"]) + datetime.timedelta(days=LOAN_DAYS)).isoformat()
            c.execute("UPDATE loans SET due=? WHERE id=?", (new_due, loan["id"]))
            c.commit()
            flash(f"Renewed. New due date {new_due}.", "ok")
        return redirect(url_for("home"))

    @app.route("/books/add", methods=["POST"])
    @admin_required
    def add_book():
        f = request.form
        title, author = f.get("title", "").strip(), f.get("author", "").strip()
        if not title or not author:
            flash("Title and author are required.", "error")
        else:
            db().execute("INSERT INTO books(title,author,category,isbn) VALUES(?,?,?,?)",
                         (title, author, f.get("category", "").strip(), f.get("isbn", "").strip()))
            db().commit()
            flash("Book added.", "ok")
        return redirect(url_for("home"))

    @app.route("/books/<int:i>/delete", methods=["POST"])
    @admin_required
    def delete_book(i):
        if db().execute("SELECT 1 FROM loans WHERE book_id=? AND returned IS NULL", (i,)).fetchone():
            flash("Cannot delete a book that is currently issued.", "error")
        else:
            db().execute("DELETE FROM books WHERE id=?", (i,))
            db().commit()
            flash("Book deleted.", "ok")
        return redirect(url_for("home"))

    @app.route("/members", methods=["GET", "POST"])
    @admin_required
    def members():
        c = db()
        if request.method == "POST":
            name, email = request.form.get("name", "").strip(), request.form.get("email", "").strip().lower()
            if not name or "@" not in email:
                flash("Valid name and email are required.", "error")
            else:
                try:
                    c.execute("INSERT INTO members(name,email) VALUES(?,?)", (name, email))
                    c.commit()
                    flash("Member added.", "ok")
                except sqlite3.IntegrityError:
                    flash("A member with that email already exists.", "error")
            return redirect(url_for("members"))
        rows = c.execute("""SELECT m.*, (SELECT COUNT(*) FROM loans l WHERE l.member_id=m.id AND l.returned IS NULL) AS active
                            FROM members m ORDER BY m.name""").fetchall()
        return render_template("members.html", members=rows)

    @app.route("/members/<int:i>/delete", methods=["POST"])
    @admin_required
    def delete_member(i):
        if db().execute("SELECT 1 FROM loans WHERE member_id=? AND returned IS NULL", (i,)).fetchone():
            flash("Member still has books issued.", "error")
        else:
            db().execute("DELETE FROM members WHERE id=?", (i,))
            db().commit()
            flash("Member deleted.", "ok")
        return redirect(url_for("members"))

    @app.route("/dashboard")
    @admin_required
    def dashboard():
        c = db()
        stats = {
            "books": c.execute("SELECT COUNT(*) FROM books").fetchone()[0],
            "issued": c.execute("SELECT COUNT(*) FROM loans WHERE returned IS NULL").fetchone()[0],
            "members": c.execute("SELECT COUNT(*) FROM members").fetchone()[0],
            "fines": c.execute("SELECT COALESCE(SUM(fine),0) FROM loans").fetchone()[0],
        }
        stats["available"] = stats["books"] - stats["issued"]
        overdue = [dict(r, fine=overdue_fine(r["due"])) for r in c.execute(
            """SELECT b.title, m.name AS member, l.due FROM loans l JOIN books b ON b.id=l.book_id
               LEFT JOIN members m ON m.id=l.member_id WHERE l.returned IS NULL AND l.due < ? ORDER BY l.due""",
            (today().isoformat(),))]
        history = c.execute(
            """SELECT b.title, m.name AS member, l.issued, l.due, l.returned, l.fine FROM loans l
               JOIN books b ON b.id=l.book_id LEFT JOIN members m ON m.id=l.member_id
               ORDER BY l.id DESC LIMIT 25""").fetchall()
        return render_template("dashboard.html", stats=stats, overdue=overdue, history=history)

    return app


# Module-level instance for `gunicorn app:app`; creating it needs a writable DATABASE path.
if os.environ.get("SKIP_APP_INIT") != "1":
    app = create_app()
