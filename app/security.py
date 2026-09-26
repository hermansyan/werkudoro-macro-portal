import time
import secrets
import bcrypt
import logging
from typing import Optional
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.database import DBContext

logger = logging.getLogger("macro.security")

security_bearer = HTTPBearer(auto_error=False)

FAILED_ATTEMPTS = {}  # ip -> {"count": int, "locked_until": float}
REQUEST_RATES = {}    # ip -> [timestamps]

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION = 900  # 15 minutes
RATE_LIMIT_WINDOW = 60  # 60 seconds
MAX_REQUESTS_PER_WINDOW = 120  # max 120 requests/minute per IP

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def init_auth_tables():
    with DBContext(commit=True) as cur:
        # Seed default user: syant / syant123456 / hermansyantoso@gmail.com
        cur.execute("SELECT username FROM macro.users WHERE username = %s", ("syant",))
        row = cur.fetchone()
        if not row:
            hashed = hash_password("syant123456")
            cur.execute("""
            INSERT INTO macro.users (username, email, password_hash, role, created_at)
            VALUES (%s, %s, %s, %s, %s)
            """, ("syant", "hermansyantoso@gmail.com", hashed, "admin", time.time()))
            logger.info("Default user 'syant' created with secure bcrypt hash in PostgreSQL.")
        else:
            cur.execute("UPDATE macro.users SET email = %s WHERE username = %s AND (email IS NULL OR email = '')", ("hermansyantoso@gmail.com", "syant"))

def check_ip_lockout(ip: str):
    now = time.time()
    record = FAILED_ATTEMPTS.get(ip)
    if record and record.get("locked_until", 0) > now:
        remaining = int(record["locked_until"] - now)
        logger.warning(f"Blocked request from locked out IP: {ip}. Remaining: {remaining}s")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Terlalu banyak percobaan login gagal. IP diblokir sementara ({remaining} detik tersisa)."
        )

def record_failed_attempt(ip: str):
    now = time.time()
    record = FAILED_ATTEMPTS.setdefault(ip, {"count": 0, "locked_until": 0})
    record["count"] += 1
    if record["count"] >= MAX_FAILED_ATTEMPTS:
        record["locked_until"] = now + LOCKOUT_DURATION
        logger.warning(f"IP {ip} locked out for {LOCKOUT_DURATION}s due to failed logins.")

def clear_failed_attempts(ip: str):
    if ip in FAILED_ATTEMPTS:
        del FAILED_ATTEMPTS[ip]

def check_rate_limit(request: Request):
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    
    history = REQUEST_RATES.setdefault(ip, [])
    REQUEST_RATES[ip] = [t for t in history if now - t < RATE_LIMIT_WINDOW]
    
    if len(REQUEST_RATES[ip]) >= MAX_REQUESTS_PER_WINDOW:
        logger.warning(f"Rate limit exceeded for IP: {ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit terlampaui. Mohon tunggu beberapa saat sebelum mengirim permintaan kembali."
        )
        
    REQUEST_RATES[ip].append(now)

def get_user_by_identifier(identifier: str):
    with DBContext(commit=False) as cur:
        cur.execute("SELECT username, email, password_hash, role FROM macro.users WHERE username = %s OR email = %s", (identifier, identifier))
        row = cur.fetchone()
        return dict(row) if row else None

def create_session(username: str, duration_seconds: int = 86400 * 7) -> str:
    token = secrets.token_urlsafe(32)
    now = time.time()
    expires_at = now + duration_seconds
    
    with DBContext(commit=True) as cur:
        cur.execute("""
        INSERT INTO macro.sessions (token, username, created_at, expires_at)
        VALUES (%s, %s, %s, %s)
        """, (token, username, now, expires_at))
    return token

def revoke_session(token: str):
    with DBContext(commit=True) as cur:
        cur.execute("DELETE FROM macro.sessions WHERE token = %s", (token,))

def get_current_user(request: Request, creds: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)) -> Optional[dict]:
    token = None
    if creds and creds.credentials:
        token = creds.credentials
    else:
        token = request.cookies.get("macro_session")
        
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Akses ditolak: Autentikasi diperlukan. Silakan login terlebih dahulu."
        )
        
    with DBContext(commit=False) as cur:
        cur.execute("SELECT username, expires_at FROM macro.sessions WHERE token = %s", (token,))
        row = cur.fetchone()
        
    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesi tidak valid atau telah berakhir. Silakan login kembali."
        )
        
    username, expires_at = row["username"], row["expires_at"]
    if time.time() > expires_at:
        revoke_session(token)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesi Anda telah kedaluwarsa. Silakan login kembali."
        )
        
    return {"username": username, "token": token}
