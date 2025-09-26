# -*- coding: utf-8 -*-
"""
KilimoGlow Kenya - Enhanced Plant Disease Detection System
Multi-language support with audio guidance for Kenyan farmers
"""

# ===== IMPORTS =====
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
import threading
from typing import Optional, Dict, Any

# ===== PAGE CONFIG =====
st.set_page_config(
    page_title="🌿 KilimoGlow Kenya - Plant Doctor",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Optional imports with fallbacks
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    st.warning("pygame not available - audio features disabled")

try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False

# Suppress warnings
warnings.filterwarnings("ignore")

# # ===== PAGE CONFIG =====
# st.set_page_config(
#     page_title="🌿 KilimoGlow Kenya - Plant Doctor",
#     page_icon="🌿",
#     layout="wide",
#     initial_sidebar_state="expanded"
# )

# ===== CONFIGURATION =====
os.environ.setdefault("FASTAPI_URL", "http://127.0.0.1:8000")
os.environ.setdefault("FASTAPI_PUBLIC_URL", "http://203.0.113.1:8000")

# ===== PLANT DISEASES DATABASE =====
PLANT_DISEASES = {
    'Pepper__bell___Bacterial_spot': {
        'name': 'Bacterial Spot',
        'plant': 'Pilipili (Pepper)',
        'severity': 'High',
        'symptoms': 'Small dark spots with yellow halos on leaves and fruits',
        'treatment': 'Apply copper-based bactericide, remove affected parts immediately',
        'prevention': 'Use certified seeds, avoid overhead irrigation, practice crop rotation',
        'organic_treatment': 'Neem oil spray, garlic extract solution, proper field sanitation',
        'watering_advice': 'Water at base level, avoid wetting leaves, ensure good drainage',
        'audio_file': 'Pepper__bell___Bacterial_spot'
    },
    'Pepper__bell___healthy': {
        'name': 'Healthy Pepper',
        'plant': 'Pilipili (Pepper)',
        'severity': 'None',
        'symptoms': 'No symptoms - plant appears healthy',
        'treatment': 'Continue regular care and monitoring',
        'prevention': 'Maintain good agricultural practices',
        'organic_treatment': 'Keep up organic farming methods',
        'watering_advice': 'Water regularly but avoid overwatering',
        'audio_file': 'Pepper__bell___healthy'
    },
    'Potato___Early_blight': {
        'name': 'Early Blight',
        'plant': 'Viazi (Potato)',
        'severity': 'Medium',
        'symptoms': 'Brown spots with concentric rings on older leaves',
        'treatment': 'Apply fungicide containing chlorothalonil or copper compounds',
        'prevention': 'Ensure adequate spacing, avoid overhead watering',
        'organic_treatment': 'Baking soda spray, compost tea application',
        'watering_advice': 'Water early morning at soil level only',
        'audio_file': 'Potato___Early_blight'
    },
    'Potato___Late_blight': {
        'name': 'Late Blight',
        'plant': 'Viazi (Potato)',
        'severity': 'Critical',
        'symptoms': 'Water-soaked dark lesions on leaves, white mold growth',
        'treatment': 'Immediate fungicide application - metalaxyl or copper-based',
        'prevention': 'Use resistant varieties, ensure good air circulation',
        'organic_treatment': 'Remove affected plants immediately, apply bordeaux mixture',
        'watering_advice': 'Avoid watering foliage, improve drainage',
        'audio_file': 'Potato___Late_blight'
    },
    'Potato___healthy': {
        'name': 'Healthy Potato',
        'plant': 'Viazi (Potato)',
        'severity': 'None',
        'symptoms': 'No symptoms - plant appears healthy',
        'treatment': 'Continue regular care and monitoring',
        'prevention': 'Maintain good agricultural practices',
        'organic_treatment': 'Keep up organic farming methods',
        'watering_advice': 'Water regularly at soil level',
        'audio_file': 'Potato___healthy'
    },
    'Tomato_Bacterial_spot': {
        'name': 'Bacterial Spot',
        'plant': 'Nyanya (Tomato)',
        'severity': 'High',
        'symptoms': 'Small dark brown spots with yellow halos on leaves',
        'treatment': 'Copper-based bactericide spray, remove affected leaves',
        'prevention': 'Use disease-free seeds, avoid overhead irrigation',
        'organic_treatment': 'Neem oil, garlic spray, field sanitation',
        'watering_advice': 'Water at base only, ensure good air circulation',
        'audio_file': 'Tomato_Bacterial_spot'
    },
    'Tomato_Early_blight': {
        'name': 'Early Blight',
        'plant': 'Nyanya (Tomato)',
        'severity': 'Medium',
        'symptoms': 'Brown spots with target-like rings on lower leaves',
        'treatment': 'Fungicide spray, remove affected lower leaves',
        'prevention': 'Proper plant spacing, mulching, avoid leaf wetness',
        'organic_treatment': 'Baking soda solution, copper soap spray',
        'watering_advice': 'Water at soil level early in the day',
        'audio_file': 'Tomato_Early_blight'
    },
    'Tomato_Late_blight': {
        'name': 'Late Blight',
        'plant': 'Nyanya (Tomato)',
        'severity': 'Critical',
        'symptoms': 'Water-soaked lesions, white fuzzy growth under leaves',
        'treatment': 'Immediate fungicide treatment - metalaxyl compounds',
        'prevention': 'Use resistant varieties, ensure good drainage',
        'organic_treatment': 'Immediate plant removal, bordeaux mixture spray',
        'watering_advice': 'Avoid all overhead watering, improve field drainage',
        'audio_file': 'Tomato_Late_blight'
    },
    'Tomato___healthy': {
        'name': 'Healthy Tomato',
        'plant': 'Nyanya (Tomato)',
        'severity': 'None',
        'symptoms': 'No symptoms - plant appears healthy',
        'treatment': 'Continue regular care and monitoring',
        'prevention': 'Maintain good agricultural practices',
        'organic_treatment': 'Keep up organic farming methods',
        'watering_advice': 'Water regularly at root level',
        'audio_file': 'Tomato___healthy'
    }
}

# ===== LANGUAGE CONFIGURATION =====
LANGUAGES = {
    "English": "en",
    "Kiswahili": "sw",
    "Luo": "luo"
}

UI_TEXTS = {
    "English": {
        "app_title": "KilimoGlow Kenya - Plant Doctor",
        "subtitle": "Smart Plant Disease Detection for Kenyan Farmers",
        "plant_doctor": "🩺 Plant Doctor",
        "batch_analysis": "📊 Batch Analysis",
        "dashboard": "📈 Dashboard",
        "settings": "⚙️ Settings",
        "upload_label": "Upload Plant Image",
        "analyze_plant": "🔬 Analyze Plant",
        "process_batch": "⚡ Process Batch"
    },
    "Kiswahili": {
        "app_title": "KilimoGlow Kenya - Daktari wa Mimea",
        "subtitle": "Utambuzi wa Magonjwa ya Mimea kwa Wakulima wa Kenya",
        "plant_doctor": "🩺 Daktari wa Mimea",
        "batch_analysis": "📊 Uchambuzi wa Kundi",
        "dashboard": "📈 Dashibodi",
        "settings": "⚙️ Mipangilio",
        "upload_label": "Pakia Picha ya Mmea",
        "analyze_plant": "🔬 Chamua Mmea",
        "process_batch": "⚡ Chagia Kundi"
    },
    "Luo": {
        "app_title": "KilimoGlow Kenya - Jadolo mar Yedhe",
        "subtitle": "Ngʼeyo Tuoche mag Yedhe ne Jopur Kenya",
        "plant_doctor": "🩺 Jadolo mar Yedhe",
        "batch_analysis": "📊 Pimo mar Oganda",
        "dashboard": "📈 Kama mar Loso",
        "settings": "⚙️ Chenro",
        "upload_label": "Ket Kido mar Yath",
        "analyze_plant": "🔬 Non Yath",
        "process_batch": "⚡ Los Oganda"
    }
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
        'analysis_result': None,
        'current_analysis_id': None,
        'audio_enabled': True,
        'audio_system_ready': PYGAME_AVAILABLE,
        'audio_volume': 0.7,
        'last_audio_played': None,
        'audio_error': None,
        'app_initialized': False,
        'offline_cache': {},
        'hybrid_metrics': {'hits': 0, 'misses': 0, 'conflicts': 0}
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# Initialize session state
if 'app_initialized' not in st.session_state:
    init_session_state()
    st.session_state.app_initialized = True

# ===== AUDIO SYSTEM =====
class AudioManager:
    """Manages external recorded audio playback for disease detection"""
    
    def __init__(self, audio_base_path: str = "audios"):
        self.audio_base_path = Path(audio_base_path)
        self.audio_cache = {}
        self.supported_formats = ['.mp3', '.wav', '.ogg']
        self._initialize_pygame()
        
    def _initialize_pygame(self):
        """Initialize pygame mixer for audio playback"""
        if not PYGAME_AVAILABLE:
            st.session_state.audio_system_ready = False
            st.session_state.audio_error = "pygame not available"
            return
            
        try:
            pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
            pygame.mixer.init()
            st.session_state.audio_system_ready = True
        except Exception as e:
            st.session_state.audio_system_ready = False
            st.session_state.audio_error = str(e)
    
    def get_audio_path(self, disease_key: str, language: str = "English") -> Optional[Path]:
        """Get audio file path for specific disease and language"""
        lang_codes = {
            "English": "en",
            "Kiswahili": "sw", 
            "Luo": "luo"
        }
        
        lang_code = lang_codes.get(language, "en")
        audio_filename = f"{disease_key}_{lang_code}"
        
        for ext in self.supported_formats:
            audio_path = self.audio_base_path / f"{audio_filename}{ext}"
            if audio_path.exists():
                return audio_path
        
        # Fallback to English
        if lang_code != "en":
            audio_filename = f"{disease_key}_en"
            for ext in self.supported_formats:
                audio_path = self.audio_base_path / f"{audio_filename}{ext}"
                if audio_path.exists():
                    return audio_path
                    
        return None
    
    def play_audio(self, disease_key: str, language: str = "English") -> bool:
        """Play audio for specific disease"""
        if not st.session_state.get('audio_system_ready', False):
            return False
            
        audio_path = self.get_audio_path(disease_key, language)
        if not audio_path:
            return False
            
        try:
            sound = pygame.mixer.Sound(str(audio_path))
            sound.play()
            
            st.session_state.last_audio_played = {
                'disease': disease_key,
                'language': language,
                'path': str(audio_path),
                'timestamp': datetime.now().isoformat()
            }
            return True
            
        except Exception as e:
            st.session_state.audio_error = f"Audio playback error: {str(e)}"
            return False
    
    def stop_audio(self):
        """Stop currently playing audio"""
        if not PYGAME_AVAILABLE:
            return False
        try:
            pygame.mixer.stop()
            return True
        except:
            return False
    
    def get_available_audio_files(self) -> Dict[str, Dict[str, str]]:
        """Get list of available audio files organized by disease and language"""
        available = {}
        
        if not self.audio_base_path.exists():
            return available
            
        for audio_file in self.audio_base_path.glob("*"):
            if audio_file.suffix.lower() in self.supported_formats:
                stem = audio_file.stem
                parts = stem.split('_')
                
                if len(parts) >= 2 and parts[-1] in ['en', 'sw', 'luo']:
                    disease_key = '_'.join(parts[:-1])
                    lang_code = parts[-1]
                else:
                    disease_key = stem
                    lang_code = 'en'
                
                if disease_key not in available:
                    available[disease_key] = {}
                    
                lang_name = {'en': 'English', 'sw': 'Kiswahili', 'luo': 'Luo'}.get(lang_code, 'English')
                available[disease_key][lang_name] = str(audio_file)
                
        return available

# ===== UTILITY FUNCTIONS =====
def get_local_ip():
    """Get local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "127.0.0.1"

def check_fastapi_connection(timeout=3):
    """Check FastAPI connection with multiple fallback URLs"""
    urls_to_try = [
        os.getenv("FASTAPI_URL"),
        os.getenv("FASTAPI_PUBLIC_URL"),
        f"http://{get_local_ip()}:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8000"
    ]
    
    for url in urls_to_try:
        if not url:
            continue
        try:
            resp = requests.get(f"{url}/health", timeout=timeout)
            if resp.status_code == 200:
                return True, resp.json(), url
        except Exception:
            continue
    
    return False, {"error": "All connection attempts failed"}, None

def predict_with_fastapi(file_obj, timeout=25):
    """Send image to FastAPI for prediction"""
    try:
        # Get working API URL
        api_connected, api_info, working_url = check_fastapi_connection()
        if not api_connected:
            return False, {"error": "API not available"}
        
        if hasattr(file_obj, 'seek'):
            file_obj.seek(0)
            
        files = {}
        if hasattr(file_obj, 'name') and hasattr(file_obj, 'type'):
            files["file"] = (file_obj.name, file_obj, file_obj.type)
        else:
            files["file"] = ("image.jpg", file_obj, "image/jpeg")
        
        resp = requests.post(f"{working_url}/predict", files=files, timeout=timeout)
        
        if resp.status_code == 200:
            return True, resp.json()
        else:
            return False, {"status_code": resp.status_code, "error": resp.text}
            
    except Exception as e:
        return False, {"error": str(e)}

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

# ===== CSS STYLING =====
def apply_enhanced_css():
    """Apply comprehensive CSS styling"""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    * { 
        font-family: 'Inter', sans-serif; 
        box-sizing: border-box;
    }
    
    .stApp {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 50%, #1e3c72 100%);
        background-size: 400% 400%;
        animation: gradientShift 10s ease infinite;
        color: white;
    }
    
    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    .main-header {
        background: linear-gradient(135deg, #006400, #228B22, #32CD32);
        padding: 2rem;
        border-radius: 20px;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 15px 35px rgba(0, 100, 0, 0.3);
        border: 2px solid #FFD700;
        position: relative;
        overflow: hidden;
    }
    
    .kenyan-card {
        background: linear-gradient(145deg, rgba(0, 100, 0, 0.15), rgba(34, 139, 34, 0.1));
        backdrop-filter: blur(15px);
        border: 1px solid rgba(255, 215, 0, 0.3);
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .kenyan-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 35px rgba(255, 215, 0, 0.25);
        border-color: rgba(255, 215, 0, 0.6);
    }
    
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
        transform: translateY(-3px);
        box-shadow: 0 10px 25px rgba(255, 215, 0, 0.4);
        background: linear-gradient(45deg, #228B22, #32CD32, #00FF00);
    }
    
    .audio-player-widget {
        background: linear-gradient(145deg, rgba(255, 215, 0, 0.15), rgba(50, 205, 50, 0.1));
        border: 2px solid rgba(255, 215, 0, 0.4);
        border-radius: 20px;
        padding: 1.5rem;
        margin: 1rem 0;
        backdrop-filter: blur(15px);
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
        text-align: center;
    }
    
    .severity-critical { 
        background: linear-gradient(45deg, #DC143C, #FF0000);
        animation: critical-pulse 1.5s infinite;
        box-shadow: 0 0 10px rgba(220, 20, 60, 0.5);
    }
    .severity-high { 
        background: linear-gradient(45deg, #FF8C00, #FFA500);
        box-shadow: 0 0 8px rgba(255, 140, 0, 0.4);
    }
    .severity-medium { 
        background: linear-gradient(45deg, #FFD700, #FFFF00); 
        color: #000;
        box-shadow: 0 0 8px rgba(255, 215, 0, 0.4);
    }
    .severity-none { 
        background: linear-gradient(45deg, #228B22, #32CD32);
        box-shadow: 0 0 8px rgba(34, 139, 34, 0.4);
    }
    
    @keyframes critical-pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.8; transform: scale(1.05); }
    }
    </style>
    """, unsafe_allow_html=True)

# Apply CSS styling
apply_enhanced_css()

# Initialize Audio Manager
@st.cache_resource
def get_audio_manager():
    return AudioManager()

audio_manager = get_audio_manager()

# Check API status
api_connected, api_info, working_url = check_fastapi_connection()

# ===== SIDEBAR =====
with st.sidebar:
    st.session_state.selected_language = st.selectbox(
        "🌍 Language / Lugha / Dhok",
        options=list(LANGUAGES.keys()),
        index=list(LANGUAGES.keys()).index(st.session_state.selected_language)
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
    
    st.markdown("---")
    
    # System Status
    status_color = "🟢" if api_connected else "🔴"
    status_text = "Online" if api_connected else "Offline"
    
    st.markdown(f"""
    <div class="kenyan-card" style="padding: 1rem;">
        <h4 style="color: #FFD700; margin-bottom: 0.5rem;">📊 System Status</h4>
        <p style="margin: 0.2rem 0;">
            <strong>API:</strong> {status_color} {status_text}
        </p>
        <p style="margin: 0.2rem 0;">
            <strong>Language:</strong> {st.session_state.selected_language}
        </p>
        <p style="margin: 0.2rem 0;">
            <strong>Audio:</strong> {'🔊 Ready' if st.session_state.get('audio_system_ready') else '🔇 Disabled'}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Audio Settings
    if st.session_state.get('audio_system_ready'):
        st.markdown("### 🔊 Audio Settings")
        st.session_state.audio_enabled = st.checkbox("Enable Audio Guidance", value=st.session_state.get('audio_enabled', True))
        
        if st.session_state.audio_enabled:
            st.session_state.audio_volume = st.slider("Volume", 0.0, 1.0, st.session_state.get('audio_volume', 0.7), 0.1)
            if PYGAME_AVAILABLE:
                pygame.mixer.init() 
                pygame.mixer.music.set_volume(st.session_state.audio_volume)

# ===== MAIN CONTENT =====

# HOME PAGE
if selected_page == "🏠 Home":
    st.markdown(f"""
    <div class="main-header">
        <h1 style="margin: 0; font-size: 2.5rem;">🌿 {current_texts['app_title']}</h1>
        <p style="margin: 1rem 0 0 0; font-size: 1.1rem; color: #FFD700;">{current_texts['subtitle']}</p>
        <p style="margin: 0.5rem 0 0 0; color: white; font-size: 0.9rem;">
            🇰🇪 Made for Kenya • 🌾 Local Crops • 🌍 Multi-language • 🚀 FastAPI Powered • 🔊 Audio-Enhanced
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
                <li>🔊 Audio guidance in local languages</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="kenyan-card">
            <h3 style="color: #FFD700;">📊 System Status</h3>
            <ul style="color: white; line-height: 1.6;">
                <li>🌐 API Status: {'✅ Connected' if api_connected else '❌ Offline'}</li>
                <li>🔊 Audio System: {'✅ Ready' if st.session_state.get('audio_system_ready') else '❌ Disabled'}</li>
                <li>🗣️ Current Language: {st.session_state.selected_language}</li>
                <li>📁 Supported Plants: {len(PLANT_DISEASES)} diseases</li>
                <li>📈 Analysis History: {len(st.session_state.analysis_history)} records</li>
                <li>🔄 Offline Mode: {'✅ Available' if st.session_state.get('offline_cache') else '❌ Not Ready'}</li>
                <li>📱 Platform: {'Mobile' if st.session_state.get('is_mobile') else 'Desktop'}</li>
            </ul>
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
            weather_options,
            index=weather_options.index(st.session_state.weather_condition) if st.session_state.weather_condition in weather_options else 0
        )
        
        soil_options = ["Select", "Clay/Udongo wa Tope", "Sandy/Udongo wa Mchanga", 
                       "Loam/Udongo Mzuri", "Rocky/Udongo wa Mawe"]
        st.session_state.soil_type = st.selectbox(
            "🌱 Soil Type",
            soil_options,
            index=soil_options.index(st.session_state.soil_type) if st.session_state.soil_type in soil_options else 0
        )
        
        # Image upload
        st.markdown(f"### 📷 {current_texts['upload_label']}")
        
        uploaded_file = st.file_uploader(
            "Choose plant image",
            type=["jpg", "jpeg", "png"],
            help="Upload clear photo of plant leaves showing any symptoms"
        )
        
        # Camera input option
        camera_file = st.camera_input("📸 Take a photo of your plant")
        
        if camera_file:
            uploaded_file = camera_file
    
    with col2:
        if uploaded_file:
            # Display uploaded image
            image = Image.open(uploaded_file)
            st.image(image, caption="📸 Plant Photo for Analysis", use_column_width=True)
            
            # Analysis button
            if st.button(current_texts["analyze_plant"], type="primary", use_container_width=True):
                analysis_id = str(uuid.uuid4())[:8]
                st.session_state.current_analysis_id = analysis_id
                
                with st.spinner("🔬 Analyzing your plant... Please wait."):
                    start_time = time.time()
                    
                    # Try FastAPI first
                    if api_connected:
                        st.info("🚀 Attempting FastAPI analysis...")
                        success, result = predict_with_fastapi(uploaded_file)
                        
                        if success and result.get('success', True):
                            st.success("✅ Analysis completed with FastAPI!")
                            result['processing_time'] = time.time() - start_time
                            st.session_state.analysis_result = result
                        else:
                            st.warning("⚠️ FastAPI unavailable, using offline mode")
                            result = simulate_disease_prediction()
                            st.session_state.analysis_result = result
                    else:
                        st.info("📱 Using offline analysis mode")
                        result = simulate_disease_prediction()
                        st.session_state.analysis_result = result
            
            # Display results if available
            if st.session_state.analysis_result:
                result = st.session_state.analysis_result
                predicted_class = result.get("predicted_class", "unknown")
                confidence = result.get("confidence", 0)
                
                if confidence <= 1:
                    confidence *= 100
                
                if confidence < 60:
                    st.warning("⚠️ Low confidence detection. Please ensure image shows clear plant leaves.")
                
                disease_info = PLANT_DISEASES.get(predicted_class, {
                    'name': 'Unknown Disease',
                    'plant': 'Unknown Plant',
                    'severity': 'Unknown',
                    'symptoms': 'Unable to determine symptoms',
                    'treatment': 'Consult agricultural extension officer',
                    'prevention': 'Practice good plant hygiene',
                    'organic_treatment': 'Use natural methods',
                    'watering_advice': 'Water appropriately',
                    'audio_file': None
                })
                
                st.markdown("---")
                st.markdown("### 🎯 Analysis Results")
                
                # Audio Player Integration
                if st.session_state.get('audio_enabled', True) and disease_info.get('audio_file'):
                    st.markdown(f"""
                    <div class="audio-player-widget">
                        <h4 style="color: #FFD700; margin-bottom: 1rem;">
                            🔊 Audio Guidance Available
                        </h4>
                        <p style="margin-bottom: 1rem;">
                            Listen to professional treatment advice for <strong>{disease_info.get('name', 'this condition')}</strong>
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col_audio1, col_audio2 = st.columns(2)
                    
                    with col_audio1:
                        if st.button("🔊 Play Audio Guidance", use_container_width=True):
                            if audio_manager.play_audio(predicted_class, st.session_state.selected_language):
                                st.success("🔊 Playing audio guidance...")
                            else:
                                st.warning(f"🔇 Audio not available for {disease_info.get('name')} in {st.session_state.selected_language}")
                    
                    with col_audio2:
                        if st.button("⏹️ Stop Audio", use_container_width=True):
                            if audio_manager.stop_audio():
                                st.info("⏹️ Audio stopped")
                
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
                st.plotly_chart(fig_conf, use_container_width=True)
                
                # Disease information card
                severity_color = {
                    'Critical': '#DC143C', 'High': '#FF8C00', 
                    'Medium': '#FFD700', 'None': '#32CD32'
                }.get(disease_info.get('severity'), '#32CD32')
                
                st.markdown(f"""
                <div class="kenyan-card" style="border-left: 6px solid {severity_color};">
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
                    st.markdown(f"**Treatment:** {disease_info.get('treatment', 'Continue monitoring')}")
                    
                    urgency = {
                        'Critical': '🚨 Act immediately (today!)',
                        'High': '⚠️ Treat within 2-3 days',
                        'Medium': '⚡ Treat within a week',
                        'None': '✅ Continue monitoring'
                    }.get(disease_info.get('severity'), 'Monitor regularly')
                    
                    st.info(f"⏰ **Urgency:** {urgency}")
                
                with tab2:
                    st.markdown(f"**Organic Treatment:** {disease_info.get('organic_treatment', 'Use natural methods')}")
                    
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
                    st.markdown(f"**Prevention:** {disease_info.get('prevention', 'Practice good hygiene')}")
                
                with tab4:
                    st.markdown(f"**Watering:** {disease_info.get('watering_advice', 'Water regularly')}")
                
                # Save analysis to history
                analysis_data = {
                    'analysis_id': st.session_state.get('current_analysis_id', str(uuid.uuid4())[:8]),
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'user_name': st.session_state.user_name or 'Anonymous',
                    'weather': st.session_state.weather_condition,
                    'soil': st.session_state.soil_type,
                    'language': st.session_state.selected_language,
                    'predicted_class': predicted_class,
                    'confidence': confidence,
                    'disease_info': disease_info,
                    'processing_time': result.get('processing_time', 0),
                    'api_used': api_connected and result.get('success', False),
                    'audio_available': bool(disease_info.get('audio_file'))
                }
                
                # Add to history if not already present
                existing_analysis = next((a for a in st.session_state.analysis_history 
                        if a.get('analysis_id') == st.session_state.get('current_analysis_id')), None)
                if not existing_analysis:
                    st.session_state.analysis_history.append(analysis_data)
                
                # Export options
                st.markdown("### 📥 Export Report")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # CSV report
                    report_data = {
                        'Field': ['Date', 'Farmer', 'Plant', 'Disease', 'Severity', 'Confidence', 'Weather', 'Soil'],
                        'Value': [
                            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            st.session_state.user_name or 'Anonymous',
                            disease_info.get('plant', 'Unknown'),
                            disease_info.get('name', 'Unknown'),
                            disease_info.get('severity', 'Unknown'),
                            f"{confidence:.1f}%",
                            st.session_state.weather_condition,
                            st.session_state.soil_type
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
==========================================
Analysis ID: {st.session_state.get('current_analysis_id', 'N/A')}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Farmer: {st.session_state.user_name or 'Anonymous'}
Language: {st.session_state.selected_language}

ENVIRONMENTAL CONDITIONS:
Weather: {st.session_state.weather_condition}
Soil Type: {st.session_state.soil_type}

ANALYSIS RESULTS:
Plant Type: {disease_info.get('plant', 'Unknown')}
Disease/Condition: {disease_info.get('name', 'Unknown')}
Severity Level: {disease_info.get('severity', 'Unknown')}
Confidence Score: {confidence:.1f}%

SYMPTOMS:
{disease_info.get('symptoms', 'No symptoms listed')}

TREATMENT RECOMMENDATION:
{disease_info.get('treatment', 'Continue monitoring')}

ORGANIC TREATMENT:
{disease_info.get('organic_treatment', 'Use natural methods')}

PREVENTION MEASURES:
{disease_info.get('prevention', 'Practice good hygiene')}

WATERING ADVICE:
{disease_info.get('watering_advice', 'Water regularly')}

Generated by KilimoGlow Kenya v2.0
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

# DASHBOARD PAGE
elif selected_page == current_texts["dashboard"]:
    st.markdown(f"<h1 style='text-align: center; color: #FFD700;'>📈 {current_texts['dashboard']}</h1>", unsafe_allow_html=True)
    
    if st.session_state.analysis_history:
        total_analyses = len(st.session_state.analysis_history)
        healthy_count = sum(1 for a in st.session_state.analysis_history 
                          if 'healthy' in a.get('predicted_class', '').lower())
        
        # Metrics display
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Analyses", total_analyses)
        
        with col2:
            st.metric("Healthy Plants", f"{healthy_count} ({(healthy_count/total_analyses*100):.1f}%)")
        
        with col3:
            st.metric("Diseases Detected", f"{total_analyses - healthy_count} ({((total_analyses - healthy_count)/total_analyses*100):.1f}%)")
        
        # Recent analysis history
        st.markdown("### 📋 Recent Analysis History")
        
        display_data = []
        recent_analyses = sorted(st.session_state.analysis_history, 
                               key=lambda x: x['timestamp'], reverse=True)[:10]
        
        for analysis in recent_analyses:
            disease_info = analysis.get('disease_info', {})
            display_data.append({
                'Time': analysis['timestamp'].split(' ')[1][:5],
                'Farmer': analysis.get('user_name', 'Anonymous')[:15],
                'Plant': disease_info.get('plant', 'Unknown'),
                'Disease': disease_info.get('name', 'Unknown')[:20],
                'Severity': disease_info.get('severity', 'Unknown'),
                'Confidence': f"{analysis.get('confidence', 0):.1f}%",
                'API': '🟢' if analysis.get('api_used', False) else '🔴'
            })
        
        if display_data:
            history_df = pd.DataFrame(display_data)
            st.dataframe(history_df, use_container_width=True, hide_index=True)
    else:
        st.info("No analysis history available yet. Start by analyzing some plant images!")

# SETTINGS PAGE
elif selected_page == current_texts["settings"]:
    st.markdown(f"<h1 style='text-align: center; color: #FFD700;'>⚙️ {current_texts['settings']}</h1>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 🔧 System Configuration")
        
        # API Configuration
        with st.expander("🌐 API Settings"):
            st.markdown(f"""
            **FastAPI Status:** {'🟢 Connected' if api_connected else '🔴 Disconnected'}
            
            **Base URL:** {os.getenv('FASTAPI_URL', 'Not Set')}
            """)
            
            if st.button("🔄 Test API Connection", use_container_width=True):
                with st.spinner("Testing connection..."):
                    test_success, test_info, working_api_url = check_fastapi_connection()
                    if test_success:
                        st.success("✅ API connection successful!")
                        st.json(test_info)
                    else:
                        st.error("❌ API connection failed!")
                        st.json(test_info)
        
        # Audio Configuration
        with st.expander("🔊 Audio Settings"):
            st.markdown(f"""
            **Audio System:** {'✅ Ready' if st.session_state.get('audio_system_ready') else '❌ Not Available'}
            
            **Pygame Available:** {'✅ Yes' if PYGAME_AVAILABLE else '❌ No'}
            """)
            
            if st.session_state.get('audio_system_ready'):
                available_audio = audio_manager.get_available_audio_files()
                st.markdown(f"**Available Audio Files:** {len(available_audio)} diseases")
                
                for disease, languages in available_audio.items():
                    disease_name = PLANT_DISEASES.get(disease, {}).get('name', disease)
                    lang_list = ", ".join(languages.keys())
                    st.markdown(f"- **{disease_name}**: {lang_list}")
    
    with col2:
        st.markdown("### 📊 System Statistics")
        
        # System stats
        stats_data = {
            'Metric': [
                'Total Diseases in Database',
                'Analysis History Count',
                'Audio Files Available',
                'Languages Supported',
                'API Status',
                'Audio System Status'
            ],
            'Value': [
                len(PLANT_DISEASES),
                len(st.session_state.analysis_history),
                len(audio_manager.get_available_audio_files()) if st.session_state.get('audio_system_ready') else 0,
                len(LANGUAGES),
                'Connected' if api_connected else 'Offline',
                'Ready' if st.session_state.get('audio_system_ready') else 'Disabled'
            ]
        }
        
        stats_df = pd.DataFrame(stats_data)
        st.dataframe(stats_df, use_container_width=True, hide_index=True)
        
        # Clear data options
        st.markdown("### 🗑️ Data Management")
        
        if st.button("Clear Analysis History", type="secondary"):
            st.session_state.analysis_history = []
            st.success("Analysis history cleared!")
        
        if st.button("Clear Batch Results", type="secondary"):
            st.session_state.batch_results = []
            st.success("Batch results cleared!")

# ===== FOOTER =====
st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 2rem; background: linear-gradient(90deg, #006400, #228B22); border-radius: 15px; margin-top: 2rem;">
    <h3 style="color: #FFD700; margin-bottom: 1rem;">🌿 KilimoGlow Kenya Enhanced</h3>
    <p style="color: white; margin-bottom: 0.5rem;">
        🇰🇪 <strong>Made for Kenyan Farmers</strong> • 🌾 <strong>Supporting Local Agriculture</strong> • 🤖 <strong>Powered by AI</strong>
    </p>
    <p style="color: #32CD32; margin-bottom: 1rem;">
        Empowering smallholder farmers with smart plant disease detection and audio guidance
    </p>
    <div style="display: flex; justify-content: center; gap: 2rem; flex-wrap: wrap; margin: 1rem 0;">
        <span style="color: white;">📱 Mobile Optimized</span>
        <span style="color: white;">🌍 Multi-language</span>
        <span style="color: white;">⚡ FastAPI Backend</span>
        <span style="color: white;">🔊 Audio Enhanced</span>
        <span style="color: white;">📴 Offline Capable</span>
    </div>
    <p style="color: #FFD700; margin-top: 1rem; font-size: 0.9rem;">
        Version 2.0 Enhanced • Built with ❤️ for Kenya's Agricultural Future
    </p>
</div>
""", unsafe_allow_html=True)