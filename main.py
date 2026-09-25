from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
import os
import sqlite3
import hashlib
import secrets
from datetime import datetime, timezone

APP_NAME = "WHYNZO Platform Backend"
DB_PATH = os.getenv("WHYNZO_DB_PATH", "whynzo.db")

app = FastAPI(title=APP_NAME, version="0.1.0")

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    conn.executescript("""
    PRAGMA foreign_keys = ON;

    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS learner_profiles (
        user_id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        country TEXT,
        occupation TEXT,
        learning_language TEXT,
        workplace_language TEXT,
        skill_level TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS learning_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        module TEXT NOT NULL,
        progress INTEGER NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL,
        UNIQUE(user_id, module),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
    );
    """)
    conn.commit()
    conn.close()

init_db()

class Signup(BaseModel):
    email: EmailStr
    password: str

class Profile(BaseModel):
    name: str
    country: str = ""
    occupation: str = ""
    learning_language: str = ""
    workplace_language: str = ""
    skill_level: str = ""

class Progress(BaseModel):
    module: str
    progress: int

def hash_password(password: str, salt: str | None = None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 210000)
    return f"pbkdf2_sha256$210000${salt}${digest.hex()}"

@app.get("/health")
def health():
    return {"status": "ok", "service": APP_NAME}

@app.post("/users")
def create_user(data: Signup):
    if len(data.password) < 10:
        raise HTTPException(400, "Password must contain at least 10 characters.")
    conn = db()
    try:
        now = datetime.now(timezone.utc).isoformat()
        cur = conn.execute(
            "INSERT INTO users(email,password_hash,created_at) VALUES(?,?,?)",
            (data.email.lower(), hash_password(data.password), now)
        )
        conn.execute(
            "INSERT INTO audit_log(user_id,action,created_at) VALUES(?,?,?)",
            (cur.lastrowid, "account_created", now)
        )
        conn.commit()
        return {"id": cur.lastrowid, "email": data.email.lower()}
    except sqlite3.IntegrityError:
        raise HTTPException(409, "An account with this email already exists.")
    finally:
        conn.close()

@app.put("/users/{user_id}/profile")
def save_profile(user_id: int, data: Profile):
    conn = db()
    if conn.execute("SELECT id FROM users WHERE id=?", (user_id,)).fetchone() is None:
        conn.close()
        raise HTTPException(404, "User not found.")
    conn.execute("""
        INSERT INTO learner_profiles
        (user_id,name,country,occupation,learning_language,workplace_language,skill_level)
        VALUES(?,?,?,?,?,?,?)
        ON CONFLICT(user_id) DO UPDATE SET
        name=excluded.name,country=excluded.country,occupation=excluded.occupation,
        learning_language=excluded.learning_language,
        workplace_language=excluded.workplace_language,skill_level=excluded.skill_level
    """, (user_id, data.name, data.country, data.occupation,
          data.learning_language, data.workplace_language, data.skill_level))
    conn.commit()
    conn.close()
    return {"status": "saved"}

@app.put("/users/{user_id}/progress")
def save_progress(user_id: int, data: Progress):
    if not 0 <= data.progress <= 100:
        raise HTTPException(400, "Progress must be between 0 and 100.")
    conn = db()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        INSERT INTO learning_progress(user_id,module,progress,updated_at)
        VALUES(?,?,?,?)
        ON CONFLICT(user_id,module) DO UPDATE SET
        progress=excluded.progress,updated_at=excluded.updated_at
    """, (user_id, data.module, data.progress, now))
    conn.commit()
    conn.close()
    return {"status": "saved"}

@app.get("/users/{user_id}/dashboard")
def dashboard(user_id: int):
    conn = db()
    user = conn.execute(
        "SELECT id,email,created_at,is_active FROM users WHERE id=?", (user_id,)
    ).fetchone()
    if not user:
        conn.close()
        raise HTTPException(404, "User not found.")
    profile = conn.execute(
        "SELECT * FROM learner_profiles WHERE user_id=?", (user_id,)
    ).fetchone()
    progress = conn.execute(
        "SELECT module,progress,updated_at FROM learning_progress WHERE user_id=? ORDER BY module",
        (user_id,)
    ).fetchall()
    conn.close()
    return {
        "user": dict(user),
        "profile": dict(profile) if profile else None,
        "progress": [dict(x) for x in progress]
    }
