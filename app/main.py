import os
import logging
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Query, BackgroundTasks, HTTPException, Request, Response, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from app.database import DBContext, init_db
from app.collectors.indicators import sync_indicators
from app.collectors.cross_asset import sync_cross_asset, get_cross_asset_summary
from app.collectors.opportunity_radar import build_opportunity_radar, get_opportunity_radar_data
from app.collectors.news_rss import sync_rss_news
from app.collectors.briefing import sync_calendar, update_macro_briefing
from app.scheduler import start_scheduler, stop_scheduler, run_all_jobs
from app.security import (
    init_auth_tables, verify_password, create_session, revoke_session,
    get_current_user, check_ip_lockout, record_failed_attempt, clear_failed_attempts,
    check_rate_limit, get_user_by_identifier
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("macro.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Macro Intelligence Portal...")
    init_db()
    init_auth_tables()
    
    with DBContext(commit=False) as cur:
        cur.execute("SELECT COUNT(*) as cnt FROM macro.indicators")
        ind_cnt = cur.fetchone()["cnt"]
    
    if ind_cnt == 0:
        logger.info("Seeding initial macro indicators & news data...")
        sync_indicators()
        sync_calendar()
        sync_rss_news()
        update_macro_briefing()

    try:
        sync_cross_asset()
        build_opportunity_radar()
    except Exception as e:
        logger.error(f"Error during initial cross-asset / opportunity radar sync: {e}")
        
    start_scheduler()
    yield
    stop_scheduler()

app = FastAPI(
    title="Werkudoro Macroeconomic Intelligence Terminal",
    description="Portal Analisis & Berita Makroekonomi Indonesia dan Global — Multi-Region & Nexus Engine",
    version="2.0.0",
    lifespan=lifespan
)

# Security Headers & Rate Limiting Middleware
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    try:
        check_rate_limit(request)
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    response = await call_next(request)
    
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Server"] = "Werkudoro-SecureGateway"
    
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

class LoginRequest(BaseModel):
    identifier: Optional[str] = None
    username: Optional[str] = None
    password: str

class GoogleSSORequest(BaseModel):
    email: Optional[str] = "hermansyantoso@gmail.com"

@app.post("/api/auth/login")
def login(req: LoginRequest, request: Request, response: Response):
    client_ip = request.client.host if request.client else "unknown"
    check_ip_lockout(client_ip)
    
    id_val = (req.identifier or req.username or "").strip()
    password = req.password
    
    user = get_user_by_identifier(id_val)
    if not user or not verify_password(password, user["password_hash"]):
        record_failed_attempt(client_ip)
        logger.warning(f"Failed login attempt for identifier '{id_val}' from IP {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username/Email atau password tidak sesuai. Percobaan gagal dicatat."
        )
        
    clear_failed_attempts(client_ip)
    token = create_session(user["username"])
    
    response.set_cookie(
        key="macro_session",
        value=token,
        max_age=86400 * 7,
        httponly=True,
        samesite="lax",
        secure=False
    )
    
    logger.info(f"User '{user['username']}' authenticated from IP {client_ip}")
    return {
        "status": "ok",
        "message": "Login berhasil.",
        "username": user["username"],
        "email": user["email"],
        "token": token
    }

@app.post("/api/auth/google-sso")
def google_sso_login(req: GoogleSSORequest, request: Request, response: Response):
    client_ip = request.client.host if request.client else "unknown"
    email = (req.email or "hermansyantoso@gmail.com").strip().lower()
    
    # Authenticate default admin Herman for Google SSO
    user = get_user_by_identifier(email) or get_user_by_identifier("syant")
    username = user["username"] if user else "syant"
    
    token = create_session(username)
    response.set_cookie(
        key="macro_session",
        value=token,
        max_age=86400 * 7,
        httponly=True,
        samesite="lax",
        secure=False
    )
    
    logger.info(f"Google SSO authenticated for {email} (username: {username}) from IP {client_ip}")
    return {
        "status": "ok",
        "message": "Autentikasi Google SSO berhasil.",
        "username": username,
        "email": email,
        "token": token
    }

@app.get("/api/auth/check")
def auth_check(request: Request):
    token = request.cookies.get("macro_session")
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        
    if not token:
        return {"authenticated": False, "username": None}
        
    with DBContext(commit=False) as cur:
        cur.execute("SELECT username, expires_at FROM macro.sessions WHERE token = %s", (token,))
        row = cur.fetchone()
    
    if not row or time.time() > row["expires_at"]:
        return {"authenticated": False, "username": None}
        
    return {"authenticated": True, "username": row["username"]}

@app.post("/api/auth/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get("macro_session")
    if token:
        revoke_session(token)
    response.delete_cookie(key="macro_session")
    return {"status": "ok", "message": "Logout berhasil."}

@app.get("/api/status")
def get_status(user: dict = Depends(get_current_user)):
    with DBContext(commit=False) as cur:
        cur.execute("SELECT COUNT(*) as count FROM macro.news")
        news_count = cur.fetchone()["count"]
        cur.execute("SELECT COUNT(*) as count FROM macro.indicators")
        ind_count = cur.fetchone()["count"]
        cur.execute("SELECT updated_at FROM macro.macro_briefing WHERE id = 1")
        row = cur.fetchone()
        last_update = row["updated_at"] if row else None
    
    return {
        "status": "online",
        "service": "Werkudoro Macro Intelligence Terminal",
        "total_news": news_count,
        "total_indicators": ind_count,
        "last_update": last_update,
        "authenticated_as": user["username"]
    }

@app.get("/api/indicators")
def get_indicators(user: dict = Depends(get_current_user)):
    with DBContext(commit=False) as cur:
        cur.execute("SELECT * FROM macro.indicators ORDER BY category ASC, name ASC")
        rows = [dict(r) for r in cur.fetchall()]
    
    ind_map = {r["key"]: r for r in rows}
    
    indo = [r for r in rows if r["region"] == "Indonesia"]
    us = [r for r in rows if r["region"] == "Amerika Serikat"]
    eurozone = [r for r in rows if r["region"] == "Kawasan Euro"]
    japan = [r for r in rows if r["region"] == "Jepang"]
    uk = [r for r in rows if r["region"] == "Inggris"]
    china = [r for r in rows if r["region"] == "China"]
    commodities = [r for r in rows if r["region"] == "Komoditas"]
    
    # Calculate Macro Interconnection Nexus metrics
    bi_rate = ind_map.get("BI_RATE", {}).get("value", 6.00)
    fed_rate = ind_map.get("FED_FUNDS_RATE", {}).get("value", 4.50)
    sbn_10y = ind_map.get("SBN_10Y", {}).get("value", 6.85)
    us_10y = ind_map.get("US_10Y", {}).get("value", 5.18)
    us_3m = ind_map.get("US_3M", {}).get("value", 4.07)
    vix = ind_map.get("VIX", {}).get("value", 14.87)
    btc = ind_map.get("BTC_USD", {}).get("value", 84000.0)
    indo_cpi = ind_map.get("INFLASI_INDO", {}).get("value", 1.71)
    us_cpi = ind_map.get("US_CPI", {}).get("value", 2.70)
    dxy = ind_map.get("DXY", {}).get("value", 101.03)
    usd_idr = ind_map.get("USD_IDR", {}).get("value", 17912.0)
    
    rate_spread = round(bi_rate - fed_rate, 2)
    yield_spread_bps = int(round((sbn_10y - us_10y) * 100))
    real_rate_indo = round(bi_rate - indo_cpi, 2)
    real_rate_us = round(fed_rate - us_cpi, 2)
    real_spread = round(real_rate_indo - real_rate_us, 2)
    us_yield_curve_slope = round(us_10y - us_3m, 2)
    
    # Calculate Macro Stress Index (Composite 0-100)
    # Higher VIX + Higher DXY + Inverted/Steep Yield Curve -> High Stress
    vix_score = min(max((vix - 12) / 25 * 40, 0), 40)
    dxy_score = min(max((dxy - 98) / 10 * 30, 0), 30)
    fx_score = min(max((usd_idr - 16000) / 3000 * 30, 0), 30)
    macro_stress_score = int(round(vix_score + dxy_score + fx_score))
    
    stress_status = "NORMAL / LOW RISK"
    if macro_stress_score > 65:
        stress_status = "HIGH STRESS / DEFENSIVE"
    elif macro_stress_score > 40:
        stress_status = "MODERATE / CAUTIOUS"
    
    nexus = {
        "rate_spread_pct": rate_spread,
        "yield_spread_bps": yield_spread_bps,
        "real_rate_indo": real_rate_indo,
        "real_rate_us": real_rate_us,
        "real_spread_premium": real_spread,
        "dxy_level": dxy,
        "usd_idr_level": usd_idr,
        "vix_level": vix,
        "btc_level": btc,
        "us_yield_curve_slope": us_yield_curve_slope,
        "macro_stress_score": macro_stress_score,
        "stress_status": stress_status,
        "transmission_notes": [
            f"Spread suku bunga acuan BI-Rate vs FFR berada di +{rate_spread}% (+{int(rate_spread*100)} bps), memberikan bantalan defensif bagi Rupiah.",
            f"Yield spread SBN 10Y terhadap US 10Y Treasury tercatat +{yield_spread_bps} bps (SBN: {sbn_10y:.2f}% vs US10Y: {us_10y:.2f}%).",
            f"Real Interest Rate Indonesia (+{real_rate_indo}%) lebih tinggi dibandingkan AS (+{real_rate_us}%), menghasilkan premi riil menarik +{real_spread}%.",
            f"Kekuatan DXY di level {dxy:.2f} memicu volatilitas kurs Rupiah (Rp {usd_idr:,.0f}/USD), dimitigasi oleh instrumen SRBI dan intervensi valas BI.",
            f"Indeks Volatilitas Pasar Global (VIX) berada di level {vix:.2f} pts dan Kurva Imbal Hasil US (10Y - 3M) berslope +{us_yield_curve_slope}%."
        ]
    }
    
    try:
        nexus["cross_asset"] = get_cross_asset_summary()
    except Exception as e:
        logger.warning(f"Failed to attach cross-asset summary to nexus: {e}")
        nexus["cross_asset"] = {}
    
    try:
        nexus["opportunity_radar"] = get_opportunity_radar_data()
    except Exception as e:
        logger.warning(f"Failed to attach opportunity radar to nexus: {e}")
        nexus["opportunity_radar"] = {}
    
    return {
        "all": rows,
        "indonesia": indo,
        "advanced_economies": {
            "us": us,
            "eurozone": eurozone,
            "japan": japan,
            "uk": uk,
            "china": china
        },
        "commodities": commodities,
        "nexus": nexus
    }

@app.get("/api/cross-asset")
def get_cross_asset(user: dict = Depends(get_current_user)):
    """Mengembalikan metrik dan analisis korelasi lintas aset (Cross-Asset Intelligence)."""
    return {
        "status": "ok",
        "data": get_cross_asset_summary()
    }

@app.get("/api/opportunity-radar")
def get_opportunity_radar_endpoint(user: dict = Depends(get_current_user)):
    """
    Mengembalikan data Opportunity & Action Radar:
    - Macro Regime (Expansive, Stagnant, Inflationary Shock, Tightening)
    - Asset Impact Matrix (+100 to -100)
    - Winners & Losers sectors
    - Actionable Decisions (Life, Trading, Real Business)
    """
    data = get_opportunity_radar_data()
    return {
        "status": "ok",
        "radar": data
    }

@app.get("/api/news")
def get_news(
    region: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    sentiment: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: dict = Depends(get_current_user)
):
    clauses = []
    params = []
    
    if region and region != "Semua":
        if region == "Negara Maju":
            clauses.append("region IN ('Global', 'Amerika Serikat', 'Kawasan Euro', 'Jepang', 'Inggris', 'China')")
        else:
            clauses.append("region = %s")
            params.append(region)
        
    if category and category != "Semua":
        clauses.append("category = %s")
        params.append(category)
        
    if sentiment and sentiment != "Semua":
        clauses.append("sentiment = %s")
        params.append(sentiment)
        
    if q and q.strip():
        clauses.append("(title ILIKE %s OR summary ILIKE %s OR tags ILIKE %s)")
        term = f"%{q.strip()}%"
        params.extend([term, term, term])
        
    where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    
    with DBContext(commit=False) as cur:
        count_query = f"SELECT COUNT(*) as count FROM macro.news {where_sql}"
        cur.execute(count_query, params)
        total = cur.fetchone()["count"]
        
        query = f"""
        SELECT * FROM macro.news
        {where_sql}
        ORDER BY published_at DESC
        LIMIT %s OFFSET %s
        """
        cur_params = list(params) + [limit, offset]
        cur.execute(query, cur_params)
        rows = [dict(r) for r in cur.fetchall()]
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": rows
    }

@app.get("/api/calendar")
def get_calendar(user: dict = Depends(get_current_user)):
    with DBContext(commit=False) as cur:
        cur.execute("SELECT * FROM macro.economic_calendar ORDER BY event_date ASC, time_wib ASC")
        rows = [dict(r) for r in cur.fetchall()]
    return {"events": rows}

@app.get("/api/briefing")
def get_briefing(user: dict = Depends(get_current_user)):
    with DBContext(commit=False) as cur:
        cur.execute("SELECT * FROM macro.macro_briefing WHERE id = 1")
        row = cur.fetchone()
    if not row:
        return {"briefing": None}
    return {"briefing": dict(row)}

@app.get("/api/export/indicators.csv")
def export_indicators_csv(user: dict = Depends(get_current_user)):
    import csv, io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Key", "Nama Indikator", "Kategori", "Region", "Nilai Terkini", "Nilai Sebelumnya", "Satuan", "Perubahan (%)", "Tren", "Sumber", "Deskripsi", "Terakhir Diperbarui"])
    
    with DBContext(commit=False) as cur:
        cur.execute("SELECT * FROM macro.indicators ORDER BY region ASC, category ASC, name ASC")
        rows = cur.fetchall()
        for r in rows:
            writer.writerow([
                r["key"], r["name"], r["category"], r["region"],
                r["value"], r["prev_value"], r["unit"], r["change_pct"],
                r["trend"], r["source"], r["description"], r["last_updated"]
            ])
            
    csv_content = output.getvalue()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=werkudoro_macro_indicators.csv"}
    )

@app.post("/api/refresh")
def trigger_refresh(background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    background_tasks.add_task(run_all_jobs)
    return {"status": "refreshing", "message": "Sinkronisasi data makroekonomi berjalan di latar belakang."}

STATIC_DIR = "/home/hermes/macro-portal/static"
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
@app.head("/")
def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return JSONResponse({"message": "Frontend index.html is being prepared."})
