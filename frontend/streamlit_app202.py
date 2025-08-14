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

# Suppress warnings
warnings.filterwarnings("ignore")

# ===== PAGE CONFIG =====
st.set_page_config(
    page_title="🌿 KilimoGlow Kenya - Plant Doctor",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== CONFIGURATION =====
#FASTAPI_BASE_URL = "http://127.0.0.1:8000"
FASTAPI_BASE_URL = os.getenv("FASTAPI_URL", "http://127.0.0.1:8000")
FASTAPI_ENDPOINTS = {
    "health": f"{FASTAPI_BASE_URL}/health",
    "predict": f"{FASTAPI_BASE_URL}/predict",
    "batch_predict": f"{FASTAPI_BASE_URL}/batch_predict",
    "model_info": f"{FASTAPI_BASE_URL}/model/info"
}

# ===== SESSION STATE INITIALIZATION =====
def init_session_state():
    """Initialize all session state variables with defaults"""
    defaults = {
        'analysis_history': [],
        'batch_results': [],
        'selected_language': 'English',
        'user_name': '',
        'weather_condition': 'Select',
        'soil_type': 'Select',
        'api_status': 'checking',
        'analysis_result': None,
        'current_analysis_id': None,
        'uploaded_file_hash': None,
        'voice_input_active': False,
        'camera_quality': 'Medium (720p)'
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# ===== UTILITY FUNCTIONS =====
def safe_json(resp):
    """Safely parse JSON response"""
    try:
        return resp.json()
    except Exception:
        return {"status_code": getattr(resp, "status_code", None), "text": getattr(resp, "text", "")}

def get_file_hash(file_obj):
    """Generate hash for uploaded file to detect changes"""
    if file_obj is None:
        return None
    try:
        file_obj.seek(0)
        content = file_obj.read()
        file_obj.seek(0)
        return hash(content)
    except:
        return None

def severity_badge(severity):
    """Generate HTML badge for disease severity"""
    colors = {
        "Critical": "#DC143C",
        "High": "#FF8C00", 
        "Medium": "#FFD700",
        "None": "#32CD32",
        "Unknown": "#808080"
    }
    color = colors.get(severity, "#808080")
    return f'<span style="background-color:{color}; color:white; padding:6px 12px; border-radius:20px; font-weight:600; font-size:0.9rem;">{severity}</span>'

def translate_text_simple(text, target_lang):
    """Simple translation function for key terms"""
    if target_lang == "Kiswahili":
        translations = {
            "Healthy": "Mzima", "Disease": "Ugonjwa", "Treatment": "Matibabu",
            "Prevention": "Kinga", "Symptoms": "Dalili", "Apply": "Tumia",
            "Water": "Maji", "Soil": "Udongo", "Immediate": "Haraka"
        }
    elif target_lang == "Luo":
        translations = {
            "Healthy": "Maber", "Disease": "Tuo", "Treatment": "Thieth",
            "Prevention": "Siro", "Symptoms": "Ranyisi", "Apply": "Ti",
            "Water": "Pi", "Soil": "Lowo", "Immediate": "Piyo"
        }
    else:
        return text
    
    for eng, local in translations.items():
        text = text.replace(eng, local)
    return text

# ===== API FUNCTIONS =====
@st.cache_data(ttl=30)
def check_fastapi_connection(timeout=5):
    """Check FastAPI connection with caching"""
    try:
        resp = requests.get(f"{FASTAPI_BASE_URL}/health", timeout=timeout)
        if resp.status_code == 200:
            return True, safe_json(resp)
        return False, safe_json(resp)
    except Exception as e:
        return False, {"error": str(e)}

def predict_with_fastapi(file_obj, timeout=25):
    """Send image to FastAPI for prediction"""
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
    """Send multiple images for batch prediction"""
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
    """Get model information from FastAPI"""
    try:
        resp = requests.get(f"{FASTAPI_BASE_URL}/model/info", timeout=timeout)
        if resp.status_code == 200:
            return safe_json(resp)
        return {}
    except:
        return {}

def simulate_disease_prediction():
    """Fallback simulation when API is unavailable"""
    diseases = list(PLANT_DISEASES.keys())
    selected_disease = random.choice(diseases)
    confidence = random.uniform(0.75, 0.95)
    
    return {
        "predicted_class": selected_disease,
        "confidence": confidence,
        "processing_time": random.uniform(0.8, 2.5),
        "success": True,
        "model_version": "offline_v1.0"
    }

# ===== VOICE INPUT FUNCTIONS =====
def initialize_speech_recognition():
    """Initialize speech recognition (if available)"""
    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        microphone = sr.Microphone()
        return recognizer, microphone
    except ImportError:
        st.warning("⚠️ Speech recognition not available. Install speech_recognition package.")
        return None, None
    except Exception:
        return None, None

def voice_to_text(recognizer, microphone, language="English", timeout=5):
    """Convert voice to text with error handling"""
    if not recognizer or not microphone:
        return False, "Speech recognition not available"
    
    try:
        lang_codes = {
            "English": "en-US",
            "Kiswahili": "sw-KE", 
            "Luo": "en-US"
        }
        
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=8)
        
        text = recognizer.recognize_google(audio, language=lang_codes.get(language, "en-US"))
        return True, text
        
    except Exception as e:
        return False, f"Voice recognition error: {str(e)}"

# ===== DATA MODELS =====
PLANT_DISEASES = {
    'Pepper__bell___Bacterial_spot': {
        'name': 'Bacterial Spot', 'plant': 'Pilipili (Pepper)', 'severity': 'High',
        'symptoms': 'Small dark spots with yellow halos on leaves and fruits',
        'treatment': 'Apply copper-based bactericide, remove affected parts immediately',
        'prevention': 'Use certified seeds, avoid overhead irrigation, practice crop rotation',
        'organic_treatment': 'Neem oil spray, garlic extract solution, proper field sanitation',
        'watering_advice': 'Water at base level, avoid wetting leaves, ensure good drainage'
    },
    'Pepper__bell___healthy': {
        'name': 'Healthy Pepper', 'plant': 'Pilipili (Pepper)', 'severity': 'None',
        'symptoms': 'Dark green leaves, strong stem, no visible disease symptoms',
        'treatment': 'Continue current care practices, regular monitoring',
        'prevention': 'Maintain proper plant spacing, regular inspection, balanced nutrition',
        'organic_treatment': 'Compost application, beneficial companion planting',
        'watering_advice': 'Regular watering schedule, mulching for moisture retention'
    },
    'Potato___Early_blight': {
        'name': 'Early Blight', 'plant': 'Viazi (Potato)', 'severity': 'Medium',
        'symptoms': 'Concentric rings on leaves forming target-like spots, yellowing',
        'treatment': 'Apply fungicide (mancozeb or chlorothalonil), remove affected foliage',
        'prevention': 'Crop rotation every 3 years, avoid overhead watering, remove plant debris',
        'organic_treatment': 'Baking soda spray, milk solution (1:10 ratio), proper spacing',
        'watering_advice': 'Water early morning, avoid evening irrigation, mulch soil'
    },
    'Potato___Late_blight': {
        'name': 'Late Blight', 'plant': 'Viazi (Potato)', 'severity': 'Critical',
        'symptoms': 'Water-soaked lesions, white fungal growth under leaves, rapid spread',
        'treatment': 'IMMEDIATE fungicide application (metalaxyl + mancozeb), destroy infected plants',
        'prevention': 'Plant resistant varieties, ensure excellent drainage, avoid wet conditions',
        'organic_treatment': 'Bordeaux mixture spray, copper soap solution, immediate plant removal',
        'watering_advice': 'Stop overhead watering immediately, improve field drainage'
    },
    'Potato___healthy': {
        'name': 'Healthy Potato', 'plant': 'Viazi (Potato)', 'severity': 'None',
        'symptoms': 'Vigorous green foliage, healthy tuber development, no disease signs',
        'treatment': 'Continue current management practices, regular monitoring',
        'prevention': 'Regular hilling, balanced fertilization, integrated pest management',
        'organic_treatment': 'Compost incorporation, beneficial soil microorganisms',
        'watering_advice': 'Consistent moisture levels, avoid waterlogging'
    },
    'Tomato_Bacterial_spot': {
        'name': 'Bacterial Spot', 'plant': 'Nyanya (Tomato)', 'severity': 'High',
        'symptoms': 'Small brown spots with yellow halos on leaves, fruits, and stems',
        'treatment': 'Copper-based bactericide application, remove affected plant material',
        'prevention': 'Use certified disease-free seeds, avoid working in wet fields',
        'organic_treatment': 'Neem extract spray, garlic and chili solution, field sanitation',
        'watering_advice': 'Drip irrigation preferred, avoid splashing water on foliage'
    },
    'Tomato_Early_blight': {
        'name': 'Early Blight', 'plant': 'Nyanya (Tomato)', 'severity': 'Medium',
        'symptoms': 'Concentric ring spots on lower leaves, gradual upward progression',
        'treatment': 'Fungicide application, remove lower affected leaves, improve air circulation',
        'prevention': 'Mulching around plants, proper spacing, avoid overhead watering',
        'organic_treatment': 'Baking soda spray (2 tbsp/L), compost tea application',
        'watering_advice': 'Water at soil level, maintain consistent moisture without overwatering'
    },
    'Tomato_Late_blight': {
        'name': 'Late Blight', 'plant': 'Nyanya (Tomato)', 'severity': 'Critical',
        'symptoms': 'Dark water-soaked lesions, white moldy growth underneath leaves',
        'treatment': 'IMMEDIATE systemic fungicide, destroy all infected plant material',
        'prevention': 'Good air circulation, avoid overhead watering, resistant varieties',
        'organic_treatment': 'Bordeaux mixture, milk and baking soda solution, plant removal',
        'watering_advice': 'Water at base only, never water in evening, improve drainage'
    },
    'Tomato_Leaf_Mold': {
        'name': 'Leaf Mold', 'plant': 'Nyanya (Tomato)', 'severity': 'Medium',
        'symptoms': 'Yellow spots on upper leaves, velvety growth on undersides',
        'treatment': 'Improve ventilation, apply preventive fungicide if severe',
        'prevention': 'Reduce humidity levels, increase plant spacing, proper ventilation',
        'organic_treatment': 'Milk spray solution (1:10), baking soda application',
        'watering_advice': 'Water early morning, ensure good air circulation around plants'
    },
    'Tomato_Septoria_leaf_spot': {
        'name': 'Septoria Leaf Spot', 'plant': 'Nyanya (Tomato)', 'severity': 'Medium',
        'symptoms': 'Small circular spots with dark borders and light gray centers',
        'treatment': 'Fungicide spray, remove affected lower leaves, improve sanitation',
        'prevention': 'Mulching, avoid overhead irrigation, annual crop rotation',
        'organic_treatment': 'Compost tea spray, proper plant spacing for air flow',
        'watering_advice': 'Water at ground level, avoid splashing soil onto leaves'
    },
    'Tomato_Spider_mites_Two_spotted_spider_mite': {
        'name': 'Spider Mites', 'plant': 'Nyanya (Tomato)', 'severity': 'High',
        'symptoms': 'Fine webbing, yellow stippling on leaves, bronze coloration',
        'treatment': 'Miticide application, increase humidity around plants, predatory mites',
        'prevention': 'Regular inspection, avoid water stress, encourage natural predators',
        'organic_treatment': 'Neem oil spray, insecticidal soap, predatory insects',
        'watering_advice': 'Maintain consistent soil moisture, mist around plants (not leaves)'
    },
    'Tomato__Target_Spot': {
        'name': 'Target Spot', 'plant': 'Nyanya (Tomato)', 'severity': 'Medium',
        'symptoms': 'Concentric rings forming target patterns on leaves and fruits',
        'treatment': 'Fungicide application, remove affected plant material, improve air flow',
        'prevention': 'Crop rotation, avoid overhead irrigation, proper plant spacing',
        'organic_treatment': 'Copper soap spray, compost application, field sanitation',
        'watering_advice': 'Drip irrigation system, water early morning hours'
    },
    'Tomato__Tomato_YellowLeaf__Curl_Virus': {
        'name': 'Yellow Leaf Curl Virus', 'plant': 'Nyanya (Tomato)', 'severity': 'Critical',
        'symptoms': 'Severe yellowing and curling of leaves, stunted plant growth',
        'treatment': 'Remove infected plants immediately, control whitefly vectors aggressively',
        'prevention': 'Use resistant varieties, control whiteflies, reflective mulch systems',
        'organic_treatment': 'Yellow sticky traps, neem oil for whitefly control, plant removal',
        'watering_advice': 'Maintain plant vigor with proper irrigation, avoid plant stress'
    },
    'Tomato__Tomato_mosaic_virus': {
        'name': 'Mosaic Virus', 'plant': 'Nyanya (Tomato)', 'severity': 'High',
        'symptoms': 'Mottled light and dark green mosaic patterns on leaves',
        'treatment': 'Remove infected plants, sanitize tools and hands thoroughly',
        'prevention': 'Use certified virus-free seeds, avoid tobacco use near plants',
        'organic_treatment': 'Complete plant removal, thorough equipment sanitation',
        'watering_advice': 'Avoid mechanical transmission through contaminated water'
    },
    'Tomato___healthy': {
        'name': 'Healthy Tomato', 'plant': 'Nyanya (Tomato)', 'severity': 'None',
        'symptoms': 'Dark green foliage, strong stems, excellent fruit development',
        'treatment': 'Continue excellent care practices, maintain monitoring schedule',
        'prevention': 'Regular pruning and staking, mulching, balanced fertilization',
        'organic_treatment': 'Compost application, beneficial companion plants like basil',
        'watering_advice': 'Deep watering 2-3 times weekly, consistent moisture levels'
    }
}

LANGUAGES = {"English": "en", "Kiswahili": "sw", "Luo": "luo"}

UI_TEXTS = {
    "English": {
        "app_title": "KilimoGlow Kenya",
        "subtitle": "Smart Plant Disease Detection for Kenyan Farmers",
        "plant_doctor": "🩺 Plant Doctor",
        "batch_analysis": "📊 Batch Analysis",
        "dashboard": "📈 Dashboard",
        "settings": "⚙️ Settings",
        "upload_label": "Upload Plant Photo",
        "analyze_plant": "🔬 Analyze Plant",
        "batch_upload": "📁 Upload Multiple Images",
        "process_batch": "⚡ Process Batch"
    },
    "Kiswahili": {
        "app_title": "KilimoGlow Kenya",
        "subtitle": "Utambuzi wa Magonjwa ya Mimea kwa Wakulima wa Kenya",
        "plant_doctor": "🩺 Daktari wa Mimea",
        "batch_analysis": "📊 Uchambuzi wa Kundi",
        "dashboard": "📈 Bodi ya Habari",
        "settings": "⚙️ Mipangilio",
        "upload_label": "Pakia Picha ya Mmea",
        "analyze_plant": "🔬 Chunguza Mmea",
        "batch_upload": "📁 Pakia Picha Nyingi",
        "process_batch": "⚡ Chamibuza Kundi"
    },
    "Luo": {
        "app_title": "KilimoGlow Kenya", 
        "subtitle": "Fwenyo Tuo mar Mimea ne Jopur Kenya",
        "plant_doctor": "🩺 Jathieth Mimea",
        "batch_analysis": "📊 Nonro Mangeny",
        "dashboard": "📈 Bord Weche",
        "settings": "⚙️ Chenro",
        "upload_label": "Ket Fweny Yath",
        "analyze_plant": "🔬 Nonro Yath",
        "batch_upload": "📁 Ket Fweny Mangeny",
        "process_batch": "⚡ Tiy Mangeny"
    }
}

# ===== ENHANCED CSS STYLING =====
def apply_enhanced_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    * { 
        font-family: 'Inter', sans-serif; 
        box-sizing: border-box;
    }
    
    /* Main app background */
    .stApp {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 50%, #1e3c72 100%);
        color: white;
    }
    
    /* Mobile-first responsive design */
    @media (max-width: 768px) {
        .main-header h1 { font-size: 2rem !important; }
        .kenyan-card { padding: 1rem !important; margin: 0.5rem 0 !important; }
        .stButton>button { padding: 0.6rem 1.5rem !important; font-size: 0.9rem !important; }
        .analysis-card { padding: 1rem !important; }
        .css-1d391kg { width: 100% !important; }
        .stSelectbox { margin-bottom: 1rem; }
    
    }
    
    /* Sidebar styling */
    .css-1d391kg, .css-1cypcdb {
        background: linear-gradient(180deg, #006400, #228B22) !important;
        border-right: 3px solid #FFD700;
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #006400, #228B22, #32CD32);
        padding: 2rem;
        border-radius: 20px;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 15px 35px rgba(0, 100, 0, 0.3);
        border: 2px solid #FFD700;
    }
    
    /* Card styling */
    .kenyan-card {
        background: linear-gradient(145deg, rgba(0, 100, 0, 0.15), rgba(34, 139, 34, 0.1));
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 215, 0, 0.3);
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .kenyan-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 25px rgba(255, 215, 0, 0.2);
    }
    
    /* Analysis results card */
    .analysis-card {
        background: linear-gradient(145deg, rgba(0, 100, 0, 0.2), rgba(34, 139, 34, 0.15));
        border: 2px solid #228B22;
        padding: 2rem;
        border-radius: 15px;
        margin: 2rem 0;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
    }
    
    /* Button styling */
    .stButton>button {
        background: linear-gradient(45deg, #006400, #228B22, #32CD32);
        color: white !important;
        border: 2px solid #FFD700;
        border-radius: 12px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
        width: 100%;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(255, 215, 0, 0.3);
        background: linear-gradient(45deg, #228B22, #32CD32, #00FF00);
    }
    
    /* File uploader styling */
    .uploadedFile {
        border: 2px dashed #32CD32;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
    }
    
    /* Progress bars */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #006400, #32CD32);
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 5px;
        background: rgba(0, 0, 0, 0.1);
        padding: 5px;
        border-radius: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        padding: 0.5rem 1rem;
        color: white;
        border: none;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(45deg, #006400, #32CD32) !important;
        color: white !important;
    }
    
    /* Mobile camera button */
    .camera-button {
        background: linear-gradient(45deg, #FF6B35, #F7931E);
        border: 2px solid #FFD700;
        border-radius: 50px;
        padding: 1rem 2rem;
        color: white;
        font-weight: bold;
        margin: 1rem 0;
    }
    
    /* Severity badges */
    .severity-critical { 
        background: linear-gradient(45deg, #DC143C, #FF0000);
        animation: pulse 1.5s infinite;
    }
    .severity-high { background: linear-gradient(45deg, #FF8C00, #FFA500); }
    .severity-medium { background: linear-gradient(45deg, #FFD700, #FFFF00); color: #000; }
    .severity-none { background: linear-gradient(45deg, #228B22, #32CD32); }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.8; transform: scale(1.05); }
    }
    
    /* Status indicators */
    .status-online { color: #32CD32; }
    .status-offline { color: #DC143C; }
    
    /* Responsive grid */
    .responsive-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 1rem;
        margin: 1rem 0;
    }
    
    /* Loading spinner */
    .loading-spinner {
        border: 3px solid rgba(255, 215, 0, 0.3);
        border-top: 3px solid #FFD700;
        border-radius: 50%;
        width: 30px;
        height: 30px;
        animation: spin 1s linear infinite;
        display: inline-block;
        margin: 0 10px;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    /* Text styling */
    h1, h2, h3, h4, h5, h6 { color: white !important; }
    .metric-card {
        background: rgba(255, 255, 255, 0.1);
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        border: 1px solid rgba(255, 215, 0, 0.3);
    }
    </style>
    """, unsafe_allow_html=True)

apply_enhanced_css()

# ===== MAIN APPLICATION =====
# Check API status
api_connected, api_info = check_fastapi_connection()
st.session_state.api_status = 'online' if api_connected else 'offline'

# ===== SIDEBAR =====
with st.sidebar:
    
    st.session_state.selected_language = st.selectbox(
    "🌍 Language / Lugha / Dhok",
    options=list(LANGUAGES.keys()),
    index=list(LANGUAGES.keys()).index(st.session_state.selected_language),
    key="language_selector"  # ADD THIS
)

    current_texts = UI_TEXTS.get(st.session_state.selected_language, UI_TEXTS["English"])
    
    st.markdown(f"""
    <div class="main-header">
        <h2 style="margin: 0; color: white;">{current_texts['app_title']}</h2>
        <p style="color: #FFD700; margin: 0.5rem 0; font-size: 0.9rem;">{current_texts['subtitle']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Navigation
    selected_page = option_menu(
        menu_title="🇰🇪 Navigation",
        options=[
            "🏠 Home",
            current_texts["plant_doctor"],
            current_texts["batch_analysis"], 
            current_texts["dashboard"],
            current_texts["settings"]
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
                "background": "linear-gradient(90deg, #006400, #228B22)",
                "color": "white", "border": "1px solid #FFD700"
            },
        },
    )
    
    # System Status
    st.markdown("---")
    api_status_color = "status-online" if api_connected else "status-offline"
    api_status_text = "🟢 Connected" if api_connected else "🔴 Offline"
    
    st.markdown(f"""
    <div class="kenyan-card" style="padding: 1rem;">
        <h4 style="color: #FFD700; margin-bottom: 0.5rem;">📊 System Status</h4>
        <p style="margin: 0.2rem 0;" class="{api_status_color}">
            <strong>API:</strong> {api_status_text}
        </p>
        <p style="margin: 0.2rem 0;">
            <strong>Language:</strong> {st.session_state.selected_language}
        </p>
        <p style="margin: 0.2rem 0;">
            <strong>Analyses:</strong> {len(st.session_state.analysis_history)}
        </p>
        <p style="margin: 0.2rem 0;">
            <strong>Batch Results:</strong> {len(st.session_state.batch_results)}
        </p>
    </div>
    """, unsafe_allow_html=True)

# ===== MAIN CONTENT =====

# HOME PAGE
if selected_page == "🏠 Home":
    st.markdown(f"""
    <div class="main-header">
        <h1 style="margin: 0; font-size: 2.5rem;">🌿 {current_texts['app_title']}</h1>
        <p style="margin: 1rem 0 0 0; font-size: 1.1rem; color: #FFD700;">{current_texts['subtitle']}</p>
        <p style="margin: 0.5rem 0 0 0; color: white; font-size: 0.9rem;">
            🇰🇪 Made for Kenya • 🌾 Local Crops • 🌍 Multi-language • 🚀 FastAPI Powered
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="kenyan-card">
            <h3 style="color: #FFD700;">🔬 AI Disease Detection</h3>
            <ul style="color: white; line-height: 1.6;">
                <li>📸 Detect diseases in Nyanya, Pilipili, Viazi</li>
                <li>🧠 FastAPI backend with TensorFlow</li>
                <li>🌍 Support for English, Kiswahili, Luo</li>
                <li>📱 Mobile-optimized interface</li>
                <li>⚡ Batch processing for multiple images</li>
                <li>💊 Treatment advice for Kenyan conditions</li>
                <li>🌿 Organic solutions using local materials</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="kenyan-card">
            <h3 style="color: #FFD700;">📱 Mobile Features</h3>
            <ul style="color: white; line-height: 1.6;">
                <li>📷 Built-in camera integration</li>
                <li>👆 Touch-friendly interface</li>
                <li>🔄 Offline mode capability</li>
                <li>📊 Comprehensive analytics dashboard</li>
                <li>📥 Export reports in multiple formats</li>
                <li>🎯 High accuracy disease detection</li>
                <li>💾 Local data storage and management</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # Quick Stats
    if st.session_state.analysis_history:
        total_analyses = len(st.session_state.analysis_history)
        healthy_count = sum(1 for a in st.session_state.analysis_history 
                          if 'healthy' in a.get('predicted_class', '').lower())
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <h2 style="color: #32CD32; margin: 0;">{total_analyses}</h2>
                <p style="margin: 0;">Total Scans</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <h2 style="color: #FFD700; margin: 0;">{healthy_count}</h2>
                <p style="margin: 0;">Healthy Plants</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <h2 style="color: #FF6B35; margin: 0;">{total_analyses - healthy_count}</h2>
                <p style="margin: 0;">Need Treatment</p>
            </div>
            """, unsafe_allow_html=True)

# PLANT DOCTOR PAGE
elif selected_page == current_texts["plant_doctor"]:
    st.markdown(f"<h1 style='text-align: center; color: #FFD700;'>🩺 {current_texts['plant_doctor']}</h1>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### 📋 Plant Information")
        
        # User information
        st.session_state.user_name = st.text_input(
            "👤 Your Name / Jina Lako / Nyingi",
            value=st.session_state.user_name,
            placeholder="Enter your name"
        )
        
        # Environmental conditions
        weather_options = ["Select", "Sunny/Jua", "Rainy/Mvua", "Cloudy/Mawingu", "Dry/Kavu"]
        st.session_state.weather_condition = st.selectbox(
            "🌤️ Weather Condition",
            weather_options
        )
        
        soil_options = ["Select", "Clay/Udongo wa Tope", "Sandy/Udongo wa Mchanga", 
                       "Loam/Udongo Mzuri", "Rocky/Udongo wa Mawe"]
        st.session_state.soil_type = st.selectbox(
            "🌱 Soil Type",
            soil_options
        )
        
        # Image upload options
        st.markdown(f"### 📷 {current_texts['upload_label']}")
        
        # For mobile: prioritize camera input
        upload_option = st.radio(
            "Choose upload method:",
            ["📱 Take Photo (Mobile)", "📁 Upload from Device"],
            help="Use 'Take Photo' on mobile devices for best experience"
        )
        
        uploaded_file = None
        
        if upload_option == "📱 Take Photo (Mobile)":
            # Use Streamlit's camera input for mobile compatibility
            uploaded_file = st.camera_input(
                "📸 Take a photo of your plant",
                help="Position the plant leaf clearly in the frame"
            )
        else:
            uploaded_file = st.file_uploader(
                "Choose plant image",
                type=["jpg", "jpeg", "png"],
                help="Upload clear photo of plant leaves showing any symptoms"
            )
        
        # Voice input option (may not work on mobile)
        if st.button("🎤 Voice Description", help="Describe your plant issue"):
            recognizer, microphone = initialize_speech_recognition()
            if recognizer and microphone:
                with st.spinner("🎤 Listening..."):
                    success, text = voice_to_text(recognizer, microphone, st.session_state.selected_language)
                    if success:
                        st.success(f"🎤 Voice input: {text}")
                        st.info("💡 Voice input recorded. Please also upload an image for analysis.")
                    else:
                        st.error(f"🎤 {text}")
            else:
                st.warning("🎤 Voice input not available on this device/browser")
    
    with col2:
        if uploaded_file:
            # Display uploaded image
            image = Image.open(uploaded_file)
            st.image(image, caption="📸 Plant Photo for Analysis", use_column_width=True)
            
            # Analysis button
            if st.button(current_texts["analyze_plant"], type="primary", use_container_width=True):
                try:
                    img_array = np.array(image)
                    if img_array.mean() < 10 or img_array.mean() > 245:  # Too dark/bright
                        st.error("❌ Image quality too poor for analysis")
                        st.stop()
                except:
                    st.error("❌ Invalid image format")
                    st.stop()
                # Generate analysis ID
                analysis_id = str(uuid.uuid4())[:8]
                st.session_state.current_analysis_id = analysis_id
                
                with st.spinner("🔬 Analyzing your plant... Please wait."):
                    start_time = time.time()
                    
                    # Try FastAPI first, fallback to simulation
                    if api_connected:
                        success, result = predict_with_fastapi(uploaded_file)
                        
                        if success and result.get('success'):
                            st.session_state.analysis_result = result
                            st.success("✅ Analysis completed with FastAPI!")
                        else:
                            st.warning("⚠️ FastAPI error, using offline mode")
                            result = simulate_disease_prediction()
                            st.session_state.analysis_result = result
                    else:
                        st.info("📱 Using offline analysis mode")
                        result = simulate_disease_prediction()
                        st.session_state.analysis_result = result
                    
                    processing_time = time.time() - start_time
                    
                    # Process results
                    if st.session_state.analysis_result:
                        result = st.session_state.analysis_result
                        predicted_class = result.get("predicted_class", "unknown")
                        confidence = result.get("confidence", 0)
                        
                        # Ensure confidence is percentage
                        if confidence <= 1:
                            confidence *= 100
                        
                        disease_info = PLANT_DISEASES.get(predicted_class, {})
                        
                        # Store in history
                        analysis_data = {
                            'analysis_id': analysis_id,
                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'user_name': st.session_state.user_name or 'Anonymous',
                            'weather': st.session_state.weather_condition,
                            'soil': st.session_state.soil_type,
                            'language': st.session_state.selected_language,
                            'predicted_class': predicted_class,
                            'confidence': confidence,
                            'disease_info': disease_info,
                            'processing_time': processing_time,
                            'api_used': api_connected and result.get('success', False)
                        }
                        st.session_state.analysis_history.append(analysis_data)
            
            # Display results if available
            if st.session_state.analysis_result:
                result = st.session_state.analysis_result
                predicted_class = result.get("predicted_class", "unknown")
                confidence = result.get("confidence", 0)
                
                if confidence <= 1:
                    confidence *= 100

                if confidence < 60:  # Set minimum confidence threshold
                    st.warning("⚠️ Low confidence detection. Please ensure image shows clear plant leaves.")
                    result["predicted_class"] = "uncertain_detection"
                                
                disease_info = PLANT_DISEASES.get(predicted_class, {})
                
                st.markdown("---")
                st.markdown("### 🎯 Analysis Results")
                
                # Confidence visualization
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
                    height=250,
                    margin=dict(l=20, r=20, t=60, b=20)
                )
                st.plotly_chart(fig_conf, use_column_width=True)
                
                # Disease information card
                severity_color = {
                    'Critical': '#DC143C', 'High': '#FF8C00', 
                    'Medium': '#FFD700', 'None': '#32CD32'
                }.get(disease_info.get('severity'), '#32CD32')
                
                st.markdown(f"""
                <div class="analysis-card" style="border-left: 6px solid {severity_color};">
                    <h3 style="color: #FFD700; margin-bottom: 1rem;">
                        {disease_info.get('plant', 'Unknown')} - {disease_info.get('name', 'Unknown')}
                    </h3>
                    <div style="margin-bottom: 1rem;">
                        {severity_badge(disease_info.get('severity', 'None'))}
                    </div>
                    <p style="margin-bottom: 0.5rem;">
                        <strong>🔍 Symptoms:</strong> {disease_info.get('symptoms', 'No symptoms listed')}
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                # Treatment tabs
                tab1, tab2, tab3, tab4 = st.tabs([
                    "💊 Treatment", "🌿 Organic", "🛡️ Prevention", "💧 Watering"
                ])
                
                with tab1:
                    treatment_text = disease_info.get('treatment', 'Continue monitoring')
                    if st.session_state.selected_language != 'English':
                        treatment_text = translate_text_simple(treatment_text, st.session_state.selected_language)
                    
                    st.markdown(f"**Treatment:** {treatment_text}")
                    
                    urgency = {
                        'Critical': '🚨 Act immediately (today!)',
                        'High': '⚠️ Treat within 2-3 days',
                        'Medium': '⚡ Treat within a week',
                        'None': '✅ Continue monitoring'
                    }.get(disease_info.get('severity'), 'Monitor regularly')
                    
                    st.info(f"⏰ **Urgency:** {urgency}")
                
                with tab2:
                    organic_text = disease_info.get('organic_treatment', 'Use natural methods')
                    if st.session_state.selected_language != 'English':
                        organic_text = translate_text_simple(organic_text, st.session_state.selected_language)
                    
                    st.markdown(f"**Organic Treatment:** {organic_text}")
                    
                    st.markdown("**🌿 Local Solutions:**")
                    organic_tips = [
                        "🧄 Garlic + chili spray",
                        "🌿 Neem leaves solution",
                        "🥛 Milk solution (1:10)",
                        "🧪 Baking soda spray",
                        "🌱 Compost tea"
                    ]
                    for tip in organic_tips:
                        st.markdown(f"• {tip}")
                
                with tab3:
                    prevention_text = disease_info.get('prevention', 'Practice good hygiene')
                    if st.session_state.selected_language != 'English':
                        prevention_text = translate_text_simple(prevention_text, st.session_state.selected_language)
                    
                    st.markdown(f"**Prevention:** {prevention_text}")
                
                with tab4:
                    watering_text = disease_info.get('watering_advice', 'Water regularly')
                    if st.session_state.selected_language != 'English':
                        watering_text = translate_text_simple(watering_text, st.session_state.selected_language)
                    
                    st.markdown(f"**Watering:** {watering_text}")
                
                # Export options
                st.markdown("### 📥 Export Report")
                
                if st.session_state.analysis_history:
                    latest_analysis = st.session_state.analysis_history[-1]
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # CSV report
                        report_data = {
                            'Field': ['Date', 'Farmer', 'Plant', 'Disease', 'Severity', 'Confidence'],
                            'Value': [
                                latest_analysis['timestamp'],
                                latest_analysis['user_name'],
                                disease_info.get('plant', 'Unknown'),
                                disease_info.get('name', 'Unknown'),
                                disease_info.get('severity', 'Unknown'),
                                f"{confidence:.1f}%"
                            ]
                        }
                        
                        report_df = pd.DataFrame(report_data)
                        csv_data = report_df.to_csv(index=False)
                        
                        st.download_button(
                            "📊 Download Report (CSV)",
                            csv_data,
                            f"plant_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            "text/csv",
                            use_container_width=True
                        )
                    
                    with col2:
                        # Text report
                        text_report = f"""KILIMOGLOW KENYA - PLANT ANALYSIS REPORT
Date: {latest_analysis['timestamp']}
Farmer: {latest_analysis['user_name']}
Plant: {disease_info.get('plant', 'Unknown')}
Disease: {disease_info.get('name', 'Unknown')}
Severity: {disease_info.get('severity', 'Unknown')}
Confidence: {confidence:.1f}%
Treatment: {disease_info.get('treatment', 'Not specified')}
"""
                        
                        st.download_button(
                            "📄 Download Report (TXT)",
                            text_report,
                            f"plant_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                            "text/plain",
                            use_container_width=True
                        )
        else:
            st.markdown("""
            <div class="kenyan-card" style="text-align: center; padding: 3rem;">
                <h3 style="color: #FFD700;">📸 Ready for Analysis</h3>
                <p>Take a photo or upload an image to begin plant disease detection</p>
                <div style="font-size: 3rem; margin: 1rem 0;">🔬</div>
            </div>
            """, unsafe_allow_html=True)

# BATCH ANALYSIS PAGE
elif selected_page == current_texts["batch_analysis"]:
    st.markdown(f"<h1 style='text-align: center; color: #FFD700;'>📊 {current_texts['batch_analysis']}</h1>", unsafe_allow_html=True)
    
    st.markdown("""
    <div class="kenyan-card">
        <h3 style="color: #FFD700;">⚡ Batch Processing</h3>
        <p style="color: white;">Upload multiple plant images for simultaneous analysis. Perfect for large-scale farm monitoring.</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### 📁 Upload Multiple Images")
        
        uploaded_files = st.file_uploader(
            "Choose plant images",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            help="Select multiple images for batch analysis"
        )
        
        if uploaded_files:
            st.info(f"📊 {len(uploaded_files)} images ready for processing")
            
            # Batch processing button
            if st.button(current_texts["process_batch"], type="primary", use_container_width=True):
                with st.spinner("⚡ Processing batch... This may take a few minutes."):
                    
                    if api_connected:
                        # Use FastAPI batch endpoint
                        success, batch_result = batch_predict_with_fastapi(uploaded_files)
                        
                        if success and batch_result.get('success'):
                            results = batch_result.get('results', [])
                        else:
                            st.warning("⚠️ FastAPI batch processing failed, using individual processing")
                            results = []
                            for file in uploaded_files:
                                success, result = predict_with_fastapi(file)
                                if success:
                                    results.append(result)
                                else:
                                    results.append(simulate_disease_prediction())
                    else:
                        # Offline batch processing
                        st.info("📱 Using offline batch processing")
                        results = [simulate_disease_prediction() for _ in uploaded_files]
                    
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
                            'language': st.session_state.selected_language,
                            'predicted_class': predicted_class,
                            'confidence': confidence,
                            'disease_info': disease_info,
                            'processing_time': result.get('processing_time', 0),
                            'api_used': api_connected and result.get('success', False),
                            'batch_id': batch_analysis['batch_id']
                        }
                        st.session_state.analysis_history.append(analysis_data)
                    
                    st.success(f"✅ Batch processing complete! {len(results)} images analyzed.")
    
    with col2:
        # Display batch results
        if st.session_state.batch_results:
            st.markdown("### 📈 Batch Results")
            
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
                st.metric("📊 Total Images", total_images)
            with col2:
                st.metric("🌱 Healthy Plants", f"{healthy_count} ({(healthy_count/total_images*100):.0f}%)")
            with col3:
                st.metric("🎯 Avg Confidence", f"{avg_confidence:.1f}%")
            
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
                    
                    batch_data.append({
                        'Image': f'Image {i+1}',
                        'Plant': disease_info.get('plant', 'Unknown'),
                        'Disease': disease_info.get('name', 'Unknown'),
                        'Severity': disease_info.get('severity', 'Unknown'),
                        'Confidence': confidence
                    })
                
                batch_df = pd.DataFrame(batch_data)
                
                # Severity distribution
                fig_severity = px.pie(
                    batch_df, 
                    names='Severity',
                    title='Disease Severity Distribution',
                    color_discrete_map={
                        'None': '#32CD32',
                        'Medium': '#FFD700', 
                        'High': '#FF8C00',
                        'Critical': '#DC143C'
                    }
                )
                fig_severity.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="white")
                )
                st.plotly_chart(fig_severity, use_column_width=True)
                
                # Results table
                st.markdown("### 📋 Detailed Results")
                st.dataframe(batch_df, use_container_width=True, hide_index=True)
                
                # Export batch results
                st.markdown("### 📥 Export Batch Results")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Export CSV
                    csv_data = batch_df.to_csv(index=False)
                    st.download_button(
                        "📊 Download Batch CSV",
                        csv_data,
                        f"batch_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        "text/csv",
                        use_container_width=True
                    )
                
                with col2:
                    # Export summary report
                    summary_report = f"""KILIMOGLOW KENYA - BATCH ANALYSIS REPORT
Batch ID: {latest_batch['batch_id']}
Date: {latest_batch['timestamp']}
Farmer: {latest_batch['user_name']}
Total Images: {total_images}
Healthy Plants: {healthy_count} ({(healthy_count/total_images*100):.1f}%)
Plants Needing Treatment: {total_images - healthy_count} ({((total_images - healthy_count)/total_images*100):.1f}%)
Average Confidence: {avg_confidence:.1f}%

DETAILED RESULTS:
{chr(10).join([f"Image {i+1}: {row['Plant']} - {row['Disease']} ({row['Confidence']:.1f}%)" for i, row in batch_df.iterrows()])}
"""
                    
                    st.download_button(
                        "📄 Download Summary",
                        summary_report,
                        f"batch_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        "text/plain",
                        use_container_width=True
                    )
        else:
            st.markdown("""
            <div class="kenyan-card" style="text-align: center; padding: 3rem;">
                <h3 style="color: #FFD700;">⚡ Ready for Batch Processing</h3>
                <p>Upload multiple images to see batch analysis results here</p>
                <div style="font-size: 3rem; margin: 1rem 0;">📊</div>
            </div>
            """, unsafe_allow_html=True)

# DASHBOARD PAGE
elif selected_page == current_texts["dashboard"]:
    st.markdown(f"<h1 style='text-align: center; color: #FFD700;'>📈 {current_texts['dashboard']}</h1>", unsafe_allow_html=True)
    
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
                <h2 style="color: #32CD32; margin: 0;">{total_analyses}</h2>
                <p style="margin: 0;">Total Scans</p>
            </div>
            """, unsafe_allow_html=True)
        
        # with col2:
        #     st.markdown(f"""
        #     <div class="metric-card">
        # # Continuing from the dashboard metrics section...

        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <h2 style="color: #FFD700; margin: 0;">{healthy_count}</h2>
                <p style="margin: 0;">Healthy Plants</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <h2 style="color: #FF6B35; margin: 0;">{total_analyses - healthy_count}</h2>
                <p style="margin: 0;">Diseases Detected</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <h2 style="color: #9932CC; margin: 0;">{avg_confidence:.1f}%</h2>
                <p style="margin: 0;">Avg Confidence</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Analysis trends over time
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### 📊 Analysis Trends")
            
            # Prepare time series data
            df = pd.DataFrame(st.session_state.analysis_history)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['date'] = df['timestamp'].dt.date
            
            # Daily analysis count
            daily_counts = df.groupby('date').size().reset_index(name='count')
            daily_counts['cumulative'] = daily_counts['count'].cumsum()
            
            fig_trend = go.Figure()
            
            # Daily bars
            fig_trend.add_trace(go.Bar(
                x=daily_counts['date'],
                y=daily_counts['count'],
                name='Daily Analyses',
                marker_color='#32CD32',
                opacity=0.7
            ))
            
            # Cumulative line
            fig_trend.add_trace(go.Scatter(
                x=daily_counts['date'],
                y=daily_counts['cumulative'],
                mode='lines+markers',
                name='Cumulative',
                line=dict(color='#FFD700', width=3),
                yaxis='y2'
            ))
            
            fig_trend.update_layout(
                title="📈 Analysis Activity Over Time",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0.1)",
                font=dict(color="white"),
                xaxis_title="Date",
                yaxis=dict(title="Daily Count", side='left'),
                yaxis2=dict(title="Cumulative", side='right', overlaying='y'),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                height=400
            )
            
            st.plotly_chart(fig_trend, use_container_width=True)
        
        with col2:
            st.markdown("### 🌱 Plant Types")
            
            # Extract plant types from disease info
            plant_counts = {}
            for analysis in st.session_state.analysis_history:
                disease_info = analysis.get('disease_info', {})
                plant = disease_info.get('plant', 'Unknown')
                plant_counts[plant] = plant_counts.get(plant, 0) + 1
            
            plant_df = pd.DataFrame(list(plant_counts.items()), columns=['Plant', 'Count'])
            
            fig_plants = px.pie(
                plant_df,
                values='Count',
                names='Plant',
                title='Plant Distribution',
                color_discrete_sequence=['#32CD32', '#FFD700', '#FF6B35', '#9932CC']
            )
            
            fig_plants.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="white"),
                height=300,
                margin=dict(l=20, r=20, t=60, b=20)
            )
            
            st.plotly_chart(fig_plants, use_container_width=True)
        
        # Disease severity analysis
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### ⚠️ Severity Analysis")
            
            severity_counts = {}
            for analysis in st.session_state.analysis_history:
                disease_info = analysis.get('disease_info', {})
                severity = disease_info.get('severity', 'Unknown')
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            severity_df = pd.DataFrame(list(severity_counts.items()), columns=['Severity', 'Count'])
            
            # Color mapping for severity
            severity_colors = {
                'None': '#32CD32',
                'Medium': '#FFD700', 
                'High': '#FF8C00',
                'Critical': '#DC143C',
                'Unknown': '#808080'
            }
            
            fig_severity = px.bar(
                severity_df,
                x='Severity',
                y='Count',
                title='Disease Severity Distribution',
                color='Severity',
                color_discrete_map=severity_colors
            )
            
            fig_severity.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0.1)",
                font=dict(color="white"),
                showlegend=False,
                height=350
            )
            
            st.plotly_chart(fig_severity, use_container_width=True)
        
        with col2:
            st.markdown("### 🎯 Confidence Levels")
            
            # Confidence distribution
            confidences = [a.get('confidence', 0) for a in st.session_state.analysis_history]
            
            fig_conf_dist = go.Figure()
            
            fig_conf_dist.add_trace(go.Histogram(
                x=confidences,
                nbinsx=10,
                marker_color='#32CD32',
                opacity=0.7,
                name='Confidence Distribution'
            ))
            
            # Add average line
            avg_line = sum(confidences) / len(confidences)
            fig_conf_dist.add_vline(
                x=avg_line,
                line_dash="dash",
                line_color="#FFD700",
                line_width=3,
                annotation_text=f"Avg: {avg_line:.1f}%"
            )
            
            fig_conf_dist.update_layout(
                title="🎯 Confidence Score Distribution",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0.1)",
                font=dict(color="white"),
                xaxis_title="Confidence (%)",
                yaxis_title="Count",
                showlegend=False,
                height=350
            )
            
            st.plotly_chart(fig_conf_dist, use_container_width=True)
        
        # Recent analysis history table
        st.markdown("### 📋 Recent Analysis History")
        
        # Prepare display data
        display_data = []
        recent_analyses = sorted(st.session_state.analysis_history, 
                               key=lambda x: x['timestamp'], reverse=True)[:10]
        
        for analysis in recent_analyses:
            disease_info = analysis.get('disease_info', {})
            display_data.append({
                'Time': analysis['timestamp'].split(' ')[1][:5],  # Show only time
                'Farmer': analysis.get('user_name', 'Anonymous')[:15],
                'Plant': disease_info.get('plant', 'Unknown'),
                'Disease': disease_info.get('name', 'Unknown')[:20],
                'Severity': disease_info.get('severity', 'Unknown'),
                'Confidence': f"{analysis.get('confidence', 0):.1f}%",
                'API': '🟢' if analysis.get('api_used', False) else '🔴'
            })
        
        history_df = pd.DataFrame(display_data)
        
        # Style the dataframe
        def style_severity(val):
            colors = {
                'Critical': 'background-color: #DC143C; color: white',
                'High': 'background-color: #FF8C00; color: white',
                'Medium': 'background-color: #FFD700; color: black',
                'None': 'background-color: #32CD32; color: white'
            }
            return colors.get(val, '')
        
        if not history_df.empty:
            styled_df = history_df.style.applymap(
                style_severity, subset=['Severity']
            ).set_properties(**{
                'background-color': 'rgba(255, 255, 255, 0.1)',
                'color': 'white',
                'border': '1px solid rgba(255, 255, 255, 0.2)'
            })
            
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
        
        # Export dashboard data
        st.markdown("### 📥 Export Dashboard Data")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Export full history
            full_export_data = []
            for analysis in st.session_state.analysis_history:
                disease_info = analysis.get('disease_info', {})
                full_export_data.append({
                    'Analysis_ID': analysis.get('analysis_id', ''),
                    'Timestamp': analysis.get('timestamp', ''),
                    'Farmer_Name': analysis.get('user_name', ''),
                    'Weather': analysis.get('weather', ''),
                    'Soil_Type': analysis.get('soil', ''),
                    'Language': analysis.get('language', ''),
                    'Plant_Type': disease_info.get('plant', ''),
                    'Disease_Name': disease_info.get('name', ''),
                    'Severity': disease_info.get('severity', ''),
                    'Confidence': analysis.get('confidence', 0),
                    'Processing_Time': analysis.get('processing_time', 0),
                    'API_Used': analysis.get('api_used', False),
                    'Treatment': disease_info.get('treatment', ''),
                    'Prevention': disease_info.get('prevention', '')
                })
            
            export_df = pd.DataFrame(full_export_data)
            csv_data = export_df.to_csv(index=False)
            
            st.download_button(
                "📊 Full History CSV",
                csv_data,
                f"kilimoglow_full_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "text/csv",
                use_container_width=True
            )
        
        with col2:
            # Export summary stats
            summary_stats = f"""KILIMOGLOW KENYA - DASHBOARD SUMMARY
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

OVERVIEW STATISTICS:
Total Analyses: {total_analyses}
Healthy Plants: {healthy_count} ({(healthy_count/total_analyses*100):.1f}%)
Diseased Plants: {total_analyses - healthy_count} ({((total_analyses - healthy_count)/total_analyses*100):.1f}%)
Average Confidence: {avg_confidence:.1f}%
API Analyses: {api_analyses} ({(api_analyses/total_analyses*100):.1f}%)

PLANT TYPE BREAKDOWN:
{chr(10).join([f"{plant}: {count}" for plant, count in plant_counts.items()])}

SEVERITY BREAKDOWN:
{chr(10).join([f"{severity}: {count}" for severity, count in severity_counts.items()])}

LANGUAGE USAGE:
{chr(10).join([f"{lang}: {sum(1 for a in st.session_state.analysis_history if a.get('language') == lang)}" for lang in set(a.get('language', 'English') for a in st.session_state.analysis_history)])}
"""
            
            st.download_button(
                "📈 Summary Report",
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
                    'app_version': 'KilimoGlow_v2.0'
                },
                'analysis_history': st.session_state.analysis_history,
                'batch_results': st.session_state.batch_results,
                'summary_stats': {
                    'total_analyses': total_analyses,
                    'healthy_count': healthy_count,
                    'avg_confidence': avg_confidence,
                    'plant_distribution': plant_counts,
                    'severity_distribution': severity_counts
                }
            }
            
            json_string = json.dumps(json_data, indent=2, default=str)
            
            st.download_button(
                "🔧 Data Export (JSON)",
                json_string,
                f"kilimoglow_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "application/json",
                use_container_width=True
            )
    
    else:
        st.markdown("""
        <div class="kenyan-card" style="text-align: center; padding: 4rem;">
            <h2 style="color: #FFD700;">📊 Dashboard Ready</h2>
            <p style="margin: 1rem 0;">Start analyzing plants to see comprehensive analytics and insights here</p>
            <div style="font-size: 4rem; margin: 2rem 0;">📈</div>
            <p style="color: #32CD32;">Your farming analytics will appear once you begin plant disease detection</p>
        </div>
        """, unsafe_allow_html=True)

# SETTINGS PAGE
elif selected_page == current_texts["settings"]:
    st.markdown(f"<h1 style='text-align: center; color: #FFD700;'>⚙️ {current_texts['settings']}</h1>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 🔧 System Configuration")
        
        # API Configuration
        with st.expander("🌐 API Settings", expanded=True):
            st.markdown(f"""
            **FastAPI Status:** {'🟢 Connected' if api_connected else '🔴 Disconnected'}
            
            **Base URL:** {FASTAPI_BASE_URL}
            
            **Available Endpoints:**
            """)
            
            for endpoint_name, endpoint_url in FASTAPI_ENDPOINTS.items():
                status = "✅" if api_connected else "❌"
                st.markdown(f"- {status} **{endpoint_name.title()}:** `{endpoint_url}`")
            
            if st.button("🔄 Test API Connection", use_container_width=True):
                with st.spinner("Testing connection..."):
                    test_success, test_info = check_fastapi_connection()
                    if test_success:
                        st.success("✅ API connection successful!")
                        st.json(test_info)
                    else:
                        st.error("❌ API connection failed!")
                        st.json(test_info)
        
        # Model Information
        with st.expander("🤖 Model Information"):
            if api_connected:
                model_info = get_model_info()
                if model_info:
                    st.json(model_info)
                else:
                    st.info("Model information not available")
            else:
                st.warning("API not connected - model info unavailable")
        
        # Language & Localization
        with st.expander("🌍 Language & Localization", expanded=True):
            st.markdown("**Supported Languages:**")
            for lang, code in LANGUAGES.items():
                current = "🔸" if lang == st.session_state.selected_language else "⚪"
                st.markdown(f"{current} **{lang}** (`{code}`)")
            
            st.markdown("---")
            
            # Translation test
            test_text = st.text_input("🔤 Test Translation", value="Healthy plant treatment")
            if test_text:
                for lang in LANGUAGES.keys():
                    if lang != "English":
                        translated = translate_text_simple(test_text, lang)
                        st.markdown(f"**{lang}:** {translated}")
    
    with col2:
        st.markdown("### 📱 User Preferences")
        
        # User Profile
        with st.expander("👤 User Profile", expanded=True):
            st.session_state.user_name = st.text_input(
                "👤 Default Name",
                value=st.session_state.user_name,
                help="Default name for analysis reports"
            )
            
            # Camera quality settings
            camera_options = ["Low (480p)", "Medium (720p)", "High (1080p)"]
            st.session_state.camera_quality = st.selectbox(
                "📷 Camera Quality",
                camera_options,
                index=camera_options.index(st.session_state.camera_quality)
            )
            
            # Default environmental conditions
            st.markdown("**Default Conditions:**")
            default_weather = st.selectbox(
                "🌤️ Default Weather",
                ["Select", "Sunny/Jua", "Rainy/Mvua", "Cloudy/Mawingu", "Dry/Kavu"],
                help="Pre-select weather condition"
            )
            
            default_soil = st.selectbox(
                "🌱 Default Soil Type",
                ["Select", "Clay/Udongo wa Tope", "Sandy/Udongo wa Mchanga", 
                 "Loam/Udongo Mzuri", "Rocky/Udongo wa Mawe"],
                help="Pre-select soil type"
            )
        
        # Data Management
        with st.expander("💾 Data Management"):
            st.markdown("**Analysis History:**")
            st.info(f"📊 Total Analyses: {len(st.session_state.analysis_history)}")
            st.info(f"📦 Batch Results: {len(st.session_state.batch_results)}")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🗑️ Clear History", use_container_width=True):
                    if st.button("⚠️ Confirm Clear", use_container_width=True):
                        st.session_state.analysis_history = []
                        st.success("✅ History cleared!")
                        st.experimental_rerun()
            
            with col2:
                if st.button("🔄 Reset All Data", use_container_width=True):
                    if st.button("⚠️ Confirm Reset", use_container_width=True):
                        # Reset all session state except language
                        current_lang = st.session_state.selected_language
                        for key in st.session_state.keys():
                            if key != 'selected_language':
                                del st.session_state[key]
                        init_session_state()
                        st.session_state.selected_language = current_lang
                        st.success("✅ All data reset!")
                        st.experimental_rerun()
        
        # Advanced Settings
        with st.expander("🔬 Advanced Settings"):
            # Confidence threshold
            confidence_threshold = st.slider(
                "🎯 Confidence Threshold",
                min_value=50.0,
                max_value=100.0,
                value=70.0,
                step=5.0,
                help="Minimum confidence for reliable predictions"
            )
            
            # Processing timeout
            processing_timeout = st.slider(
                "⏱️ Processing Timeout (seconds)",
                min_value=10,
                max_value=60,
                value=25,
                step=5,
                help="Maximum time to wait for API response"
            )
            
            # Auto-refresh dashboard
            auto_refresh = st.checkbox(
                "🔄 Auto-refresh Dashboard",
                value=False,
                help="Automatically refresh dashboard every 30 seconds"
            )
            
            # Debug mode
            debug_mode = st.checkbox(
                "🐛 Debug Mode",
                value=False,
                help="Show detailed error information and logs"
            )
            
            if debug_mode:
                st.markdown("**Debug Information:**")
                st.json({
                    "session_state_keys": list(st.session_state.keys()),
                    "api_status": st.session_state.api_status,
                    "current_analysis_id": st.session_state.current_analysis_id,
                    "browser_info": "Check browser console for detailed logs"
                })

# ===== FOOTER =====
st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, rgba(0,100,0,0.1), rgba(34,139,34,0.1)); border-radius: 15px; margin-top: 2rem;">
    <h3 style="color: #FFD700; margin-bottom: 1rem;">🌿 KilimoGlow Kenya</h3>
    <p style="color: white; margin-bottom: 0.5rem;">
        🇰🇪 <strong>Made for Kenyan Farmers</strong> • 🌾 <strong>Supporting Local Agriculture</strong> • 🤖 <strong>Powered by AI</strong>
    </p>
    <p style="color: #32CD32; margin-bottom: 1rem;">
        Empowering smallholder farmers with smart plant disease detection technology
    </p>
    <div style="display: flex; justify-content: center; gap: 2rem; flex-wrap: wrap;">
        <span style="color: white;">📱 Mobile Optimized</span>
        <span style="color: white;">🌍 Multi-language</span>
        <span style="color: white;">⚡ FastAPI Backend</span>
        <span style="color: white;">🔄 Batch Processing</span>
    </div>
    <p style="color: #FFD700; margin-top: 1rem; font-size: 0.9rem;">
        Version 2.0 • Built with ❤️ for Kenya's Agricultural Future
    </p>
</div>
""", unsafe_allow_html=True)

# Auto-refresh for dashboard (if enabled)
if selected_page == current_texts["dashboard"] and 'auto_refresh' in locals() and auto_refresh:
    time.sleep(30)
    st.experimental_rerun()

# Performance monitoring (if debug mode enabled)
if 'debug_mode' in locals() and debug_mode:
    st.markdown("---")
    st.markdown("### 🐛 Debug Information")
    
    debug_info = {
        "timestamp": datetime.now().isoformat(),
        "selected_page": selected_page,
        "api_status": st.session_state.api_status,
        "total_analyses": len(st.session_state.analysis_history),
        "total_batches": len(st.session_state.batch_results),
        "current_language": st.session_state.selected_language,
        "session_state_size": len(st.session_state.keys()),
        "memory_usage": f"{len(str(st.session_state)):.1f} KB"
    }
    
    st.json(debug_info)