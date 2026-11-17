import json
import os
import time

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory

# Load keys from the .env file (never commit .env)
load_dotenv()

app = Flask(__name__, static_folder="static")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
# Models are tried in order; if one is overloaded or unavailable, the next one is used
_primary = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
MODELS = list(dict.fromkeys([_primary, "gemini-3.6-flash", "gemini-3.5-flash-lite"]))
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# City coordinates (used for live AQI)
CITIES = {
    "Lahore": (31.5204, 74.3587),
    "Karachi": (24.8607, 67.0011),
    "Islamabad": (33.6844, 73.0479),
    "Faisalabad": (31.4504, 73.1350),
    "Multan": (30.1575, 71.5249),
    "Rawalpindi": (33.5651, 73.0169),
    "Peshawar": (34.0151, 71.5249),
}

# Safety rules for the AI (system instruction)
SYSTEM_RULES = (
    "You are 'AI Smog Health Guide', a health guide for ordinary people about air pollution. "
    "Rules: 1) Never give a diagnosis or treatment, and never mention medicines or doses. "
    "2) Give only general prevention and precaution guidance. "
    "3) If someone has difficulty breathing, chest pain, fainting, or a child or pregnant woman has severe symptoms, "
    "tell them to see a doctor or call emergency services (1122) immediately. "
    "4) Keep answers short, clear and in simple language. "
    "5) If information is missing, do not guess; say so clearly."
)


def aqi_band(aqi):
    """Converts US AQI into a category (this part is done in code, not by the AI)."""
    if aqi <= 50:
        return "Good"
    if aqi <= 100:
        return "Moderate"
    if aqi <= 150:
        return "Unhealthy for sensitive groups"
    if aqi <= 200:
        return "Unhealthy"
    if aqi <= 300:
        return "Very unhealthy"
    return "Hazardous"


def call_gemini(prompt, json_mode=False):
    """Makes a live call to Gemini. Raises an exception if something goes wrong."""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set. Check your .env file.")
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM_RULES}]},
        "contents": [{"parts": [{"text": prompt}]}],
    }
    if json_mode:
        body["generationConfig"] = {"responseMimeType": "application/json"}
    headers = {"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"}
    last = None
    for model in MODELS:
        for attempt in range(2):
            last = requests.post(
                f"{GEMINI_BASE}/{model}:generateContent", headers=headers, json=body, timeout=30
            )
            if last.status_code == 200:
                return last.json()["candidates"][0]["content"]["parts"][0]["text"]
            if last.status_code == 404:
                break  # this model is not available for this account, try the next one
            if last.status_code in (429, 500, 503, 504):
                time.sleep(1.5)  # busy server, wait and retry
                continue
            last.raise_for_status()  # other errors (for example a bad key) are raised straight away
    last.raise_for_status()
    raise RuntimeError("The AI service is busy. Please try again in a moment.")


def profile_text(p):
    """Writes the user's profile as a single line for the AI."""
    conditions = ", ".join(p.get("conditions") or []) or "none"
    return (
        f"City: {p.get('city', 'Lahore')}; Age group: {p.get('age_group', 'adult')}; "
        f"Existing conditions: {conditions}; Works outdoors: {'yes' if p.get('outdoor_worker') else 'no'}"
    )


@app.route("/")
def home():
    return send_from_directory("static", "index.html")


@app.route("/api/aqi")
def get_aqi():
    """Live AQI (Open-Meteo, free, no key needed)."""
    city = request.args.get("city", "Lahore")
    lat, lon = CITIES.get(city, CITIES["Lahore"])
    try:
        r = requests.get(
            "https://air-quality-api.open-meteo.com/v1/air-quality",
            params={"latitude": lat, "longitude": lon, "current": "us_aqi,pm2_5"},
            timeout=15,
        )
        r.raise_for_status()
        cur = r.json()["current"]
        aqi = round(cur["us_aqi"])
        return jsonify({"city": city, "aqi": aqi, "pm25": cur.get("pm2_5"), "band": aqi_band(aqi)})
    except Exception as e:
        # If the API fails, the frontend offers manual AQI entry
        return jsonify({"error": f"Could not get live AQI. Please enter the AQI manually. ({e})"}), 502


@app.route("/api/advice", methods=["POST"])
def advice():
    data = request.get_json(silent=True) or {}
    profile = data.get("profile") or {}
    language = data.get("language", "Roman Urdu")
    try:
        aqi = float(data.get("aqi"))
    except (TypeError, ValueError):
        return jsonify({"error": "Please enter a valid AQI number."}), 400
    if not 0 <= aqi <= 1000:
        return jsonify({"error": "AQI must be between 0 and 1000."}), 400

    band = aqi_band(aqi)
    prompt = (
        f"Today's AQI: {aqi:.0f} ({band}).\n"
        f"User profile: {profile_text(profile)}.\n"
        f"Reply language: {language}.\n\n"
        "Give personalised guidance for this user. Return JSON only, in exactly this format:\n"
        '{"risk_level": "Low/Medium/High/Severe (for this user)", '
        '"headline": "one-line conclusion", '
        '"go_outside": {"verdict": "yes/with caution/no", "details": "how long, when"}, '
        '"mask": "which mask and when", '
        '"do": ["3-4 actions"], "avoid": ["3-4 things to avoid"], '
        '"home_tips": ["2-3 tips for the home"], '
        '"see_doctor_if": ["2-4 symptoms that need a doctor or 1122"]}'
    )
    try:
        raw = call_gemini(prompt, json_mode=True)
        result = json.loads(raw)
        result["aqi"] = round(aqi)
        result["band"] = band
        return jsonify(result)
    except requests.exceptions.Timeout:
        return jsonify({"error": "The AI took too long. Please try again."}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Could not reach the AI: {e}"}), 502
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500
    except (KeyError, IndexError, json.JSONDecodeError):
        return jsonify({"error": "Could not understand the AI's response. Please try again."}), 502


@app.route("/api/ask", methods=["POST"])
def ask():
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"error": "Please write a question first."}), 400
    if len(question) > 500:
        return jsonify({"error": "Please keep the question short (up to 500 characters)."}), 400

    profile = data.get("profile") or {}
    language = data.get("language", "Roman Urdu")
    aqi = data.get("aqi")
    prompt = (
        f"Today's AQI: {aqi}. User profile: {profile_text(profile)}.\n"
        f"Guidance already given: {json.dumps(data.get('advice') or {}, ensure_ascii=False)[:1500]}\n"
        f"Reply language: {language}.\n"
        f"User's question: {question}\n"
        "Answer in 3-4 lines, based on this AQI and profile."
    )
    try:
        return jsonify({"answer": call_gemini(prompt).strip()})
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Could not reach the AI: {e}"}), 502
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500
    except (KeyError, IndexError):
        return jsonify({"error": "Could not understand the AI's response. Please try again."}), 502


if __name__ == "__main__":
    app.run(debug=True, port=5000)