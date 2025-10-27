import os
import random
import sqlite3
from contextlib import closing

import bcrypt
from flask import Flask, jsonify, request
from flask_cors import CORS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "users.db")
PORT = int(os.getenv("PORT", "5000"))


app = Flask(__name__)
CORS(app)

def init_db():
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash BLOB NOT NULL,
                otp TEXT
            )
            """
        )
        conn.commit()


init_db()


def normalize_username(username: str) -> str:
    return username.strip()


def get_user_by_username(username: str):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT id, username, password_hash, otp FROM users WHERE lower(username) = lower(?)",
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
        }


@app.post("/api/signup")
def signup():
    payload = request.get_json(silent=True) or {}
    username = payload.get("username", "")
    password = payload.get("password", "")

    if not isinstance(username, str) or not isinstance(password, str):
        return jsonify({"error": "Username and password are required."}), 400

    clean_username = normalize_username(username)
    if not clean_username or len(password) < 6:
        return (
            jsonify(
                {"error": "Invalid username or password must be at least 6 characters."}
            ),
            400,
        )

    if get_user_by_username(clean_username):
        return jsonify({"error": "Username already exists."}), 409

    try:
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        with closing(sqlite3.connect(DB_PATH)) as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (clean_username, password_hash),
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

    stored_hash = user["password_hash"]
    if not bcrypt.checkpw(password.encode("utf-8"), stored_hash):
        return jsonify({"error": "Invalid credentials."}), 401

    otp = f"{random.randint(0, 999999):06d}"
    try:
        with closing(sqlite3.connect(DB_PATH)) as conn:
            conn.execute("UPDATE users SET otp = ? WHERE id = ?", (otp, user["id"]))
            conn.commit()

        print(f"[login] OTP generated for {user['username']}: {otp}")
        return jsonify({"message": "OTP generated.", "otp": otp})
    except sqlite3.Error as exc:
        print(f"[login] Database error: {exc}")
        return jsonify({"error": "Internal server error."}), 500


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


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=PORT)
