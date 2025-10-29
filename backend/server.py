import os
import random
import re
import smtplib
import sqlite3
import ssl
from contextlib import closing
from email.message import EmailMessage

import bcrypt
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "users.db")
PORT = int(os.getenv("PORT", "5000"))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend"))


app = Flask(__name__)
CORS(app)

SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
SMTP_SENDER = os.getenv("SMTP_SENDER", SMTP_USERNAME).strip()
SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "false").lower() == "true"
SMTP_DISABLE_TLS = os.getenv("SMTP_DISABLE_TLS", "false").lower() == "true"

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def init_db():
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash BLOB NOT NULL,
                email TEXT,
                otp TEXT
            )
            """
        )
        existing_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()
        }
        if "email" not in existing_columns:
            conn.execute("ALTER TABLE users ADD COLUMN email TEXT")
        conn.commit()


init_db()


def normalize_username(username: str) -> str:
    return username.strip()


def get_user_by_username(username: str):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT id, username, password_hash, otp, email FROM users WHERE lower(username) = lower(?)",
            (username,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        password_hash = row["password_hash"]
        if isinstance(password_hash, memoryview):
            password_hash = bytes(password_hash)

        return {
            "id": row["id"],
            "username": row["username"],
            "password_hash": password_hash,
            "otp": row["otp"],
            "email": row["email"],
        }


def get_user_by_email(email: str):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT id, username, password_hash, otp, email FROM users WHERE lower(email) = lower(?)",
            (email,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        password_hash = row["password_hash"]
        if isinstance(password_hash, memoryview):
            password_hash = bytes(password_hash)

        return {
            "id": row["id"],
            "username": row["username"],
            "password_hash": password_hash,
            "otp": row["otp"],
            "email": row["email"],
        }


def normalize_email(email: str) -> str:
    return email.strip().lower()


def send_otp_email(recipient: str, otp: str):
    if not recipient:
        raise RuntimeError("No recipient email provided.")

    if not SMTP_HOST or not SMTP_SENDER:
        raise RuntimeError(
            "Email sending is not configured. Set SMTP_HOST and SMTP_SENDER."
        )

    message = EmailMessage()
    message["Subject"] = "Your one-time passcode"
    message["From"] = SMTP_SENDER
    message["To"] = recipient
    message.set_content(
        f"""Hello,

Your one-time passcode is {otp}.
It expires once used.

If you did not request this code, please secure your account.

Thanks."""
    )

    try:
        if SMTP_USE_SSL:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
                if SMTP_USERNAME and SMTP_PASSWORD:
                    server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(message)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                if not SMTP_DISABLE_TLS:
                    context = ssl.create_default_context()
                    server.starttls(context=context)
                if SMTP_USERNAME and SMTP_PASSWORD:
                    server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(message)
    except Exception as exc:
        print(f"[email] Failed to send OTP to {recipient}: {exc}")
        raise


def mask_email(email: str) -> str:
    if not email or "@" not in email:
        return ""
    local_part, _, domain = email.partition("@")
    if not local_part or not domain:
        return email
    if len(local_part) <= 2:
        masked_local = local_part[0] + "*" * (len(local_part) - 1)
    else:
        masked_local = (
            local_part[0] + "*" * (max(len(local_part) - 2, 0)) + local_part[-1]
        )
    return f"{masked_local}@{domain}"


@app.post("/api/signup")
def signup():
    payload = request.get_json(silent=True) or {}
    username = payload.get("username", "")
    password = payload.get("password", "")
    email = payload.get("email", "")

    if not isinstance(username, str) or not isinstance(password, str) or not isinstance(
        email, str
    ):
        return jsonify({"error": "Username, password, and email are required."}), 400

    clean_username = normalize_username(username)
    clean_email = normalize_email(email)
    if (
        not clean_username
        or len(password) < 6
        or not clean_email
        or not EMAIL_PATTERN.match(clean_email)
    ):
        return (
            jsonify(
                {
                    "error": "Invalid signup details. Use a unique username, valid email, and a password with at least 6 characters."
                }
            ),
            400,
        )

    if get_user_by_username(clean_username):
        return jsonify({"error": "Username already exists."}), 409

    if get_user_by_email(clean_email):
        return jsonify({"error": "Email already registered."}), 409

    try:
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        with closing(sqlite3.connect(DB_PATH)) as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)",
                (clean_username, password_hash, clean_email),
            )
            conn.commit()

        print(f"[signup] User registered: {clean_username}")
        return jsonify({"message": "Signup successful."}), 201
    except sqlite3.Error as exc:
        print(f"[signup] Database error: {exc}")
        return jsonify({"error": "Internal server error."}), 500


@app.post("/api/login")
def login():
    payload = request.get_json(silent=True) or {}
    username = payload.get("username", "")
    password = payload.get("password", "")

    if not isinstance(username, str) or not isinstance(password, str):
        return jsonify({"error": "Username and password are required."}), 400

    clean_username = normalize_username(username)
    user = get_user_by_username(clean_username)

    if not user:
        return jsonify({"error": "Invalid credentials."}), 401

    if not user.get("email"):
        return (
            jsonify({"error": "Email not set for this account. Contact support."}),
            400,
        )

    stored_hash = user["password_hash"]
    if not bcrypt.checkpw(password.encode("utf-8"), stored_hash):
        return jsonify({"error": "Invalid credentials."}), 401

    otp = f"{random.randint(0, 999999):06d}"
    try:
        with closing(sqlite3.connect(DB_PATH)) as conn:
            conn.execute("UPDATE users SET otp = ? WHERE id = ?", (otp, user["id"]))
            conn.commit()
    except sqlite3.Error as exc:
        print(f"[login] Database error before sending OTP: {exc}")
        return jsonify({"error": "Internal server error."}), 500

    try:
        send_otp_email(user.get("email"), otp)
    except Exception:
        with closing(sqlite3.connect(DB_PATH)) as conn:
            conn.execute("UPDATE users SET otp = NULL WHERE id = ?", (user["id"],))
            conn.commit()
        return (
            jsonify({"error": "Could not send OTP email. Try again later."}),
            500,
        )

    print(f"[login] OTP generated for {user['username']}")
    return jsonify(
        {
            "message": "OTP sent to your email address.",
            "email_hint": mask_email(user.get("email", "")),
        }
    )


@app.post("/api/verify")
def verify():
    payload = request.get_json(silent=True) or {}
    username = payload.get("username", "")
    otp = payload.get("otp", "")

    if not isinstance(username, str) or not isinstance(otp, str):
        return jsonify({"error": "Username and OTP are required."}), 400

    clean_username = normalize_username(username)
    user = get_user_by_username(clean_username)

    if not user or not user.get("otp"):
        return jsonify({"error": "OTP verification failed."}), 401

    if user["otp"] != otp.strip():
        return jsonify({"error": "OTP verification failed."}), 401

    try:
        with closing(sqlite3.connect(DB_PATH)) as conn:
            conn.execute("UPDATE users SET otp = NULL WHERE id = ?", (user["id"],))
            conn.commit()

        print(f"[verify] OTP verified for {user['username']}")
        return jsonify({"message": "Verification successful."})
    except sqlite3.Error as exc:
        print(f"[verify] Database error: {exc}")
        return jsonify({"error": "Internal server error."}), 500


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/")
def serve_root():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/<path:asset>")
def serve_asset(asset: str):
    asset_path = os.path.join(FRONTEND_DIR, asset)
    if os.path.isfile(asset_path):
        return send_from_directory(FRONTEND_DIR, asset)
    return jsonify({"error": "Not found"}), 404


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=PORT)
