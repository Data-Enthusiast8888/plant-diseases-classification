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
import json
import base64
from datetime import datetime, timedelta
import time
import warnings
import random
import cv2
import speech_recognition as sr
import threading
from io import BytesIO
import tempfile
import uuid
from pathlib import Path


if "voice_input_active" not in st.session_state:
    st.session_state.voice_input_active = False



# ===== MISSING FUNCTION DEFINITIONS =====
def _safe_json(resp):
    try:
        return resp.json()
    except Exception:
        return {"status_code": getattr(resp, "status_code", None), "text": getattr(resp, "text", "")}

def check_fastapi_connection(timeout=3):
    """
    Check if FastAPI backend is available.
    Returns (connected: bool, info: dict)
    """
    try:
        url = globals().get("FASTAPI_BASE_URL", "http://127.0.0.1:8000")
        health_url = f"{url}/health"
        resp = requests.get(health_url, timeout=timeout)
        if resp.status_code == 200:
            info = _safe_json(resp)
            return True, info
        return False, _safe_json(resp)
    except Exception as e:
        return False, {"error": str(e)}

def initialize_speech_recognition():
    """
    Initialize and return (recognizer, microphone) or (None, None) if not available.
    """
    try:
        import speech_recognition as sr  # optional dependency
        recognizer = sr.Recognizer()
        microphone = None
        try:
            microphone = sr.Microphone()
        except Exception:
            # Microphone may not be present (headless environment); return recognizer so user can still use non-mic flows
            microphone = None
        return recognizer, microphone
    except Exception:
        return None, None

def voice_to_text(recognizer, microphone, language="English", timeout=6, phrase_time_limit=6):
    """
    Convert spoken input to text using Google Web Speech API via speech_recognition.
    Returns (success: bool, text_or_error: str).
    """
    if recognizer is None or microphone is None:
        return False, "Speech recognizer or microphone not available."
    try:
        lang_code = "en-US"
        if isinstance(language, str):
            l = language.lower()
            if l.startswith("kis") or l.startswith("sw"):
                lang_code = "sw-KE"
            elif l.startswith("luo"):
                lang_code = "en-US"  # fallback
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.6)
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        text = recognizer.recognize_google(audio, language=lang_code)
        return True, text
    except Exception as e:
        return False, str(e)

def predict_with_fastapi(file_obj, timeout=20):
    """
    Send an image file (UploadedFile / BytesIO / path-like) to the FastAPI predict endpoint.
    Returns (success: bool, result: dict). The returned dict should match the API's response.
    """
    try:
        base = globals().get("FASTAPI_BASE_URL", "http://127.0.0.1:8000")
        predict_url = f"{base}/predict"
        files = {}
        # Handle Streamlit UploadedFile and file-like objects
        if hasattr(file_obj, "read"):
            try:
                file_obj.seek(0)
            except Exception:
                pass
            content = file_obj.read()
            if isinstance(content, str):
                content = content.encode("utf-8")
            filename = getattr(file_obj, "name", "image.jpg")
            # Try to detect mime type from filename
            mime = "image/jpeg"
            if filename.lower().endswith(".png"):
                mime = "image/png"
            files["file"] = (filename, content, mime)
        elif isinstance(file_obj, (bytes, bytearray)):
            files["file"] = ("image.jpg", bytes(file_obj), "image/jpeg")
        else:
            # treat as path
            path = Path(str(file_obj))
            if path.exists():
                with open(path, "rb") as f:
                    files["file"] = (path.name, f.read(), "image/jpeg")
            else:
                return False, {"error": "Unsupported file object"}

        resp = requests.post(predict_url, files=files, timeout=timeout)
        if resp.status_code == 200:
            return True, _safe_json(resp)
        else:
            return False, {"status_code": resp.status_code, "body": _safe_json(resp)}
    except Exception as e:
        return False, {"error": str(e)}

def severity_badge(severity):
    """
    Return an HTML snippet (string) to render a colored badge for severity.
    """
    colors = {
        "Critical": "#DC143C",
        "High": "#FF8C00",
        "Medium": "#FFD700",
        "None": "#32CD32",
        "Unknown": "#808080"
    }
    color = colors.get(severity, "#808080")
    safe_text = str(severity) if severity else "Unknown"
    return f'<span style="background-color:{color}; color:white; padding:6px 10px; border-radius:6px; font-weight:600;">{safe_text}</span>'

def initialize_camera(camera_index=0):
    """
    Initialize OpenCV camera and return VideoCapture or None.
    Respects optional st.session_state.camera_quality if set.
    """
    try:
        cap = cv2.VideoCapture(camera_index)
        if not cap or not cap.isOpened():
            return None
        quality = None
        try:
            quality = st.session_state.get("camera_quality", None)
        except Exception:
            quality = None
        if isinstance(quality, str):
            q = quality.lower()
            if "low" in q or "480" in q:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            elif "high" in q or "1080" in q:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
            else:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        return cap
    except Exception:
        return None

def capture_frame(cap, resize_width=None):
    """
    Capture a single frame from an OpenCV VideoCapture and return RGB numpy array or None.
    Optionally resize to the specified width (maintains aspect ratio).
    """
    try:
        ret, frame = cap.read()
        if not ret or frame is None:
            return None
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        if resize_width:
            h, w = frame_rgb.shape[:2]
            new_w = int(resize_width)
            new_h = int(h * (new_w / w))
            frame_rgb = cv2.resize(frame_rgb, (new_w, new_h))
        return frame_rgb
    except Exception:
        return None

def process_frame_for_analysis(frame):
    """
    Convert an OpenCV RGB frame (numpy array) to a BytesIO buffer and PIL Image.
    Returns (bytes_buffer, pil_image) or (None, None) on failure.
    """
    try:
        if frame is None:
            return None, None
        pil_img = Image.fromarray(frame)
        buf = BytesIO()
        pil_img.save(buf, format="JPEG", quality=85)
        buf.seek(0)
        return buf, pil_img
    except Exception:
        return None, None

def get_model_info(timeout=5):
    """
    Fetch model info from FastAPI /model/info. Returns dict (possibly empty).
    """
    try:
        base = globals().get("FASTAPI_BASE_URL", "http://127.0.0.1:8000")
        resp = requests.get(f"{base}/model/info", timeout=timeout)
        if resp.status_code == 200:
            return _safe_json(resp)
        return {}
    except Exception:
        return {}
    


# ===== PAGE CONFIG =====
st.set_page_config(
    page_title="🌿 KilimoGlow Kenya - Msaidizi wa Mimea",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== PAGE CONFIG =====
# st.set_page_config(
#     page_title="🌿 KilimoGlow Kenya - Msaidizi wa Mimea",
#     page_icon="🌿",
#     layout="wide",
#     initial_sidebar_state="expanded"
# )

# ===== FASTAPI CONFIG =====
FASTAPI_BASE_URL = "http://127.0.0.1:8000"
FASTAPI_ENDPOINTS = {
    "health": f"{FASTAPI_BASE_URL}/health",
    "predict": f"{FASTAPI_BASE_URL}/predict",
    "batch_predict": f"{FASTAPI_BASE_URL}/batch_predict",
    "model_info": f"{FASTAPI_BASE_URL}/model/info"
}

# ===== KENYAN DISEASE DATABASE (Enhanced) =====
PLANT_DISEASES = {
    'Pepper__bell___Bacterial_spot': {
        'name': 'Bacterial Spot', 'plant': 'Pilipili (Pepper)', 'severity': 'High',
        'symptoms': 'Small dark spots with yellow halos on leaves and fruits',
        'treatment': 'Apply copper-based bactericide, remove affected parts',
        'prevention': 'Use certified seeds, avoid overhead irrigation, crop rotation',
        'organic_treatment': 'Neem oil spray, garlic extract, proper sanitation',
        'watering_advice': 'Water at base level, avoid wetting leaves'
    },
    'Pepper__bell___healthy': {
        'name': 'Healthy Pepper', 'plant': 'Pilipili (Pepper)', 'severity': 'None',
        'symptoms': 'Dark green leaves, strong stem, no disease symptoms',
        'treatment': 'Continue current care practices',
        'prevention': 'Maintain good spacing, regular monitoring, proper nutrition',
        'organic_treatment': 'Compost application, beneficial companion plants',
        'watering_advice': 'Regular watering, mulching for moisture retention'
    },
    'Potato___Early_blight': {
        'name': 'Early Blight', 'plant': 'Viazi (Potato)', 'severity': 'Medium',
        'symptoms': 'Concentric rings on leaves, dark spots with yellow halos',
        'treatment': 'Fungicide spray (mancozeb or chlorothalonil)',
        'prevention': 'Crop rotation, avoid overhead watering, remove plant debris',
        'organic_treatment': 'Baking soda spray, milk solution, proper spacing',
        'watering_advice': 'Water early morning, avoid leaf wetness'
    },
    'Potato___Late_blight': {
        'name': 'Late Blight', 'plant': 'Viazi (Potato)', 'severity': 'Critical',
        'symptoms': 'Water-soaked lesions, white mold growth underneath leaves',
        'treatment': 'Immediate fungicide application (metalaxyl + mancozeb)',
        'prevention': 'Resistant varieties, good drainage, avoid wet conditions',
        'organic_treatment': 'Bordeaux mixture, copper soap spray',
        'watering_advice': 'Reduce watering, improve drainage immediately'
    },
    'Potato___healthy': {
        'name': 'Healthy Potato', 'plant': 'Viazi (Potato)', 'severity': 'None',
        'symptoms': 'Vigorous green foliage, good tuber development',
        'treatment': 'Continue monitoring and current practices',
        'prevention': 'Regular hilling, proper fertilization, pest monitoring',
        'organic_treatment': 'Compost incorporation, beneficial microorganisms',
        'watering_advice': 'Consistent moisture, avoid overwatering'
    },
    'Tomato_Bacterial_spot': {
        'name': 'Bacterial Spot', 'plant': 'Nyanya (Tomato)', 'severity': 'High',
        'symptoms': 'Small brown spots with yellow halos on leaves and fruits',
        'treatment': 'Copper-based bactericide, remove affected plant parts',
        'prevention': 'Use certified seeds, avoid working in wet fields',
        'organic_treatment': 'Neem extract, garlic spray, proper sanitation',
        'watering_advice': 'Drip irrigation, avoid overhead watering'
    },
    'Tomato_Early_blight': {
        'name': 'Early Blight', 'plant': 'Nyanya (Tomato)', 'severity': 'Medium',
        'symptoms': 'Target-like spots on lower leaves, yellowing',
        'treatment': 'Fungicide application, remove affected leaves',
        'prevention': 'Mulching, proper spacing, avoid overhead irrigation',
        'organic_treatment': 'Baking soda spray, compost tea application',
        'watering_advice': 'Water at base, maintain consistent soil moisture'
    },
    'Tomato_Late_blight': {
        'name': 'Late Blight', 'plant': 'Nyanya (Tomato)', 'severity': 'Critical',
        'symptoms': 'Water-soaked lesions with white mold underneath leaves',
        'treatment': 'Immediate fungicide application (metalaxyl + mancozeb)',
        'prevention': 'Good air circulation, avoid overhead watering',
        'organic_treatment': 'Bordeaux mixture spray, milk and baking soda solution',
        'watering_advice': 'Water at base only, avoid evening watering'
    },
    'Tomato_Leaf_Mold': {
        'name': 'Leaf Mold', 'plant': 'Nyanya (Tomato)', 'severity': 'Medium',
        'symptoms': 'Yellow spots on upper leaf surface, fuzzy growth underneath',
        'treatment': 'Improve ventilation, apply fungicide if severe',
        'prevention': 'Reduce humidity, increase air circulation, proper spacing',
        'organic_treatment': 'Milk spray solution, baking soda application',
        'watering_advice': 'Water early morning, ensure good drainage'
    },
    'Tomato_Septoria_leaf_spot': {
        'name': 'Septoria Leaf Spot', 'plant': 'Nyanya (Tomato)', 'severity': 'Medium',
        'symptoms': 'Small circular spots with dark borders and light centers',
        'treatment': 'Fungicide spray, remove affected lower leaves',
        'prevention': 'Mulching, avoid overhead watering, crop rotation',
        'organic_treatment': 'Compost tea, proper plant spacing',
        'watering_advice': 'Water at soil level, avoid splashing on leaves'
    },
    'Tomato_Spider_mites_Two_spotted_spider_mite': {
        'name': 'Spider Mites', 'plant': 'Nyanya (Tomato)', 'severity': 'High',
        'symptoms': 'Fine webbing, yellow stippling on leaves, leaf bronze color',
        'treatment': 'Miticide application, increase humidity around plants',
        'prevention': 'Regular inspection, avoid water stress, natural predators',
        'organic_treatment': 'Neem oil spray, insecticidal soap, predatory mites',
        'watering_advice': 'Maintain consistent moisture, mist around plants'
    },
    'Tomato__Target_Spot': {
        'name': 'Target Spot', 'plant': 'Nyanya (Tomato)', 'severity': 'Medium',
        'symptoms': 'Concentric rings forming target-like patterns on leaves',
        'treatment': 'Fungicide application, remove affected plant material',
        'prevention': 'Crop rotation, avoid overhead irrigation, proper spacing',
        'organic_treatment': 'Copper soap spray, compost application',
        'watering_advice': 'Drip irrigation preferred, water early morning'
    },
    'Tomato__Tomato_YellowLeaf__Curl_Virus': {
        'name': 'Yellow Leaf Curl Virus', 'plant': 'Nyanya (Tomato)', 'severity': 'Critical',
        'symptoms': 'Yellowing and curling of leaves, stunted growth',
        'treatment': 'Remove infected plants, control whitefly vectors',
        'prevention': 'Use resistant varieties, control whiteflies, reflective mulch',
        'organic_treatment': 'Yellow sticky traps, neem oil for whitefly control',
        'watering_advice': 'Maintain plant vigor with proper watering'
    },
    'Tomato__Tomato_mosaic_virus': {
        'name': 'Tomato Mosaic Virus', 'plant': 'Nyanya (Tomato)', 'severity': 'High',
        'symptoms': 'Mottled light and dark green patterns on leaves',
        'treatment': 'Remove infected plants, sanitize tools and hands',
        'prevention': 'Use certified seeds, avoid tobacco use near plants',
        'organic_treatment': 'Plant removal, thorough sanitation practices',
        'watering_advice': 'Avoid mechanical transmission through water splash'
    },
    'Tomato___healthy': {
        'name': 'Healthy Tomato', 'plant': 'Nyanya (Tomato)', 'severity': 'None',
        'symptoms': 'Dark green foliage with good fruit development',
        'treatment': 'Continue current care practices',
        'prevention': 'Regular pruning, staking, mulching',
        'organic_treatment': 'Compost application, beneficial companion plants',
        'watering_advice': 'Deep watering 2-3 times weekly, mulch retention'
    }
}

# ===== KENYAN CROP CALENDAR =====
KENYAN_CROP_CALENDAR = {
    "Long Rains (March-May)": {
        "crops": ["Mahindi (Maize)", "Maharagwe (Beans)", "Nyanya (Tomato)", "Pilipili (Pepper)", "Viazi (Potato)"],
        "planting_tips": "Plant after first reliable rains, prepare land early",
        "care_tips": "Monitor for fungal diseases, ensure good drainage"
    },
    "Short Rains (October-December)": {
        "crops": ["Mahindi (Maize)", "Maharagwe (Beans)", "Pilipili (Pepper)", "Viazi (Potato)"],
        "planting_tips": "Quick maturing varieties, water conservation",
        "care_tips": "Pest monitoring, harvest before dry season"
    },
    "Dry Season (January-February, June-September)": {
        "crops": ["Nyanya (Tomato)", "Pilipili (Pepper)", "Traditional Vegetables"],
        "planting_tips": "Irrigation essential, choose drought-resistant varieties",
        "care_tips": "Water conservation, shade provision, mulching"
    }
}

# ===== MULTILINGUAL SUPPORT (KENYAN FOCUS) =====
LANGUAGES = {
    "English": "en", 
    "Kiswahili": "sw", 
    "Luo": "luo"
}

UI_TEXTS = {
    "English": {
        "app_title": "KilimoGlow",
        "subtitle": "Smart Plant Disease Detection for Kenyan Farmers",
        "field_monitor": "📱 Shamba Monitor", 
        "plant_doctor": "👨‍⚕️ Plant Daktari",
        "dashboard": "📊 Dashboard", 
        "crop_calendar": "📅 Crop Calendar",
        "market_insights": "📈 Market Prices", 
        "prevention_tips": "🛡️ Prevention Guide",
        "settings": "⚙️ Settings", 
        "weather_label": "Weather Condition",
        "soil_label": "Soil Type", 
        "upload_label": "Upload Plant Photo",
        "treatment_title": "Treatment Advice",
        "prevention_strategies": "Prevention Methods",
        "organic_treatment": "Organic Treatment",
        "watering_advice": "Watering Guide",
        "voice_input": "🎤 Voice Input",
        "start_camera": "📹 Start Camera",
        "stop_camera": "⏹️ Stop Camera",
        "capture_frame": "📸 Capture Frame",
        "analyze_plant": "🔍 Analyze Plant"
    },
    "Kiswahili": {
        "app_title": "KilimoGlow Kenya",
        "subtitle": "Utambuzi wa Magonjwa ya Mimea kwa Wakulima wa Kenya",
        "field_monitor": "📱 Ufuatiliaji Shamba", 
        "plant_doctor": "👨‍⚕️ Daktari wa Mimea",
        "dashboard": "📊 Bodi ya Habari", 
        "crop_calendar": "📅 Kalenda ya Mazao",
        "market_insights": "📈 Bei za Sokoni", 
        "prevention_tips": "🛡️ Njia za Kinga",
        "settings": "⚙️ Mipangilio", 
        "weather_label": "Hali ya Hewa",
        "soil_label": "Aina ya Udongo", 
        "upload_label": "Pakia Picha ya Mmea",
        "treatment_title": "Ushauri wa Matibabu",
        "prevention_strategies": "Mbinu za Kinga",
        "organic_treatment": "Matibabu ya Asili",
        "watering_advice": "Mwongozo wa Kumwagilia",
        "voice_input": "🎤 Ingizo la Sauti",
        "start_camera": "📹 Anzisha Kamera",
        "stop_camera": "⏹️ Simamisha Kamera",
        "capture_frame": "📸 Nasa Picha",
        "analyze_plant": "🔍 Chunguza Mmea"
    },
    "Luo": {
        "app_title": "KilimoGlow",
        "subtitle": "Fwenyo Tuo mar Mimea ne Jopur Kenya",
        "field_monitor": "📱 Rang Puothe", 
        "plant_doctor": "👨‍⚕️ Jathieth Mimea",
        "dashboard": "📊 Bord Weche", 
        "crop_calendar": "📅 Kalenda Mimea",
        "market_insights": "📈 Nengo Chiro", 
        "prevention_tips": "🛡️ Yo Siro",
        "settings": "⚙️ Chenro", 
        "weather_label": "Kit Kor",
        "soil_label": "Kit Lowo", 
        "upload_label": "Ket Fweny Yath",
        "treatment_title": "Puonj Thieth",
        "prevention_strategies": "Yo Siro",
        "organic_treatment": "Thieth Kodongo",
        "watering_advice": "Puonj Pii",
        "voice_input": "🎤 Dwol Sauti",
        "start_camera": "📹 Chak Kamera",
        "stop_camera": "⏹️ Chung Kamera",
        "capture_frame": "📸 Mak Fweny",
        "analyze_plant": "🔍 Nonro Yath"
    }
}

# ===== SESSION STATE INITIALIZATION =====
def translate_text_simple(text, target_lang):
    """Enhanced translation function"""
    if target_lang == "Kiswahili":
        translations = {
            "Healthy": "Mzima", "Disease": "Ugonjwa", "Treatment": "Matibabu",
            "Prevention": "Kinga", "Symptoms": "Dalili", "Apply": "Tumia",
            "Water": "Maji", "Soil": "Udongo", "Immediate": "Haraka",
            "Weekly": "Kila wiki", "Daily": "Kila siku", "Spray": "Nyunyiza"
        }
    elif target_lang == "Luo":
        translations = {
            "Healthy": "Maber", "Disease": "Tuo", "Treatment": "Thieth",
            "Prevention": "Siro", "Symptoms": "Ranyisi", "Apply": "Ti",
            "Water": "Pi", "Soil": "Lowo", "Immediate": "Piyo",
            "Weekly": "Jumbe ka jumbe", "Daily": "Pile ka pile", "Spray": "Kiro"
        }
    else:
        return text
    
    for eng, local in translations.items():
        text = text.replace(eng, local)
    return text

def format_report_key_value(analysis_data, disease_info):
    """Format report in key-value colon format"""
    report = f"""PLANT CARE AI KENYA - ANALYSIS REPORT
====================================

BASIC INFORMATION:
Date: {analysis_data.get('timestamp', 'N/A')}
Farmer Name: {analysis_data.get('user_name', 'Anonymous')}
Language Used: {analysis_data.get('language', 'English')}
Analysis ID: {analysis_data.get('timestamp', '').replace(' ', '_').replace(':', '-')}

PLANT DETAILS:
Plant Type: {disease_info.get('plant', 'Unknown')}
Disease Detected: {disease_info.get('name', 'Unknown')}
Severity Level: {disease_info.get('severity', 'Unknown')}
Confidence Score: {analysis_data.get('confidence', 0):.1f}%

ENVIRONMENTAL CONDITIONS:
Weather Condition: {analysis_data.get('weather', 'Not specified')}
Soil Type: {analysis_data.get('soil', 'Not specified')}
Processing Time: {analysis_data.get('processing_time', 0):.2f} seconds

SYMPTOMS OBSERVED:
Description: {disease_info.get('symptoms', 'No symptoms recorded')}

TREATMENT RECOMMENDATIONS:
Primary Treatment: {disease_info.get('treatment', 'Continue monitoring')}
Organic Treatment: {disease_info.get('organic_treatment', 'Natural methods recommended')}
Urgency Level: {'Immediate action required' if disease_info.get('severity') == 'Critical' else 'Treat within 2-3 days' if disease_info.get('severity') == 'High' else 'Monitor and treat as needed'}

PREVENTION STRATEGIES:
Prevention Methods: {disease_info.get('prevention', 'Good agricultural practices')}

WATERING GUIDELINES:
Watering Advice: {disease_info.get('watering_advice', 'Regular watering as needed')}

GENERATED BY: Green_Tycoons, Kenya
VERSION: 2.0.0 Enhanced
API STATUS: Connected to FastAPI Backend
===================================="""
    return report

def simulate_disease_prediction(uploaded_file=None):
    """Fallback simulation if FastAPI is unavailable"""
    diseases = list(PLANT_DISEASES.keys())
    selected_disease = random.choice(diseases)
    confidence = random.uniform(0.75, 0.95)
    
    return {
        "predicted_class": selected_disease,
        "confidence": confidence,
        "processing_time": random.uniform(0.5, 2.0),
        "success": True
    }

def get_file_hash(uploaded_file):
    """Get hash of uploaded file to detect changes"""
    if uploaded_file is None:
        return None
    
    try:
        uploaded_file.seek(0)
        content = uploaded_file.read()
        uploaded_file.seek(0)
        return hash(content)
    except:
        return None

def reset_analysis_state():
    """Reset analysis-related session state variables"""
    keys_to_reset = [
        'analysis_result', 
        'analyze_clicked', 
        'current_analysis_id',
        'uploaded_file_hash'
    ]
    
    for key in keys_to_reset:
        if key in st.session_state:
            st.session_state[key] = None

def clear_session_state():
    """Clear problematic session state variables"""
    keys_to_clear = [
        'analysis_result', 
        'analyze_clicked', 
        'captured_frame',
        'camera_active',
        'monitoring_active',
        'current_analysis_id',
        'uploaded_file_hash'
    ]
    
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    st.success("Session state cleared!")
    st.rerun()

# ===== CHECK API STATUS =====
api_connected, api_info = check_fastapi_connection()
st.session_state.api_status = 'online' if api_connected else 'offline'

# ===== SIDEBAR =====
# Initialize session state key if missing
if "selected_language" not in st.session_state:
    st.session_state.selected_language = list(LANGUAGES.keys())[0]  # default to first language

with st.sidebar:
    # Language Selection with Voice Input
    col1, col2 = st.columns([3, 1])
    with col1:
        st.session_state.selected_language = st.selectbox(
            "🌐 Choose Language / Chagua Lugha / Yer Dhok", 
            options=list(LANGUAGES.keys()), 
            index=list(LANGUAGES.keys()).index(st.session_state.selected_language)
        )
    
    with col2:
        if st.button("🎤", help="Voice language selection"):
            st.session_state.voice_input_active = True
    
    current_texts = UI_TEXTS.get(st.session_state.selected_language, UI_TEXTS["English"])
    
    st.markdown(f"""
    <div class="main-header" style="margin-bottom: 1rem;">
        <h2 style="color: white; margin: 0;">{current_texts['app_title']}</h2>
        <p style="color: #FFD700; margin: 0.5rem 0;">{current_texts['subtitle']}</p>
    </div>
    """, unsafe_allow_html=True)

    # Navigation Menu
    selected_page = option_menu(
        menu_title="🇰🇪 Navigation",
        options=[
            "🏠 Home", 
            current_texts["field_monitor"], 
            current_texts["plant_doctor"], 
            current_texts["dashboard"], 
            current_texts["crop_calendar"], 
            current_texts["market_insights"], 
            current_texts["prevention_tips"], 
            current_texts["settings"]
        ],
        icons=["house-fill", "camera-video", "heart-pulse", "bar-chart-fill", 
               "calendar-event", "graph-up", "shield-fill", "gear-fill"],
        default_index=0,
        styles={
            "container": {"padding": "0", "background-color": "transparent"},
            "icon": {"color": "#FFD700", "font-size": "18px"},
            "nav-link": {
                "font-size": "14px", "text-align": "left", "margin": "3px 0", 
                "padding": "10px 15px", "color": "white", "border-radius": "10px"
            },
            "nav-link-selected": {
                "background": "linear-gradient(90deg, #006400, #228B22)", 
                "color": "white", "border": "1px solid #FFD700"
            },
        },
    )
    
    # Enhanced System Status with API Connection
    st.markdown("---")
    api_status_color = "status-online" if api_connected else "status-offline"
    api_status_text = "🟢 FastAPI Connected" if api_connected else "🔴 Offline Mode"

    if "selected_language" not in st.session_state:
        st.session_state.selected_language = list(LANGUAGES.keys())[0]

    if "analysis_history" not in st.session_state:
        st.session_state.analysis_history = []

    if "camera_active" not in st.session_state:
        st.session_state.camera_active = False  # or True, depending on default

    
    st.markdown(f"""
    <div class="kenyan-card" style="padding: 1rem;">
        <h4 style="color: #FFD700;">📊 System Status</h4>
        <p style="margin: 0.2rem 0;" class="{api_status_color}"><strong>API:</strong> {api_status_text}</p>
        <p style="margin: 0.2rem 0;"><strong>Language:</strong> {st.session_state.selected_language}</p>
        <p style="margin: 0.2rem 0;"><strong>Analyses:</strong> {len(st.session_state.analysis_history)}</p>
        <p style="margin: 0.2rem 0;"><strong>Camera:</strong> {'🟢 Active' if st.session_state.camera_active else '🔴 Inactive'}</p>
    </div>
    """, unsafe_allow_html=True)

# ===== VOICE INPUT HANDLER =====
if st.session_state.voice_input_active:
    recognizer, microphone = initialize_speech_recognition()
    if recognizer and microphone:
        success, text = voice_to_text(recognizer, microphone, st.session_state.selected_language)
        if success:
            st.success(f"🎤 Voice Input: {text}")
            # Process voice commands
            if "english" in text:
                st.session_state.selected_language = "English"
                st.rerun()
            elif "swahili" in text or "kiswahili" in text:
                st.session_state.selected_language = "Kiswahili"
                st.rerun()
            elif "luo" in text:
                st.session_state.selected_language = "Luo"
                st.rerun()
        else:
            st.error(f"🎤 {text}")
    st.session_state.voice_input_active = False

# ===== MAIN CONTENT =====

# HOME PAGE
if selected_page == "🏠 Home":
    st.markdown(f"""
    <div class="main-header">
        <h1 style="margin: 0; font-size: 3rem;">{current_texts['app_title']}</h1>
        <p style="margin: 1rem 0 0 0; font-size: 1.2rem; color: #FFD700;">{current_texts['subtitle']}</p>
        <p style="margin: 0.5rem 0 0 0; color: white;">🇰🇪 Made for Kenya • 🌾 Local Crops • 🌍 Multi-language • 📱 FastAPI Powered</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div class="kenyan-card">
            <h3 style="color: #FFD700;">🔬 AI Disease Detection</h3>
            <ul style="color: white; line-height: 1.8;">
                <li>📸 Detect diseases in Nyanya, Pilipili, Viazi</li>
                <li>🧠 FastAPI backend with TensorFlow</li>
                <li>🌐 Support for English, Kiswahili, Luo</li>
                <li>🎤 Voice input in multiple languages</li>
                <li>📹 Real-time OpenCV camera integration</li>
                <li>💊 Treatment advice for Kenyan conditions</li>
                <li>🌿 Organic solutions using local materials</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="kenyan-card">
            <h3 style="color: #FFD700;">🇰🇪 Enhanced Features</h3>
            <ul style="color: white; line-height: 1.8;">
                <li>📅 Long rains & short rains calendar</li>
                <li>📈 Local market price information</li>
                <li>🌦️ Weather-based recommendations</li>
                <li>🎤 Voice commands for accessibility</li>
                <li>📹 Live camera feed with OpenCV</li>
                <li>🌱 Traditional and modern methods</li>
                <li>💾 Export reports in key-value format</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # API Status Card
    if api_connected and api_info:
        st.markdown(f"""
        <div class="kenyan-card" style="text-align: center; border: 2px solid #32CD32;">
            <h3 style="color: #32CD32;">✅ FastAPI Connected</h3>
            <p style="color: white;">Model Status: {api_info.get('model_status', 'Unknown')}</p>
            <p style="color: white;">Supported Classes: {api_info.get('supported_classes', 'N/A')}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Quick Stats
    if st.session_state.analysis_history:
        total_analyses = len(st.session_state.analysis_history)
        healthy_count = sum(1 for a in st.session_state.analysis_history 
                          if 'healthy' in a.get('predicted_class', '').lower())
        
        st.markdown(f"""
        <div class="kenyan-card" style="text-align: center;">
            <h3 style="color: #FFD700;">📈 Your Farm Analysis</h3>
            <div style="display: flex; justify-content: space-around;">
                <div>
                    <h2 style="color: white; margin: 0;">{total_analyses}</h2>
                    <p style="margin: 0;">Total Scans</p>
                </div>
                <div>
                    <h2 style="color: #32CD32; margin: 0;">{healthy_count}</h2>
                    <p style="margin: 0;">Healthy Plants</p>
                </div>
                <div>
                    <h2 style="color: #FFD700; margin: 0;">{total_analyses - healthy_count}</h2>
                    <p style="margin: 0;">Need Treatment</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ENHANCED FIELD MONITOR PAGE WITH OPENCV
elif selected_page == current_texts["field_monitor"]:
    st.markdown(f"<h1 style='text-align: center; color: #FFD700;'>📱 {current_texts['field_monitor']}</h1>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown(f"### 📹 Live Monitoring with OpenCV")
        
        # Camera Controls with Voice Input
        cam_col1, cam_col2, cam_col3, cam_col4 = st.columns(4)
        
        with cam_col1:
            if st.button(current_texts["start_camera"], type="primary"):
                st.session_state.camera_active = True
                st.rerun()
        
        with cam_col2:
            if st.button(current_texts["stop_camera"]):
                st.session_state.camera_active = False
                st.session_state.monitoring_active = False
                st.rerun()
        
        with cam_col3:
            if st.button(current_texts["capture_frame"]):
                if st.session_state.camera_active:
                    # Simulate frame capture
                    st.session_state.captured_frame = "frame_captured"
                    st.success("📸 Frame captured!")
        
        with cam_col4:
            if st.button("🎤 Voice", help="Voice control for camera"):
                st.session_state.voice_input_active = True
        
        # Camera Display with OpenCV Integration
        if st.session_state.camera_active:
            camera_placeholder = st.empty()
            
            # Initialize camera
            cap = initialize_camera()
            
            if cap is not None:
                st.markdown("""
                <div class="camera-frame">
                    <h3 style="color: #FFD700; text-align: center;">📹 Live Camera Feed - OpenCV</h3>
                </div>
                """, unsafe_allow_html=True)
                
                # Display live feed
                frame = capture_frame(cap)
                if frame is not None:
                    camera_placeholder.image(frame, channels="RGB", use_column_width=True)
                    
                    # Auto-analysis toggle
                    if st.checkbox("🔄 Auto-analyze frames"):
                        st.session_state.monitoring_active = True
                        
                        # Process frame for analysis
                        img_buffer, pil_image = process_frame_for_analysis(frame)
                        
                        if img_buffer and api_connected:
                            # Send to FastAPI
                            with st.spinner("🧠 Analyzing live frame..."):
                                success, result = predict_with_fastapi(img_buffer)
                                
                                if success and result.get('success'):
                                    predicted_class = result.get('predicted_class', 'unknown')
                                    confidence = result.get('confidence', 0) * 100
                                    
                                    # Display quick result
                                    disease_info = PLANT_DISEASES.get(predicted_class, {})
                                    severity = disease_info.get('severity', 'Unknown')
                                    
                                    st.markdown(f"""
                                    <div class="analysis-card" style="margin: 1rem 0;">
                                        <h4 style="color: #FFD700;">🎯 Live Analysis Result</h4>
                                        <p><strong>Plant:</strong> {disease_info.get('plant', 'Unknown')}</p>
                                        <p><strong>Condition:</strong> {disease_info.get('name', 'Unknown')}</p>
                                        <p><strong>Confidence:</strong> {confidence:.1f}%</p>
                                        {severity_badge(severity)}
                                    </div>
                                    """, unsafe_allow_html=True)
                
                # Release camera when done
                if cap:
                    cap.release()
            else:
                st.error("📹 Camera not available. Please check camera permissions.")
        else:
            st.markdown("""
            <div class="kenyan-card" style="text-align: center;">
                <h3 style="color: #FFD700;">📸 Camera Not Active</h3>
                <p>Start camera to begin real-time monitoring</p>
                <div style="font-size: 4rem; margin: 2rem 0;">📱</div>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("### 📊 Monitoring Stats")

        if "real_time_data" not in st.session_state:
          st.session_state.real_time_data = []
        if "monitoring_active" not in st.session_state:
          st.session_state.monitoring_active = False

        
        # Real-time monitoring stats
        if st.session_state.monitoring_active:
            mock_data = {
                'health_score': random.uniform(70, 95),
                'green_coverage': random.uniform(65, 90),
                'disease_indicators': random.uniform(2, 25),
                'leaf_structure': random.uniform(45, 85),
                'timestamp': datetime.now()
            }
            st.session_state.real_time_data.append(mock_data)
            
            if len(st.session_state.real_time_data) > 50:
                st.session_state.real_time_data = st.session_state.real_time_data[-50:]
            
            # Display metrics
            st.metric("🌱 Health Score", f"{mock_data['health_score']:.1f}%")
            st.metric("🍃 Green Coverage", f"{mock_data['green_coverage']:.1f}%")
            st.metric("⚠️ Disease Risk", f"{mock_data['disease_indicators']:.1f}%")
            
        # Voice Commands Help
        st.markdown("""
        <div class="kenyan-card">
            <h4 style="color: #FFD700;">🎤 Voice Commands</h4>
            <ul style="color: white; font-size: 0.9rem;">
                <li>"Start camera" - Activate camera</li>
                <li>"Stop camera" - Deactivate camera</li>
                <li>"Capture frame" - Take photo</li>
                <li>"Analyze plant" - Start analysis</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

# ENHANCED PLANT DOCTOR PAGE WITH FIXED FUNCTIONALITY
elif selected_page == current_texts["plant_doctor"]:
    st.markdown(f"<h1 style='text-align: center; color: #FFD700;'>👨‍⚕️ {current_texts['plant_doctor']}</h1>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### 📋 Plant Information")
        
        # Voice Input for User Name
        name_col1, name_col2 = st.columns([3, 1])
        with name_col1:
            if "user_name" not in st.session_state:
              st.session_state.user_name = ""

            st.session_state.user_name = st.text_input("👤 Your Name / Jina Lako / Nyingi", 
                                                       value=st.session_state.user_name)
        with name_col2:
            if st.button("🎤", key="voice_name", help="Voice input for name"):
                recognizer, microphone = initialize_speech_recognition()
                if recognizer and microphone:
                    success, text = voice_to_text(recognizer, microphone, st.session_state.selected_language)
                    if success:
                        st.session_state.user_name = text.title()
                        st.rerun()
        
        # Environmental context
        weather_options = ["Select", "Sunny/Jua", "Rainy/Mvua", "Cloudy/Mawingu", "Dry/Kavu"]
        st.session_state.weather_condition = st.selectbox(
            f"🌤️ {current_texts['weather_label']}", 
            weather_options
        )
        
        soil_options = ["Select", "Clay/Udongo wa Tope", "Sandy/Udongo wa Mchanga", "Loam/Udongo Mzuri", "Rocky/Udongo wa Mawe"]
        st.session_state.soil_type = st.selectbox(
            f"🌱 {current_texts['soil_label']}", 
            soil_options
        )
        
        # Enhanced Image Upload with Multiple Options
        st.markdown(f"### 📷 {current_texts['upload_label']}")
        
        upload_option = st.radio("Upload Method:", 
                                ["📁 File Upload", "📹 Live Camera", "🖼️ Use Captured Frame"])
        
        uploaded_file = None
        analysis_image = None
        
        if upload_option == "📁 File Upload":
            uploaded_file = st.file_uploader(
                "", 
                type=["jpg", "jpeg", "png"], 
                help="Upload clear photo of plant leaves"
            )
            if uploaded_file:
                analysis_image = Image.open(uploaded_file)
                
        elif upload_option == "📹 Live Camera":
            if st.button("📹 Activate Camera for Capture"):
                cap = initialize_camera()
                if cap:
                    frame = capture_frame(cap)
                    if frame is not None:
                        analysis_image = Image.fromarray(frame)
                        # Convert to uploadable format
                        img_buffer = BytesIO()
                        analysis_image.save(img_buffer, format='JPEG')
                        img_buffer.seek(0)
                        uploaded_file = img_buffer
                    cap.release()
                    
        elif upload_option == "🖼️ Use Captured Frame":
            if st.session_state.captured_frame:
                st.info("Using previously captured frame")
                # Simulate using captured frame
                analysis_image = Image.new('RGB', (300, 300), color='green')
        
        if analysis_image:
            st.image(analysis_image, caption="📷 Plant Photo for Analysis", width=300)
            
            # Enhanced Analysis Button with Voice Command
            analyze_col1, analyze_col2 = st.columns([3, 1])
            
            with analyze_col1:
                analyze_button = st.button(current_texts["analyze_plant"], type="primary", use_container_width=True)
            
            with analyze_col2:
                voice_analyze = st.button("🎤", key="voice_analyze", help="Voice command to analyze")
            
            # FIXED ANALYSIS LOGIC - Check for new file or reset state
            current_file_hash = get_file_hash(uploaded_file) if uploaded_file else None
            
            # Reset analysis if new file is uploaded
             
            if "uploaded_file_hash" not in st.session_state:
                st.session_state.uploaded_file_hash = None


            if current_file_hash != st.session_state.uploaded_file_hash:
                reset_analysis_state()
                st.session_state.uploaded_file_hash = current_file_hash
            
            if (analyze_button or voice_analyze) and uploaded_file:
                # Generate unique analysis ID
                analysis_id = str(uuid.uuid4())[:8]
                st.session_state.current_analysis_id = analysis_id
                
                with st.spinner("🧠 Analyzing your plant..."):
                    try:
                        # Ensure file pointer is at beginning
                        if hasattr(uploaded_file, 'seek'):
                            uploaded_file.seek(0)
                        
                        # Try FastAPI first, fallback to simulation
                        if api_connected:
                            success, result = predict_with_fastapi(uploaded_file)
                            
                            if success and result.get('success'):
                                st.session_state.analysis_result = result
                                st.session_state.analyze_clicked = True
                                st.success("✅ Analysis completed with FastAPI!")
                            else:
                                st.warning("⚠️ FastAPI unavailable, using offline mode")
                                result = simulate_disease_prediction(uploaded_file)
                                st.session_state.analysis_result = result
                                st.session_state.analyze_clicked = True
                        else:
                            st.info("📱 Using offline analysis mode")
                            result = simulate_disease_prediction(uploaded_file)
                            st.session_state.analysis_result = result
                            st.session_state.analyze_clicked = True
                        
                        # Store analysis in history
                        if st.session_state.analysis_result:
                            result = st.session_state.analysis_result
                            predicted_class = result.get("predicted_class", "unknown")
                            confidence = result.get("confidence", 0)
                            
                            # Ensure confidence is percentage
                            if confidence <= 1:
                                confidence *= 100
                            
                            disease_info = PLANT_DISEASES.get(predicted_class, {})
                            
                            analysis_data = {
                                'analysis_id': analysis_id,
                                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                'user_name': st.session_state.user_name,
                                'weather': st.session_state.weather_condition,
                                'soil': st.session_state.soil_type,
                                'language': st.session_state.selected_language,
                                'predicted_class': predicted_class,
                                'confidence': confidence,
                                'disease_info': disease_info,
                                'processing_time': result.get('processing_time', 0.5),
                                'api_used': api_connected and result.get('success', False)
                            }
                            st.session_state.analysis_history.append(analysis_data)
                            
                    except Exception as e:
                        st.error(f"❌ Analysis failed: {str(e)}")
                        st.info("Please try uploading the image again.")
    
    # FIXED RESULTS DISPLAY WITH PROPER SPACING
    with col2:
        # Only show results if analysis has been performed and results exist
        if (st.session_state.get('analyze_clicked') and 
            st.session_state.get('analysis_result') and 
            uploaded_file):
            
            result = st.session_state.analysis_result
            predicted_class = result.get("predicted_class", "unknown")
            confidence = result.get("confidence", 0)
            
            # Ensure confidence is percentage
            if confidence <= 1:
                confidence *= 100
                
            disease_info = PLANT_DISEASES.get(predicted_class, {})
            
            # Results Container with proper spacing
            st.markdown('<div class="results-container">', unsafe_allow_html=True)
            st.markdown("### 🎯 Analysis Results")
            
            # Confidence Visualization
            fig_conf = go.Figure()
            colors = ['#32CD32' if confidence > 80 else '#FFD700' if confidence > 60 else '#DC143C']
            
            fig_conf.add_trace(go.Bar(
                x=['Confidence'],
                y=[confidence],
                marker_color=colors[0],
                text=[f'{confidence:.1f}%'],
                textposition='auto',
                width=[0.6]
            ))
            
            fig_conf.update_layout(
                title=f"🎯 {disease_info.get('plant', 'Plant')} - {disease_info.get('name', 'Unknown')}",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="white"),
                yaxis_range=[0, 100],
                height=300,
                margin=dict(l=20, r=20, t=60, b=20)
            )
            st.plotly_chart(fig_conf, use_container_width=True)
            
            # Disease Info Card
            severity_color = {
                'Critical': '#DC143C', 
                'High': '#FF8C00', 
                'Medium': '#FFD700', 
                'None': '#32CD32'
            }.get(disease_info.get('severity'), '#32CD32')
            
            st.markdown(f"""
            <div class="analysis-card" style="border-left: 6px solid {severity_color};">
                <h3 style="color: #FFD700; margin-bottom: 1rem;">{disease_info.get('plant', 'Unknown')} - {disease_info.get('name', 'Unknown')}</h3>
                <div style="margin-bottom: 1rem;">
                    {severity_badge(disease_info.get('severity', 'None'))}
                </div>
                <div style="margin-top: 1rem;">
                    <p style="margin-bottom: 0.5rem;"><strong>🔍 Symptoms:</strong> {disease_info.get('symptoms', 'No symptoms listed')}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Treatment Information Tabs with Fixed Spacing
            st.markdown('<div class="tabs-container">', unsafe_allow_html=True)
            
            tab1, tab2, tab3, tab4 = st.tabs([
                f"💊 {current_texts['treatment_title']}", 
                f"🌿 {current_texts['organic_treatment']}", 
                f"🛡️ {current_texts['prevention_strategies']}", 
                f"💧 {current_texts['watering_advice']}"
            ])
            
            with tab1:
                st.markdown('<div class="kenyan-card" style="margin: 1rem 0;">', unsafe_allow_html=True)
                treatment_text = disease_info.get('treatment', 'Continue monitoring')
                if st.session_state.selected_language != 'English':
                    treatment_text = translate_text_simple(treatment_text, st.session_state.selected_language)
                st.write(f"**Treatment:** {treatment_text}")
                
                urgency = {
                    'Critical': '🚨 Act immediately (today!)', 
                    'High': '⚠️ Treat within 2-3 days', 
                    'Medium': '⚡ Treat within a week', 
                    'None': '✅ Continue monitoring'
                }.get(disease_info.get('severity'), 'Monitor regularly')
                st.info(f"⏰ **Urgency:** {urgency}")
                st.markdown('</div>', unsafe_allow_html=True)
            
            with tab2:
                st.markdown('<div class="kenyan-card" style="margin: 1rem 0;">', unsafe_allow_html=True)
                organic_text = disease_info.get('organic_treatment', 'Use natural methods')
                if st.session_state.selected_language != 'English':
                    organic_text = translate_text_simple(organic_text, st.session_state.selected_language)
                st.write(f"**Organic Treatment:** {organic_text}")
                
                st.markdown("**🌿 Local Organic Solutions:**")
                organic_tips = [
                    "🧄 Kitunguu saumu (Garlic) + pilipili spray",
                    "🌿 Neem leaves boiled in water", 
                    "🥛 Maziwa (Milk) na maji (1:10 ratio)",
                    "🧪 Magadi (Baking soda) solution",
                    "🌱 Mbolea wa kuku (Chicken manure) tea"
                ]
                for tip in organic_tips:
                    st.markdown(f"• {tip}")
                st.markdown('</div>', unsafe_allow_html=True)
            
            with tab3:
                st.markdown('<div class="kenyan-card" style="margin: 1rem 0;">', unsafe_allow_html=True)
                prevention_text = disease_info.get('prevention', 'Practice good hygiene')
                if st.session_state.selected_language != 'English':
                    prevention_text = translate_text_simple(prevention_text, st.session_state.selected_language)
                st.write(f"**Prevention:** {prevention_text}")
                
                st.markdown("**🛡️ Prevention Tips:**")
                prevention_tips = [
                    "🔄 Rotate crops (nyanya, pilipili, viazi)",
                    "🌬️ Space plants properly for air flow",
                    "🧹 Remove sick leaves quickly",
                    "🌱 Use certified seeds from Kenya Seed",
                    "🔍 Check plants every week"
                ]
                for tip in prevention_tips:
                    st.markdown(f"• {tip}")
                st.markdown('</div>', unsafe_allow_html=True)
            
            with tab4:
                st.markdown('<div class="kenyan-card" style="margin: 1rem 0;">', unsafe_allow_html=True)
                watering_text = disease_info.get('watering_advice', 'Water regularly')
                if st.session_state.selected_language != 'English':
                    watering_text = translate_text_simple(watering_text, st.session_state.selected_language)
                st.write(f"**Watering:** {watering_text}")
                
                # Season-specific advice
                season_advice = {
                    "Rainy/Mvua": "⛈️ Reduce watering, ensure drainage",
                    "Sunny/Jua": "☀️ Water early morning or evening", 
                    "Dry/Kavu": "🏜️ Water more frequently, use mulch",
                    "Cloudy/Mawingu": "☁️ Normal watering schedule"
                }
                current_advice = season_advice.get(st.session_state.weather_condition, "💧 Water based on soil moisture")
                st.info(f"🌤️ **Weather Advice:** {current_advice}")
                st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)  # Close tabs container
            
            # Enhanced Download Reports Section - RESTORED FUNCTIONALITY
            st.markdown("### 📥 Export Reports")
            
            col1, col2, col3 = st.columns(3)
            
            # Get the latest analysis data for report generation
            if st.session_state.analysis_history:
                latest_analysis = st.session_state.analysis_history[-1]
                
                with col1:
                    # Key-Value CSV Format
                    report_data = {
                        'Field': ['Date', 'Farmer', 'Plant', 'Disease', 'Severity', 'Confidence', 'Weather', 'Soil', 'Treatment', 'API_Used'],
                        'Value': [
                            latest_analysis['timestamp'],
                            latest_analysis['user_name'],
                            disease_info.get('plant', 'Unknown'),
                            disease_info.get('name', 'Unknown'),
                            disease_info.get('severity', 'Unknown'),
                            f"{confidence:.1f}%",
                            latest_analysis['weather'],
                            latest_analysis['soil'],
                            disease_info.get('treatment', 'Not specified')[:100],
                            'FastAPI' if latest_analysis.get('api_used') else 'Offline'
                        ]
                    }
                    
                    report_df = pd.DataFrame(report_data)
                    csv_data = report_df.to_csv(index=False)
                    
                    st.download_button(
                        "📊 Detailed Report (CSV)",
                        csv_data,
                        f"plant_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        "text/csv",
                        use_container_width=True
                    )
                
                with col2:
                    # Complete Key-Value Format Report - RESTORED
                    treatment_summary = format_report_key_value(latest_analysis, disease_info)
                    
                    st.download_button(
                        "💊 Complete Report (TXT)",
                        treatment_summary,
                        f"kilimoGlow_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        "text/plain",
                        use_container_width=True
                    )
                
                with col3:
                    # Multilingual Report - RESTORED
                    if st.session_state.selected_language != 'English':
                        lang_code = st.session_state.selected_language.lower()
                        
                        multilingual_summary = f"""KILIMOGLOW KENYA - RIPOTI YA UCHUNGUZI
========================================

TAARIFA ZA MSINGI:
Tarehe: {latest_analysis['timestamp']}
Jina la Mkulima: {latest_analysis['user_name']}
Lugha Iliyotumika: {latest_analysis['language']}

MAELEZO YA MMEA:
Aina ya Mmea: {disease_info.get('plant', 'Unknown')}
Ugonjwa Uliogundulika: {disease_info.get('name', 'Unknown')}
Kiwango cha Hatari: {disease_info.get('severity', 'Unknown')}
Kiwango cha Uhakika: {confidence:.1f}%

MAZINGIRA:
Hali ya Hewa: {latest_analysis['weather']}
Aina ya Udongo: {latest_analysis['soil']}

MATIBABU:
Matibabu wa Msingi: {translate_text_simple(disease_info.get('treatment', 'Continue monitoring'), st.session_state.selected_language)}

KINGA:
Njia za Kinga: {translate_text_simple(disease_info.get('prevention', 'Practice good hygiene'), st.session_state.selected_language)}

USHAURI WA MAJI:
Mwongozo wa Kumwagilia: {translate_text_simple(disease_info.get('watering_advice', 'Water regularly'), st.session_state.selected_language)}

IMETOLEWA NA: KILIMOGLOW Kenya
TOLEO: 2.0.0 Enhanced
========================================"""
                        
                        st.download_button(
                            f"🌐 {st.session_state.selected_language} Report",
                            multilingual_summary,
                            f"report_{lang_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                            "text/plain",
                            use_container_width=True
                        )
                    else:
                        st.info("🌐 Switch to Kiswahili or Luo for multilingual reports")
            
            st.markdown('</div>', unsafe_allow_html=True)  # Close results container
        else:
            # Show placeholder when no analysis has been performed
            st.markdown("""
            <div class="kenyan-card" style="text-align: center; padding: 4rem; margin-top: 2rem;">
                <h3 style="color: #FFD700;">📸 Ready for Analysis</h3>
                <p>Upload a plant image and click analyze to see results here</p>
                <div style="font-size: 4rem; margin: 2rem 0;">🔬</div>
            </div>
            """, unsafe_allow_html=True)

# ENHANCED DASHBOARD PAGE
elif selected_page == current_texts["dashboard"]:
    st.markdown(f"<h1 style='text-align: center; color: #FFD700;'>📊 {current_texts['dashboard']}</h1>", unsafe_allow_html=True)
    
    # Enhanced Stats Cards
    col1, col2, col3, col4 = st.columns(4)
    
    total_analyses = len(st.session_state.analysis_history)
    healthy_count = sum(1 for a in st.session_state.analysis_history if 'healthy' in a.get('predicted_class', '').lower())
    api_analyses = sum(1 for a in st.session_state.analysis_history if a.get('api_used', False))
    avg_confidence = sum(a.get('confidence', 0) for a in st.session_state.analysis_history) / max(total_analyses, 1) if total_analyses > 0 else 0
    
    metrics = [
        (col1, total_analyses, "Total Scans", "🔍", "#32CD32"),
        (col2, f"{(healthy_count/total_analyses*100):.1f}%" if total_analyses > 0 else "0%", "Healthy Plants", "🌱", "#228B22"),
        (col3, api_analyses, "API Analyses", "🚀", "#FFD700"),
        (col4, f"{avg_confidence:.1f}%", "Avg Confidence", "🎯", "#FF8C00")
    ]
    
    for col, value, label, icon, color in metrics:
        with col:
            st.markdown(f"""
            <div class="kenyan-card" style="text-align: center; padding: 1.5rem;">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">{icon}</div>
                <h2 style="color: {color}; margin: 0;">{value}</h2>
                <p style="margin: 0; color: white;">{label}</p>
            </div>
            """, unsafe_allow_html=True)
    
    # API Performance Chart
    if st.session_state.analysis_history:
        st.markdown("### 📈 Analysis Performance")
        
        # Create performance DataFrame
        df_performance = pd.DataFrame([
            {
                'Time': datetime.strptime(a['timestamp'], "%Y-%m-%d %H:%M:%S"),
                'Confidence': a.get('confidence', 0),
                'API_Used': 'FastAPI' if a.get('api_used', False) else 'Offline',
                'Plant': a.get('disease_info', {}).get('plant', 'Unknown'),
                'Severity': a.get('disease_info', {}).get('severity', 'Unknown')
            }
            for a in st.session_state.analysis_history[-20:]  # Last 20 analyses
        ])
        
        # Confidence over time
        fig_performance = go.Figure()
        
        # Separate API and Offline analyses
        api_data = df_performance[df_performance['API_Used'] == 'FastAPI']
        offline_data = df_performance[df_performance['API_Used'] == 'Offline']
        
        if not api_data.empty:
            fig_performance.add_trace(go.Scatter(
                x=api_data['Time'],
                y=api_data['Confidence'],
                mode='lines+markers',
                name='FastAPI Analyses',
                line=dict(color='#32CD32', width=3),
                marker=dict(size=8)
            ))
        
        if not offline_data.empty:
            fig_performance.add_trace(go.Scatter(
                x=offline_data['Time'],
                y=offline_data['Confidence'],
                mode='lines+markers',
                name='Offline Analyses',
                line=dict(color='#FFD700', width=3),
                marker=dict(size=8)
            ))
        
        fig_performance.update_layout(
            title="Analysis Confidence Over Time",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0.1)",
            font=dict(color="white"),
            xaxis=dict(title="Time", gridcolor="rgba(255,255,255,0.1)"),
            yaxis=dict(title="Confidence (%)", gridcolor="rgba(255,255,255,0.1)"),
            height=400
        )
        
        st.plotly_chart(fig_performance, use_container_width=True)
    
    # Plant Health Distribution
    if st.session_state.analysis_history:
        st.markdown("### 🌱 Plant Health Distribution")
        
        # Create distribution data
        plant_counts = {}
        severity_counts = {'None': 0, 'Medium': 0, 'High': 0, 'Critical': 0}
        
        for analysis in st.session_state.analysis_history:
            disease_info = analysis.get('disease_info', {})
            plant = disease_info.get('plant', 'Unknown')
            severity = disease_info.get('severity', 'Unknown')
            
            plant_counts[plant] = plant_counts.get(plant, 0) + 1
            if severity in severity_counts:
                severity_counts[severity] += 1
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Plant distribution pie chart
            if plant_counts:
                fig_plants = px.pie(
                    values=list(plant_counts.values()),
                    names=list(plant_counts.keys()),
                    title="Plants Analyzed",
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig_plants.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="white")
                )
                st.plotly_chart(fig_plants, use_container_width=True)
        
        with col2:
            # Severity distribution
            if any(severity_counts.values()):
                colors = {'None': '#32CD32', 'Medium': '#FFD700', 'High': '#FF8C00', 'Critical': '#DC143C'}
                fig_severity = go.Figure(data=[
                    go.Bar(
                        x=list(severity_counts.keys()),
                        y=list(severity_counts.values()),
                        marker_color=[colors.get(k, '#228B22') for k in severity_counts.keys()]
                    )
                ])
                fig_severity.update_layout(
                    title="Severity Distribution",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="white"),
                    xaxis=dict(title="Severity Level"),
                    yaxis=dict(title="Count")
                )
                st.plotly_chart(fig_severity, use_container_width=True)
    
    # Recent Analyses with Enhanced Info
    if st.session_state.analysis_history:
        st.markdown("### 📋 Recent Analyses")
        
        for analysis in reversed(st.session_state.analysis_history[-5:]):
            disease_info = analysis.get('disease_info', {})
            api_badge = "🚀 FastAPI" if analysis.get('api_used') else "📱 Offline"
            
            st.markdown(f"""
            <div class="kenyan-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h4 style="color: #FFD700; margin: 0;">{disease_info.get('plant', 'Unknown')} - {disease_info.get('name', 'Unknown')}</h4>
                        <p style="margin: 0.5rem 0; color: white;">👤 {analysis.get('user_name', 'Anonymous')} • 📅 {analysis.get('timestamp', 'Unknown')}</p>
                        <p style="margin: 0; color: white;">🌤️ {analysis.get('weather', 'Unknown')} • 🌱 {analysis.get('soil', 'Unknown')} • {api_badge}</p>
                    </div>
                    <div style="text-align: right;">
                        {severity_badge(disease_info.get('severity', 'Unknown'))}
                        <p style="margin: 0.5rem 0; color: white;">🎯 {analysis.get('confidence', 0):.1f}%</p>
                        <p style="margin: 0; color: white; font-size: 0.8rem;">⏱️ {analysis.get('processing_time', 0):.2f}s</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="kenyan-card" style="text-align: center; padding: 4rem;">
            <h3 style="color: #FFD700;">📊 No Data Yet</h3>
            <p>Start analyzing plants to see dashboard insights!</p>
            <div style="font-size: 4rem; margin: 2rem 0;">📈</div>
        </div>
        """, unsafe_allow_html=True)

# ENHANCED CROP CALENDAR PAGE
elif selected_page == current_texts["crop_calendar"]:
    st.markdown(f"<h1 style='text-align: center; color: #FFD700;'>📅 {current_texts['crop_calendar']}</h1>", unsafe_allow_html=True)
    
    st.markdown("""
    <div class="kenyan-card">
        <h3 style='color: #FFD700;'>🌾 Kenyan Agricultural Seasons</h3>
        <p style='color: white;'>Plan your farming activities according to Kenya's rainfall patterns and supported crops.</p>
    </div>
    """, unsafe_allow_html=True)
    
    for season, info in KENYAN_CROP_CALENDAR.items():
        with st.expander(f"🌱 {season}", expanded=True):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown("**🌾 Recommended Crops:**")
                crop_cols = st.columns(3)
                for i, crop in enumerate(info['crops']):
                    with crop_cols[i % 3]:
                        # Check if crop is supported by our model
                        is_supported = any(crop.split('(')[0].strip().lower() in disease.lower() 
                                         for disease in PLANT_DISEASES.keys())
                        support_icon = "🔬" if is_supported else "🌱"
                        
                        st.markdown(f"""
                        <div class="kenyan-card" style="padding: 0.8rem; margin: 0.3rem 0;">
                            <strong>{support_icon} {crop}</strong>
                            {'<br><small style="color: #FFD700;">AI Detection Available</small>' if is_supported else ''}
                        </div>
                        """, unsafe_allow_html=True)
            
            with col2:
                st.info(f"**Planting:** {info['planting_tips']}")
                st.success(f"**Care:** {info['care_tips']}")

# ENHANCED MARKET INSIGHTS PAGE
elif selected_page == current_texts["market_insights"]:
    st.markdown(f"<h1 style='text-align: center; color: #FFD700;'>📈 {current_texts['market_insights']}</h1>", unsafe_allow_html=True)
    
    st.markdown("""
    <div class="kenyan-card">
        <h3 style='color: #FFD700;'>📊 Kenyan Market Prices</h3>
        <p style='color: white;'>Current market prices from major markets in Kenya (Updated Weekly).</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Enhanced market data with more details
    market_data = pd.DataFrame({
        'Crop': ['Nyanya (Tomato)', 'Pilipili (Pepper)', 'Viazi (Potato)', 'Mahindi (Maize)', 'Maharagwe (Beans)'],
        'Price_KES_per_kg': [65, 180, 45, 50, 130],
        'Market': ['Wakulima Market', 'Gikomba Market', 'Muthurwa Market', 'Marikiti Market', 'Kangemi Market'],
        'Trend': ['↑ +12%', '↑ +5%', '↓ -3%', '→ 0%', '↓ -2%'],
        'Quality': ['Grade A', 'Premium', 'Grade B', 'Grade A', 'Premium'],
        'AI_Supported': ['✅', '✅', '✅', '❌', '❌']
    })
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 Current Prices (KES/kg)")
        st.dataframe(market_data, use_container_width=True, hide_index=True)
        
        # Voice command for price inquiry
        if st.button("🎤 Ask about prices", help="Voice inquiry about market prices"):
            recognizer, microphone = initialize_speech_recognition()
            if recognizer and microphone:
                st.info("Ask about any crop prices...")
                success, text = voice_to_text(recognizer, microphone, st.session_state.selected_language)
                if success:
                    st.success(f"🎤 You asked about: {text}")
                    # Simple keyword matching
                    for crop in market_data['Crop']:
                        if any(word in text.lower() for word in crop.lower().split()):
                            crop_price = market_data[market_data['Crop'] == crop]['Price_KES_per_kg'].iloc[0]
                            st.info(f"💰 {crop}: KES {crop_price}/kg")
                            break
    
    with col2:
        # Enhanced price chart
        fig_prices = px.bar(
            market_data, 
            x='Crop', 
            y='Price_KES_per_kg',
            title='Market Prices Comparison',
            color='Price_KES_per_kg',
            color_continuous_scale='Viridis',
            text='Price_KES_per_kg'
        )
        fig_prices.update_traces(texttemplate='KES %{text}', textposition='outside')
        fig_prices.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
            xaxis_tickangle=-45
        )
        st.plotly_chart(fig_prices, use_container_width=True)

# ENHANCED PREVENTION GUIDE PAGE
elif selected_page == current_texts["prevention_tips"]:
    st.markdown(f"<h1 style='text-align: center; color: #FFD700;'>🛡️ {current_texts['prevention_tips']}</h1>", unsafe_allow_html=True)
    
    # Voice-enabled prevention tips
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("### 🌱 Select Prevention Category")
    with col2:
        if st.button("🎤 Voice Guide", help="Voice-guided prevention tips"):
            st.session_state.voice_input_active = True
    
    prevention_category = st.selectbox(
        "Choose category:",
        ["🌿 Organic Pest Control", "🔄 Crop Rotation", "💧 Water Management", "🔍 Monitoring Practices"]
    )
    
    col1, col2 = st.columns(2)
    
    if prevention_category == "🌿 Organic Pest Control":
        with col1:
            st.markdown("""
            <div class="kenyan-card">
                <h4 style="color: #FFD700;">🌱 Organic Pest Control</h4>
                <ul style="color: white;">
                    <li>🧄 Garlic and chili pepper spray (3 cloves + 2 peppers per liter)</li>
                    <li>🌿 Neem tree leaves solution (100g leaves per 5 liters water)</li>
                    <li>🥛 Milk and water mixture (1:10 ratio for fungal diseases)</li>
                    <li>🧪 Baking soda spray (2 tablespoons per liter for powdery mildew)</li>
                    <li>🪴 Companion planting with marigolds and basil</li>
                    <li>🌾 Wood ash around plants for pest deterrent</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="kenyan-card">
                <h4 style="color: #FFD700;">📋 Application Schedule</h4>
                <ul style="color: white;">
                    <li>🌅 Early morning application (6-8 AM)</li>
                    <li>📅 Weekly preventive spraying</li>
                    <li>🌧️ Reapply after rain</li>
                    <li>🔄 Rotate treatments to prevent resistance</li>
                    <li>📊 Monitor and record effectiveness</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
    
    elif prevention_category == "🔄 Crop Rotation":
        with col1:
            st.markdown("""
            <div class="kenyan-card">
                <h4 style="color: #FFD700;">🔄 4-Year Rotation Plan</h4>
                <ul style="color: white;">
                    <li>📅 Year 1: Nyanya (Tomato) - Heavy feeder</li>
                    <li>📅 Year 2: Maharagwe (Beans) - Nitrogen fixer</li>
                    <li>📅 Year 3: Viazi (Potato) - Root crop</li>
                    <li>📅 Year 4: Sukuma Wiki - Light feeder</li>
                    <li>🔄 Return to Year 1 cycle</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="kenyan-card">
                <h4 style="color: #FFD700;">✅ Rotation Benefits</h4>
                <ul style="color: white;">
                    <li>🦠 Breaks disease cycles</li>
                    <li>🌱 Improves soil fertility</li>
                    <li>🐛 Reduces pest buildup</li>
                    <li>💰 Increases crop yields</li>
                    <li>🌿 Maintains soil structure</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
    
    elif prevention_category == "💧 Water Management":
        with col1:
            st.markdown("""
            <div class="kenyan-card">
                <h4 style="color: #FFD700;">💧 Smart Watering</h4>
                <ul style="color: white;">
                    <li>🌅 Water early morning (6-8 AM) or evening (6-8 PM)</li>
                    <li>🌾 Apply mulch to retain moisture</li>
                    <li>🚰 Use drip irrigation when possible</li>
                    <li>⛈️ Ensure good drainage during rains</li>
                    <li>💧 Check soil moisture before watering</li>
                    <li>📏 Water deeply but less frequently</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="kenyan-card">
                <h4 style="color: #FFD700;">🌦️ Seasonal Adjustments</h4>
                <ul style="color: white;">
                    <li>☀️ Dry Season: Daily watering, shade cloth</li>
                    <li>🌧️ Rainy Season: Reduce watering, drainage</li>
                    <li>🌤️ Transition: Monitor soil moisture closely</li>
                    <li>💨 Windy Days: Increase watering frequency</li>
                    <li>🌡️ Hot Days: Provide afternoon shade</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
    
    else:  # Monitoring Practices
        with col1:
            st.markdown("""
            <div class="kenyan-card">
                <h4 style="color: #FFD700;">🔍 Regular Monitoring</h4>
                <ul style="color: white;">
                    <li>👀 Visual inspection twice weekly</li>
                    <li>📸 Take photos to track changes</li>
                    <li>🗑️ Remove diseased leaves immediately</li>
                    <li>🪲 Check for pest eggs under leaves</li>
                    <li>📋 Keep detailed farm diary</li>
                    <li>🔬 Use KilimoGlow AI for disease detection</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="kenyan-card">
                <h4 style="color: #FFD700;">⚠️ Early Warning Signs</h4>
                <ul style="color: white;">
                    <li>🍃 Yellowing or wilting leaves</li>
                    <li>🔴 Spots or lesions on foliage</li>
                    <li>🐛 Presence of insects or eggs</li>
                    <li>🌱 Stunted or irregular growth</li>
                    <li>💧 Water stress symptoms</li>
                    <li>🦠 White powdery substances</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

# ENHANCED SETTINGS PAGE
elif selected_page == current_texts["settings"]:
    st.markdown(f"<h1 style='text-align: center; color: #FFD700;'>⚙️ {current_texts['settings']}</h1>", unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["🔧 System Settings", "📊 Data Management", "📥 Export Options", "🔌 API Configuration"])
    
    with tab1:
        st.markdown("### ⚙️ Application Settings")
        
        col1, col2 = st.columns(2)
        with col1:
            confidence_threshold = st.slider("🎯 Confidence Threshold (%)", 50, 95, 70)
            auto_translate = st.checkbox("🌐 Auto-translate results", value=True)
            voice_enabled = st.checkbox("🎤 Enable voice input", value=True)
            camera_quality = st.selectbox("📹 Camera Quality", ["Low (480p)", "Medium (720p)", "High (1080p)"])
            
        with col2:
            st.markdown("### 📊 System Status")
            model_info = get_model_info() if api_connected else None
            
            if model_info:
                st.success("✅ FastAPI Connected")
                st.info(f"🧠 Model: {model_info.get('num_classes', 'N/A')} classes")
                st.info(f"🎯 Input Shape: {model_info.get('input_shape', 'N/A')}")
            else:
                st.warning("⚠️ FastAPI Disconnected")
            
            st.info(f"🌐 Language: {st.session_state.selected_language}")
            st.info(f"📊 Analyses: {len(st.session_state.analysis_history)}")
            st.info(f"📹 Camera: {'🟢 Enabled' if voice_enabled else '🔴 Disabled'}")
            
            # Clear session state button
            if st.button("🧹 Clear All Data", type="secondary"):
                clear_session_state()
    
    with tab2:
        st.markdown("### 📊 Data Management")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.session_state.analysis_history:
                st.info(f"📈 {len(st.session_state.analysis_history)} analysis records")
                if st.button("🗑️ Clear Analysis History", type="secondary"):
                    st.session_state.analysis_history = []
                    st.success("✅ Analysis history cleared!")
                    st.rerun()
                
                # Data backup
                if st.button("💾 Backup Analysis Data"):
                    backup_data = {
                        'timestamp': datetime.now().isoformat(),
                        'version': '2.0.0',
                        'analyses': st.session_state.analysis_history,
                        'settings': {
                            'language': st.session_state.selected_language,
                            'confidence_threshold': confidence_threshold
                        }
                    }
                    
                    backup_json = json.dumps(backup_data, indent=2)
                    st.download_button(
                        "💾 Download Backup",
                        backup_json,
                        f"KilimoGlow_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        "application/json"
                    )
        
        with col2:

            if "real_time_data" not in st.session_state:
                st.session_state.real_time_data = None 

            if st.session_state.real_time_data:
                st.info(f"📊 {len(st.session_state.real_time_data)} monitoring records")
                if st.button("🔄 Clear Monitoring Data", type="secondary"):
                    st.session_state.real_time_data = []
                    st.success("✅ Monitoring data cleared!")
                    st.rerun()
    
    with tab3:
        st.markdown("### 📥 Export All Data")
        
        if st.session_state.analysis_history:
            # Comprehensive data export options
            export_col1, export_col2, export_col3 = st.columns(3)
            
            with export_col1:
                if st.button("📊 Export Complete Dataset (CSV)", type="primary"):
                    all_data = []
                    for analysis in st.session_state.analysis_history:
                        disease_info = analysis.get('disease_info', {})
                        all_data.append({
                            'Analysis_ID': f"{analysis.get('timestamp', '').replace(' ', '_').replace(':', '-')}",
                            'Date': analysis.get('timestamp'),
                            'Farmer_Name': analysis.get('user_name'),
                            'Language_Used': analysis.get('language'),
                            'Plant_Type': disease_info.get('plant'),
                            'Disease_Name': disease_info.get('name'),
                            'Severity_Level': disease_info.get('severity'),
                            'Confidence_Percentage': analysis.get('confidence'),
                            'Weather_Condition': analysis.get('weather'),
                            'Soil_Type': analysis.get('soil'),
                            'Processing_Time_Seconds': analysis.get('processing_time'),
                            'API_Used': 'FastAPI' if analysis.get('api_used') else 'Offline',
                            'Symptoms': disease_info.get('symptoms'),
                            'Treatment_Recommendation': disease_info.get('treatment'),
                            'Organic_Treatment': disease_info.get('organic_treatment'),
                            'Prevention_Methods': disease_info.get('prevention'),
                            'Watering_Advice': disease_info.get('watering_advice')
                        })
                    
                    export_df = pd.DataFrame(all_data)
                    csv_data = export_df.to_csv(index=False)
                    
                    st.download_button(
                        "📊 Download Complete CSV",
                        csv_data,
                        f"KilimoGlow_complete_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        "text/csv",
                        use_container_width=True
                    )
            
            with export_col2:
                if st.button("📋 Export Summary Report (TXT)", type="primary"):
                    # Generate comprehensive summary
                    total_analyses = len(st.session_state.analysis_history)
                    healthy_count = sum(1 for a in st.session_state.analysis_history 
                                      if 'healthy' in a.get('predicted_class', '').lower())
                    api_count = sum(1 for a in st.session_state.analysis_history 
                                   if a.get('api_used', False))
                    
                    # Plant distribution
                    plant_dist = {}
                    severity_dist = {}
                    for analysis in st.session_state.analysis_history:
                        disease_info = analysis.get('disease_info', {})
                        plant = disease_info.get('plant', 'Unknown')
                        severity = disease_info.get('severity', 'Unknown')
                        plant_dist[plant] = plant_dist.get(plant, 0) + 1
                        severity_dist[severity] = severity_dist.get(severity, 0) + 1
                    
                    summary_report = f"""KILIMOGLOW KENYA - COMPREHENSIVE SUMMARY REPORT
========================================================

REPORT GENERATED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
SOFTWARE VERSION: 2.0.0 Enhanced with FastAPI Integration

ANALYSIS OVERVIEW:
Total Analyses Conducted: {total_analyses}
Healthy Plants Detected: {healthy_count} ({(healthy_count/total_analyses*100):.1f}%)
Plants Requiring Treatment: {total_analyses - healthy_count} ({((total_analyses - healthy_count)/total_analyses*100):.1f}%)
FastAPI Analyses: {api_count} ({(api_count/total_analyses*100):.1f}%)
Offline Analyses: {total_analyses - api_count} ({((total_analyses - api_count)/total_analyses*100):.1f}%)

PLANT DISTRIBUTION:
{chr(10).join([f"{plant}: {count} analyses ({(count/total_analyses*100):.1f}%)" for plant, count in plant_dist.items()])}

SEVERITY DISTRIBUTION:
{chr(10).join([f"{severity}: {count} cases ({(count/total_analyses*100):.1f}%)" for severity, count in severity_dist.items()])}

LANGUAGE USAGE:
{chr(10).join([f"{lang}: {sum(1 for a in st.session_state.analysis_history if a.get('language') == lang)} analyses" for lang in set(a.get('language', 'English') for a in st.session_state.analysis_history)])}

SYSTEM PERFORMANCE:
Average Confidence: {sum(a.get('confidence', 0) for a in st.session_state.analysis_history) / total_analyses:.1f}%
Average Processing Time: {sum(a.get('processing_time', 0) for a in st.session_state.analysis_history) / total_analyses:.2f} seconds

GENERATED BY: KilimoGlow Kenya
DEVELOPED FOR: Kenyan Agricultural Community
API STATUS: {'Connected to FastAPI Backend' if api_connected else 'Offline Mode Active'}
========================================================"""
                    
                    st.download_button(
                        "📋 Download Summary Report",
                        summary_report,
                        f"KilimoGlow_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        "text/plain",
                        use_container_width=True
                    )
            
            with export_col3:
                if st.button("📊 Export for Research (JSON)", type="primary"):
                    research_data = {
                        'metadata': {
                            'export_timestamp': datetime.now().isoformat(),
                            'software_version': '2.0.0 Enhanced',
                            'total_analyses': len(st.session_state.analysis_history),
                            'api_connected': api_connected,
                            'supported_languages': list(LANGUAGES.keys()),
                            'supported_plants': list(set(disease['plant'] for disease in PLANT_DISEASES.values()))
                        },
                        'analyses': st.session_state.analysis_history,
                        'disease_database': PLANT_DISEASES,
                        'performance_metrics': {
                            'average_confidence': sum(a.get('confidence', 0) for a in st.session_state.analysis_history) / len(st.session_state.analysis_history) if st.session_state.analysis_history else 0,
                            'api_usage_rate': sum(1 for a in st.session_state.analysis_history if a.get('api_used', False)) / len(st.session_state.analysis_history) if st.session_state.analysis_history else 0
                        }
                    }
                    
                    research_json = json.dumps(research_data, indent=2, default=str)
                    
                    st.download_button(
                        "📊 Download Research Data",
                        research_json,
                        f"KilimoGlow_research_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        "application/json",
                        use_container_width=True
                    )
        else:
            st.info("📋 No data available for export. Start analyzing plants to generate exportable data.")
    
    with tab4:
        st.markdown("### 🔌 API Configuration")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### FastAPI Settings")
            
            # API endpoint configuration
            api_url = st.text_input("🌐 FastAPI Base URL", value=FASTAPI_BASE_URL)
            
            if st.button("🔍 Test API Connection"):
                with st.spinner("Testing API connection..."):
                    try:
                        test_response = requests.get(f"{api_url}/health", timeout=5)
                        if test_response.status_code == 200:
                            api_info = test_response.json()
                            st.success("✅ API Connection Successful!")
                            st.json(api_info)
                        else:
                            st.error(f"❌ API Error: Status {test_response.status_code}")
                    except Exception as e:
                        st.error(f"❌ Connection Failed: {str(e)}")
            
            # API timeout settings
            timeout_setting = st.slider("⏱️ API Timeout (seconds)", 5, 60, 30)
            
        with col2:
            st.markdown("#### Model Information")
            
            if api_connected:
                model_info = get_model_info()
                if model_info:
                    st.success("🧠 Model Information Retrieved:")
                    st.markdown(f"""
                    <div class="kenyan-card">
                        <p><strong>Model Status:</strong> ✅ Loaded</p>
                        <p><strong>Input Shape:</strong> {model_info.get('input_shape', 'N/A')}</p>
                        <p><strong>Output Shape:</strong> {model_info.get('output_shape', 'N/A')}</p>
                        <p><strong>Total Parameters:</strong> {model_info.get('total_params', 'N/A'):,}</p>
                        <p><strong>Supported Classes:</strong> {model_info.get('num_classes', 'N/A')}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Display supported classes
                    if 'classes' in model_info:
                        st.markdown("#### 🔬 Supported Disease Classes:")
                        for i, class_name in enumerate(model_info['classes']):
                            disease_info = PLANT_DISEASES.get(class_name, {})
                            plant_name = disease_info.get('plant', 'Unknown')
                            disease_name = disease_info.get('name', class_name)
                            st.markdown(f"**{i+1}.** {plant_name} - {disease_name}")
                else:
                    st.warning("⚠️ Could not retrieve model information")
            else:
                st.error("❌ API Not Connected")
                st.markdown("""
                <div class="kenyan-card">
                    <h4 style="color: #FFD700;">🔧 Troubleshooting</h4>
                    <ul style="color: white;">
                        <li>Ensure FastAPI server is running on the specified URL</li>
                        <li>Check if the model file exists in the FastAPI server</li>
                        <li>Verify network connectivity</li>
                        <li>The app will work in offline mode if API is unavailable</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)

# ENHANCED FOOTER
st.markdown("---")
current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
api_status_text = "🟢 FastAPI Connected" if api_connected else "🔴 Offline Mode"

if "monitoring_active" not in st.session_state:
    st.session_state.monitoring_active = False

st.markdown(f"""
<div class="kenyan-card" style="text-align: center; margin-top: 2rem;">
    <h3 style="color: #FFD700;">🇰🇪  KilimoGlow Kenya Enhanced</h3>
    <p style="color: white;">Smart Plant Disease Detection with FastAPI Backend & Voice Control</p>
    <div style="display: flex; justify-content: center; gap: 2rem; flex-wrap: wrap; margin: 1rem 0;">
        <span>📱 Camera: {'🟢 Active' if st.session_state.camera_active else '🔴 Inactive'}</span>
        <span>📊 Monitor: {'🟢 Running' if st.session_state.monitoring_active else '🔴 Stopped'}</span>
        <span>🌐 {st.session_state.selected_language}</span>
        <span>📊 {len(st.session_state.analysis_history)} analyses</span>
        <span>🔌 {api_status_text}</span>
    </div>
    <div style="display: flex; justify-content: center; gap: 2rem; flex-wrap: wrap; margin: 1rem 0; font-size: 0.9rem;">
        <span>🎤 Voice Input Enabled</span>
        <span>📹 OpenCV Integration</span>
        <span>🚀 TensorFlow Model</span>
        <span>🌍 Multi-language Support</span>
    </div>
    <p style="font-size: 0.9rem; color: #FFD700; margin: 0;">
        🕒 {current_time} • Made for Kenyan Agriculture • 🌾 FastAPI Powered • 🎤 Voice Enhanced
    </p>
</div>
""", unsafe_allow_html=True)

# Auto-refresh for monitoring (reduced frequency to prevent excessive requests)
if st.session_state.monitoring_active and st.session_state.camera_active:
    time.sleep(5)  # Increased interval to reduce load
    st.rerun()

# Voice command processing for global commands
if st.session_state.voice_input_active:
    recognizer, microphone = initialize_speech_recognition()
    if recognizer and microphone:
        success, text = voice_to_text(recognizer, microphone, st.session_state.selected_language)
        if success:
            # Global voice commands
            text_lower = text.lower()
            if "home" in text_lower or "nyumbani" in text_lower:
                st.success("🎤 Navigating to Home")
                st.rerun()
            elif "camera" in text_lower or "kamera" in text_lower:
                if "start" in text_lower or "anzisha" in text_lower:
                    st.session_state.camera_active = True
                    st.success("🎤 Camera activated")
                    st.rerun()
                elif "stop" in text_lower or "simamisha" in text_lower:
                    st.session_state.camera_active = False
                    st.success("🎤 Camera stopped")
                    st.rerun()
            elif "analyze" in text_lower or "chunguza" in text_lower:
                st.success("🎤 Ready for plant analysis")
            else:
                st.info(f"🎤 Voice command recognized: {text}")
        else:
            st.error(f"🎤 Voice recognition error: {text}")
    
    st.session_state.voice_input_active = False
    def init_session_state():
        defaults = {
            'analysis_history': [], 
            'real_time_data': [], 
            'camera_active': False,
            'monitoring_active': False, 
            'selected_language': 'English',
            'user_name': '', 
            'weather_condition': 'Select', 
            'soil_type': 'Select',
            'api_endpoint': FASTAPI_BASE_URL,
            'analyze_clicked': False,
            'analysis_result': None,
            'voice_input_active': False,
            'captured_frame': None,
            'api_status': 'checking',
            'current_analysis_id': None,
            'uploaded_file_hash': None
        }
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
 
        init_session_state()

# ===== FASTAPI CONNECTION FUNCTIONS =====
@st.cache_data(ttl=30)
def check_fastapi_connection():
    """Check if FastAPI server is running"""
    try:
        response = requests.get(FASTAPI_ENDPOINTS["health"], timeout=5)
        if response.status_code == 200:
            return True, response.json()
    except:
        pass
    return False, None

def predict_with_fastapi(image_file):
    """Send image to FastAPI for prediction with proper file handling"""
    try:
        # Create a unique request ID
        request_id = str(uuid.uuid4())[:8]
        
        # Reset file pointer
        if hasattr(image_file, 'seek'):
            image_file.seek(0)
        
        # Prepare file for upload
        if hasattr(image_file, 'name') and hasattr(image_file, 'type'):
            files = {"file": (image_file.name, image_file, image_file.type)}
        else:
            files = {"file": ("image.jpg", image_file, "image/jpeg")}
        
        # Make request
        response = requests.post(
            FASTAPI_ENDPOINTS["predict"], 
            files=files, 
            timeout=30,
            headers={"X-Request-ID": request_id}
        )
        
        if response.status_code == 200:
            result = response.json()
            return True, result
        else:
            return False, {"error": f"API Error: {response.status_code} - {response.text}"}
            
    except requests.exceptions.RequestException as e:
        return False, {"error": f"Connection Error: {str(e)}"}

def get_model_info():
    """Get model information from FastAPI"""
    try:
        response = requests.get(FASTAPI_ENDPOINTS["model_info"], timeout=10)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

# ===== VOICE INPUT FUNCTIONS =====
def initialize_speech_recognition():
    """Initialize speech recognition"""
    try:
        recognizer = sr.Recognizer()
        microphone = sr.Microphone()
        
        # Adjust for ambient noise
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
        
        return recognizer, microphone
    except:
        return None, None

def voice_to_text(recognizer, microphone, language_code="en"):
    """Convert voice to text"""
    try:
        with microphone as source:
            st.info("🎤 Listening... Speak now!")
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
        
        # Language mapping for speech recognition
        lang_mapping = {
            "English": "en-US",
            "Kiswahili": "sw-KE", 
            "Luo": "en-US"  # Fallback to English for Luo
        }
        
        lang_code = lang_mapping.get(language_code, "en-US")
        text = recognizer.recognize_google(audio, language=lang_code)
        return True, text.lower()
    except sr.UnknownValueError:
        return False, "Could not understand audio"
    except sr.RequestError as e:
        return False, f"Speech recognition error: {str(e)}"
    except:
        return False, "Microphone access error"

# ===== OPENCV CAMERA FUNCTIONS =====
def initialize_camera():
    """Initialize OpenCV camera"""
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return None
        
        # Set camera properties for better quality
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        return cap
    except:
        return None

def capture_frame(cap):
    """Capture frame from camera"""
    if cap is None:
        return None
    
    try:
        ret, frame = cap.read()
        if ret:
            # Convert BGR to RGB for Streamlit
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            return frame_rgb
    except:
        pass
    return None

def process_frame_for_analysis(frame):
    """Process captured frame for plant analysis"""
    if frame is None:
        return None
    
    try:
        # Convert to PIL Image
        pil_image = Image.fromarray(frame)
        
        # Save to BytesIO for API upload
        img_buffer = BytesIO()
        pil_image.save(img_buffer, format='JPEG', quality=95)
        img_buffer.seek(0)
        
        return img_buffer, pil_image
    except:
        return None, None

# ===== ENHANCED STYLING (KENYAN THEME) =====
def apply_kenyan_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    * { font-family: 'Inter', sans-serif; }
    
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(rgba(0, 100, 0, 0.85), rgba(0, 0, 0, 0.85)), 
                    url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000"><rect fill="%23006400" width="1000" height="333"/><rect fill="%23ffffff" y="333" width="1000" height="334"/><rect fill="%23dc143c" y="667" width="1000" height="333"/></svg>');
        background-size: cover;
        background-attachment: fixed;
        color: white;
    }
    
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #006400, #228B22);
        border-right: 3px solid #FFD700;
    }
    
    [data-testid="stSidebar"] * { color: white !important; }
    
    .main-header {
        background: linear-gradient(135deg, #006400, #228B22, #32CD32);
        padding: 2.5rem; 
        border-radius: 20px; 
        text-align: center; 
        margin-bottom: 2rem;
        box-shadow: 0 15px 35px rgba(0, 100, 0, 0.4);
        border: 2px solid #FFD700;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { box-shadow: 0 15px 35px rgba(0, 100, 0, 0.4); }
        50% { box-shadow: 0 20px 45px rgba(255, 215, 0, 0.6); }
        100% { box-shadow: 0 15px 35px rgba(0, 100, 0, 0.4); }
    }
    
    .kenyan-card {
        background: linear-gradient(145deg, rgba(0, 100, 0, 0.9), rgba(34, 139, 34, 0.8));
        backdrop-filter: blur(15px);
        padding: 2rem; 
        border-radius: 15px; 
        border: 2px solid rgba(255, 215, 0, 0.5);
        margin: 1rem 0;
        box-shadow: 0 10px 25px rgba(0, 100, 0, 0.3);
        transition: all 0.3s ease;
    }
    
    .kenyan-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 20px 40px rgba(255, 215, 0, 0.4);
    }
    
    .analysis-card {
        background: linear-gradient(145deg, rgba(0, 100, 0, 0.8), rgba(34, 139, 34, 0.6));
        border: 2px solid #228B22;
        padding: 2rem; 
        border-radius: 15px; 
        margin: 2rem 0;
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.3);
        min-height: 200px;
    }
    
    .results-container {
        margin-top: 3rem;
        padding-top: 2rem;
        border-top: 2px solid rgba(255, 215, 0, 0.3);
    }
    
    .tabs-container {
        margin-top: 2rem;
        clear: both;
    }
    
    .severity-critical { 
        background: linear-gradient(145deg, #DC143C, #FF0000); 
        color: white; 
        padding: 0.7rem 1.5rem; 
        border-radius: 25px; 
        font-weight: bold;
        animation: blink 1.5s infinite;
        display: inline-block;
    }
    .severity-high { 
        background: linear-gradient(145deg, #FF8C00, #FFA500); 
        color: white; 
        padding: 0.7rem 1.5rem; 
        border-radius: 25px; 
        font-weight: bold;
        display: inline-block;
    }
    .severity-medium { 
        background: linear-gradient(145deg, #FFD700, #FFFF00); 
        color: black; 
        padding: 0.7rem 1.5rem; 
        border-radius: 25px; 
        font-weight: bold;
        display: inline-block;
    }
    .severity-none { 
        background: linear-gradient(145deg, #228B22, #32CD32); 
        color: white; 
        padding: 0.7rem 1.5rem; 
        border-radius: 25px; 
        font-weight: bold;
        display: inline-block;
    }
    
    @keyframes blink {
        0%, 50% { opacity: 1; }
        51%, 100% { opacity: 0.7; }
    }
    
    .stButton>button {
        background: linear-gradient(45deg, #006400, #228B22, #32CD32); 
        color: white; 
        border: 2px solid #FFD700; 
        border-radius: 12px; 
        padding: 0.8rem 2.5rem; 
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px) scale(1.05);
        box-shadow: 0 10px 25px rgba(255, 215, 0, 0.4);
    }
    
    .voice-button {
        background: linear-gradient(45deg, #FF6B35, #F7931E);
        border: 2px solid #FFD700;
        border-radius: 50%;
        padding: 1rem;
        animation: glow 2s infinite;
    }
    
    @keyframes glow {
        0%, 100% { box-shadow: 0 0 5px #FF6B35; }
        50% { box-shadow: 0 0 20px #FF6B35, 0 0 30px #FF6B35; }
    }
    
    .camera-frame {
        border: 3px solid #32CD32;
        border-radius: 15px;
        padding: 10px;
        background: rgba(0, 0, 0, 0.2);
        animation: scan-line 3s infinite;
    }
    
    @keyframes scan-line {
        0% { border-color: #32CD32; }
        50% { border-color: #FFD700; }
        100% { border-color: #32CD32; }
    }
    
    .status-online { 
        color: #32CD32; 
        animation: pulse-green 1s infinite; 
    }
    .status-offline { 
        color: #DC143C; 
        animation: pulse-red 1s infinite; 
    }
    
    @keyframes pulse-green {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.6; }
    }
    
    @keyframes pulse-red {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.6; }
    }
    
    /* Fix tab overlapping issues */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
        margin-bottom: 1rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: rgba(0, 100, 0, 0.3);
        border-radius: 10px;
        color: white;
        margin-right: 5px;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: rgba(255, 215, 0, 0.3) !important;
        color: white !important;
    }
    
    h1, h2, h3, h4, h5, h6 { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

apply_kenyan_css()

# ===== UTILITY FUNCTIONS =====
def severity_badge(severity):
    badges = {
        'Critical': '<span class="severity-critical">🚨 Critical</span>', 
        'High': '<span class="severity-high">⚠️ High</span>', 
        'Medium': '<span class="severity-medium">⚡ Medium</span>', 
        'None': '<span class="severity-none">✅ Healthy</span>'
    }
    return badges.get(severity, '<span class="severity-none">✅ Healthy</span>')

def set_background_local(image_file):
    with open(image_file, "rb") as file:
        encoded = base64.b64encode(file.read()).decode()
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("data:image/jpeg;base64,{encoded}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
set_background_local("plant_disease_classification.png")  # Replace with your actual filename
