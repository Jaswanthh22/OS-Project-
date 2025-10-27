# Simple Auth Dashboard

A minimal authentication workflow with username/password signup, one-time passcode (OTP) verification, and a protected dashboard. The backend now runs on Flask with SQLite for persistence, while the frontend remains plain HTML, CSS, and vanilla JavaScript.

## Features
- Password hashing with bcrypt before storage
- Login flow that generates a six-digit OTP and requires verification
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
   python3 server.py
   ```
   The API is available at `http://localhost:5000`. The SQLite database (`users.db`) is created automatically the first time the server runs.

   *If port 5000 is busy*, run `PORT=5050 python3 server.py` (adjust the number as needed) or stop the process currently bound to that port.

3. **Open the frontend**
   - Open `frontend/index.html` (sign up) or `frontend/login.html` directly in your browser, or
   - Serve the `frontend` directory with a lightweight static server.

## API Endpoints
| Method | Endpoint      | Description                                      |
|--------|---------------|--------------------------------------------------|
| POST   | `/api/signup` | Create a user with `username` and `password`     |
| POST   | `/api/login`  | Validate credentials and return a 6-digit OTP    |
| POST   | `/api/verify` | Validate the OTP and clear it on success         |

All endpoints accept and return JSON.

## Usage Notes
- Passwords are never stored in plain text—only bcrypt hashes are saved in the database.
- OTP codes are stored temporarily and cleared after successful verification.
- The dashboard checks `localStorage` for an authenticated flag; use the logout button to clear it.

## Development Tips
- Remove the `.venv` directory if you need to recreate your virtual environment.
- To reset users, stop the server and delete `backend/users.db`; it will be recreated on the next run.
- For real deployments you would send the OTP through email/SMS rather than returning it in the API response.
