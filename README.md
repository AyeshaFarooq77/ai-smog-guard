# AI Smog Health Guide

An AI-powered, multilingual air-quality health advisor that turns live AQI data into personalised protection guidance (Urdu, Roman Urdu, English).

Built for the STCS AI Hackathon & Startup Pitch, Minhaj University Lahore (SDG 3: Good Health and Well-Being).

## Problem
Everyone sees the AQI number, but few know what it means for *them*. An asthma patient, a pregnant woman, a child and a healthy adult face very different risks on the same smog day, and generic advice ("stay indoors") does not fit everyone.

## Users
- Families, children and elderly people in smog-affected cities (Lahore and other Pakistani cities)
- People with asthma, heart or breathing problems, and pregnant women
- Outdoor workers (riders, vendors, labourers)

## What it does
1. Fetches live AQI for the chosen city (Open-Meteo, no key needed). Manual AQI entry is the fallback.
2. User picks a simple health profile (age group, conditions, outdoor work) and language.
3. Gemini generates personalised advice as structured JSON: whether to go outside, mask guidance, do and avoid lists, home tips, and warning signs for seeing a doctor or calling 1122.
4. User can ask follow-up questions, answered using the same AQI and profile.
5. A "Read aloud" button speaks the advice (browser speech).

## AI stack
- Google Gemini API (live calls, structured JSON output, system-instruction safety rules)
- Open-Meteo Air Quality API (live data)
- Flask backend, plain HTML/CSS/JS frontend

## Safety
No diagnosis, treatment or dosage. General prevention guidance only, with a disclaimer on every result and referral to a doctor or 1122 for serious symptoms. No personal or patient data is stored.

## Startup model
- Schools and employers: per-seat subscription for smog alerts and guidance
- Hospitals and clinics: patient advisory tool for asthma and heart patients
- Delivery and ride companies: rider-safety programme
- Insurance and NGOs: partnerships for preventive health
- Individuals: free basic plan, family premium plan

## Local setup
1. Python 3.10+ required.
2. Create and activate a virtual environment:
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
3. Copy `.env.example` to `.env` and add your Gemini key:
```
GEMINI_API_KEY=your_key_here
```
4. Run:
```
python app.py
```
5. Open http://localhost:5000

## Project structure
```
app.py            Flask backend (AQI fetch, Gemini calls)
static/           index.html, style.css, script.js
requirements.txt
.env.example      template only, no real keys
```
