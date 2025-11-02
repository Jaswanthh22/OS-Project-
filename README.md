# Simple Auth Dashboard

A minimal authentication workflow with username/password signup, one-time passcode (OTP) verification, and a protected dashboard. The backend now runs on Flask with SQLite for persistence, while the frontend remains plain HTML, CSS, and vanilla JavaScript.

## Features
- Password hashing with bcrypt before storage
- Login flow that emails a six-digit OTP for verification
- Lightweight SQLite database (`backend/users.db`) instead of a JSON file
- Clean, responsive frontend that works when opened directly via `file://`
- LocalStorage flag to gate access to the dashboard after OTP verification

## Prerequisites
- Python 3.10 or later

## Getting Started

1. **Install backend dependencies**
   ```bash
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate.bat
   pip install -r requirements.txt
   ```

2. **Start the backend server**
   ```bash
   set -a; source .env; set +a
   python3 server.py
   ```
   The API is available at `http://localhost:5000`. The SQLite database (`users.db`) is created automatically the first time the server runs.

   Configure the following environment variables before starting the server so OTPs can be delivered via email:

   - `SMTP_HOST` (required)
   - `SMTP_PORT` (defaults to `587`)
   - `SMTP_USERNAME` and `SMTP_PASSWORD` (if authentication is required)
   - `SMTP_SENDER` (defaults to `SMTP_USERNAME`)
   - Optional: `SMTP_USE_SSL=true` for implicit TLS (otherwise STARTTLS is used), `SMTP_DISABLE_TLS=true` to skip STARTTLS.

   *If port 5000 is busy*, run `PORT=5050 python3 server.py` (adjust the number as needed) or stop the process currently bound to that port.

3. **Open the frontend**
   - Visit `http://localhost:5000` in your browser (the Flask server now serves the static frontend), or
   - Open `frontend/index.html` manually / serve the directory with any static file server.

If port `5000` is already in use, start the server with a different port and the frontend will automatically target the same origin:

```bash
PORT=5050 python server.py
# then browse http://localhost:5050
```

## API Endpoints
| Method | Endpoint      | Description                                      |
|--------|---------------|--------------------------------------------------|
| POST   | `/api/signup` | Create a user with username, email, and password |
| POST   | `/api/login`  | Validate credentials and email a 6-digit OTP (returns an email hint) |
| POST   | `/api/verify` | Validate the OTP and clear it on success         |

All endpoints accept and return JSON.

## Usage Notes
- Passwords are never stored in plain text—only bcrypt hashes are saved in the database.
- OTP codes are stored temporarily and cleared after successful verification.
- The dashboard checks `localStorage` for an authenticated flag; use the logout button to clear it.

## Development Tips
- Remove the `.venv` directory if you need to recreate your virtual environment.
- To reset users, stop the server and delete `backend/users.db`; it will be recreated on the next run.
- Ensure the SMTP credentials and sender are valid for your email provider; failures block the OTP flow.
