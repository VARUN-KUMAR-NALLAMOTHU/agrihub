import os
import random
import secrets
import smtplib
import sqlite3
import time
from datetime import datetime, timedelta
from email.message import EmailMessage
from functools import wraps

import requests
from dotenv import load_dotenv
from flask import (Flask, flash, g, jsonify, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from crop_data import CROPS, SOILS, SOIL_COLORS, recommend, soil_crops

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "agrihub.db")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY") or secrets.token_hex(16)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "") or GOOGLE_API_KEY
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
# Tried in order if the main model is overloaded or unavailable (comma-separated in .env)
GEMINI_FALLBACKS = [m.strip() for m in os.getenv("GEMINI_FALLBACK_MODELS", "gemini-2.5-flash,gemini-2.0-flash").split(",") if m.strip()]
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
# HTTPS email provider (works on free hosts that block SMTP). Brevo: https://www.brevo.com
BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
BREVO_SENDER = os.getenv("BREVO_SENDER", "") or SMTP_USER
OTP_TTL_MIN = 10
MAX_OTP_ATTEMPTS = 5


# ---------- Database ----------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        with open(os.path.join(BASE_DIR, "schema.sql"), encoding="utf-8") as f:
            conn.executescript(f.read())


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


# ---------- Email OTP ----------
def send_otp_email(to_email: str, otp: str) -> bool:
    """Send OTP via Brevo API (preferred) or SMTP. With neither configured, print it (dev mode)."""
    subject = "Your AgriHub verification code"
    body = (f"Your AgriHub verification code is {otp}.\n"
            f"It expires in {OTP_TTL_MIN} minutes. If you didn't request it, ignore this email.")
    if BREVO_API_KEY and BREVO_SENDER:
        r = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={"api-key": BREVO_API_KEY, "accept": "application/json"},
            json={"sender": {"name": "AgriHub", "email": BREVO_SENDER},
                  "to": [{"email": to_email}], "subject": subject, "textContent": body},
            timeout=15,
        )
        if r.status_code >= 300:
            raise RuntimeError(f"Brevo error {r.status_code}: {r.text[:200]}")
        return True
    if not (SMTP_USER and SMTP_PASS):
        print(f"[DEV MODE] OTP for {to_email}: {otp}")
        return False
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = to_email
    msg.set_content(body)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as s:
        s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)
    return True


def create_and_send_otp(email: str):
    otp = f"{random.SystemRandom().randint(0, 999999):06d}"
    db = get_db()
    db.execute("DELETE FROM otps WHERE email = ?", (email,))
    db.execute(
        "INSERT INTO otps (email, otp_hash, expires_at) VALUES (?, ?, ?)",
        (email, generate_password_hash(otp),
         (datetime.utcnow() + timedelta(minutes=OTP_TTL_MIN)).isoformat()),
    )
    db.commit()
    try:
        send_otp_email(email, otp)
    except Exception as exc:  # network / auth problems shouldn't crash signup
        print(f"[WARN] Could not send OTP email: {exc}. OTP for {email}: {otp}")
        return False
    return True


# ---------- Weather (Google Cloud APIs) ----------
def geocode(city: str):
    r = requests.get(
        "https://maps.googleapis.com/maps/api/geocode/json",
        params={"address": city, "key": GOOGLE_API_KEY}, timeout=10,
    )
    data = r.json()
    if data.get("status") != "OK":
        return None
    loc = data["results"][0]["geometry"]["location"]
    return loc["lat"], loc["lng"], data["results"][0]["formatted_address"]


def fetch_google_weather(city: str):
    """Real-time weather via Google Maps Platform Weather API (needs a billing-enabled key)."""
    try:
        place = geocode(city)
        if not place:
            return {"error": f"Could not find location '{city}'."}
        lat, lng, address = place
        r = requests.get(
            "https://weather.googleapis.com/v1/currentConditions:lookup",
            params={"key": GOOGLE_API_KEY, "location.latitude": lat, "location.longitude": lng},
            timeout=10,
        )
    except (requests.RequestException, ValueError):
        return {"error": "Could not reach the Google weather service."}
    if r.status_code != 200:
        return {"error": f"Weather API error {r.status_code}: {r.text[:200]}"}
    d = r.json()
    return {
        "location": address,
        "temperature_c": d.get("temperature", {}).get("degrees"),
        "feels_like_c": d.get("feelsLikeTemperature", {}).get("degrees"),
        "humidity": d.get("relativeHumidity"),
        "condition": d.get("weatherCondition", {}).get("description", {}).get("text"),
        "wind_kmh": d.get("wind", {}).get("speed", {}).get("value"),
        "rain_chance": d.get("precipitation", {}).get("probability", {}).get("percent"),
        "source": "Google Weather API",
    }


WMO_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast", 45: "Fog", 48: "Fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle", 56: "Freezing drizzle", 57: "Freezing drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain", 66: "Freezing rain", 67: "Freezing rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Light showers", 81: "Showers", 82: "Heavy showers", 85: "Snow showers", 86: "Snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with hail",
}


def fetch_openmeteo_weather(city: str):
    """Free fallback (no API key or billing): Open-Meteo geocoding + current weather."""
    try:
        g = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                         params={"name": city, "count": 1, "language": "en"}, timeout=10).json()
        found = g.get("results") or []
        if not found:
            return {"error": f"Could not find '{city}'. Try a nearby larger town or add the district."}
        p = found[0]
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": p["latitude"], "longitude": p["longitude"], "timezone": "auto",
                    "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
                    "daily": "precipitation_probability_max", "forecast_days": 1},
            timeout=10,
        )
        if r.status_code != 200:
            return {"error": f"Weather service error {r.status_code}."}
        d = r.json()
        cur = d.get("current", {})
        rain = (d.get("daily", {}).get("precipitation_probability_max") or [None])[0]
        place = ", ".join(x for x in (p.get("name"), p.get("admin1"), p.get("country")) if x)
        return {
            "location": place,
            "temperature_c": cur.get("temperature_2m"),
            "feels_like_c": cur.get("apparent_temperature"),
            "humidity": cur.get("relative_humidity_2m"),
            "condition": WMO_CODES.get(cur.get("weather_code"), "Unknown"),
            "wind_kmh": cur.get("wind_speed_10m"),
            "rain_chance": rain,
            "source": "Open-Meteo",
        }
    except (requests.RequestException, ValueError, KeyError):
        return {"error": "Could not reach the weather service. Try again in a moment."}


def fetch_weather(city: str):
    """Use Google's Weather API when a working key is set, otherwise fall back to Open-Meteo."""
    if GOOGLE_API_KEY:
        result = fetch_google_weather(city)
        if "error" not in result:
            return result
        print(f"[INFO] Google weather unavailable ({result['error'][:100]}); using Open-Meteo instead.")
    return fetch_openmeteo_weather(city)


# ---------- AI chatbot (Gemini) ----------
SYSTEM_PROMPT = (
    "You are AgriBot, a friendly farming assistant inside the AgriHub app. "
    "Give practical, concise advice on crops, soil, irrigation, fertilizers, pests and weather "
    "for Indian farmers. Use simple language and short bullet points. "
    "If a question is not about agriculture, politely steer back to farming."
)


_model_cache = {"t": 0.0, "names": []}


def discover_models():
    """Ask Google which Flash models this key can actually use (cached 10 min)."""
    if _model_cache["names"] and time.time() - _model_cache["t"] < 600:
        return _model_cache["names"]
    names = []
    try:
        r = requests.get("https://generativelanguage.googleapis.com/v1beta/models",
                         params={"key": GEMINI_API_KEY, "pageSize": 100}, timeout=10)
        if r.status_code == 200:
            for m in r.json().get("models", []):
                n = m["name"].split("/", 1)[-1]
                if ("generateContent" in m.get("supportedGenerationMethods", [])
                        and "flash" in n
                        and not any(x in n for x in ("image", "tts", "live", "audio", "embedding", "robotics"))):
                    names.append(n)
            names.sort(key=lambda n: (("preview" in n) or ("exp" in n), "lite" in n, n))  # stable ones first
        else:
            print(f"[WARN] ListModels -> {r.status_code}: {r.text[:200]}")
    except requests.RequestException as exc:
        print(f"[WARN] ListModels failed: {type(exc).__name__}")
    _model_cache.update(t=time.time(), names=names)
    return names


def ask_chatbot(history, user_msg):
    """Return (reply_text, ok). Retries temporary errors and falls back to other models."""
    if not GEMINI_API_KEY:
        return ("AI chatbot is not configured yet (set GEMINI_API_KEY in .env). "
                "Meanwhile: use the Recommendation tab for soil/crop guidance.", False)

    contents = [{"role": "user", "parts": [{"text": f"Instructions: {SYSTEM_PROMPT}"}]}]
    for h in history:
        contents.append({
            "role": "user" if h["role"] == "user" else "model",
            "parts": [{"text": h["message"]}],
        })
    contents.append({"role": "user", "parts": [{"text": user_msg}]})

    deadline = time.time() + 40  # never leave the user waiting longer than this
    tried = []

    def try_model(model):
        tried.append(model)
        for attempt in range(2):
            if time.time() > deadline:
                return None
            try:
                r = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                    params={"key": GEMINI_API_KEY}, json={"contents": contents}, timeout=15,
                )
            except requests.RequestException as exc:
                print(f"[WARN] Gemini {model}: {type(exc).__name__}")
                time.sleep(1)
                continue
            if r.status_code == 200:
                try:
                    return r.json()["candidates"][0]["content"]["parts"][0]["text"]
                except (KeyError, IndexError):
                    print(f"[WARN] Gemini {model} returned no text: {r.text[:300]}")
                    return None
            print(f"[WARN] Gemini {model} -> {r.status_code}: {r.text[:300]}")
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(1.5)
                continue
            return None  # 400/403/404: this model won't work for this key
        return None

    for model in [GEMINI_MODEL] + [m for m in GEMINI_FALLBACKS if m != GEMINI_MODEL]:
        text = try_model(model)
        if text:
            return text, True
    # Last resort: models that Google says this key can use
    for model in [m for m in discover_models() if m not in tried][:3]:
        text = try_model(model)
        if text:
            print(f"[INFO] Working model found: {model} (set GEMINI_MODEL={model} in .env)")
            return text, True
    return ("The AI assistant is busy or unavailable right now. Please try again in a moment.", False)


# ---------- Routes: auth ----------
@app.context_processor
def inject_soils():
    return {"all_soils": SOILS, "soil_colors": SOIL_COLORS}


@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("landing.html", soil_crops=soil_crops())


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or "@" not in email or len(password) < 8:
            flash("Enter a name, valid email, and a password of at least 8 characters.", "error")
            return render_template("register.html")
        db = get_db()
        existing = db.execute("SELECT id, is_verified FROM users WHERE email = ?", (email,)).fetchone()
        if existing and existing["is_verified"]:
            flash("That email is already registered. Please log in.", "error")
            return redirect(url_for("login"))
        if existing:
            db.execute("UPDATE users SET name=?, password_hash=? WHERE id=?",
                       (name, generate_password_hash(password), existing["id"]))
        else:
            db.execute("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                       (name, email, generate_password_hash(password)))
        db.commit()
        sent = create_and_send_otp(email)
        session["pending_email"] = email
        flash("We emailed you a 6-digit code." if sent
              else "Email not configured - check the server console for your OTP (dev mode).", "info")
        return redirect(url_for("verify"))
    return render_template("register.html")


@app.route("/verify", methods=["GET", "POST"])
def verify():
    email = session.get("pending_email")
    if not email:
        return redirect(url_for("register"))
    if request.method == "POST":
        code = request.form.get("otp", "").strip()
        db = get_db()
        row = db.execute("SELECT * FROM otps WHERE email = ?", (email,)).fetchone()
        if not row:
            flash("No active code. Please request a new one.", "error")
        elif datetime.utcnow() > datetime.fromisoformat(row["expires_at"]):
            flash("That code has expired. Request a new one.", "error")
        elif row["attempts"] >= MAX_OTP_ATTEMPTS:
            flash("Too many attempts. Request a new code.", "error")
        elif not check_password_hash(row["otp_hash"], code):
            db.execute("UPDATE otps SET attempts = attempts + 1 WHERE id = ?", (row["id"],))
            db.commit()
            flash("Incorrect code.", "error")
        else:
            db.execute("UPDATE users SET is_verified = 1 WHERE email = ?", (email,))
            db.execute("DELETE FROM otps WHERE email = ?", (email,))
            db.commit()
            session.pop("pending_email", None)
            flash("Email verified! You can log in now.", "success")
            return redirect(url_for("login"))
    return render_template("verify.html", email=email)


@app.route("/resend-otp", methods=["POST"])
def resend_otp():
    email = session.get("pending_email")
    if not email:
        return redirect(url_for("register"))
    sent = create_and_send_otp(email)
    flash("New code sent." if sent else "New code generated - check the server console (dev mode).", "info")
    return redirect(url_for("verify"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.", "error")
        elif not user["is_verified"]:
            session["pending_email"] = email
            create_and_send_otp(email)
            flash("Please verify your email first. We sent a new code.", "info")
            return redirect(url_for("verify"))
        else:
            session.clear()
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------- Routes: app ----------
@app.route("/dashboard")
@login_required
def dashboard():
    recent = get_db().execute(
        "SELECT soil, crop, city, created_at FROM searches WHERE user_id=? ORDER BY id DESC LIMIT 5",
        (session["user_id"],),
    ).fetchall()
    chat = get_db().execute(
        "SELECT role, message FROM chat_history WHERE user_id=? ORDER BY id DESC LIMIT 30",
        (session["user_id"],),
    ).fetchall()[::-1]
    return render_template("dashboard.html", soils=SOILS, crops=sorted(CROPS), recent=recent, chat=chat)


@app.route("/api/weather")
@login_required
def api_weather():
    city = request.args.get("city", "").strip()
    if not city:
        return jsonify({"error": "City is required."}), 400
    result = fetch_weather(city)
    return jsonify(result), (400 if "error" in result else 200)


@app.route("/api/recommend", methods=["POST"])
@login_required
def api_recommend():
    data = request.get_json(silent=True) or {}
    soil, crop, city = data.get("soil"), data.get("crop"), (data.get("city") or "").strip()
    weather, temp = None, None
    if city:
        weather = fetch_weather(city)
        if "error" not in weather:
            temp = weather.get("temperature_c")
    result = recommend(soil, crop, temp)
    if not result:
        return jsonify({"error": "Invalid soil or crop."}), 400
    db = get_db()
    db.execute("INSERT INTO searches (user_id, soil, crop, city) VALUES (?, ?, ?, ?)",
               (session["user_id"], soil, crop, city or None))
    db.commit()
    return jsonify({"recommendation": result, "weather": weather})


@app.route("/api/chat", methods=["POST"])
@login_required
def api_chat():
    msg = ((request.get_json(silent=True) or {}).get("message") or "").strip()
    if not msg:
        return jsonify({"error": "Message is empty."}), 400
    db = get_db()
    history = db.execute(
        "SELECT role, message FROM chat_history WHERE user_id=? ORDER BY id DESC LIMIT 10",
        (session["user_id"],),
    ).fetchall()[::-1]
    reply, ok = ask_chatbot(history, msg[:1000])
    if ok:  # don't store errors in history, they would pollute future prompts
        db.execute("INSERT INTO chat_history (user_id, role, message) VALUES (?, 'user', ?)", (session["user_id"], msg))
        db.execute("INSERT INTO chat_history (user_id, role, message) VALUES (?, 'bot', ?)", (session["user_id"], reply))
        db.commit()
    return jsonify({"reply": reply})


init_db()

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "1") == "1")
