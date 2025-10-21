# -*- coding: utf-8 -*-
import streamlit as st
from streamlit_option_menu import option_menu
import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image
import io
import os
import json
import base64
from datetime import datetime, timedelta
import time
import warnings
import random
import uuid
from pathlib import Path
from io import BytesIO
import tempfile
import socket
import hashlib
import os
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from twilio.rest import Client

# Load environment variables from .env file
load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
FASTAPI_URL = os.getenv("FASTAPI_URL", "http://localhost:8000")
DATABASE_PATH = os.getenv("DATABASE_PATH", "kilimoglow.db")



warnings.filterwarnings("ignore")


st.set_page_config(
    page_title="KilimoGlow Kenya - Plant Doctor",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)
# ================== BASE_64_CONVERSION ==================
@st.cache_data
def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except:
        return None

# ================== CSS STYLING ==================
def apply_enhanced_css():
    bg_image_base64 = get_base64_image("plant_disease_classification.png")
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    * { font-family: 'Inter', sans-serif; box-sizing: border-box; }
    
    
    .stApp {
    """ + (f"""
    background: linear-gradient(rgba(26, 77, 46, 0.85), rgba(45, 94, 63, 0.85)), 
                url('data:image/png;base64,{bg_image_base64}') center/cover no-repeat fixed;
    """ if bg_image_base64 else """
    background: linear-gradient(135deg, #1a4d2e 0%, #2d5e3f 25%, #1a4d2e 50%, #2d5e3f 75%, #1a4d2e 100%);
    background-size: 400% 400%;
    animation: gradientShift 15s ease infinite;
    """) + """
    color: white;
}
                
    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    @media (max-width: 768px) {
        .main-header h1 { font-size: 2rem !important; }
        .kenyan-card { padding: 1rem !important; margin: 0.5rem 0 !important; }
        .stButton>button { padding: 0.6rem 1.5rem !important; font-size: 0.9rem !important; }
    }
    .css-1d391kg, .css-1cypcdb, [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a4d2e, #2d5e3f) !important;
        border-right: 3px solid #FFD700;
    }
    .main-header {
        background: linear-gradient(135deg, #1a4d2e, #2d5e3f, #3a7f4a);
        padding: 2rem; border-radius: 20px; text-align: center; margin-bottom: 2rem;
        box-shadow: 0 15px 35px rgba(26, 77, 46, 0.4); border: 2px solid #FFD700;
        position: relative; overflow: hidden;
    }
    .main-header::before {
        content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%;
        background: radial-gradient(circle, rgba(255, 215, 0, 0.1) 0%, transparent 70%);
        animation: rotate 20s linear infinite;
    }
    @keyframes rotate { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    .kenyan-card {
        background: linear-gradient(145deg, rgba(26, 77, 46, 0.3), rgba(45, 94, 63, 0.2));
        backdrop-filter: blur(15px); border: 1px solid rgba(255, 215, 0, 0.3);
        padding: 1.5rem; border-radius: 15px; margin: 1rem 0;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2); transition: all 0.3s;
    }
    .kenyan-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 35px rgba(255, 215, 0, 0.3);
    }
    .analysis-card {
        background: linear-gradient(145deg, rgba(26, 77, 46, 0.4), rgba(45, 94, 63, 0.3));
        border: 2px solid #3a7f4a; padding: 2rem; border-radius: 15px; margin: 2rem 0;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
    }
    .stButton>button {
        background: linear-gradient(45deg, #1a4d2e, #2d5e3f, #3a7f4a);
        color: white !important; border: 2px solid #FFD700; border-radius: 12px;
        padding: 0.75rem 2rem; font-weight: 600; transition: all 0.3s; width: 100%;
    }
    .stButton>button:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 25px rgba(255, 215, 0, 0.4);
        background: linear-gradient(45deg, #2d5e3f, #3a7f4a, #4a9f5a);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px; background: rgba(26, 77, 46, 0.3); padding: 8px; border-radius: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        background: rgba(255, 255, 255, 0.1); border-radius: 10px; padding: 0.7rem 1.2rem;
        color: white; border: 1px solid rgba(255, 215, 0, 0.2); transition: all 0.3s;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(45deg, #1a4d2e, #3a7f4a) !important;
        color: white !important; border-color: #FFD700 !important;
    }
    .metric-card {
        background: rgba(58, 127, 74, 0.2); padding: 1.5rem; border-radius: 15px;
        text-align: center; border: 1px solid rgba(255, 215, 0, 0.3);
        transition: all 0.3s; backdrop-filter: blur(10px);
    }
    .metric-card:hover { transform: translateY(-3px); }
    .app-footer {
        background: linear-gradient(135deg, rgba(26, 77, 46, 0.3), rgba(45, 94, 63, 0.2));
        border: 1px solid rgba(255, 215, 0, 0.3); border-radius: 15px;
        padding: 2rem; margin-top: 3rem; text-align: center; backdrop-filter: blur(10px);
    }
    h1, h2, h3, h4, h5, h6 { color: white !important; text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3); }
    </style>
    """, unsafe_allow_html=True)

# ================== APPLY GLOBAL CSS ==================
apply_enhanced_css()
# ======================================================


# ================== CACHE & OFFLINE SYSTEM ==================
_HYBRID_CACHE_FILE = Path.home() / ".kilimoglow_cache.json"

def _load_persistent_cache():
    try:
        if _HYBRID_CACHE_FILE.exists():
            return json.loads(_HYBRID_CACHE_FILE.read_text(encoding="utf-8"))
    except:
        pass
    return {"images":{}, "history":[], "version":"1.0"}

def _save_persistent_cache(cache_obj):
    try:
        _HYBRID_CACHE_FILE.write_text(json.dumps(cache_obj, ensure_ascii=False, indent=2), encoding="utf-8")
    except:
        pass

def _md5_bytes(b: bytes) -> str:
    h = hashlib.md5()
    h.update(b)
    return h.hexdigest()

def compute_file_hash(file_obj):
    try:
        pos = file_obj.tell()
    except:
        pos = None
    try:
        content = file_obj.read()
        if hasattr(file_obj, "seek"):
            file_obj.seek(0 if pos is None else pos)
        return _md5_bytes(content)
    except:
        return None

def _image_from_filelike(file_obj):
    try:
        cur = file_obj.tell()
    except:
        cur = None
    try:
        img = Image.open(file_obj).convert("RGB")
        if hasattr(file_obj, "seek") and cur is not None:
            file_obj.seek(cur)
        return img
    except:
        if hasattr(file_obj, "seek"):
            try:
                file_obj.seek(0)
                img = Image.open(file_obj).convert("RGB")
                return img
            except:
                return None
        return None

def compute_color_histogram(img: Image.Image, bins=32):
    arr = np.asarray(img.resize((256,256)))
    hist = []
    for c in range(3):
        h, _ = np.histogram(arr[...,c], bins=bins, range=(0,255), density=True)
        hist.append(h.astype(np.float32))
    return np.concatenate(hist, axis=0)

def compute_phash(img: Image.Image, size=32, smaller=8):
    img_small = img.resize((size, size)).convert("L")
    a = np.asarray(img_small, dtype=np.float32)
    dct = np.real(np.fft.fft2(a))
    dct_lowfreq = dct[:smaller, :smaller]
    med = np.median(dct_lowfreq)
    bits = (dct_lowfreq > med).astype(np.uint8).flatten()
    return bits

def cosine_similarity(a, b, eps=1e-8):
    a = a.astype(np.float32); b = b.astype(np.float32)
    num = float(np.dot(a, b))
    den = float(np.linalg.norm(a) * np.linalg.norm(b) + eps)
    return num / den

def hamming_similarity(a_bits, b_bits):
    if a_bits.shape != b_bits.shape:
        return 0.0
    same = np.sum(a_bits == b_bits)
    return float(same) / float(a_bits.size)

def _now_ts():
    return int(time.time())

def _season_weight(month):
    if month in (3,4,5,10,11,12):
        return 1.1
    return 1.0

def hybrid_offline_predict(file_obj, metadata=None, simulate_fn=None):
    persistent = _load_persistent_cache()
    if 'offline_cache' not in st.session_state:
        st.session_state.offline_cache = {}
    if 'offline_queue' not in st.session_state:
        st.session_state.offline_queue = []
    if 'hybrid_metrics' not in st.session_state:
        st.session_state.hybrid_metrics = {'hits':0,'misses':0,'conflicts':0}

    meta = metadata or {}
    meta.setdefault("weather", st.session_state.get("weather_condition", "Unknown"))
    meta.setdefault("soil", st.session_state.get("soil_type", "Unknown"))
    meta.setdefault("timestamp", _now_ts())

    img_hash = compute_file_hash(file_obj)
    if img_hash and img_hash in persistent.get("images", {}):
        rec = persistent["images"][img_hash]
        st.session_state.hybrid_metrics['hits'] += 1
        rec['model_version'] = "offline_cached_exact_v1"
        return rec

    img = _image_from_filelike(file_obj)
    if img is None:
        if simulate_fn is not None:
            return simulate_fn()
        return {"success": True, "predicted_class": "Unknown", "confidence": 0.5, "model_version": "offline_unknown_image"}

    color_hist = compute_color_histogram(img, bins=32)
    phash_bits = compute_phash(img, size=32, smaller=8)

    best_score = -1.0
    best_rec = None
    for k, rec in persistent.get("images", {}).items():
        try:
            rh = np.array(rec.get("color_hist", []), dtype=np.float32)
            rb = np.array(rec.get("phash_bits", []), dtype=np.uint8)
            if rh.size and rb.size:
                sim1 = cosine_similarity(color_hist, rh)
                sim2 = hamming_similarity(phash_bits, rb)
                vscore = 0.6*sim1 + 0.4*sim2
                if meta.get("soil") and rec.get("meta", {}).get("soil") == meta.get("soil"):
                    vscore *= 1.05
                if meta.get("weather") and rec.get("meta", {}).get("weather") == meta.get("weather"):
                    vscore *= 1.05
                if vscore > best_score:
                    best_score = vscore
                    best_rec = rec
        except:
            continue

    if best_rec is not None and best_score >= 0.78:
        st.session_state.hybrid_metrics['hits'] += 1
        enriched = dict(best_rec)
        enriched['model_version'] = "offline_visual_match_v1"
        enriched['similarity'] = float(best_score)
        return enriched

    priors = {}
    history = st.session_state.get("analysis_history", [])
    month = datetime.utcnow().month
    for h in history[-50:]:
        cls = h.get("predicted_class") or h.get("label") or h.get("class")
        if not cls:
            continue
        w = 1.0
        if h.get("soil") == meta.get("soil"):
            w *= 1.2
        if h.get("weather") == meta.get("weather"):
            w *= 1.2
        w *= _season_weight(month)
        priors[cls] = priors.get(cls, 0.0) + w

    if priors:
        total = sum(priors.values())
        items = sorted(((k, v/total) for k, v in priors.items()), key=lambda x: -x[1])
        top_cls, prob = items[0]
        if prob >= 0.25:
            st.session_state.hybrid_metrics['hits'] += 1
            return {
                "success": True,
                "predicted_class": top_cls,
                "confidence": round(min(0.95, 0.6 + prob*0.4), 3),
                "model_version": "offline_context_priors_v1",
                "explain": {"source":"farm_history", "top_prob": float(prob)}
            }

    if simulate_fn is not None:
        return simulate_fn()
    return {"success": True, "predicted_class": "Unknown", "confidence": 0.5, "model_version": "offline_sim_last_resort"}

def hybrid_cache_learn(image_file, result_record, metadata=None):
    persistent = _load_persistent_cache()
    img = _image_from_filelike(image_file)
    if img is None:
        return
    color_hist = compute_color_histogram(img, bins=32).tolist()
    phash_bits = compute_phash(img, size=32, smaller=8).astype(int).tolist()
    try:
        image_file.seek(0)
        content = image_file.read()
        image_file.seek(0)
        key = _md5_bytes(content)
    except:
        key = str(uuid.uuid4())
    rec = {
        "predicted_class": result_record.get("predicted_class") or result_record.get("label"),
        "confidence": float(result_record.get("confidence", 0.7)),
        "timestamp": _now_ts(),
        "color_hist": color_hist,
        "phash_bits": phash_bits,
        "meta": {
            "weather": st.session_state.get("weather_condition", "Unknown"),
            "soil": st.session_state.get("soil_type", "Unknown")
        }
    }
    persistent.setdefault("images", {})[key] = rec
    persistent.setdefault("history", []).append({
        "predicted_class": rec["predicted_class"],
        "confidence": rec["confidence"],
        "timestamp": rec["timestamp"],
        "soil": rec["meta"]["soil"],
        "weather": rec["meta"]["weather"]
    })
    _save_persistent_cache(persistent)

# ================== NETWORK & API ==================
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "127.0.0.1"

def get_api_url():

    # Check .env first
    env_url = os.getenv("FASTAPI_URL")
    if env_url:
        try:
            resp = requests.get(f"{env_url}/health", timeout=2)
            if resp.status_code == 200:
                return env_url
        except:
            pass


    if 'working_api_url' in st.session_state and st.session_state.working_api_url:
        try:
            resp = requests.get(f"{st.session_state.working_api_url}/health", timeout=2)
            if resp.status_code == 200:
                return st.session_state.working_api_url
        except:
            pass

    urls_to_try = []
    lan_ip = get_local_ip()
    if lan_ip and lan_ip != "127.0.0.1":
        urls_to_try.append(f"http://{lan_ip}:8000")
    pub_url = os.getenv("FASTAPI_PUBLIC_URL")
    if pub_url:
        urls_to_try.append(pub_url)
    urls_to_try += ["http://127.0.0.1:8000", "http://localhost:8000"]

    for url in urls_to_try:
        try:
            resp = requests.get(f"{url}/health", timeout=3)
            if resp.status_code == 200:
                st.session_state.working_api_url = url
                return url
        except:
            continue
    return "http://127.0.0.1:8000"

FASTAPI_BASE_URL = get_api_url()
FASTAPI_ENDPOINTS = {
    "health": f"{FASTAPI_BASE_URL}/health",
    "predict": f"{FASTAPI_BASE_URL}/predict",
    "batch_predict": f"{FASTAPI_BASE_URL}/batch_predict",
    "model_info": f"{FASTAPI_BASE_URL}/model/info"
}

def safe_json(resp):
    try:
        return resp.json()
    except:
        return {"status_code": getattr(resp, "status_code", None), "text": getattr(resp, "text", "")}

def check_fastapi_connection(timeout=3):
    urls_to_try = [os.getenv("FASTAPI_URL"), os.getenv("FASTAPI_PUBLIC_URL"), f"http://{get_local_ip()}:8000", "http://127.0.0.1:8000", "http://localhost:8000"]
    for url in urls_to_try:
        if not url:
            continue
        try:
            resp = requests.get(f"{url}/health", timeout=timeout)
            if resp.status_code == 200:
                return True, safe_json(resp), url
        except:
            continue
    return False, {"error": "All connection attempts failed"}, None

def predict_with_fastapi(file_obj, timeout=25):
    try:
        if hasattr(file_obj, 'seek'):
            file_obj.seek(0)
        files = {}
        if hasattr(file_obj, 'name') and hasattr(file_obj, 'type'):
            files["file"] = (file_obj.name, file_obj, file_obj.type)
        elif hasattr(file_obj, 'read'):
            content = file_obj.read()
            file_obj.seek(0)
            files["file"] = ("image.jpg", BytesIO(content), "image/jpeg")
        else:
            files["file"] = ("image.jpg", file_obj, "image/jpeg")
        resp = requests.post(f"{FASTAPI_BASE_URL}/predict", files=files, timeout=timeout)
        if resp.status_code == 200:
            return True, safe_json(resp)
        else:
            return False, {"status_code": resp.status_code, "error": safe_json(resp)}
    except Exception as e:
        return False, {"error": str(e)}

def batch_predict_with_fastapi(file_list, timeout=60):
    try:
        files = []
        for i, file_obj in enumerate(file_list):
            if hasattr(file_obj, 'seek'):
                file_obj.seek(0)
            if hasattr(file_obj, 'name') and hasattr(file_obj, 'type'):
                files.append(('files', (file_obj.name, file_obj, file_obj.type)))
            else:
                files.append(('files', (f"image_{i}.jpg", file_obj, "image/jpeg")))
        resp = requests.post(f"{FASTAPI_BASE_URL}/batch_predict", files=files, timeout=timeout)
        if resp.status_code == 200:
            return True, safe_json(resp)
        else:
            return False, {"status_code": resp.status_code, "error": safe_json(resp)}
    except Exception as e:
        return False, {"error": str(e)}

def get_model_info(timeout=10):
    try:
        resp = requests.get(f"{FASTAPI_BASE_URL}/model/info", timeout=timeout)
        if resp.status_code == 200:
            return safe_json(resp)
        return {}
    except:
        return {}

def simulate_disease_prediction():
    diseases = ['Pepper__bell___Bacterial_spot', 'Pepper__bell___healthy', 'Potato___Early_blight', 'Potato___Late_blight', 'Potato___healthy', 'Tomato_Bacterial_spot', 'Tomato_Early_blight', 'Tomato_Late_blight', 'Tomato___healthy']
    selected_disease = random.choice(diseases)
    confidence = random.uniform(0.75, 0.95)
    return {"predicted_class": selected_disease, "confidence": confidence, "processing_time": random.uniform(0.8, 2.5), "success": True, "model_version": "offline_v1.0"}

def cache_model_offline():
    try:
        model_info = get_model_info()
        if model_info:
            st.session_state.cached_model_info = model_info
            st.session_state.model_cached = True
            return True
    except:
        pass
    st.session_state.model_cached = True
    st.session_state.cached_model_info = {"model_version": "offline_cached_v1.0", "classes": [], "total_classes": 0}
    return True

# ================== TWILIO ALERTS ==================


def send_sms(to_number, message):
    try:
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        client.messages.create(
            body=message,
            from_=TWILIO_PHONE,
            to=to_number
        )
        st.success("📲 SMS sent successfully!")
    except Exception as e:
        st.error(f"Failed to send SMS: {e}")
# ===================================================

# ================== EMAIL NOTIFICATION ==================


def send_email(subject, body, recipient):
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = EMAIL_USER
        msg["To"] = recipient

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        st.success(f"📧 Email sent to {recipient}")
    except Exception as e:
        st.error(f"Email failed: {e}")
# =========================================================
def get_weather(city):
                    try:
                        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric"
                        response = requests.get(url)
                        if response.status_code == 200:
                            data = response.json()
                            return {
                                "temp": data["main"]["temp"],
                                "desc": data["weather"][0]["description"],
                                "humidity": data["main"]["humidity"]
                            }
                    except Exception as e:
                        st.warning(f"Weather fetch failed: {e}")
                        return None
# ==========================================================

# ================== SESSION STATE ==================
def init_session_state():
    defaults = {
        'analysis_history': [], 'batch_results': [], 'selected_language': 'English', 'user_name': '',
        'weather_condition': 'Select', 'soil_type': 'Select', 'api_status': 'checking', 'analysis_result': None,
        'current_analysis_id': None, 'uploaded_file_hash': None, 'voice_input_active': False,
        'camera_quality': 'Medium (720p)', 'working_api_url': None, 'cached_api_status': None,
        'model_cached': False, 'cached_model_info': {}, 'app_initialized': False, 'audio_enabled': True,
        'offline_cache': {}, 'offline_queue': [], 'hybrid_metrics': {'hits':0,'misses':0,'conflicts':0}
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

if 'app_initialized' not in st.session_state:
    init_session_state()
    st.session_state.app_initialized = True

# ================== TRANSLATIONS ==================
LANGUAGES = {"English": "en", "Kiswahili": "sw", "Luo": "luo"}

def translate_text(text, target_lang):
    if target_lang == "English":
        return text
    translations = {
        "Kiswahili": {
            "Home": "Nyumbani", "Plant Doctor": "Daktari wa Mimea", "Batch Analysis": "Uchambuzi wa Kundi",
            "Dashboard": "Bodi ya Habari", "Settings": "Mipangilio", "Bacterial Spot": "Madoa ya Bakteria",
            "Healthy Pepper": "Pilipili Mzima", "Early Blight": "Ukungu wa Mapema", "Late Blight": "Ukungu wa Mwisho",
            "Healthy Potato": "Viazi Mzima", "Healthy Tomato": "Nyanya Mzima", "Symptoms": "Dalili",
            "Treatment": "Matibabu", "Prevention": "Kinga", "Organic Treatment": "Matibabu Asilia",
            "Watering Advice": "Ushauri wa Kumwagilia", "Confidence": "Uhakika", "Severity": "Ukali",
            "Plant Type": "Aina ya Mmea", "Disease": "Ugonjwa", "Healthy": "Mzima", "Weather": "Hali ya Hewa",
            "Soil Type": "Aina ya Udongo", "Analysis Results": "Matokeo ya Uchambuzi", "Processing": "Inachakata",
            "Upload": "Pakia", "Analyze": "Chunguza", "Download": "Pakua", "Report": "Ripoti",
            "Total Scans": "Jumla ya Uchunguzi", "Healthy Plants": "Mimea Mizima", "Need Treatment": "Inahitaji Matibabu",
            "Please wait": "Tafadhali subiri", "Take a photo": "Piga picha", "Choose image": "Chagua picha",
            "Ready for analysis": "Iko tayari kwa uchambuzi", "Language": "Lugha", "Farmer": "Mkulima",
            "Date": "Tarehe", "Plant": "Mmea", "Critical": "Hatari Sana", "High": "Juu", "Medium": "Wastani",
            "None": "Hakuna", "Unknown": "Haijulikani", "Online": "Mtandaoni", "Offline": "Nje ya Mtandao",
            "Cached": "Imehifadhiwa", "System Status": "Hali ya Mfumo", "API": "API", "Analyses": "Uchambuzi",
            "Batch Results": "Matokeo ya Kundi", "Enable Audio Guidance": "Washa Mwongozo wa Sauti",
            "Made for Kenya": "Imefanyiwa Kenya", "Local Crops": "Mazao ya Ndani", "Multi-language": "Lugha Nyingi",
            "FastAPI Powered": "Inaendeshwa na FastAPI", "Mobile Optimized": "Imetengenezwa kwa Simu",
            "Batch Processing": "Uchakataji wa Kundi", "Audio Guidance": "Mwongozo wa Sauti",
            "AI Disease Detection": "Utambuzi wa Ugonjwa wa AI", "Mobile Features": "Vipengele vya Simu",
            "Built-in camera integration": "Kamera iliyojengwa ndani", "Touch-friendly interface": "Kiolesura kinacho guswa",
            "Offline mode capability": "Uwezo wa hali nje ya mtandao", "Comprehensive analytics dashboard": "Bodi kamili ya uchambuzi",
            "Export reports in multiple formats": "Hamisha ripoti katika muundo mbalimbali",
            "High accuracy disease detection": "Utambuzi wa usahihi wa juu wa magonjwa",
            "Local data storage and management": "Uhifadhi na usimamizi wa data ya ndani",
            "Audio guidance for accessibility": "Mwongozo wa sauti kwa upatikanaji",
            "Plant Information": "Taarifa za Mmea", "Your Name": "Jina Lako", "Enter your name": "Weka jina lako",
            "Weather Condition": "Hali ya Hewa", "Choose upload method:": "Chagua njia ya kupakia:",
            "Take Photo": "Piga Picha", "Upload from Device": "Pakia kutoka Kifaa",
            "Voice Description": "Maelezo ya Sauti", "Describe your plant issue": "Eleza tatizo la mmea wako",
            "Listening...": "Inasikiliza...", "Voice input": "Ingizo la sauti",
            "Voice input recorded. Please also upload an image for analysis.": "Sauti imerekodi. Tafadhali pia pakia picha kwa uchambuzi.",
            "Voice input not available on this device/browser": "Ingizo la sauti halipo kwenye kifaa/kivinjari hiki",
            "Plant Photo for Analysis": "Picha ya Mmea kwa Uchambuzi", "Analyze Plant": "Chunguza Mmea",
            "Image quality too poor for analysis": "Ubora wa picha ni duni sana kwa uchambuzi",
            "Invalid image format": "Muundo wa picha si sahihi", "Analyzing your plant... Please wait.": "Inachakata mmea wako... Tafadhali subiri.",
            "Attempting FastAPI analysis...": "Inajaribu uchambuzi wa FastAPI...", "Analysis completed with FastAPI!": "Uchambuzi umekamilika na FastAPI!",
            "FastAPI unavailable, using offline mode": "FastAPI haipo, inatumia hali nje ya mtandao",
            "Using cached analysis mode": "Inatumia hali ya uchambuzi iliyohifadhiwa",
            "Using offline simulation mode": "Inatumia hali ya uigaji nje ya mtandao",
            "Low confidence detection. Please ensure image shows clear plant leaves.": "Utambuzi wa uhakika mdogo. Hakikisha picha inaonyesha majani wazi ya mmea.",
            "Urgency": "Dharura", "Act immediately (today!)": "Fanya haraka (leo!)",
            "Treat within 2-3 days": "Tibu ndani ya siku 2-3", "Treat within a week": "Tibu ndani ya wiki",
            "Continue monitoring": "Endelea kufuatilia", "Monitor regularly": "Fuatilia mara kwa mara",
            "Local Solutions": "Suluhisho za Ndani", "Garlic + chili spray": "Dawa ya thumu + pilipili",
            "Neem leaves solution": "Suluhisho la majani ya neem", "Milk solution (1:10)": "Suluhisho la maziwa (1:10)",
            "Baking soda spray": "Dawa ya soda ya kuoka", "Compost tea": "Chai ya mbolea asilia",
            "Export Report": "Hamisha Ripoti", "Download Report (CSV)": "Pakua Ripoti (CSV)",
            "Download Report (TXT)": "Pakua Ripoti (TXT)", "Field": "Shamba", "Value": "Thamani",
            "PLANT ANALYSIS REPORT": "RIPOTI YA UCHAMBUZI WA MMEA", "Analysis ID": "Kitambulisho cha Uchambuzi",
            "ENVIRONMENTAL CONDITIONS": "HALI ZA MAZINGIRA", "ANALYSIS RESULTS": "MATOKEO YA UCHAMBUZI",
            "Disease/Condition": "Ugonjwa/Hali", "Severity Level": "Kiwango cha Ukali",
            "Confidence Score": "Alama ya Uhakika", "SYMPTOMS": "DALILI", "TREATMENT RECOMMENDATION": "MAPENDEKEZO YA MATIBABU",
            "ORGANIC TREATMENT": "MATIBABU ASILIA", "PREVENTION MEASURES": "HATUA ZA KUZUIA",
            "WATERING ADVICE": "USHAURI WA KUMWAGILIA", "MODEL INFO": "TAARIFA ZA MODELI",
            "Processing Time": "Muda wa Uchakataji", "Model Version": "Toleo la Modeli",
            "API Used": "API Iliyotumika", "Yes": "Ndio", "No": "Hapana", "Generated by": "Imetengenezwa na",
            "Upload Multiple Images": "Pakia Picha Nyingi", "Choose plant images": "Chagua picha za mimea",
            "Select multiple images for batch analysis": "Chagua picha nyingi kwa uchambuzi wa kundi",
            "images ready for processing": "picha ziko tayari kwa uchakataji", "Process Batch": "Chakata Kundi",
            "Processing batch... This may take a few minutes.": "Inachakata kundi... Hii inaweza kuchukua dakika chache.",
            "FastAPI batch processing failed, using individual processing": "Uchakataji wa kundi wa FastAPI umeshindwa, inatumia uchakataji wa moja kwa moja",
            "Using offline batch processing": "Inatumia uchakataji wa kundi nje ya mtandao",
            "Batch processing complete!": "Uchakataji wa kundi umekamilika!", "images analyzed.": "picha zimechambuliwa.",
            "Batch Results": "Matokeo ya Kundi", "Total Images": "Picha Zote", "Avg Confidence": "Uhakika Wastani",
            "Image": "Picha", "Disease Severity Distribution": "Usambazaji wa Ukali wa Ugonjwa",
            "Detailed Results": "Matokeo ya Kina", "Export Batch Results": "Hamisha Matokeo ya Kundi",
            "Download Batch CSV": "Pakua CSV ya Kundi", "Download Summary": "Pakua Muhtasari",
            "BATCH ANALYSIS REPORT": "RIPOTI YA UCHAMBUZI WA KUNDI", "Batch ID": "Kitambulisho cha Kundi",
            "Plants Needing Treatment": "Mimea Inayohitaji Matibabu", "Average Confidence": "Uhakika wa Wastani",
            "DETAILED RESULTS": "MATOKEO YA KINA", "Ready for Batch Processing": "Iko Tayari kwa Uchakataji wa Kundi",
            "Upload multiple images to see batch analysis results here": "Pakia picha nyingi kuona matokeo ya uchambuzi wa kundi hapa",
            "Dashboard Ready": "Bodi Iko Tayari", "Start analyzing plants to see comprehensive analytics and insights here": "Anza kuchambua mimea kuona uchambuzi kamili na maarifa hapa",
            "Your farming analytics will appear once you begin plant disease detection": "Uchambuzi wako wa kilimo utaonekana baada ya kuanza utambuzi wa magonjwa ya mimea",
            "Diseases Detected": "Magonjwa Yaliyogunduliwa", "Analysis Trends": "Mwelekeo wa Uchambuzi",
            "Daily Analyses": "Uchambuzi wa Kila Siku", "Cumulative": "Jumla", "Analysis Activity Over Time": "Shughuli za Uchambuzi kwa Wakati",
            "Daily Count": "Hesabu ya Kila Siku", "Plant Types": "Aina za Mimea", "Count": "Hesabu",
            "Plant Distribution": "Usambazaji wa Mimea", "Recent Analysis History": "Historia ya Uchambuzi wa Karibuni",
            "Time": "Muda", "System Configuration": "Usanidi wa Mfumo", "API Settings": "Mipangilio ya API",
            "FastAPI Status": "Hali ya FastAPI", "Connected": "Imeunganishwa", "Disconnected": "Imetenganishwa",
            "Base URL": "URL ya Msingi", "Available Endpoints": "Maeneo Yanayopatikana",
            "Test API Connection": "Jaribu Muunganisho wa API", "Testing connection...": "Inajaribu muunganisho...",
            "API connection successful!": "Muunganisho wa API umefanikiwa!", "API connection failed!": "Muunganisho wa API umeshindwa!",
            "Language & Localization": "Lugha na Utafsiri", "Supported Languages": "Lugha Zinazosaidia",
            "User Preferences": "Mapendeleo ya Mtumiaji", "User Profile": "Wasifu wa Mtumiaji",
            "Default Name": "Jina la Kawaida", "Default name for analysis reports": "Jina la kawaida kwa ripoti za uchambuzi",
            "Camera Quality": "Ubora wa Kamera", "Data Management": "Usimamizi wa Data",
            "Analysis History": "Historia ya Uchambuzi", "Total Analyses": "Uchambuzi Wote",
            "Clear History": "Futa Historia", "Reset All Data": "Rudisha Data Zote",
            "History cleared!": "Historia imefutwa!", "All data reset!": "Data zote zimerudishwa!",
            "Made for Kenyan Farmers": "Imefanyiwa Wakulima wa Kenya", "Supporting Local Agriculture": "Inasaidia Kilimo cha Ndani",
            "Powered by AI": "Inaendeshwa na AI", "Empowering smallholder farmers with smart plant disease detection technology": "Kuwezesha wakulima wadogo wa teknolojia ya utambuzi wa magonjwa ya mimea",
            "Version 2.0": "Toleo 2.0", "Built with": "Imejengwa na", "for Kenya's Agricultural Future": "kwa Mustakabali wa Kilimo wa Kenya"
        },
        "Luo": {
            "Home": "Dala", "Plant Doctor": "Jathieth Yath", "Batch Analysis": "Nonro Mangeny",
            "Dashboard": "Bord Weche", "Settings": "Chenro", "Bacterial Spot": "Kido mar Bacteria",
            "Healthy Pepper": "Pilipili Maber", "Early Blight": "Tuo mokwongo", "Late Blight": "Tuo mogik",
            "Healthy Potato": "Viazi Maber", "Healthy Tomato": "Nyanya Maber", "Symptoms": "Ranyisi",
            "Treatment": "Thieth", "Prevention": "Siro", "Organic Treatment": "Thieth Asili",
            "Watering Advice": "Puonj mar Pi", "Confidence": "Ogeno", "Severity": "Tek mar tuo",
            "Plant Type": "Kit yath", "Disease": "Tuo", "Healthy": "Maber", "Weather": "Koth gi chieng",
            "Soil Type": "Kit lowo", "Analysis Results": "Gik monyiso", "Processing": "Timo",
            "Upload": "Ket", "Analyze": "Nono", "Download": "Gol", "Report": "Ripoti",
            "Total Scans": "Nonro duto", "Healthy Plants": "Yath maber", "Need Treatment": "Dwaro thieth",
            "Please wait": "Rit", "Take a photo": "Mak fweny", "Choose image": "Yer fweny",
            "Ready for analysis": "Oikore ne nonro", "Language": "Dhok", "Farmer": "Japur",
            "Date": "Chieng", "Plant": "Yath", "Critical": "Lich marach", "High": "Malo", "Medium": "Maliyo",
            "None": "Onge", "Unknown": "Ok ongere", "Online": "E internet", "Offline": "Ok e internet",
            "Cached": "Osekano", "System Status": "Kaka gima tiyego", "API": "API", "Analyses": "Nonro",
            "Batch Results": "Gik manyiso mangeny", "Enable Audio Guidance": "Mok puonj gi dwond",
            "Made for Kenya": "Olos ne Kenya", "Local Crops": "Cham mag piny", "Multi-language": "Dhok mangeny",
            "FastAPI Powered": "FastAPI ema tiyogo", "Mobile Optimized": "Olos maber ne simu",
            "Batch Processing": "Tiy gi mangeny kanyachiel", "Audio Guidance": "Puonj gi dwond",
            "AI Disease Detection": "AI fwenyo tuo", "Mobile Features": "Gik ma simu nyal tiyo",
            "Built-in camera integration": "Kamera man ei simu", "Touch-friendly interface": "Gin ma inyalo mulo",
            "Offline mode capability": "Nyalo tiyo ka ionge internet", "Comprehensive analytics dashboard": "Bord weche duto",
            "Export reports in multiple formats": "Gol ripoti e kite mangeny",
            "High accuracy disease detection": "Fwenyo tuo maber ahinya",
            "Local data storage and management": "Kano gi rito weche mag piny",
            "Audio guidance for accessibility": "Puonj gi dwond ne ji duto",
            "Plant Information": "Weche mag yath", "Your Name": "Nyingi", "Enter your name": "Ndik nyingi",
            "Weather Condition": "Kaka koth gi chieng chalo", "Choose upload method:": "Yer kaka ibiro keto:",
            "Take Photo": "Mak Fweny", "Upload from Device": "Ket koa e gir", "Voice Description": "Lero gi dwond",
            "Describe your plant issue": "Nyis chandruok mar yathi", "Listening...": "Awinjo...",
            "Voice input": "Wach mane iwuoyo", "Voice input recorded. Please also upload an image for analysis.": "Dwondi osekano. Kendo ket fweny mondo onon.",
            "Voice input not available on this device/browser": "Dwond ok nyal tiyo e gir/browser-ni",
            "Plant Photo for Analysis": "Fweny yath mondo onon", "Analyze Plant": "Non yath",
            "Image quality too poor for analysis": "Fweny ok ler maber mondo onon",
            "Invalid image format": "Fweny ok nikare", "Analyzing your plant... Please wait.": "Anono yathi... Rit.",
            "Attempting FastAPI analysis...": "Atemo tiyo gi FastAPI...", "Analysis completed with FastAPI!": "Nonro oserumo gi FastAPI!",
            "FastAPI unavailable, using offline mode": "FastAPI ok ntie, atiyogo ka onge internet",
            "Using cached analysis mode": "Atiyogo gi nonro mosekani", "Using offline simulation mode": "Atiyogo ka onge internet",
            "Low confidence detection. Please ensure image shows clear plant leaves.": "Fwenyo ok ber ahinya. Ne ni fweny nyiso lith yath maler.",
            "Urgency": "Piyo mowinjore", "Act immediately (today!)": "Tim kawuono!", "Treat within 2-3 days": "Thiedh bangʼ ndalo 2-3",
            "Treat within a week": "Thiedh e juma", "Continue monitoring": "Dhi nyime kirango", "Monitor regularly": "Rang pile",
            "Local Solutions": "Yedhe mag piny", "Garlic + chili spray": "Yath thumu gi pilipili",
            "Neem leaves solution": "Suluhisho mar lith neem", "Milk solution (1:10)": "Suluhisho mar chak (1:10)",
            "Baking soda spray": "Yath soda kuteyo", "Compost tea": "Chai mar mbolea asilia",
            "Export Report": "Gol ripoti", "Download Report (CSV)": "Gol Ripoti (CSV)", "Download Report (TXT)": "Gol Ripoti (TXT)",
            "Field": "Puodho", "Value": "Nengo", "PLANT ANALYSIS REPORT": "RIPOTI MAR NONO YATH",
            "Analysis ID": "Namba mar nonro", "ENVIRONMENTAL CONDITIONS": "KAKA PINY CHALO",
            "ANALYSIS RESULTS": "GIK MANYISO", "Disease/Condition": "Tuo/Kaka ochalo",
            "Severity Level": "Kaka tuo tek", "Confidence Score": "Kaka ogeno ni adier",
            "SYMPTOMS": "RANYISI", "TREATMENT RECOMMENDATION": "PUONJ MAR THIETH",
            "ORGANIC TREATMENT": "THIETH ASILI", "PREVENTION MEASURES": "GIK MITIMO MONDO KISIR",
            "WATERING ADVICE": "PUONJ MAR OLO PI", "MODEL INFO": "WECHE MAG MODELI",
            "Processing Time": "Kinde motiyo", "Model Version": "Kaka modeli chalo",
            "API Used": "API mane otiyo", "Yes": "Ee", "No": "Ooyo", "Generated by": "Noloso gi",
            "Upload Multiple Images": "Ket fweny mangeny", "Choose plant images": "Yer fweny yath",
            "Select multiple images for batch analysis": "Yer fweny mangeny mondo onon kanyachiel",
            "images ready for processing": "fweny oikore mondo onon", "Process Batch": "Non mangeny kanyachiel",
            "Processing batch... This may take a few minutes.": "Anono mangeny... Manyalo kawo dakika moko.",
            "FastAPI batch processing failed, using individual processing": "FastAPI ok onyal nono mangeny, atiyogo achiel kachiel",
            "Using offline batch processing": "Atiyogo nono mangeny ka onge internet",
            "Batch processing complete!": "Nonro mangeny oserumo!", "images analyzed.": "fweny osenon.",
            "Batch Results": "Gik ma nonro mangeny onyiso", "Total Images": "Fweny duto",
            "Avg Confidence": "Ogeno wastani", "Image": "Fweny", "Disease Severity Distribution": "Kaka tuo opog",
            "Detailed Results": "Gik manyiso matut", "Export Batch Results": "Gol gik ma nonro mangeny onyiso",
            "Download Batch CSV": "Gol CSV mar mangeny", "Download Summary": "Gol mugiko",
            "BATCH ANALYSIS REPORT": "RIPOTI MAR NONO MANGENY", "Batch ID": "Namba mar mangeny",
            "Plants Needing Treatment": "Yath madwaro thieth", "Average Confidence": "Ogeno wastani",
            "DETAILED RESULTS": "GIK MANYISO MATUT", "Ready for Batch Processing": "Oikore ne nono mangeny",
            "Upload multiple images to see batch analysis results here": "Ket fweny mangeny mondo ine gik ma nonro onyiso ka",
            "Dashboard Ready": "Bord oikore", "Start analyzing plants to see comprehensive analytics and insights here": "Chak nono yath mondo ine weche duto ka",
            "Your farming analytics will appear once you begin plant disease detection": "Weche mag puothoni biro nenore ka ichako fwenyo tuo",
            "Diseases Detected": "Tuo mofweny", "Analysis Trends": "Kaka nonro dhi", "Daily Analyses": "Nonro pile",
            "Cumulative": "Giko duto", "Analysis Activity Over Time": "Tich nonro e kinde",
            "Daily Count": "Kwan pile", "Plant Types": "Kit yath", "Count": "Kwan", "Plant Distribution": "Kaka yath opog",
            "Recent Analysis History": "Nonro machien", "Time": "Saa", "System Configuration": "Kaka gima tiyego olos",
            "API Settings": "Chenro API", "FastAPI Status": "Kaka FastAPI tiyogi", "Connected": "Oriwore",
            "Disconnected": "Ok oriwore", "Base URL": "URL ma oko", "Available Endpoints": "Kuonde manyalo tiyo",
            "Test API Connection": "Tem API", "Testing connection...": "Atemo riwo...",
            "API connection successful!": "Riwo API otieko maber!", "API connection failed!": "Riwo API ok otieko!",
            "Language & Localization": "Dhok gi chenro", "Supported Languages": "Dhok ma itiyogi",
            "User Preferences": "Gima ihero", "User Profile": "Wecheni", "Default Name": "Nyingi machon",
            "Default name for analysis reports": "Nyingi machon ne ripoti", "Camera Quality": "Ler kamera",
            "Data Management": "Rito weche", "Analysis History": "Weche mag nonro machon",
            "Total Analyses": "Nonro duto", "Clear History": "Gol weche machon",
            "Reset All Data": "Dwok weche duto", "History cleared!": "Weche machon osegol!",
            "All data reset!": "Weche duto osedwok!", "Made for Kenyan Farmers": "Olos ne jopur Kenya",
            "Supporting Local Agriculture": "Konyo pur mag piny", "Powered by AI": "AI ema tiyogo",
            "Empowering smallholder farmers with smart plant disease detection technology": "Konyo jopur matindo gi teknoloji mar fwenyo tuo",
            "Version 2.0": "Version 2.0", "Built with": "Olos gi", "for Kenya's Agricultural Future": "ne kinde mag pur Kenya mabiro"
        }
    }
    lang_dict = translations.get(target_lang, {})
    if text in lang_dict:
        return lang_dict[text]
    for key, value in lang_dict.items():
        if key in text:
            text = text.replace(key, value)
    return text

def severity_badge(severity, lang="English"):
    colors = {"Critical": "#DC143C", "High": "#FF8C00", "Medium": "#FFD700", "None": "#32CD32", "Unknown": "#808080"}
    severity_translations = {
        "English": {"Critical": "Critical", "High": "High", "Medium": "Medium", "None": "Healthy", "Unknown": "Unknown"},
        "Kiswahili": {"Critical": "Hatari Sana", "High": "Juu", "Medium": "Wastani", "None": "Mzima", "Unknown": "Haijulikani"},
        "Luo": {"Critical": "Lich Marach", "High": "Malo", "Medium": "Maliyo", "None": "Maber", "Unknown": "Ok Ongʼere"}
    }
    translated_severity = severity_translations.get(lang, severity_translations["English"]).get(severity, severity)
    color = colors.get(severity, "#808080")
    return f'<span style="background-color:{color}; color:white; padding:6px 12px; border-radius:20px; font-weight:600; font-size:0.9rem;">{translated_severity}</span>'

def get_audio_file(disease_name, language):
    audio_map = {'Pepper__bell___Bacterial_spot': 'P_bacterial_spot', 'Pepper__bell___healthy': 'healthy_pepper',
        'Potato___Early_blight': 'early_blight', 'Potato___Late_blight': 'late_blight', 'Potato___healthy': 'healthy_potato',
        'Tomato_Bacterial_spot': 'bacterial_spot', 'Tomato_Early_blight': 'T_early_blight',
        'Tomato_Late_blight': 'T_late_blight', 'Tomato___healthy': 'healthy_tomato',
        'Tomato__Tomato_mosaic_virus':'mosaic_virus',
        'Tomato_Spider_mites_Two_spotted_spider_mite':'spider_mite',
        'Tomato_Leaf_Mold':'leaf_mold',
        'Tomato__Target_Spot':'target_spot'
        }
    lang_map = {"English": "en", "Kiswahili": "sw", "Luo": "luo"}
    base_name = audio_map.get(disease_name, 'general_guidance')
    lang_code = lang_map.get(language, "en")
    audio_path = f"assets/audio/{lang_code}/{base_name}.mp3"
    if os.path.exists(audio_path):
        return audio_path
    return None

def play_audio_guidance(disease_name, language, autoplay=True):
    if not st.session_state.get('audio_enabled', True):
        return
    audio_file = get_audio_file(disease_name, language)
    if audio_file and os.path.exists(audio_file):
        try:
            with open(audio_file, 'rb') as audio:
                audio_bytes = audio.read()
                st.audio(audio_bytes, format='audio/mp3', autoplay=False)
        except Exception as e:
            st.warning(f"{translate_text('Audio playback unavailable', language)}: {str(e)}")
    else:
        lang_messages = {
            "English": "Audio guidance is being prepared for this diagnosis.",
            "Kiswahili": "Mwongozo wa sauti unaandaliwa kwa uchunguzi huu.",
            "Luo": "Puonj gi dwond wach biro ike ne nonro-ni."
        }
        st.info(lang_messages.get(language, lang_messages["English"]))




# ================== PLANT DISEASES DATABASE ==================
PLANT_DISEASES = {
    'Pepper__bell___Bacterial_spot': {
        'name': 'Bacterial Spot', 'plant': 'Pepper', 'severity': 'High',
        'name_sw': 'Madoa ya Bakteria', 'plant_sw': 'Pilipili', 'name_luo': 'Kido mar Bacteria', 'plant_luo': 'Pilipili',
        'symptoms': 'Small dark spots with yellow halos on leaves and fruits',
        'symptoms_sw': 'Madoa madogo meusi yenye mviringo wa manjano kwenye majani na matunda',
        'symptoms_luo': 'Kido matindo marateng gi mbiringo makwar e lith kod olembe',
        'treatment': 'Apply copper-based bactericide, remove affected parts immediately',
        'treatment_sw': 'Tumia dawa ya bakteria ya shaba, ondoa sehemu zilizopata haraka',
        'treatment_luo': 'Ti yath mar bacteria mar shaba, gol migawo mohinore piyo',
        'prevention': 'Use certified seeds, avoid overhead irrigation, practice crop rotation',
        'prevention_sw': 'Tumia mbegu zilizothibitishwa, epuka kumwagilia juu, fanya mzunguko wa mazao',
        'prevention_luo': 'Ti kothe momigi chike, kik iumo pi ewi yath, loki kit puodho',
        'organic_treatment': 'Neem oil spray, garlic extract solution, proper field sanitation',
        'organic_treatment_sw': 'Dawa ya mafuta ya neem, suluhisho la thumu, usafi wa shamba',
        'organic_treatment_luo': 'Yath neem, suluhisho mar thumu, ler puodho maber',
        'watering_advice': 'Water at base level, avoid wetting leaves, ensure good drainage',
        'watering_advice_sw': 'Mwagilia chini, epuka kumnyeshea majani, hakikisha maji yanatoka vizuri',
        'watering_advice_luo': 'Ol pi e tiend yath, kik imienyo lith, ne pi wuok maber'
    },
    'Pepper__bell___healthy': {
        'name': 'Healthy Pepper', 'plant': 'Pepper', 'severity': 'None',
        'name_sw': 'Pilipili Mzima', 'plant_sw': 'Pilipili', 'name_luo': 'Pilipili Maber', 'plant_luo': 'Pilipili',
        'symptoms': 'Dark green leaves, strong stem, no visible disease symptoms',
        'symptoms_sw': 'Majani ya kijani kibichi, shina imara, hakuna dalili za ugonjwa',
        'symptoms_luo': 'Lith marateng, bad motegno, onge ranyisi mar tuo',
        'treatment': 'Continue current care practices, regular monitoring',
        'treatment_sw': 'Endelea na utunzaji wa sasa, ufuatiliaji wa kawaida',
        'treatment_luo': 'Dhi nyime gi ritruok machien, rang pile',
        'prevention': 'Maintain proper plant spacing, regular inspection, balanced nutrition',
        'prevention_sw': 'Dumisha nafasi nzuri kati ya mimea, ukaguzi wa kawaida, lishe sawa',
        'prevention_luo': 'Rit bor makare e kind yath, nono pile, chiemo moromo',
        'organic_treatment': 'Compost application, beneficial companion planting',
        'organic_treatment_sw': 'Tumia mbolea asilia, panda mimea rafiki',
        'organic_treatment_luo': 'Ti mbolea asilia, pidh yath mowinjore',
        'watering_advice': 'Regular watering schedule, mulching for moisture retention',
        'watering_advice_sw': 'Ratiba ya kumwagilia mara kwa mara, funika ardhi kudumisha unyevunyevu',
        'watering_advice_luo': 'Ol pi pile ka ochunore, um lowo mondo irit pi'
    },
    'Potato___Early_blight': {
        'name': 'Early Blight', 'plant': 'Potato', 'severity': 'Medium',
        'name_sw': 'Ukungu wa Mapema', 'plant_sw': 'Viazi', 'name_luo': 'Tuo mokwongo', 'plant_luo': 'Viazi',
        'symptoms': 'Concentric ring spots on lower leaves, gradual upward progression',
        'symptoms_sw': 'Madoa ya pete kwenye majani ya chini, kuenea kwa taratibu kuelekea juu',
        'symptoms_luo': 'Kido maduong molworore e lith manie piny, landore matin matin kadhi malo',
        'treatment': 'Fungicide application, remove lower affected leaves, improve air circulation',
        'treatment_sw': 'Tumia dawa ya kuulia, ondoa majani ya chini yaliyoathirika, boresha mzunguko wa hewa',
        'treatment_luo': 'Ti yath mar bor, gol lith manie piny mohinore, mi yamo mol maber',
        'prevention': 'Mulching around plants, proper spacing, avoid overhead watering',
        'prevention_sw': 'Funika ardhi karibu na mimea, nafasi nzuri, epuka kumwagilia juu',
        'prevention_luo': 'Um lowo but yath, bor makare, kik iumo pi ewi yath',
        'organic_treatment': 'Baking soda spray (2 tbsp/L), compost tea application',
        'organic_treatment_sw': 'Dawa ya soda ya kuoka (vijiko 2/L), tumia chai ya mbolea asilia',
        'organic_treatment_luo': 'Yath soda kuteyo (kijiko 2/L), ti chai mar mbolea asilia',
        'watering_advice': 'Water at soil level, maintain consistent moisture without overwatering',
        'watering_advice_sw': 'Mwagilia kwenye ardhi, dumisha unyevunyevu sawa bila kumwagilia kupita kiasi',
        'watering_advice_luo': 'Ol pi e lowo, rit pi moromo ma ok ingʼenyo'
    },
    'Tomato_Late_blight': {
        'name': 'Late Blight', 'plant': 'Tomato', 'severity': 'Critical',
        'name_sw': 'Ukungu wa Mwisho', 'plant_sw': 'Nyanya', 'name_luo': 'Tuo mogik', 'plant_luo': 'Nyanya',
        'symptoms': 'Dark water-soaked lesions, white moldy growth underneath leaves',
        'symptoms_sw': 'Majeraha meusi yenye maji, ukuaji wa ukungu mweupe chini ya majani',
        'symptoms_luo': 'Adhonde marateng mopongʼ gi pi, twi mar bor marachar e bwo lith',
        'treatment': 'IMMEDIATE systemic fungicide, destroy all infected plant material',
        'treatment_sw': 'Dawa ya kuulia ya mfumo HARAKA, angamiza vifaa vyote vya mmea vilivyoambukizwa',
        'treatment_luo': 'Ti yath mar bor PIYO, tiek gik duto mag yath mohinore',
        'prevention': 'Good air circulation, avoid overhead watering, resistant varieties',
        'prevention_sw': 'Mzunguko mzuri wa hewa, epuka kumwagilia juu, aina zinazopinga',
        'prevention_luo': 'Yamo mol maber, kik iumo pi ewi yath, kit yath makedo gi tuo',
        'organic_treatment': 'Bordeaux mixture, milk and baking soda solution, plant removal',
        'organic_treatment_sw': 'Mchanganyiko wa Bordeaux, suluhisho la maziwa na soda ya kuoka, ondoa mmea',
        'organic_treatment_luo': 'Yath Bordeaux, suluhisho mar chak gi soda, gol yath',
        'watering_advice': 'Water at base only, never water in evening, improve drainage',
        'watering_advice_sw': 'Mwagilia mzizi tu, usiwe ukimwagilia jioni, boresha mfereji',
        'watering_advice_luo': 'Ol pi e tiend yath kende, kik iumo pi odhiambo, loso kaka pi wuok'
    },
    'Tomato___healthy': {
        'name': 'Healthy Tomato', 'plant': 'Tomato', 'severity': 'None',
        'name_sw': 'Nyanya Mzima', 'plant_sw': 'Nyanya', 'name_luo': 'Nyanya Maber', 'plant_luo': 'Nyanya',
        'symptoms': 'Dark green foliage, strong stems, excellent fruit development',
        'symptoms_sw': 'Majani ya kijani kibichi, shina imara, ukuaji mzuri wa matunda',
        'symptoms_luo': 'Lith marateng, bad motegno, twi mar olembe maber',
        'treatment': 'Continue excellent care practices, maintain monitoring schedule',
        'treatment_sw': 'Endelea na mbinu bora za utunzaji, endelea na ratiba ya ufuatiliaji',
        'treatment_luo': 'Dhi nyime gi ritruok maber, rang pile ka ochunore',
        'prevention': 'Regular pruning and staking, mulching, balanced fertilization',
        'prevention_sw': 'Kukata na kusimika mara kwa mara, kufunika ardhi, mbolea sawa',
        'prevention_luo': 'Ngʼado gi guro pile, um lowo, mbolea moromo',
        'organic_treatment': 'Compost application, beneficial companion plants like basil',
        'organic_treatment_sw': 'Tumia mbolea asilia, panda mimea rafiki kama vumbasi',
        'organic_treatment_luo': 'Ti mbolea asilia, pidh yath mowinjore ka basil',
        'watering_advice': 'Deep watering 2-3 times weekly, consistent moisture levels',
        'watering_advice_sw': 'Mwagilia kwa kina mara 2-3 kwa wiki, viwango vya unyevunyevu sawa',
        'watering_advice_luo': 'Ol pi matut ndi 2-3 e juma, rit pi moromo pile'
    },
    'Potato___Early_blight': {
        'name': 'Early blight', 'plant': 'Potato', 'severity': 'Medium',
        'name_sw': 'Ukungu wa Mwisho', 'plant_sw': 'Viazi', 'name_luo': 'Tuo Mokwongo', 'plant_luo': 'Gwacho',
        'symptoms': 'Circular, dark-brown or black lesions with yellow halos on leaves',
        'symptoms_sw': 'Pete zenye mviringo kwenye majani zinazofanya madoa kama shabaha, kuwa manjano',
        'symptoms_luo': 'Duong molworore e lith mamiyo kido machal gi shabaha, lokore makwar',
        'treatment': 'Apply fungicide (mancozeb or chlorothalonil), remove affected foliage',
        'treatment_sw': 'Tumia dawa ya kuulia (mancozeb au chlorothalonil), ondoa majani yaliyoathirika',
        'treatment_luo': 'Ti yath mar bor (mancozeb kata chlorothalonil), gol lith mohinore',
        'prevention': 'Crop rotation every 3 years, avoid overhead watering, remove plant debris',
        'prevention_sw': 'Mzunguko wa mazao kila miaka 3, epuka kumwagilia juu, ondoa mabaki ya mimea',
        'prevention_luo': 'Loki cham higni 3, kik iumo pi ewi yath, gol lith motho',
        'organic_treatment': 'Baking soda spray, milk solution (1:10 ratio), proper spacing',
        'organic_treatment_sw': 'Dawa ya soda ya kuoka, suluhisho la maziwa (uwiano wa 1:10), nafasi nzuri',
        'organic_treatment_luo': 'Yath soda kuteyo, suluhisho mar chak (1:10), bor makare',
        'watering_advice': 'Water early morning, avoid evening irrigation, mulch soil',
        'watering_advice_sw': 'Mwagilia asubuhi na mapema, epuka kumwagilia jioni, funika udongo',
        'watering_advice_luo': 'Ol pi okinyi gokinyi, kik iumo pi odhiambo, um lowo'
        },
                        
    'Potato___Late_blight': {
        'name': 'Late Blight', 'plant': 'Potato', 'severity': 'Critical',
        'name_sw': 'Ukungu wa Mwisho', 'plant_sw': 'Viazi', 'name_luo': 'Tuo mogik', 'plant_luo': 'Gwacho',
        'symptoms': 'Water-soaked lesions, white fungal growth under leaves, rapid spread',
        'symptoms_sw': 'Majeraha yenye maji, ukuaji wa ukungu mweupe chini ya majani, kuenea kwa haraka',
        'symptoms_luo': 'Adhonde mopongʼ gi pi, twi mar bor marachar e bwo lith, landore mapiyo',
        'treatment': 'IMMEDIATE fungicide application (metalaxyl + mancozeb), destroy infected plants',
        'treatment_sw': 'Tumia dawa ya kuulia HARAKA (metalaxyl + mancozeb), angamiza mimea iliyoambukizwa',
        'treatment_luo': 'Ti yath mar bor PIYO (metalaxyl + mancozeb), tiek yath mohinore',
        'prevention': 'Plant resistant varieties, ensure excellent drainage, avoid wet conditions',
        'prevention_sw': 'Panda aina zinazopinga, hakikisha maji yanatoka vizuri, epuka hali za unyevunyevu',
        'prevention_luo': 'Pidh kit yath makedo gi tuo, ne pi wuok maber, kweyo kama ma pi ngʼeny',
        'organic_treatment': 'Bordeaux mixture spray, copper soap solution, immediate plant removal',
        'organic_treatment_sw': 'Dawa ya mchanganyiko wa Bordeaux, suluhisho la sabuni ya shaba, ondoa mimea haraka',
        'organic_treatment_luo': 'Yath Bordeaux, suluhisho mar sabuni mar shaba, gol yath piyo',
        'watering_advice': 'Stop overhead watering immediately, improve field drainage',
        'watering_advice_sw': 'Acha kumwagilia juu mara moja, boresha mfereji wa shamba',
        'watering_advice_luo': 'Chung giolo pi ewi yath piyo, loso kaka pi wuok e puodho'
    },
    'Potato___healthy': {
        'name': 'Healthy Potato', 'plant': 'Potato', 'severity': 'None',
        'name_sw': 'Viazi Mzima', 'plant_sw': 'Viazi', 'name_luo': 'Viazi Maber', 'plant_luo': 'Viazi',
        'symptoms': 'Vigorous green foliage, healthy tuber development, no disease signs',
        'symptoms_sw': 'Majani ya kijani kibichi yenye nguvu, ukuaji mzuri wa viazi, hakuna dalili za ugonjwa',
        'symptoms_luo': 'Lith marateng motegno, twi mar viazi maber, onge ranyisi mar tuo',
        'treatment': 'Continue current management practices, regular monitoring',
        'treatment_sw': 'Endelea na mbinu za usimamizi za sasa, ufuatiliaji wa kawaida',
        'treatment_luo': 'Dhi nyime gi kaka iritogo machien, rang pile',
        'prevention': 'Regular hilling, balanced fertilization, integrated pest management',
        'prevention_sw': 'Kuchanganya udongo mara kwa mara, mbolea sawa, usimamizi kamili wa wadudu',
        'prevention_luo': 'Um lowo pile, mbolea moromo, rito kwach gi tuo duto',
        'organic_treatment': 'Compost incorporation, beneficial soil microorganisms',
        'organic_treatment_sw': 'Ongeza mbolea asilia, viini vya udongo vya manufaa',
        'organic_treatment_luo': 'Med mbolea asilia, gimoro matindo maleng e lowo',
        'watering_advice': 'Consistent moisture levels, avoid waterlogging',
        'watering_advice_sw': 'Viwango vya unyevunyevu sawa, epuka maji mengi sana',
        'watering_advice_luo': 'Rit pi moromo pile, kik iwe gi pi mangʼeny miwuoro'
    },
    'Tomato_Bacterial_spot': {
        'name': 'Bacterial Spot', 'plant': 'Tomato', 'severity': 'High',
        'name_sw': 'Madoa ya Bakteria', 'plant_sw': 'Nyanya', 'name_luo': 'Kido mar Bacteria', 'plant_luo': 'Nyanya',
        'symptoms': 'Small brown spots with yellow halos on leaves, fruits, and stems',
        'symptoms_sw': 'Madoa madogo ya kahawia yenye mviringo wa manjano kwenye majani, matunda na shina',
        'symptoms_luo': 'Kido matindo maburro gi mbiringo makwar e lith, olembe kod bad',
        'treatment': 'Copper-based bactericide application, remove affected plant material',
        'treatment_sw': 'Tumia dawa ya bakteria ya shaba, ondoa sehemu za mmea zilizopata',
        'treatment_luo': 'Ti yath mar bacteria mar shaba, gol migawo mag yath mohinore',
        'prevention': 'Use certified disease-free seeds, avoid working in wet fields',
        'prevention_sw': 'Tumia mbegu zilizothibitishwa bila ugonjwa, epuka kufanya kazi mashambani yenye unyevunyevu',
        'prevention_luo': 'Ti kothe maonge tuo momigi chike, kik iti e puodho mapioth',
        'organic_treatment': 'Neem extract spray, garlic and chili solution, field sanitation',
        'organic_treatment_sw': 'Dawa ya neem, suluhisho la thumu na pilipili, usafi wa shamba',
        'organic_treatment_luo': 'Yath neem, suluhisho mar thumu gi pilipili, ler puodho',
        'watering_advice': 'Drip irrigation preferred, avoid splashing water on foliage',
        'watering_advice_sw': 'Umwagiliaji wa matone unapendelewa, epuka kumwagiza maji kwenye majani',
        'watering_advice_luo': 'Pi matono ber moloyo, kik iumienyo pi ewi lith'
    },
    
    
    'Tomato_Early_blight': {
        'name': 'Early Blight', 'plant': 'Tomato', 'severity': 'Medium',
        'name_sw': 'Ukungu wa Mapema', 'plant_sw': 'Nyanya', 'name_luo': 'Tuo mokwongo', 'plant_luo': 'Nyanya',
        'symptoms': 'Concentric ring spots on lower leaves, gradual upward progression',
        'symptoms_sw': 'Pete zenye mviringo kwenye majani ya chini, kuenea kwa taratibu kuelekea juu',
        'symptoms_luo': 'Kido maduong molworore e lith manie piny, landore matin matin kadhi malo',
        'treatment': 'Fungicide application, remove lower affected leaves, improve air circulation',
        'treatment_sw': 'Tumia dawa ya kuulia, ondoa majani ya chini yaliyoathirika, boresha mzunguko wa hewa',
        'treatment_luo': 'Ti yath mar bor, gol lith manie piny mohinore, mi yamo mol maber',
        'prevention': 'Mulching around plants, proper spacing, avoid overhead watering',
        'prevention_sw': 'Funika ardhi karibu na mimea, nafasi nzuri, epuka kumwagilia juu',
        'prevention_luo': 'Um lowo but yath, bor makare, kik iumo pi ewi yath',
        'organic_treatment': 'Baking soda spray (2 tbsp/L), compost tea application',
        'organic_treatment_sw': 'Dawa ya soda ya kuoka (vijiko 2/L), tumia chai ya mbolea asilia',
        'organic_treatment_luo': 'Yath soda kuteyo (kijiko 2/L), ti chai mar mbolea asilia',
        'watering_advice': 'Water at soil level, maintain consistent moisture without overwatering',
        'watering_advice_sw': 'Mwagilia kwenye ardhi, dumisha unyevunyevu sawa bila kumwagilia kupita kiasi',
        'watering_advice_luo': 'Ol pi e lowo, rit pi moromo ma ok ingʼenyo'
    },
    
    'Tomato_Leaf_Mold': {
        'name': 'Leaf Mold', 'plant': 'Tomato', 'severity': 'Medium',
        'name_sw': 'Ukungu wa Majani', 'plant_sw': 'Nyanya', 'name_luo': 'Bor mar Lith', 'plant_luo': 'Nyanya',
        'symptoms': 'Yellow spots on upper leaves, velvety growth on undersides',
        'symptoms_sw': 'Madoa ya manjano juu ya majani, ukuaji laini chini ya majani',
        'symptoms_luo': 'Kido makwar ewi lith, twi mabwoth e bwo lith',
        'treatment': 'Improve ventilation, apply preventive fungicide if severe',
        'treatment_sw': 'Boresha uingizaji hewa, tumia dawa ya kuulia kama ni kali',
        'treatment_luo': 'Loso kaka yamo donjo, ti yath mar bor ka tuo tek',
        'prevention': 'Reduce humidity levels, increase plant spacing, proper ventilation',
        'prevention_sw': 'Punguza viwango vya unyevu, ongeza nafasi ya mimea, uingizaji hewa mzuri',
        'prevention_luo': 'Dwok pi mar yamo, med bor e kind yath, yamo mol maber',
        'organic_treatment': 'Milk spray solution (1:10), baking soda application',
        'organic_treatment_sw': 'Suluhisho la dawa ya maziwa (1:10), tumia soda ya kuoka',
        'organic_treatment_luo': 'Yath chak (1:10), ti soda kuteyo',
        'watering_advice': 'Water early morning, ensure good air circulation around plants',
        'watering_advice_sw': 'Mwagilia asubuhi na mapema, hakikisha mzunguko mzuri wa hewa kuzunguka mimea',
        'watering_advice_luo': 'Ol pi okinyi gokinyi, ne yamo mol maber but yath'
    },
    
    'Tomato_Septoria_leaf_spot': {
        'name': 'Septoria Leaf Spot', 'plant': 'Tomato', 'severity': 'Medium',
        'name_sw': 'Madoa ya Majani ya Septoria', 'plant_sw': 'Nyanya', 'name_luo': 'Kido mar Lith Septoria', 'plant_luo': 'Nyanya',
        'symptoms': 'Small circular spots with dark borders and light gray centers',
        'symptoms_sw': 'Madoa madogo ya mviringo yenye mipaka meusi na katikati za kijivu',
        'symptoms_luo': 'Kido matindo maduong gi gok marateng kod chuny marateng matin',
        'treatment': 'Fungicide spray, remove affected lower leaves, improve sanitation',
        'treatment_sw': 'Dawa ya kuulia, ondoa majani ya chini yaliyoathirika, boresha usafi',
        'treatment_luo': 'Yath mar bor, gol lith manie piny mohinore, ler puodho maber',
        'prevention': 'Mulching, avoid overhead irrigation, annual crop rotation',
        'prevention_sw': 'Kufunika ardhi, epuka umwagiliaji juu, mzunguko wa mazao kila mwaka',
        'prevention_luo': 'Um lowo, kik iumo pi ewi yath, loki cham higa ka higa',
        'organic_treatment': 'Compost tea spray, proper plant spacing for air flow',
        'organic_treatment_sw': 'Dawa ya chai ya mbolea asilia, nafasi nzuri ya mimea kwa mzunguko wa hewa',
        'organic_treatment_luo': 'Yath chai mar mbolea asilia, bor makare mondo yamo mol',
        'watering_advice': 'Water at ground level, avoid splashing soil onto leaves',
        'watering_advice_sw': 'Mwagilia kwenye ardhi, epuka kumwagiza udongo kwenye majani',
        'watering_advice_luo': 'Ol pi e lowo, kik imienyo lowo ewi lith'
    },
    
    'Tomato_Spider_mites_Two_spotted_spider_mite': {
        'name': 'Spider Mites', 'plant': 'Tomato', 'severity': 'High',
        'name_sw': 'Buibui Wadogo', 'plant_sw': 'Nyanya', 'name_luo': 'Oguyo Matindo', 'plant_luo': 'Nyanya',
        'symptoms': 'Fine webbing, yellow stippling on leaves, bronze coloration',
        'symptoms_sw': 'Wavu laini, madoa madogo ya manjano kwenye majani, rangi ya shaba',
        'symptoms_luo': 'Gogo malach, kido matindo makwar e lith, rangi mar chuma',
        'treatment': 'Miticide application, increase humidity around plants, predatory mites',
        'treatment_sw': 'Tumia dawa ya kuua wadudu, ongeza unyevu kuzunguka mimea, buibui wa kuwinda',
        'treatment_luo': 'Ti yath mar kwach, med pi mar yamo but yath, oguyo manego gik mamoko',
        'prevention': 'Regular inspection, avoid water stress, encourage natural predators',
        'prevention_sw': 'Ukaguzi wa kawaida, epuka kukosa maji, himiza wawindaji wa asili',
        'prevention_luo': 'Nono pile, kik iwe maonge pi, koyo gik malamo kwach mamoko',
        'organic_treatment': 'Neem oil spray, insecticidal soap, predatory insects',
        'organic_treatment_sw': 'Dawa ya mafuta ya neem, sabuni ya wadudu, wadudu wa kuwinda',
        'organic_treatment_luo': 'Yath neem, sabuni mar kwach, kwach maneg kwach mamoko',
        'watering_advice': 'Maintain consistent soil moisture, mist around plants (not leaves)',
        'watering_advice_sw': 'Dumisha unyevunyevu wa udongo, nyunyiza maji kuzunguka mimea (si majani)',
        'watering_advice_luo': 'Rit pi e lowo moromo, mienyo pi but yath (ok e lith)'
    },
    
    'Tomato__Target_Spot': {
        'name': 'Target Spot', 'plant': 'Tomato', 'severity': 'Medium',
        'name_sw': 'Madoa ya Shabaha', 'plant_sw': 'Nyanya', 'name_luo': 'Kido mar Shabaha', 'plant_luo': 'Nyanya',
        'symptoms': 'Concentric rings forming target patterns on leaves and fruits',
        'symptoms_sw': 'Pete zenye mviringo zinazofanya mifumo ya shabaha kwenye majani na matunda',
        'symptoms_luo': 'Duong molworore mamiyo kit shabaha e lith kod olembe',
        'treatment': 'Fungicide application, remove affected plant material, improve air flow',
        'treatment_sw': 'Tumia dawa ya kuulia, ondoa vifaa vya mmea vilivyoathirika, boresha mzunguko wa hewa',
        'treatment_luo': 'Ti yath mar bor, gol migawo mag yath mohinore, loso kaka yamo mol',
        'prevention': 'Crop rotation, avoid overhead irrigation, proper plant spacing',
        'prevention_sw': 'Mzunguko wa mazao, epuka kumwagilia juu, nafasi nzuri ya mimea',
        'prevention_luo': 'Loki cham, kik iumo pi ewi yath, bor makare e kind yath',
        'organic_treatment': 'Copper soap spray, compost application, field sanitation',
        'organic_treatment_sw': 'Dawa ya sabuni ya shaba, tumia mbolea asilia, usafi wa shamba',
        'organic_treatment_luo': 'Yath sabuni mar shaba, ti mbolea asilia, ler puodho',
        'watering_advice': 'Drip irrigation system, water early morning hours',
        'watering_advice_sw': 'Mfumo wa umwagiliaji wa matone, mwagilia masaa ya asubuhi na mapema',
        'watering_advice_luo': 'Kaka mar olo pi matono, ol pi seche mag okinyi'
    },
    
    'Tomato__Tomato_YellowLeaf__Curl_Virus': {
        'name': 'Yellow Leaf Curl Virus', 'plant': 'Tomato', 'severity': 'Critical',
        'name_sw': 'Virusi ya Majani ya Manjano Yaliyopinda', 'plant_sw': 'Nyanya', 'name_luo': 'Tuo mar Lith Makwar Molokore', 'plant_luo': 'Nyanya',
        'symptoms': 'Severe yellowing and curling of leaves, stunted plant growth',
        'symptoms_sw': 'Kuwa manjano kwa nguvu na kupinda kwa majani, ukuaji mdogo wa mmea',
        'symptoms_luo': 'Lokore makwar malich kod lokore mar lith, twi mar yath mogol',
        'treatment': 'Remove infected plants immediately, control whitefly vectors aggressively',
        'treatment_sw': 'Ondoa mimea iliyoambukizwa mara moja, dhibiti nzi weupe kwa nguvu',
        'treatment_luo': 'Gol yath mohinore piyo, nek lwech marachar maber ahinya',
        'prevention': 'Use resistant varieties, control whiteflies, reflective mulch systems',
        'prevention_sw': 'Tumia aina zinazopinga, dhibiti nzi weupe, mifumo ya kufunika ardhi inayoakisi',
        'prevention_luo': 'Ti kit yath makedo gi tuo, rit lwech marachar, um lowo gi gik mamil ler',
        'organic_treatment': 'Yellow sticky traps, neem oil for whitefly control, plant removal',
        'organic_treatment_sw': 'Mitego laini ya manjano, mafuta ya neem kwa kudhibiti nzi weupe, ondoa mimea',
        'organic_treatment_luo': 'Obadho makwar malach, yath neem ne lwech marachar, gol yath',
        'watering_advice': 'Maintain plant vigor with proper irrigation, avoid plant stress',
        'watering_advice_sw': 'Dumisha nguvu ya mmea kwa umwagiliaji sahihi, epuka msongo wa mmea',
        'watering_advice_luo': 'Rit teko mar yath gi olo pi makare, kik imiyo yath chandruok'
    },
    
    'Tomato__Tomato_mosaic_virus': {
        'name': 'Mosaic Virus', 'plant': 'Tomato', 'severity': 'High',
        'name_sw': 'Virusi ya Mosaic', 'plant_sw': 'Nyanya', 'name_luo': 'Tuo mar Mosaic', 'plant_luo': 'Nyanya',
        'symptoms': 'Mottled light and dark green mosaic patterns on leaves',
        'symptoms_sw': 'Mifumo ya mosaic ya kijani kibichi na kijani kibichi kwenye majani',
        'symptoms_luo': 'Kit mosaic mar rateng kod marateng e lith',
        'treatment': 'Remove infected plants, sanitize tools and hands thoroughly',
        'treatment_sw': 'Ondoa mimea iliyoambukizwa, safisha vyombo na mikono vizuri',
        'treatment_luo': 'Gol yath mohinore, lwoko gige tich kod lwedo maber',
        'prevention': 'Use certified virus-free seeds, avoid tobacco use near plants',
        'prevention_sw': 'Tumia mbegu zilizothibitishwa bila virusi, epuka matumizi ya tumbaku karibu na mimea',
        'prevention_luo': 'Ti kothe momigi chike maonge tuo, kik iti gi taba but yath',
        'organic_treatment': 'Complete plant removal, thorough equipment sanitation',
        'organic_treatment_sw': 'Ondoa mimea kabisa, usafi kamili wa vifaa',
        'organic_treatment_luo': 'Gol yath duto, lwoko gige tich chutho',
        'watering_advice': 'Avoid mechanical transmission through contaminated water',
        'watering_advice_sw': 'Epuka kueneza kwa mitambo kupitia maji yaliyochafuliwa',
        'watering_advice_luo': 'Kik iland tuo gi pi mochido'
    }

}
UI_TEXTS = {
    "English": {
        "app_title": "KilimoGlow Kenya", "subtitle": "Smart Plant Disease Detection for Kenyan Farmers",
        "plant_doctor": "Plant Doctor", "batch_analysis": "Batch Analysis", "dashboard": "Dashboard",
        "settings": "Settings", "home": "Home", "upload_label": "Upload Plant Photo",
        "analyze_plant": "Analyze Plant", "batch_upload": "Upload Multiple Images",
        "process_batch": "Process Batch", "take_photo": "Take Photo", "upload_device": "Upload from Device",
        "voice_description": "Voice Description", "analysis_results": "Analysis Results",
        "treatment": "Treatment", "organic": "Organic", "prevention": "Prevention", "watering": "Watering",
        "export_report": "Export Report", "download_csv": "Download Report (CSV)",
        "download_txt": "Download Report (TXT)", "ready_analysis": "Ready for Analysis",
        "total_scans": "Total Scans", "healthy_plants": "Healthy Plants",
        "need_treatment": "Need Treatment", "recent_analysis": "Recent Analysis History",
        "audio_guidance": "Audio Guidance", "enable_audio": "Enable Audio Guidance"
    },
    "Kiswahili": {
        "app_title": "KilimoGlow Kenya", "subtitle": "Utambuzi wa Magonjwa ya Mimea kwa Wakulima wa Kenya",
        "plant_doctor": "Daktari wa Mimea", "batch_analysis": "Uchambuzi wa Kundi",
        "dashboard": "Bodi ya Habari", "settings": "Mipangilio", "home": "Nyumbani",
        "upload_label": "Pakia Picha ya Mmea", "analyze_plant": "Chunguza Mmea",
        "batch_upload": "Pakia Picha Nyingi", "process_batch": "Chamibuza Kundi",
        "take_photo": "Piga Picha", "upload_device": "Pakia kutoka Kifaa",
        "voice_description": "Maelezo ya Sauti", "analysis_results": "Matokeo ya Uchambuzi",
        "treatment": "Matibabu", "organic": "Asilia", "prevention": "Kinga", "watering": "Kumwagilia",
        "export_report": "Hamisha Ripoti", "download_csv": "Pakua Ripoti (CSV)",
        "download_txt": "Pakua Ripoti (TXT)", "ready_analysis": "Iko Tayari kwa Uchambuzi",
        "total_scans": "Jumla ya Uchunguzi", "healthy_plants": "Mimea Mizima",
        "need_treatment": "Inahitaji Matibabu", "recent_analysis": "Historia ya Uchambuzi wa Karibuni",
        "audio_guidance": "Mwongozo wa Sauti", "enable_audio": "Washa Mwongozo wa Sauti"
    },
    "Luo": {
        "app_title": "KilimoGlow Kenya", "subtitle": "Fwenyo Tuo mar Mimea ne Jopur Kenya",
        "plant_doctor": "Jathieth Yath", "batch_analysis": "Nonro Mangeny",
        "dashboard": "Bord Weche", "settings": "Chenro", "home": "Dala",
        "upload_label": "Ket Fweny Yath", "analyze_plant": "Nono Yath",
        "batch_upload": "Ket Fweny Mangʼeny", "process_batch": "Tiy Mangʼeny",
        "take_photo": "Mak Fweny", "upload_device": "Ket koa e Gir",
        "voice_description": "Lero gi Dwond", "analysis_results": "Gik Monyiso",
        "treatment": "Thieth", "organic": "Asili", "prevention": "Siro", "watering": "Olo Pi",
        "export_report": "Gol Ripoti", "download_csv": "Gol Ripoti (CSV)",
        "download_txt": "Gol Ripoti (TXT)", "ready_analysis": "Oikore ne Nonro",
        "total_scans": "Nonro Duto", "healthy_plants": "Yath Maber",
        "need_treatment": "Dwaro Thieth", "recent_analysis": "Nonro Machien",
        "audio_guidance": "Puonj gi Dwond", "enable_audio": "Mok Puonj gi Dwond"
    }
}


if 'css_applied' not in st.session_state:
    apply_enhanced_css()
    st.session_state.css_applied = True

api_connected, api_info, working_url = check_fastapi_connection()
if working_url:
    FASTAPI_BASE_URL = working_url
    FASTAPI_ENDPOINTS = {
        "health": f"{FASTAPI_BASE_URL}/health",
        "predict": f"{FASTAPI_BASE_URL}/predict",
        "batch_predict": f"{FASTAPI_BASE_URL}/batch_predict",
        "model_info": f"{FASTAPI_BASE_URL}/model/info"
    }

# ================== SIDEBAR ==================
with st.sidebar:
    st.session_state.selected_language = st.selectbox(
        "🌍 Language / Lugha / Dhok",
        options=list(LANGUAGES.keys()),
        index=list(LANGUAGES.keys()).index(st.session_state.selected_language)
    )
    
    current_texts = UI_TEXTS.get(st.session_state.selected_language, UI_TEXTS["English"])
    lang = st.session_state.selected_language
    
    st.markdown(f"""
    <div class="main-header">
        <h2 style="margin: 0; color: white; z-index: 10; position: relative;">{current_texts['app_title']}</h2>
        <p style="color: #FFD700; margin: 0.5rem 0; font-size: 0.9rem; z-index: 10; position: relative;">{current_texts['subtitle']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    selected_page = option_menu(
        menu_title=translate_text("Navigation", lang),
        options=[
            f"🏠 {current_texts['home']}",
            f"🩺 {current_texts['plant_doctor']}",
            f"📊 {current_texts['batch_analysis']}",
            f"📈 {current_texts['dashboard']}",
            f"⚙️ {current_texts['settings']}"
        ],
        icons=["house-fill", "heart-pulse", "collection-fill", "bar-chart-fill", "gear-fill"],
        default_index=0,
        styles={
            "container": {"padding": "0", "background-color": "transparent"},
            "icon": {"color": "#FFD700", "font-size": "18px"},
            "nav-link": {
                "font-size": "14px", "text-align": "left", "margin": "2px 0",
                "padding": "8px 12px", "color": "white", "border-radius": "8px"
            },
            "nav-link-selected": {
                "background": "linear-gradient(90deg, #1a4d2e, #2d5e3f)",
                "color": "white", "border": "1px solid #FFD700"
            },
        },
    )
    
    st.markdown("---")
    
    if st.button(f"🔄 {translate_text('Refresh API Status', lang)}", use_container_width=True):
        if 'cached_api_status' in st.session_state:
            del st.session_state.cached_api_status
        if 'working_api_url' in st.session_state:
            del st.session_state.working_api_url
        st.rerun()
    
    if 'cached_api_status' not in st.session_state:
        st.session_state.cached_api_status = "online" if api_connected else "offline"

    connection_status = st.session_state.cached_api_status
    if connection_status not in ["online", "cached", "offline"]:
        connection_status = "offline"

    status_colors = {
        "online": ("🟢", translate_text("Online", lang)),
        "cached": ("🟡", translate_text("Cached", lang)),
        "offline": ("🔴", translate_text("Offline", lang))
    }
    color, status_text = status_colors[connection_status]

    st.markdown(f"""
    <div class="kenyan-card" style="padding: 1rem;">
        <h4 style="color: #FFD700; margin-bottom: 0.5rem;">📊 {translate_text("System Status", lang)}</h4>
        <p style="margin: 0.2rem 0;"><strong>API:</strong> {color} {status_text}</p>
        <p style="margin: 0.2rem 0;"><strong>{translate_text("Language", lang)}:</strong> {lang}</p>
        <p style="margin: 0.2rem 0;"><strong>{translate_text("Analyses", lang)}:</strong> {len(st.session_state.analysis_history)}</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.checkbox(
        f"🔊 {current_texts['enable_audio']}",
        value=st.session_state.get('audio_enabled', True),
        key='audio_enabled'
    )

# ================== HOME PAGE ==================
if selected_page.startswith("🏠"):
    st.markdown(f"""
    <div class="main-header">
        <h1 style="margin: 0; font-size: 2.5rem; z-index: 10; position: relative;">🌿 {current_texts['app_title']}</h1>
        <p style="margin: 1rem 0 0 0; font-size: 1.1rem; color: #FFD700; z-index: 10; position: relative;">{current_texts['subtitle']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div class="kenyan-card">
            <h3 style="color: #FFD700;">🔬 {translate_text("AI Disease Detection", lang)}</h3>
            <ul style="color: white; line-height: 1.6;">
                <li>📸 {translate_text("Detect diseases in Tomato, Pepper, Potato", lang)}</li>
                <li>🌍 {translate_text("Support for English, Kiswahili, Luo", lang)}</li>
                <li>📱 {translate_text("Mobile-optimized interface", lang)}</li>
                <li>🔊 {translate_text("Audio guidance in your language", lang)}</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="kenyan-card">
            <h3 style="color: #FFD700;">📱 {translate_text("Mobile Features", lang)}</h3>
            <ul style="color: white; line-height: 1.6;">
                <li>📷 {translate_text("Built-in camera integration", lang)}</li>
                <li>🔄 {translate_text("Offline mode capability", lang)}</li>
                <li>📊 {translate_text("Comprehensive analytics dashboard", lang)}</li>
                <li>💾 {translate_text("Local data storage and management", lang)}</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    if st.session_state.analysis_history:
        total_analyses = len(st.session_state.analysis_history)
        healthy_count = sum(1 for a in st.session_state.analysis_history if 'healthy' in a.get('predicted_class', '').lower())
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <h2 style="color: #4a9f5a; margin: 0;">{total_analyses}</h2>
                <p style="margin: 0;">{current_texts['total_scans']}</p>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <h2 style="color: #FFD700; margin: 0;">{healthy_count}</h2>
                <p style="margin: 0;">{current_texts['healthy_plants']}</p>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <h2 style="color: #FF6B35; margin: 0;">{total_analyses - healthy_count}</h2>
                <p style="margin: 0;">{current_texts['need_treatment']}</p>
            </div>
            """, unsafe_allow_html=True)

# ================== PLANT DOCTOR PAGE ==================
elif selected_page.startswith("🩺"):
    st.markdown(f"<h1 style='text-align: center; color: #FFD700;'>🩺 {current_texts['plant_doctor']}</h1>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown(f"### 📋 {translate_text('Plant Information', lang)}")
        
        st.session_state.user_name = st.text_input(
            f"👤 {translate_text('Your Name', lang)}",
            value=st.session_state.user_name,
            placeholder=translate_text("Enter your name", lang)
        )
        
        weather_options_base = ["Select", "Sunny", "Rainy", "Cloudy", "Dry"]
        weather_options = [translate_text(opt, lang) for opt in weather_options_base]
        weather_index = 0
        if st.session_state.weather_condition != "Select":
            try:
                weather_index = weather_options_base.index(st.session_state.weather_condition.split('/')[0])
            except:
                weather_index = 0
        
        selected_weather = st.selectbox(
            f"🌤️ {translate_text('Weather Condition', lang)}",
            weather_options,
            index=weather_index
        )
        st.session_state.weather_condition = weather_options_base[weather_options.index(selected_weather)]
        
        soil_options_base = ["Select", "Clay", "Sandy", "Loam", "Rocky"]
        soil_options = [translate_text(opt, lang) for opt in soil_options_base]
        soil_index = 0
        if st.session_state.soil_type != "Select":
            try:
                soil_index = soil_options_base.index(st.session_state.soil_type.split('/')[0])
            except:
                soil_index = 0
        
        selected_soil = st.selectbox(
            f"🌱 {translate_text('Soil Type', lang)}",
            soil_options,
            index=soil_index
        )
        st.session_state.soil_type = soil_options_base[soil_options.index(selected_soil)]
        
        st.markdown(f"### 📷 {current_texts['upload_label']}")
        
        upload_option = st.radio(
            translate_text("Choose upload method:", lang),
            [f"📱 {current_texts['take_photo']}", f"📁 {current_texts['upload_device']}"]
        )
        
        uploaded_file = None
        
        if upload_option.startswith("📱"):
            uploaded_file = st.camera_input(translate_text("Take a photo of your plant", lang))
        else:
            uploaded_file = st.file_uploader(translate_text("Choose plant image", lang), type=["jpg", "jpeg", "png"])
    
    with col2:
        if uploaded_file:
            image = Image.open(uploaded_file)
            st.image(image, caption=f"📸 {translate_text('Plant Photo for Analysis', lang)}", use_column_width=True)
            
            if st.button(current_texts["analyze_plant"], type="primary", use_container_width=True):
                try:
                    img_array = np.array(image)
                    if image.size[0] > 1024 or image.size[1] > 1024:
                        image = image.resize((min(1024, image.size[0]), min(1024, image.size[1])))
                except:
                    st.error(f"⚠️ {translate_text('Invalid image format', lang)}")
                    st.stop()
                
                analysis_id = str(uuid.uuid4())[:8]
                st.session_state.current_analysis_id = analysis_id
                
                with st.spinner(f"🔬 {translate_text('Analyzing your plant... Please wait.', lang)}"):
                    start_time = time.time()
                    success, result = predict_with_fastapi(uploaded_file)
                    
                    if success and result.get('success'):
                        st.success(f"✅ {translate_text('Analysis completed with FastAPI!', lang)}")
                        st.session_state.analysis_result = result
                        
                    else:
                        st.warning(f"⚠️ {translate_text('FastAPI unavailable, using offline mode', lang)}")
                        result = hybrid_offline_predict(uploaded_file, 
                            metadata={
                                'weather': st.session_state.get('weather_condition', 'Unknown'),
                                'soil': st.session_state.get('soil_type', 'Unknown')
                            }, 
                            simulate_fn=simulate_disease_prediction)
                        st.session_state.analysis_result = result
                    
                    processing_time = time.time() - start_time
            
            # Display results if available
            if st.session_state.analysis_result:
                result = st.session_state.analysis_result
                predicted_class = result.get("predicted_class", "unknown")
                confidence = result.get("confidence", 0)
                
                if confidence <= 1:
                    confidence *= 100
                
                if confidence < 60:
                    st.warning(f"⚠️ {translate_text('Low confidence detection. Please ensure image shows clear plant leaves.', lang)}")
                
                disease_info = PLANT_DISEASES.get(predicted_class, {})
                
                # Get translated fields based on current language
                lang_suffix = '' if lang == 'English' else f'_{LANGUAGES[lang]}'
                disease_name = disease_info.get(f'name{lang_suffix}', disease_info.get('name', 'Unknown'))
                plant_name = disease_info.get(f'plant{lang_suffix}', disease_info.get('plant', 'Unknown'))
                symptoms = disease_info.get(f'symptoms{lang_suffix}', disease_info.get('symptoms', 'No symptoms listed'))
                treatment = disease_info.get(f'treatment{lang_suffix}', disease_info.get('treatment', 'Continue monitoring'))
                prevention = disease_info.get(f'prevention{lang_suffix}', disease_info.get('prevention', 'Practice good hygiene'))
                organic = disease_info.get(f'organic_treatment{lang_suffix}', disease_info.get('organic_treatment', 'Use natural methods'))
                watering = disease_info.get(f'watering_advice{lang_suffix}', disease_info.get('watering_advice', 'Water regularly'))
                severity = disease_info.get('severity', 'Unknown')


                
                st.markdown("---")
                st.markdown(f"### 🎯 {translate_text('Analysis Results', lang)}")

                # === AUDIO GUIDANCE PLAYBACK ===
                if result and result.get("predicted_class"):
                    disease_name = result["predicted_class"]
                    language = st.session_state["selected_language"]
                    play_audio_guidance(disease_name, language)
                # ================================


                
                # Confidence visualization
                fig_conf = go.Figure()
                colors = ['#32CD32' if confidence > 80 else '#FFD700' if confidence > 60 else '#DC143C']
                
                fig_conf.add_trace(go.Bar(
                    x=[translate_text('Confidence', lang)],
                    y=[confidence],
                    marker_color=colors[0],
                    text=[f'{confidence:.1f}%'],
                    textposition='auto',
                    width=[0.6]
                ))
                
                fig_conf.update_layout(
                    title=f"🎯 {plant_name} - {disease_name}",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="white"),
                    yaxis_range=[0, 100],
                    height=250,
                    margin=dict(l=20, r=20, t=60, b=20)
                )
                st.plotly_chart(fig_conf, use_container_width=True)
                
                # Disease information card
                severity_color = {
                    'Critical': '#DC143C', 'High': '#FF8C00', 
                    'Medium': '#FFD700', 'None': '#32CD32'
                }.get(severity, '#32CD32')
                
                st.markdown(f"""
                <div class="analysis-card" style="border-left: 6px solid {severity_color};">
                    <h3 style="color: #FFD700; margin-bottom: 1rem;">
                        {plant_name} - {disease_name}
                    </h3>
                    <div style="margin-bottom: 1rem;">
                        {severity_badge(severity, lang)}
                    </div>
                    <p style="margin-bottom: 0.5rem;">
                        <strong>🔍 {translate_text('Symptoms', lang)}:</strong> {symptoms}
                    </p>
                </div>
                """, unsafe_allow_html=True)

                # ================== WEATHER API HELPER ==================
                import requests

                

                
               
                
                # Treatment tabs
                tab1, tab2, tab3, tab4 = st.tabs([
                    f"💊 {translate_text('Treatment', lang)}", 
                    f"🌿 {translate_text('Organic', lang)}", 
                    f"🛡️ {translate_text('Prevention', lang)}", 
                    f"💧 {translate_text('Watering', lang)}"
                ])
                
                with tab1:
                    st.markdown(f"**{translate_text('Treatment', lang)}:** {treatment}")
                    
                    urgency_map = {
                        'Critical': translate_text('Act immediately (today!)', lang),
                        'High': translate_text('Treat within 2-3 days', lang),
                        'Medium': translate_text('Treat within a week', lang),
                        'None': translate_text('Continue monitoring', lang)
                    }
                    urgency = urgency_map.get(severity, translate_text('Monitor regularly', lang))
                    
                    st.info(f"⏰ **{translate_text('Urgency', lang)}:** {urgency}")
                
                with tab2:
                    st.markdown(f"**{translate_text('Organic Treatment', lang)}:** {organic}")
                    
                    st.markdown(f"**🌿 {translate_text('Local Solutions', lang)}:**")
                    local_solutions = [
                        translate_text("Garlic + chili spray", lang),
                        translate_text("Neem leaves solution", lang),
                        translate_text("Milk solution (1:10)", lang),
                        translate_text("Baking soda spray", lang),
                        translate_text("Compost tea", lang)
                    ]
                    for tip in local_solutions:
                        st.markdown(f"• {tip}")
                
                with tab3:
                    st.markdown(f"**{translate_text('Prevention', lang)}:** {prevention}")
                
                with tab4:
                    st.markdown(f"**{translate_text('Watering', lang)}:** {watering}")
                
                # Save to cache for offline learning
                hybrid_cache_learn(uploaded_file, result, metadata={
                    'weather': st.session_state.get('weather_condition', 'Unknown'),
                    'soil': st.session_state.get('soil_type', 'Unknown')
                })
                
                # Save analysis to history
                analysis_data = {
                    'analysis_id': st.session_state.get('current_analysis_id', str(uuid.uuid4())[:8]),
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'user_name': st.session_state.user_name or 'Anonymous',
                    'weather': st.session_state.weather_condition,
                    'soil': st.session_state.soil_type,
                    'language': lang,
                    'predicted_class': predicted_class,
                    'confidence': confidence,
                    'disease_info': disease_info,
                    'processing_time': result.get('processing_time', 0),
                    'api_used': result.get('success', False)
                }
                
                # Add to history if not already present
                existing = next((a for a in st.session_state.analysis_history 
                        if a.get('analysis_id') == st.session_state.get('current_analysis_id')), None)
                if not existing:
                    st.session_state.analysis_history.append(analysis_data)
                
                # Export options
                st.markdown(f"### 📥 {translate_text('Export Report', lang)}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # CSV report
                    report_data = {
                        translate_text('Field', lang): [
                            translate_text('Date', lang),
                            translate_text('Farmer', lang),
                            translate_text('Plant', lang),
                            translate_text('Disease', lang),
                            translate_text('Severity', lang),
                            translate_text('Confidence', lang),
                            translate_text('Weather', lang),
                            translate_text('Soil Type', lang)
                        ],
                        translate_text('Value', lang): [
                            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            st.session_state.user_name or 'Anonymous',
                            plant_name,
                            disease_name,
                            translate_text(severity, lang),
                            f"{confidence:.1f}%",
                            st.session_state.weather_condition,
                            st.session_state.soil_type
                        ]
                    }
                    
                    report_df = pd.DataFrame(report_data)
                    csv_data = report_df.to_csv(index=False)
                    
                    st.download_button(
                        f"📊 {translate_text('Download Report (CSV)', lang)}",
                        csv_data,
                        f"plant_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        "text/csv",
                        use_container_width=True
                    )
                
                with col2:
                    # Text report
                    text_report = f"""{translate_text('PLANT ANALYSIS REPORT', lang)}
==========================================
{translate_text('Analysis ID', lang)}: {st.session_state.get('current_analysis_id', 'N/A')}
{translate_text('Date', lang)}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{translate_text('Farmer', lang)}: {st.session_state.user_name or 'Anonymous'}
{translate_text('Language', lang)}: {lang}

{translate_text('ENVIRONMENTAL CONDITIONS', lang)}:
{translate_text('Weather', lang)}: {st.session_state.weather_condition}
{translate_text('Soil Type', lang)}: {st.session_state.soil_type}

{translate_text('ANALYSIS RESULTS', lang)}:
{translate_text('Plant Type', lang)}: {plant_name}
{translate_text('Disease/Condition', lang)}: {disease_name}
{translate_text('Severity Level', lang)}: {translate_text(severity, lang)}
{translate_text('Confidence Score', lang)}: {confidence:.1f}%

{translate_text('SYMPTOMS', lang)}:
{symptoms}

{translate_text('TREATMENT RECOMMENDATION', lang)}:
{treatment}

{translate_text('ORGANIC TREATMENT', lang)}:
{organic}

{translate_text('PREVENTION MEASURES', lang)}:
{prevention}

{translate_text('WATERING ADVICE', lang)}:
{watering}

{translate_text('MODEL INFO', lang)}:
{translate_text('Processing Time', lang)}: {result.get('processing_time', 0):.2f}s
{translate_text('Model Version', lang)}: {result.get('model_version', 'Unknown')}
{translate_text('API Used', lang)}: {translate_text('Yes' if result.get('success', False) else 'No', lang)}

{translate_text('Generated by', lang)} KilimoGlow Kenya v2.0
"""
                    
                    st.download_button(
                        f"📄 {translate_text('Download Report (TXT)', lang)}",
                        text_report,
                        f"plant_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        "text/plain",
                        use_container_width=True
                    )
        else:
            st.markdown(f"""
            <div class="kenyan-card" style="text-align: center; padding: 3rem;">
                <h3 style="color: #FFD700;">📸 {translate_text('Ready for analysis', lang)}</h3>
                <p>{translate_text('Take a photo or upload an image to begin plant disease detection', lang)}</p>
                <div style="font-size: 3rem; margin: 1rem 0;">🔬</div>
            </div>
            """, unsafe_allow_html=True)

# ================== BATCH ANALYSIS PAGE ==================
elif selected_page.startswith("📊"):
    st.markdown(f"<h1 style='text-align: center; color: #FFD700;'>📊 {current_texts['batch_analysis']}</h1>", unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="kenyan-card">
        <h3 style="color: #FFD700;">⚡ {translate_text('Batch Processing', lang)}</h3>
        <p style="color: white;">{translate_text('Upload multiple plant images for simultaneous analysis. Perfect for large-scale farm monitoring.', lang)}</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown(f"### 📁 {translate_text('Upload Multiple Images', lang)}")
        
        uploaded_files = st.file_uploader(
            translate_text("Choose plant images", lang),
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            help=translate_text("Select multiple images for batch analysis", lang)
        )
        
        if uploaded_files:
            st.info(f"📊 {len(uploaded_files)} {translate_text('images ready for processing', lang)}")
            
            # Batch processing button
            if st.button(current_texts["process_batch"], type="primary", use_container_width=True):
                with st.spinner(f"⚡ {translate_text('Processing batch... This may take a few minutes.', lang)}"):
                    
                    if api_connected:
                        # Use FastAPI batch endpoint
                        success, batch_result = batch_predict_with_fastapi(uploaded_files)
                        
                        if success and batch_result.get('success'):
                            results = batch_result.get('results', [])
                        else:
                            st.warning(f"⚠️ {translate_text('FastAPI batch processing failed, using individual processing', lang)}")
                            results = []
                            for file in uploaded_files:
                                success, result = predict_with_fastapi(file)
                                if success:
                                    results.append(result)
                                else:
                                    results.append(hybrid_offline_predict(file, 
                                        metadata={'weather': st.session_state.get('weather_condition','Unknown'),
                                                 'soil': st.session_state.get('soil_type','Unknown')},
                                        simulate_fn=simulate_disease_prediction))
                    else:
                        # Offline batch processing
                        st.info(f"📱 {translate_text('Using offline batch processing', lang)}")
                        results = []
                        for file in uploaded_files:
                            
                            result = hybrid_offline_predict(
                                file,
                                metadata={
                                    'weather': st.session_state.get('weather_condition', 'Unknown'),
                                    'soil': st.session_state.get('soil_type', 'Unknown')
                                },
                                simulate_fn=simulate_disease_prediction)
                            results.append(result)
                    # Store batch results
                    batch_analysis = {
                        'batch_id': str(uuid.uuid4())[:8],
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'total_images': len(uploaded_files),
                        'results': results,
                        'user_name': st.session_state.user_name or 'Anonymous'
                    }
                    
                    st.session_state.batch_results.append(batch_analysis)
                    
                    # Add individual results to history
                    for i, result in enumerate(results):
                        predicted_class = result.get("predicted_class", "unknown")
                        confidence = result.get("confidence", 0)
                        if confidence <= 1:
                            confidence *= 100
                        
                        disease_info = PLANT_DISEASES.get(predicted_class, {})
                        
                        analysis_data = {
                            'analysis_id': f"batch_{batch_analysis['batch_id']}_{i}",
                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'user_name': st.session_state.user_name or 'Anonymous',
                            'weather': 'Batch Processing',
                            'soil': 'Batch Processing',
                            'language': lang,
                            'predicted_class': predicted_class,
                            'confidence': confidence,
                            'disease_info': disease_info,
                            'processing_time': result.get('processing_time', 0),
                            'api_used': api_connected and result.get('success', False),
                            'batch_id': batch_analysis['batch_id']
                        }
                        st.session_state.analysis_history.append(analysis_data)
                    
                    st.success(f"✅ {translate_text('Batch processing complete!', lang)} {len(results)} {translate_text('images analyzed.', lang)}")
    
    with col2:
        # Display batch results
        if st.session_state.batch_results:
            st.markdown(f"### 📈 {translate_text('Batch Results', lang)}")
            
            latest_batch = st.session_state.batch_results[-1]
            results = latest_batch['results']
            
            # Summary metrics
            col1, col2, col3 = st.columns(3)
            
            total_images = len(results)
            healthy_count = sum(1 for r in results if 'healthy' in r.get('predicted_class', '').lower())
            avg_confidence = sum(r.get('confidence', 0) for r in results) / total_images if total_images > 0 else 0
            if avg_confidence <= 1:
                avg_confidence *= 100
            
            with col1:
                st.metric(f"📊 {translate_text('Total Images', lang)}", total_images)
            with col2:
                st.metric(f"🌱 {translate_text('Healthy Plants', lang)}", f"{healthy_count} ({(healthy_count/total_images*100):.0f}%)")
            with col3:
                st.metric(f"🎯 {translate_text('Avg Confidence', lang)}", f"{avg_confidence:.1f}%")
            
            # Results visualization
            if results:
                # Create DataFrame for visualization
                batch_data = []
                for i, result in enumerate(results):
                    predicted_class = result.get("predicted_class", "unknown")
                    disease_info = PLANT_DISEASES.get(predicted_class, {})
                    confidence = result.get("confidence", 0)
                    if confidence <= 1:
                        confidence *= 100
                    
                    # Get translated names
                    lang_suffix = '' if lang == 'English' else f'_{LANGUAGES[lang]}'
                    plant_name = disease_info.get(f'plant{lang_suffix}', disease_info.get('plant', 'Unknown'))
                    disease_name = disease_info.get(f'name{lang_suffix}', disease_info.get('name', 'Unknown'))
                    
                    batch_data.append({
                        translate_text('Image', lang): f'{translate_text("Image", lang)} {i+1}',
                        translate_text('Plant', lang): plant_name,
                        translate_text('Disease', lang): disease_name,
                        translate_text('Severity', lang): translate_text(disease_info.get('severity', 'Unknown'), lang),
                        translate_text('Confidence', lang): f"{confidence:.1f}%"
                    })
                
                batch_df = pd.DataFrame(batch_data)
                
                # Severity distribution
                severity_col = translate_text('Severity', lang)
                fig_severity = px.pie(
                    batch_df, 
                    names=severity_col,
                    title=translate_text('Disease Severity Distribution', lang),
                    color_discrete_map={
                        translate_text('None', lang): '#32CD32',
                        translate_text('Medium', lang): '#FFD700', 
                        translate_text('High', lang): '#FF8C00',
                        translate_text('Critical', lang): '#DC143C'
                    }
                )
                fig_severity.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="white")
                )
                st.plotly_chart(fig_severity, use_container_width=True)
                
                # Results table
                st.markdown(f"### 📋 {translate_text('Detailed Results', lang)}")
                st.dataframe(batch_df, use_container_width=True, hide_index=True)
                
                # Export batch results
                st.markdown(f"### 📥 {translate_text('Export Batch Results', lang)}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Export CSV
                    csv_data = batch_df.to_csv(index=False)
                    st.download_button(
                        f"📊 {translate_text('Download Batch CSV', lang)}",
                        csv_data,
                        f"batch_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        "text/csv",
                        use_container_width=True
                    )
                
                with col2:
                    # Export summary report
                    summary_report = f"""{translate_text('BATCH ANALYSIS REPORT', lang)}
========================================
{translate_text('Batch ID', lang)}: {latest_batch['batch_id']}
{translate_text('Date', lang)}: {latest_batch['timestamp']}
{translate_text('Farmer', lang)}: {latest_batch['user_name']}
{translate_text('Total Images', lang)}: {total_images}
{translate_text('Healthy Plants', lang)}: {healthy_count} ({(healthy_count/total_images*100):.1f}%)
{translate_text('Plants Needing Treatment', lang)}: {total_images - healthy_count} ({((total_images - healthy_count)/total_images*100):.1f}%)
{translate_text('Average Confidence', lang)}: {avg_confidence:.1f}%

{translate_text('DETAILED RESULTS', lang)}:
{chr(10).join([f"{translate_text('Image', lang)} {i+1}: {row[translate_text('Plant', lang)]} - {row[translate_text('Disease', lang)]} ({row[translate_text('Confidence', lang)]})" for i, row in batch_df.iterrows()])}

{translate_text('Generated by', lang)} KilimoGlow Kenya v2.0
"""
                    
                    st.download_button(
                        f"📄 {translate_text('Download Summary', lang)}",
                        summary_report,
                        f"batch_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        "text/plain",
                        use_container_width=True
                    )
        else:
            st.markdown(f"""
            <div class="kenyan-card" style="text-align: center; padding: 3rem;">
                <h3 style="color: #FFD700;">⚡ {translate_text('Ready for Batch Processing', lang)}</h3>
                <p>{translate_text('Upload multiple images to see batch analysis results here', lang)}</p>
                <div style="font-size: 3rem; margin: 1rem 0;">📊</div>
            </div>
            """, unsafe_allow_html=True)

# ================== DASHBOARD PAGE ==================
elif selected_page.startswith("📈"):
    st.markdown(f"<h1 style='text-align: center; color: #FFD700;'>📈 {current_texts['dashboard']}</h1>", unsafe_allow_html=True)
    
    weather = get_weather("Nairobi")
    if weather:
        st.metric("Temperature (°C)", weather["temp"])
        st.metric("Condition", weather["desc"].title())
        st.metric("Humidity (%)", weather["humidity"])


    if st.session_state.analysis_history:
        # Key metrics
        total_analyses = len(st.session_state.analysis_history)
        healthy_count = sum(1 for a in st.session_state.analysis_history 
                          if 'healthy' in a.get('predicted_class', '').lower())
        api_analyses = sum(1 for a in st.session_state.analysis_history if a.get('api_used', False))
        avg_confidence = sum(a.get('confidence', 0) for a in st.session_state.analysis_history) / total_analyses
        
        # Metrics display
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <h2 style="color: #4a9f5a; margin: 0;">{total_analyses}</h2>
                <p style="margin: 0;">{current_texts['total_scans']}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <h2 style="color: #FFD700; margin: 0;">{healthy_count}</h2>
                <p style="margin: 0;">{current_texts['healthy_plants']}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <h2 style="color: #FF6B35; margin: 0;">{total_analyses - healthy_count}</h2>
                <p style="margin: 0;">{translate_text('Diseases Detected', lang)}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <h2 style="color: #9932CC; margin: 0;">{avg_confidence:.1f}%</h2>
                <p style="margin: 0;">{translate_text('Avg Confidence', lang)}</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Analysis trends over time
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(f"### 📊 {translate_text('Analysis Trends', lang)}")
            
            # Prepare time series data
            df = pd.DataFrame(st.session_state.analysis_history)
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
            df['date'] = df['timestamp'].dt.strftime('%Y-%m-%d')
                        
            # Daily analysis count
            daily_counts = df.groupby('date').size().reset_index(name='count')
            daily_counts['date'] = pd.to_datetime(daily_counts['date'])
            daily_counts['cumulative'] = daily_counts['count'].cumsum()
            
            fig_trend = go.Figure()
            
            # Daily bars
            fig_trend.add_trace(go.Bar(
                x=daily_counts['date'],
                y=daily_counts['count'],
                name=translate_text('Daily Analyses', lang),
                marker_color='#32CD32',
                opacity=0.7
            ))
            
            # Cumulative line
            fig_trend.add_trace(go.Scatter(
                x=daily_counts['date'],
                y=daily_counts['cumulative'],
                mode='lines+markers',
                name=translate_text('Cumulative', lang),
                line=dict(color='#FFD700', width=3),
                yaxis='y2'
            ))
            
            fig_trend.update_layout(
                title=f"📈 {translate_text('Analysis Activity Over Time', lang)}",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0.1)",
                font=dict(color="white"),
                xaxis=dict(title=translate_text('Date', lang), tickformat='%Y-%m-%d'),
                yaxis=dict(title=translate_text('Daily Count', lang), side='left'),
                yaxis2=dict(title=translate_text('Cumulative', lang), side='right', overlaying='y'),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                height=400
            )
            
            st.plotly_chart(fig_trend, use_container_width=True)
        
        with col2:
            st.markdown(f"### 🌱 {translate_text('Plant Types', lang)}")

            # Initialize variables for export
            plant_counts = {}
            severity_counts = {}
            
            # Extract plant types from disease info
            plant_counts = {}
            for analysis in st.session_state.analysis_history:
                disease_info = analysis.get('disease_info', {})
                lang_suffix = '' if lang == 'English' else f'_{LANGUAGES[lang]}'
                plant = disease_info.get(f'plant{lang_suffix}', disease_info.get('plant', 'Unknown'))
                plant_counts[plant] = plant_counts.get(plant, 0) + 1
            
            if plant_counts:
                plant_df = pd.DataFrame(list(plant_counts.items()), 
                                       columns=[translate_text('Plant', lang), translate_text('Count', lang)])
                
                fig_plants = px.pie(
                    plant_df,
                    values=translate_text('Count', lang),
                    names=translate_text('Plant', lang),
                    title=translate_text('Plant Distribution', lang),
                    color_discrete_sequence=['#32CD32', '#FFD700', '#FF6B35', '#9932CC']
                )
                
                fig_plants.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="white"),
                    height=300,
                    margin=dict(l=20, r=20, t=60, b=20)
                )
                
                st.plotly_chart(fig_plants, use_column_width=True)
        
        # Disease severity analysis
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"### ⚠️ {translate_text('Severity', lang)} {translate_text('Analysis', lang)}")
            
            severity_counts = {}
            for analysis in st.session_state.analysis_history:
                disease_info = analysis.get('disease_info', {})
                severity = disease_info.get('severity', 'Unknown')
                severity_trans = translate_text(severity, lang)
                severity_counts[severity_trans] = severity_counts.get(severity_trans, 0) + 1
            
            if severity_counts:
                severity_df = pd.DataFrame(list(severity_counts.items()), 
                                          columns=[translate_text('Severity', lang), translate_text('Count', lang)])
                
                # Color mapping for severity
                severity_colors = {
                    translate_text('None', lang): '#32CD32',
                    translate_text('Medium', lang): '#FFD700', 
                    translate_text('High', lang): '#FF8C00',
                    translate_text('Critical', lang): '#DC143C',
                    translate_text('Unknown', lang): '#808080'
                }
                
                fig_severity = px.bar(
                    severity_df,
                    x=translate_text('Severity', lang),
                    y=translate_text('Count', lang),
                    title=translate_text('Disease Severity Distribution', lang),
                    color=translate_text('Severity', lang),
                    color_discrete_map=severity_colors
                )
                
                fig_severity.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0.1)",
                    font=dict(color="white"),
                    showlegend=False,
                    height=350
                )
                
                st.plotly_chart(fig_severity, use_column_width=True)
        
        with col2:
            st.markdown(f"### 🎯 {translate_text('Confidence', lang)} {translate_text('Analysis', lang)}")
            
            # Confidence distribution
            confidences = [a.get('confidence', 0) for a in st.session_state.analysis_history]
            
            if confidences:
                fig_conf_dist = go.Figure()
                
                fig_conf_dist.add_trace(go.Histogram(
                    x=confidences,
                    nbinsx=10,
                    marker_color='#32CD32',
                    opacity=0.7,
                    name=translate_text('Confidence', lang)
                ))
                
                # Add average line
                avg_line = sum(confidences) / len(confidences)
                fig_conf_dist.add_vline(
                    x=avg_line,
                    line_dash="dash",
                    line_color="#FFD700",
                    line_width=3,
                    annotation_text=f"{translate_text('Avg', lang)}: {avg_line:.1f}%"
                )
                
                fig_conf_dist.update_layout(
                    title=f"🎯 {translate_text('Confidence', lang)} {translate_text('Distribution', lang)}",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0.1)",
                    font=dict(color="white"),
                    xaxis_title=f"{translate_text('Confidence', lang)} (%)",
                    yaxis_title=translate_text('Count', lang),
                    showlegend=False,
                    height=350
                )
                
                st.plotly_chart(fig_conf_dist, use_column_width=True)
        
        # Recent analysis history table
        st.markdown(f"### 📋 {current_texts['recent_analysis']}")
        
        # Prepare display data
        display_data = []
        recent_analyses = sorted(st.session_state.analysis_history, 
                               key=lambda x: x['timestamp'], reverse=True)[:10]
        
        for analysis in recent_analyses:
            disease_info = analysis.get('disease_info', {})
            lang_suffix = '' if lang == 'English' else f'_{LANGUAGES[lang]}'
            plant_name = disease_info.get(f'plant{lang_suffix}', disease_info.get('plant', 'Unknown'))
            disease_name = disease_info.get(f'name{lang_suffix}', disease_info.get('name', 'Unknown'))
            severity = disease_info.get('severity', 'Unknown')
            
            display_data.append({
                translate_text('Time', lang): analysis['timestamp'].split(' ')[1][:5],
                translate_text('Farmer', lang): analysis.get('user_name', 'Anonymous')[:15],
                translate_text('Plant', lang): plant_name,
                translate_text('Disease', lang): disease_name[:20],
                translate_text('Severity', lang): translate_text(severity, lang),
                translate_text('Confidence', lang): f"{analysis.get('confidence', 0):.1f}%",
                'API': '🟢' if analysis.get('api_used', False) else '🔴'
            })
        
        if display_data:
            history_df = pd.DataFrame(display_data)
            st.dataframe(history_df, use_container_width=True, hide_index=True)
        
        # Export dashboard data
        st.markdown(f"### 📥 {translate_text('Export', lang)} {translate_text('Dashboard', lang)}")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Export full history
            full_export_data = []
            for analysis in st.session_state.analysis_history:
                disease_info = analysis.get('disease_info', {})
                lang_suffix = '' if lang == 'English' else f'_{LANGUAGES[lang]}'
                plant_name = disease_info.get(f'plant{lang_suffix}', disease_info.get('plant', ''))
                disease_name = disease_info.get(f'name{lang_suffix}', disease_info.get('name', ''))
                
                full_export_data.append({
                    translate_text('Analysis ID', lang): analysis.get('analysis_id', ''),
                    translate_text('Date', lang): analysis.get('timestamp', ''),
                    translate_text('Farmer', lang): analysis.get('user_name', ''),
                    translate_text('Weather', lang): analysis.get('weather', ''),
                    translate_text('Soil Type', lang): analysis.get('soil', ''),
                    translate_text('Language', lang): analysis.get('language', ''),
                    translate_text('Plant Type', lang): plant_name,
                    translate_text('Disease', lang): disease_name,
                    translate_text('Severity', lang): translate_text(disease_info.get('severity', ''), lang),
                    translate_text('Confidence', lang): analysis.get('confidence', 0),
                    translate_text('Processing Time', lang): analysis.get('processing_time', 0),
                    translate_text('API Used', lang): analysis.get('api_used', False)
                })
            
            export_df = pd.DataFrame(full_export_data)
            csv_data = export_df.to_csv(index=False)
            
            st.download_button(
                f"📊 {translate_text('Download', lang)} CSV",
                csv_data,
                f"kilimoglow_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "text/csv",
                use_container_width=True
            )
        
        with col2:
            # Export summary stats
            summary_stats = f"""{translate_text('KILIMOGLOW KENYA - DASHBOARD SUMMARY', lang)}
{translate_text('Generated', lang)}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{translate_text('OVERVIEW STATISTICS', lang)}:
{translate_text('Total Analyses', lang)}: {total_analyses}
{translate_text('Healthy Plants', lang)}: {healthy_count} ({(healthy_count/total_analyses*100):.1f}%)
{translate_text('Diseases Detected', lang)}: {total_analyses - healthy_count} ({((total_analyses - healthy_count)/total_analyses*100):.1f}%)
{translate_text('Average Confidence', lang)}: {avg_confidence:.1f}%
{translate_text('API Used', lang)}: {api_analyses} ({(api_analyses/total_analyses*100):.1f}%)

{translate_text('PLANT TYPE BREAKDOWN', lang)}:

{chr(10).join([f"{plant}: {count}" for plant, count in plant_counts.items()]) if 'plant_counts' in locals() else translate_text('No data available', lang)}

{translate_text('SEVERITY BREAKDOWN', lang)}:
{chr(10).join([f"{severity}: {count}" for severity, count in severity_counts.items()]) if 'severity_counts' in locals() else translate_text('No data available', lang)}

{translate_text('Generated by', lang)} KilimoGlow Kenya v2.0
"""
            
            st.download_button(
                f"📈 {translate_text('Summary', lang)}",
                summary_stats,
                f"kilimoglow_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                "text/plain",
                use_container_width=True
            )
        
        with col3:
            # Export for analysis (JSON)
            json_data = {
                'export_info': {
                    'timestamp': datetime.now().isoformat(),
                    'total_records': total_analyses,
                    'app_version': 'KilimoGlow_v2.0',
                    'language': lang
                },
                'analysis_history': st.session_state.analysis_history,
                'batch_results': st.session_state.batch_results,
                'summary_stats': {
                    'total_analyses': total_analyses,
                    'healthy_count': healthy_count,
                    'avg_confidence': avg_confidence,
                    'plant_distribution': plant_counts if 'plant_counts' in locals() else {},
                    'severity_distribution': severity_counts if 'severity_counts' in locals() else {}
                }
            }
            
            json_string = json.dumps(json_data, indent=2, default=str)
            
            st.download_button(
                f"📦 {translate_text('Data', lang)} (JSON)",
                json_string,
                f"kilimoglow_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "application/json",
                use_container_width=True
            )
    
    else:
        st.markdown(f"""
        <div class="kenyan-card" style="text-align: center; padding: 4rem;">
            <h2 style="color: #FFD700;">📊 {translate_text('Dashboard Ready', lang)}</h2>
            <p style="margin: 1rem 0;">{translate_text('Start analyzing plants to see comprehensive analytics and insights here', lang)}</p>
            <div style="font-size: 4rem; margin: 2rem 0;">📈</div>
            <p style="color: #32CD32;">{translate_text('Your farming analytics will appear once you begin plant disease detection', lang)}</p>
        </div>
        """, unsafe_allow_html=True)

# ================== SETTINGS PAGE ==================
elif selected_page.startswith("⚙️"):
    st.markdown(f"<h1 style='text-align: center; color: #FFD700;'>⚙️ {current_texts['settings']}</h1>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown(f"### 🔧 {translate_text('System Configuration', lang)}")
        
        # API Configuration
        with st.expander(f"🌐 {translate_text('API Settings', lang)}", expanded=True):
            st.markdown(f"""
            **{translate_text('FastAPI Status', lang)}:** {'🟢 ' + translate_text('Connected', lang) if api_connected else '🔴 ' + translate_text('Disconnected', lang)}
            
            **{translate_text('Base URL', lang)}:** {FASTAPI_BASE_URL}
            
            **{translate_text('Available Endpoints', lang)}:**
            """)
            
            for endpoint_name, endpoint_url in FASTAPI_ENDPOINTS.items():
                status = "✅" if api_connected else "❌"
                st.markdown(f"- {status} **{endpoint_name.title()}:** `{endpoint_url}`")
            
            if st.button(f"🔄 {translate_text('Test API Connection', lang)}", use_container_width=True):
                with st.spinner(f"{translate_text('Testing connection...', lang)}"):
                    test_success, test_info, working_api_url = check_fastapi_connection()
                    if test_success:
                        st.success(f"✅ {translate_text('API connection successful!', lang)}")
                        st.json(test_info)
                    else:
                        st.error(f"❌ {translate_text('API connection failed!', lang)}")
                        st.json(test_info)
        
        # Model Information
        with st.expander(f"🤖 {translate_text('Model', lang)} {translate_text('Information', lang)}"):
            if api_connected:
                model_info = get_model_info()
                if model_info:
                    st.json(model_info)
                else:
                    st.info(f"{translate_text('Model information not available', lang)}")
            else:
                st.warning(f"{translate_text('API not connected - model info unavailable', lang)}")
        
        # Language & Localization
        with st.expander(f"🌍 {translate_text('Language & Localization', lang)}", expanded=True):
            st.markdown(f"**{translate_text('Supported Languages', lang)}:**")
            for language, code in LANGUAGES.items():
                current = "🔸" if language == lang else "⚪"
                st.markdown(f"{current} **{language}** (`{code}`)")
            
            st.markdown("---")
            
            # Translation test
            test_text = st.text_input(f"🔤 {translate_text('Test', lang)} {translate_text('Translation', lang)}", 
                                     value="Healthy plant treatment")
            if test_text:
                for language in LANGUAGES.keys():
                    if language != "English":
                        translated = translate_text(test_text, language)
                        st.markdown(f"**{language}:** {translated}")
    
    with col2:
        st.markdown(f"### 📱 {translate_text('User Preferences', lang)}")
        
        # User Profile
        with st.expander(f"👤 {translate_text('User Profile', lang)}", expanded=True):
            st.session_state.user_name = st.text_input(
                f"👤 {translate_text('Default Name', lang)}",
                value=st.session_state.user_name,
                help=translate_text("Default name for analysis reports", lang)
            )
            
            # Camera quality settings
            camera_options = ["Low (480p)", "Medium (720p)", "High (1080p)"]
            st.session_state.camera_quality = st.selectbox(
                f"📷 {translate_text('Camera Quality', lang)}",
                camera_options,
                index=camera_options.index(st.session_state.camera_quality) if st.session_state.camera_quality in camera_options else 1
            )
            
            # Default environmental conditions
            st.markdown(f"**{translate_text('Default', lang)} {translate_text('Weather', lang)}:**")
            default_weather = st.selectbox(
                f"🌤️ {translate_text('Weather', lang)}",
                ["Select", "Sunny", "Rainy", "Cloudy", "Dry"],
                help=translate_text("Pre-select weather condition", lang)
            )
            
            default_soil = st.selectbox(
                f"🌱 {translate_text('Soil Type', lang)}",
                ["Select", "Clay", "Sandy", "Loam", "Rocky"],
                help=translate_text("Pre-select soil type", lang)
            )
        
        # Data Management
        with st.expander(f"💾 {translate_text('Data Management', lang)}"):
            st.markdown(f"**{translate_text('Analysis History', lang)}:**")
            st.info(f"📊 {translate_text('Total Analyses', lang)}: {len(st.session_state.analysis_history)}")
            st.info(f"📦 {translate_text('Batch Results', lang)}: {len(st.session_state.batch_results)}")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button(f"🗑️ {translate_text('Clear History', lang)}", use_container_width=True):
                    st.session_state.analysis_history = []
                    st.success(f"✅ {translate_text('History cleared!', lang)}")
                    time.sleep(1)
                    st.rerun()
            
            with col2:
                if st.button(f"🔄 {translate_text('Reset All Data', lang)}", use_container_width=True):
                    # Reset all session state except language
                    current_lang = st.session_state.selected_language
                    keys_to_delete = [k for k in st.session_state.keys() if k != 'selected_language']
                    for key in keys_to_delete:
                        del st.session_state[key]
                    init_session_state()
                    st.session_state.selected_language = current_lang
                    st.success(f"✅ {translate_text('All data reset!', lang)}")
                    time.sleep(1)
                    st.rerun()
        
        # Advanced Settings
        with st.expander(f"🔬 {translate_text('Advanced', lang)} {translate_text('Settings', lang)}"):
            # Confidence threshold
            confidence_threshold = st.slider(
                f"🎯 {translate_text('Confidence', lang)} {translate_text('Threshold', lang)}",
                min_value=50.0,
                max_value=100.0,
                value=70.0,
                step=5.0,
                help=translate_text("Minimum confidence for reliable predictions", lang)
            )
            
            # Processing timeout
            processing_timeout = st.slider(
                f"⏱️ {translate_text('Processing', lang)} Timeout (s)",
                min_value=10,
                max_value=60,
                value=25,
                step=5,
                help=translate_text("Maximum time to wait for API response", lang)
            )
            
            # Auto-refresh dashboard
            auto_refresh = st.checkbox(
                f"🔄 {translate_text('Auto-refresh', lang)} {translate_text('Dashboard', lang)}",
                value=False,
                help=translate_text("Automatically refresh dashboard every 30 seconds", lang)
            )
            
            # Debug mode
            debug_mode = st.checkbox(
                f"🛠️ {translate_text('Debug', lang)} Mode",
                value=False,
                help=translate_text("Show detailed error information and logs", lang)
            )
            
            if debug_mode:
                st.markdown(f"**{translate_text('Debug', lang)} {translate_text('Information', lang)}:**")
                debug_info = {
                    "session_state_keys": list(st.session_state.keys()),
                    "api_status": st.session_state.get('cached_api_status', 'unknown'),
                    "current_analysis_id": st.session_state.get('current_analysis_id'),
                    "working_api_url": st.session_state.get('working_api_url'),
                    "total_analyses": len(st.session_state.analysis_history),
                    "total_batches": len(st.session_state.batch_results),
                    "hybrid_metrics": st.session_state.get('hybrid_metrics', {})
                }
                st.json(debug_info)

# ================== FOOTER ==================
st.markdown("---")
st.markdown(f"""
<div class="app-footer">
    <h3 style="color: #FFD700; margin-bottom: 1rem;">🌿 {current_texts['app_title']}</h3>
    <p style="color: white; margin-bottom: 0.5rem;">
        🇰🇪 <strong>{translate_text('Made for Kenyan Farmers', lang)}</strong> • 
        🌾 <strong>{translate_text('Supporting Local Agriculture', lang)}</strong> • 
        🤖 <strong>{translate_text('Powered by AI', lang)}</strong>
    </p>
    <p style="color: #32CD32; margin-bottom: 1rem;">
        {translate_text('Empowering smallholder farmers with smart plant disease detection technology', lang)}
    </p>
    <div style="display: flex; justify-content: center; gap: 2rem; flex-wrap: wrap; margin: 1rem 0;">
        <span style="color: white;">📱 {translate_text('Mobile Optimized', lang)}</span>
        <span style="color: white;">🌍 {translate_text('Multi-language', lang)}</span>
        <span style="color: white;">⚡ {translate_text('FastAPI Powered', lang)}</span>
        <span style="color: white;">🔄 {translate_text('Batch Processing', lang)}</span>
    </div>
    <p style="color: #FFD700; margin-top: 1rem; font-size: 0.9rem;">
        {translate_text('Version 2.0', lang)} • {translate_text('Built with', lang)} ❤️ {translate_text('for Kenya\'s Agricultural Future', lang)}
    </p>
</div>
""", unsafe_allow_html=True)

# Auto-refresh for dashboard (if enabled in settings)
if (selected_page.startswith("📈") and 
    locals().get('auto_refresh', False) and 
    st.session_state.analysis_history):
    # Add refresh button instead of automatic refresh to avoid constant reloading
    if st.button(f"🔄 {translate_text('Refresh', lang)} {translate_text('Dashboard', lang)}"):
        st.rerun()

# Performance monitoring (if debug mode enabled)
if locals().get('debug_mode', False):
    st.markdown("---")
    st.markdown(f"### 🛠️ {translate_text('Debug', lang)} {translate_text('Information', lang)}")
    
    debug_info = {
        "timestamp": datetime.now().isoformat(),
        "selected_page": selected_page,
        "api_status": st.session_state.get('cached_api_status', 'unknown'),
        "total_analyses": len(st.session_state.analysis_history),
        "total_batches": len(st.session_state.batch_results),
        "current_language": lang,
        "session_state_size": len(st.session_state.keys()),
        "memory_usage": f"{len(str(st.session_state)) / 1024:.1f} KB",
        "hybrid_metrics": st.session_state.get('hybrid_metrics', {})
    }
    st.json(debug_info)

# Cache model for offline use if API is connected
if api_connected and not st.session_state.get('model_cached', False):
    cache_model_offline()
                    
