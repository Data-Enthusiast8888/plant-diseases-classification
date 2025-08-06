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
import cv2
import csv
import io
import base64
from googletrans import Translator 
from gtts import gTTS
import json
from datetime import datetime, timedelta
import time
import re

# Set page configuration
st.set_page_config(
    page_title="🌿 PlantCare AI - Plant Disease Detector",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------- Enhanced Disease Classes with detailed info --------
PLANT_DISEASES = {
    'Pepper__bell___Bacterial_spot': {
        'name': 'Bacterial Spot',
        'plant': 'Bell Pepper',
        'severity': 'Medium',
        'symptoms': 'Dark brown spots with yellow halos on leaves',
        'treatment': 'Apply copper-based fungicides, improve air circulation, avoid overhead watering',
        'prevention': 'Use disease-resistant varieties, crop rotation, proper spacing'
    },
    'Pepper__bell___healthy': {
        'name': 'Healthy',
        'plant': 'Bell Pepper',
        'severity': 'None',
        'symptoms': 'No visible disease symptoms',
        'treatment': 'Continue current care practices',
        'prevention': 'Maintain good garden hygiene and proper watering'
    },
    'Potato___Early_blight': {
        'name': 'Early Blight',
        'plant': 'Potato',
        'severity': 'High',
        'symptoms': 'Dark concentric rings on leaves, starting from lower leaves',
        'treatment': 'Apply fungicides containing chlorothalonil or mancozeb',
        'prevention': 'Crop rotation, avoid overhead irrigation, remove plant debris'
    },
    'Potato___Late_blight': {
        'name': 'Late Blight',
        'plant': 'Potato',
        'severity': 'Critical',
        'symptoms': 'Water-soaked lesions with white fuzzy growth on leaf undersides',
        'treatment': 'Apply systemic fungicides immediately, remove affected plants',
        'prevention': 'Plant resistant varieties, ensure good drainage, avoid wet conditions'
    },
    'Potato___healthy': {
        'name': 'Healthy',
        'plant': 'Potato',
        'severity': 'None',
        'symptoms': 'No visible disease symptoms',
        'treatment': 'Continue current care practices',
        'prevention': 'Maintain proper soil health and watering schedule'
    },
    'Tomato_Bacterial_spot': {
        'name': 'Bacterial Spot',
        'plant': 'Tomato',
        'severity': 'Medium',
        'symptoms': 'Small dark spots with yellow halos, may cause defoliation',
        'treatment': 'Apply copper-based bactericides, improve ventilation',
        'prevention': 'Use certified seeds, avoid working with wet plants'
    },
    'Tomato_Early_blight': {
        'name': 'Early Blight',
        'plant': 'Tomato',
        'severity': 'High',
        'symptoms': 'Brown spots with concentric rings, yellowing leaves',
        'treatment': 'Apply fungicides, remove affected leaves, improve air circulation',
        'prevention': 'Mulching, drip irrigation, crop rotation'
    },
    'Tomato_Late_blight': {
        'name': 'Late Blight',
        'plant': 'Tomato',
        'severity': 'Critical',
        'symptoms': 'Water-soaked lesions, white mold on leaf undersides',
        'treatment': 'Apply systemic fungicides immediately, destroy affected plants',
        'prevention': 'Use resistant varieties, avoid overhead watering'
    },
    'Tomato_Leaf_Mold': {
        'name': 'Leaf Mold',
        'plant': 'Tomato',
        'severity': 'Medium',
        'symptoms': 'Yellow spots on upper leaf surface, fuzzy growth underneath',
        'treatment': 'Improve ventilation, apply fungicides, reduce humidity',
        'prevention': 'Ensure good air circulation, avoid overcrowding'
    },
    'Tomato_Septoria_leaf_spot': {
        'name': 'Septoria Leaf Spot',
        'plant': 'Tomato',
        'severity': 'Medium',
        'symptoms': 'Small circular spots with dark borders and light centers',
        'treatment': 'Apply fungicides, remove affected leaves, mulch soil',
        'prevention': 'Avoid overhead watering, practice crop rotation'
    },
    'Tomato_Spider_mites_Two_spotted_spider_mite': {
        'name': 'Spider Mites',
        'plant': 'Tomato',
        'severity': 'Medium',
        'symptoms': 'Fine webbing, stippled leaves, yellowing',
        'treatment': 'Apply miticides, increase humidity, use beneficial insects',
        'prevention': 'Regular monitoring, avoid water stress'
    },
    'Tomato__Target_Spot': {
        'name': 'Target Spot',
        'plant': 'Tomato',
        'severity': 'Medium',
        'symptoms': 'Concentric ring patterns on leaves and fruit',
        'treatment': 'Apply fungicides, improve air circulation, remove debris',
        'prevention': 'Crop rotation, avoid overhead irrigation'
    },
    'Tomato__Tomato_YellowLeaf__Curl_Virus': {
        'name': 'Yellow Leaf Curl Virus',
        'plant': 'Tomato',
        'severity': 'Critical',
        'symptoms': 'Yellowing and curling of leaves, stunted growth',
        'treatment': 'Remove infected plants, control whitefly vectors',
        'prevention': 'Use virus-resistant varieties, control whiteflies'
    },
    'Tomato__Tomato_mosaic_virus': {
        'name': 'Mosaic Virus',
        'plant': 'Tomato',
        'severity': 'High',
        'symptoms': 'Mottled green and yellow patterns on leaves',
        'treatment': 'Remove infected plants, disinfect tools',
        'prevention': 'Use resistant varieties, practice good sanitation'
    },
    'Tomato___healthy': {
        'name': 'Healthy',
        'plant': 'Tomato',
        'severity': 'None',
        'symptoms': 'No visible disease symptoms',
        'treatment': 'Continue current care practices',
        'prevention': 'Maintain proper nutrition and watering'
    }
}

# FastAPI Backend URL
API_BASE_URL = "http://127.0.0.1:8000"

# -------- Enhanced Language Support --------
LANGUAGES = {
    "English": "en",
    "Swahili": "sw", 
    "Spanish": "es",
    "French": "fr",
    "Arabic": "ar",
    "Portuguese": "pt",
    "Hindi": "hi"
}

# -------- Enhanced UI Texts --------
UI_TEXTS = {
    "English": {
        "app_title": "🌿 PlantCare AI",
        "app_subtitle": "Advanced AI-powered plant disease detection with comprehensive analysis",
        "menu_title": "🌿 Plant Health Navigation",
        "home": "🏠 Home",
        "plant_doctor": "👨‍⚕️ Plant Doctor", 
        "dashboard": "📊 Farm Dashboard",
        "guide": "📚 Growing Guide",
        "tips": "💡 Expert Tips",
        "settings": "⚙️ Settings",
        "upload_image": "📸 Upload Plant Image",
        "analyze_button": "🔍 Analyze Plant",
        "prediction_results": "🎯 Analysis Results",
        "treatment_plan": "💊 Treatment Plan",
        "prevention_tips": "🛡️ Prevention Strategy",
        "severity_level": "⚠️ Severity Level",
        "confidence_score": "📈 Confidence",
        "developed_by": "🔬 Developed by AgriTech Solutions"
    },
    "Swahili": {
        "app_title": "🌿 PlantCare AI",
        "app_subtitle": "Kutambua magonjwa ya mimea kwa kutumia AI na uchambuzi mkamilifu",
        "menu_title": "🌿 Urambazaji wa Afya ya Mimea",
        "home": "🏠 Nyumbani",
        "plant_doctor": "👨‍⚕️ Daktari wa Mimea",
        "dashboard": "📊 Dashibodi ya Shamba", 
        "guide": "📚 Mwongozo wa Kilimo",
        "tips": "💡 Vidokezo vya Kitaalamu",
        "settings": "⚙️ Mipangilio",
        "upload_image": "📸 Pakia Picha ya Mmea",
        "analyze_button": "🔍 Chambuza Mmea",
        "prediction_results": "🎯 Matokeo ya Uchambuzi",
        "treatment_plan": "💊 Mpango wa Matibabu",
        "prevention_tips": "🛡️ Mkakati wa Kuzuia",
        "severity_level": "⚠️ Kiwango cha Ukali",
        "confidence_score": "📈 Kiwango cha Uhakika",
        "developed_by": "🔬 Imetengenezwa na AgriTech Solutions"
    }
}

# -------- Enhanced Styling --------
def get_base64(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

def apply_custom_css():
    base64_image = get_base64("plant_disease_classification.png")
    background_url = f"data:image/png;base64,{base64_image}"

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    * {{
        font-family: 'Inter', sans-serif;
    }}
    
    [data-testid="stAppViewContainer"] {{
        
        background: linear-gradient(rgba(0, 0, 0, 0.85), rgba(0, 0, 0, 0.85)), url({background_url});        
        color: white;
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        background-repeat: no-repeat;
    }}
    
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, #1e40af 0%, #1d4ed8 100%);
        border-right: 1px solid #3b82f6;
    }}
    
    [data-testid="stSidebar"] * {{
        color: white !important;
    }}
    
    .main-header {{
        background: linear-gradient(90deg, #3b82f6, #8b5cf6);
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 25px rgba(59, 130, 246, 0.3);
    }}
    
    .metric-card {{
        background: linear-gradient(145deg, #1e293b, #334155);
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #475569;
        text-align: center;
        transition: transform 0.3s ease;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    }}
    
    .metric-card:hover {{
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(59, 130, 246, 0.2);
    }}
    
    .severity-critical {{
        background: linear-gradient(145deg, #dc2626, #ef4444);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: bold;
    }}
    
    .severity-high {{
        background: linear-gradient(145deg, #ea580c, #f97316);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: bold;
    }}
    
    .severity-medium {{
        background: linear-gradient(145deg, #ca8a04, #eab308);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: bold;
    }}
    
    .severity-none {{
        background: linear-gradient(145deg, #16a34a, #22c55e);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: bold;
    }}
    
    .stButton>button {{
        background: linear-gradient(45deg, #3b82f6, #8b5cf6);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);
    }}
    
    .stButton>button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(59, 130, 246, 0.4);
    }}
    
    .prediction-card {{
        
        background: "linear-gradient(90deg, #16a34a, #22c55e)";
        padding: 1.5rem;
        border-radius: 15px;
        border-left: 5px solid #3b82f6;
        margin: 1rem 0;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    }}
    
    .progress-bar {{
        background: #374151;
        border-radius: 10px;
        height: 8px;
        overflow: hidden;
        margin: 0.5rem 0;
    }}
    
    .progress-fill {{
        background: linear-gradient(90deg, #3b82f6, #8b5cf6);
        height: 100%;
        border-radius: 10px;
        transition: width 0.3s ease;
    }}
    
    h1, h2, h3, h4, h5, h6 {{
        color: white !important;
    }}
    
    .stSelectbox > div > div {{
        background-color: #374151;
        color: white;
    }}
    
    .stTextInput > div > div > input {{
        background-color: #374151;
        color: white;
        border: 1px solid #6b7280;
    }}
    </style>
    """, unsafe_allow_html=True)

# Apply custom styling
apply_custom_css()

# -------- Session State Management --------
if 'language' not in st.session_state:
    st.session_state.language = 'English'
if 'analysis_history' not in st.session_state:
    st.session_state.analysis_history = []
if 'user_preferences' not in st.session_state:
    st.session_state.user_preferences = {
        'notifications': True,
        'auto_translate': True,
        'save_history': True
    }

# -------- Helper Functions --------
def get_texts(lang='English'):
    return UI_TEXTS.get(lang, UI_TEXTS['English'])

def severity_badge(severity):
    if severity == 'Critical':
        return f'<span class="severity-critical">🚨 Critical</span>'
    elif severity == 'High':
        return f'<span class="severity-high">⚠️ High</span>'
    elif severity == 'Medium':
        return f'<span class="severity-medium">⚡ Medium</span>'
    else:
        return f'<span class="severity-none">✅ Healthy</span>'

def confidence_bar(confidence):
    return f"""
    <div class="progress-bar">
        <div class="progress-fill" style="width: {confidence}%"></div>
    </div>
    <small>{confidence:.1f}% Confidence</small>
    """

def predict_disease(image_file):
    """Enhanced API call with error handling"""
    try:
        image_file.seek(0)
        files = {"file": (image_file.name, image_file, image_file.type)}
        
        with st.spinner("🔍 Analyzing plant image..."):
            response = requests.post(f"{API_BASE_URL}/predict", files=files, timeout=30)
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"🚫 API Error {response.status_code}: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        st.error("🔌 Cannot connect to AI backend. Please ensure the API server is running.")
        return None
    except Exception as e:
        st.error(f"❌ Analysis failed: {str(e)}")
        return None


def save_analysis_result(result_data):
    """Save analysis to session history"""
    if st.session_state.user_preferences['save_history']:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result_data['timestamp'] = timestamp
        st.session_state.analysis_history.append(result_data)
        # Keep only last 50 analyses
        if len(st.session_state.analysis_history) > 50:
            st.session_state.analysis_history = st.session_state.analysis_history[-50:]

# -------- Sidebar Configuration --------
with st.sidebar:
    st.markdown("""
    <style>
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #166534, #22c55e);  /* dark green to bright green */
        color: white;
        # box-shadow: inset 0 0 5px #00000055;
        # border-right: 2px solid #22c55e;

    }
    </style>

    <div style="text-align: center; padding: 1rem; margin-bottom: 1rem;">
        <h2 style="color: #bbf7d0; margin: 0;">🌿 PlantCare AI</h2>
        <p style="color: #f0fdf4; margin: 0.5rem 0;">Smart Plant Health Analysis</p>
    </div>
    """, unsafe_allow_html=True)



    # Language Selection
    st.session_state.language = st.selectbox(
        "🌐 Language / Lugha", 
        options=list(UI_TEXTS.keys()), 
        index=list(UI_TEXTS.keys()).index(st.session_state.language)
    )
    
    texts = get_texts(st.session_state.language)
    
    # Navigation Menu
    selected_page = option_menu(
        menu_title=texts["menu_title"],
        options=[
            texts["home"],
            texts["plant_doctor"], 
            texts["dashboard"],
            texts["guide"],
            texts["tips"],
            texts["settings"]
        ],
        icons=["house-fill", "heart-pulse", "bar-chart-fill", "book-fill", "lightbulb-fill", "gear-fill"],
        default_index=0,
        styles={
            "container": {"padding": "0", "background-color": "transparent"},
            "icon": {"color": "#60fa60", "font-size": "18px"},
            "nav-link": {
                "font-size": "14px",
                "text-align": "left", 
                "margin": "2px 0",
                "padding": "8px 12px",
                "color": "#e2e8f0",
                "border-radius": "8px"
            },
            "nav-link-selected": {
                "background": "linear-gradient(90deg, #16a34a, #22c55e)",
                "color": "white"
            },
        },
    )
    
    st.markdown("---")
    
    # Quick Stats
    if st.session_state.analysis_history:
        total_analyses = len(st.session_state.analysis_history)
        healthy_count = sum(1 for analysis in st.session_state.analysis_history 
                          if 'healthy' in analysis.get('predicted_class', '').lower())
        
        st.markdown("### 📊 Quick Stats")
        st.metric("Total Analyses", total_analyses)
        st.metric("Healthy Plants", f"{healthy_count}/{total_analyses}")
        
    st.markdown("---")
    st.markdown(texts["developed_by"], unsafe_allow_html=True)

# -------- Main Content Pages --------

# HOME PAGE
if selected_page == texts["home"]:
    # Header
    st.markdown(f"""
    <div class="main-header">
        <h1 style="margin: 0; font-size: 3rem; font-weight: 700;">{texts['app_title']}</h1>
        <p style="margin: 1rem 0 0 0; font-size: 1.2rem; opacity: 0.9;">{texts['app_subtitle']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Feature Cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <h3 style="color: #60a5fa; margin-bottom: 1rem;">🔬 AI Detection</h3>
            <p>Advanced deep learning models for accurate disease identification</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <h3 style="color: #34d399; margin-bottom: 1rem;">💊 Treatment Plans</h3>
            <p>Comprehensive treatment and prevention strategies</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-card">
            <h3 style="color: #f59e0b; margin-bottom: 1rem;">🌐 Multi-Language</h3>
            <p>Support for multiple languages including Swahili</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="metric-card">
            <h3 style="color: #ef4444; margin-bottom: 1rem;">📊 Analytics</h3>
            <p>Track your farm's health with detailed dashboards</p>
        </div>
        """, unsafe_allow_html=True)
    
    # How it Works Section
    st.markdown("## 👨‍💻 How AI Transforms Agronomy🦾🌿")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown("""
        ### 🌟 Key Features:
        - **93.8%+ Accuracy**: State-of-the-art deep learning models
        - **15+ Diseases**: Covers major tomato, potato, and pepper diseases
        - **Real-time Analysis**: Get results in under 10 seconds
        - **Expert Advice**: Detailed treatment and prevention strategies
        """)
    
    with col2:
        st.markdown("""
        <div style="text-align: center; padding: 2rem;">
             <img src="https://i.pinimg.com/1200x/8f/b8/c8/8fb8c8fe86924744e8ef7aa66fbece7e.jpg"
                 style="height: 250px; width: 280px; border-radius: 15px; box-shadow: 0 15px 35px rgba(0,0,0,0.3); object-fit: cover;">
            <p style="margin-top: 1rem; color: #94a3b8;">Advanced Plant Health Monitoring</p>
        </div>
        """, unsafe_allow_html=True)

    # Add some spacing before the Did You Know section
    st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Dancing+Script:wght@700&display=swap" rel="stylesheet">
    <div style="background: linear-gradient(135deg, #065f46 0%, #047857 100%);
                padding: 1.2rem;
                border-radius: 15px;
                margin: 1rem 0;
                border: 1px solid #10b981;
                box-shadow: 0 4px 15px rgba(16, 185, 129, 0.2);">
        <h2 style="color: #d1fae5; 
                text-align: center; 
                margin: 0;
                font-family: 'Dancing Script', cursive;
                font-size: 2.8rem;
                font-weight: 700;
                text-shadow: 3px 3px 6px rgba(0,0,0,0.4);">💡 Did You Know?</h2>
    </div>
    """, unsafe_allow_html=True)

    # Initialize session state for tab index and last switch time
    if 'current_tab' not in st.session_state:
        st.session_state.current_tab = 0
    if 'last_switch' not in st.session_state:
        st.session_state.last_switch = time.time()

    # Auto-switch logic (every 4 seconds)
    SWITCH_INTERVAL = 4  # seconds
    current_time = time.time()

    if current_time - st.session_state.last_switch > SWITCH_INTERVAL:
        st.session_state.current_tab = (st.session_state.current_tab + 1) % 3  # 3 tabs total
        st.session_state.last_switch = current_time
        st.rerun()

    # Tab content data
    tab_data = [
        {
            "title": "📦 Post-Harvest Facts",
            "content": [
                "• <strong>30-40%</strong> of crops are lost post-harvest in developing countries",
                "• Proper storage can extend shelf life by <strong>200-300%</strong>",
                "• Cold chain management reduces losses by up to <strong>60%</strong>",
                "• AI-powered sorting increases quality by <strong>25%</strong>"
            ]
        },
        {
            "title": "🤖 AI in Agriculture", 
            "content": [
                "• AI can detect diseases <strong>2-3 weeks</strong> before visible symptoms",
                "• Machine learning reduces pesticide use by <strong>40%</strong>",
                "• Precision agriculture increases yields by <strong>15-25%</strong>",
                "• Drone monitoring covers <strong>1000x</strong> more area than manual inspection"
            ]
        },
        {
            "title": "🚀 Smart Solutions",
            "content": [
                "• IoT sensors reduce water usage by <strong>30%</strong>",
                "• Blockchain ensures <strong>100%</strong> traceability from farm to fork", 
                "• Smart greenhouses use <strong>95%</strong> less water than traditional farming",
                "• Vertical farming produces <strong>365</strong> harvests per year"
            ]
        }
    ]

    # Display current tab content with animation
    current_data = tab_data[st.session_state.current_tab]
    content_html = "".join([f"<p style='color: #a7f3d0; margin: 8px 0;'>{item}</p>" for item in current_data["content"]])

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #065f46 0%, #047857 100%);
                padding: 1.5rem;
                border-radius: 12px;
                border: 1px solid #10b981;
                box-shadow: 0 4px 15px rgba(16, 185, 129, 0.2);
                transition: all 0.5s ease-in-out;
                animation: fadeIn 0.5s ease-in;">
        <h4 style="color: #d1fae5; margin-bottom: 1rem;">{current_data["title"]}</h4>
        {content_html}
    </div>

    <style>
    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    </style>
    """, unsafe_allow_html=True)

    # Add visual indicators (dots) showing current tab
    dots_html = ""
    for i in range(3):
        color = "#10b981" if i == st.session_state.current_tab else "#374151"
        size = "12px" if i == st.session_state.current_tab else "8px"
        dots_html += f'<span style="display: inline-block; width: {size}; height: {size}; background-color: {color}; border-radius: 50%; margin: 0 4px; transition: all 0.3s ease;"></span>'

    st.markdown(f"""
    <div style="text-align: center; margin: 15px 0;">
        {dots_html}
    </div>
    """, unsafe_allow_html=True)

    # Optional: Add a progress bar showing time until next switch
    progress = ((current_time - st.session_state.last_switch) / SWITCH_INTERVAL)
    st.progress(min(progress, 1.0), text="Auto-switching in progress...")

# PLANT DOCTOR PAGE  
if selected_page == texts["plant_doctor"]:
    st.markdown(f"<h1 style='text-align: center; color: #60a5fa; margin-bottom: 2rem;'>{texts['plant_doctor']}</h1>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2], gap="large")
    
    # Input Section
    with col1:
        st.markdown("### 👤 Patient Information")
        farmer_name = st.text_input("👨‍🌾 Farmer Name", placeholder="Enter your name")
        location = st.text_input("📍 Farm Location", placeholder="e.g., Nairobi, Kenya")
        
        st.markdown("### 🌤️ Environmental Conditions")
        weather = st.selectbox("Weather", ["☀️ Sunny", "🌧️ Rainy", "☁️ Cloudy", "💨 Windy", "💧 Humid"])
        soil_type = st.selectbox("Soil Type", ["🟤 Loamy", "🔴 Clay", "🟡 Sandy", "⚫ Peat", "⚪ Chalky"])
        temperature = st.slider("Temperature (°C)", 15, 40, 25)
        
        st.markdown("### 📸 Plant Image")
        uploaded_file = st.file_uploader(
            "", type=["jpg", "jpeg", "png"], help="Upload a clear image of the affected plant leaves"
        )

        if uploaded_file:
            image = Image.open(uploaded_file)
            st.image(image, caption="📷 Uploaded Image", width=300)
            
            if st.button("🔍 Analyze Plant Health", type="primary", use_container_width=True):
                prediction_result = predict_disease(uploaded_file)
                
                if prediction_result:
                    st.session_state.analysis_result = prediction_result
                    st.session_state.analyze_clicked = True
    # Results Section
    with col2:
        if uploaded_file and st.session_state.get('analyze_clicked', False):
            uploaded_file.seek(0)  # Reset file pointer
            
            prediction_result = predict_disease(uploaded_file)
            
            if prediction_result:
                predicted_class = prediction_result["predicted_class"]
                confidence = prediction_result["confidence"] * 100
                all_predictions = prediction_result["all_predictions"]
                
                # Get disease information
                disease_info = PLANT_DISEASES.get(predicted_class, {
                    'name': 'Unknown Disease',
                    'plant': 'Unknown',
                    'severity': 'Medium',
                    'symptoms': 'Consult an expert for proper diagnosis',
                    'treatment': 'Seek professional agricultural advice',
                    'prevention': 'Follow general plant care guidelines'
                })
                
                # Save analysis result
                analysis_data = {
                    'farmer_name': farmer_name,
                    'location': location,
                    'weather': weather,
                    'soil_type': soil_type,
                    'temperature': temperature,
                    'predicted_class': predicted_class,
                    'confidence': confidence,
                    'disease_info': disease_info
                }
                save_analysis_result(analysis_data)
                
                # Display Results
                st.markdown("### 🎯 Analysis Results")
                
                # Main prediction card
                st.markdown(f"""
                <div class="prediction-card">
                    <h3 style="color: #60a5fa; margin-bottom: 1rem;">🌿 {disease_info['plant']} - {disease_info['name']}</h3>
                    <div style="margin-bottom: 1rem;">
                        {severity_badge(disease_info['severity'])}
                        <span style="margin-left: 1rem; color: #94a3b8;">Confidence: {confidence:.1f}%</span>
                    </div>
                    {confidence_bar(confidence)}
                </div>
                """, unsafe_allow_html=True)
                
                # Symptoms
                with st.expander("🔍 Symptoms & Diagnosis", expanded=True):
                    st.write(f"**Observed Symptoms:** {disease_info['symptoms']}")
                
                # Treatment Plan
                with st.expander("💊 Treatment Recommendations", expanded=True):
                    st.write(f"**Recommended Treatment:** {disease_info['treatment']}")
                    
                    # Environmental advice
                    if weather == "🌧️ Rainy":
                        st.info("💧 **Watering Advice:** Reduce watering frequency as rain provides sufficient moisture. Ensure good drainage to prevent root rot.")
                    elif weather == "☀️ Sunny":
                        st.info("☀️ **Watering Advice:** Water early morning or late evening. Consider mulching to retain soil moisture.")
                
                # Prevention Strategy
                with st.expander("🛡️ Prevention Strategy", expanded=True):
                    st.write(f"**Prevention Measures:** {disease_info['prevention']}")
                
                # Top 5 predictions
                st.markdown("### 📊 Detailed Analysis")
                sorted_predictions = sorted(all_predictions.items(), key=lambda x: x[1], reverse=True)[:5]
                
                for i, (class_name, prob) in enumerate(sorted_predictions):
                    prob_percent = prob * 100
                    disease_data = PLANT_DISEASES.get(class_name, {'name': class_name, 'plant': 'Unknown'})
                    
                    st.markdown(f"""
                    <div style="background: rgba(59, 130, 246, 0.1); padding: 1rem; border-radius: 8px; margin: 0.5rem 0;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span><strong>{i+1}.</strong> {disease_data['plant']} - {disease_data['name']}</span>
                            <span style="color: #60a5fa; font-weight: bold;">{prob_percent:.1f}%</span>
                        </div>
                        <div class="progress-bar" style="margin-top: 0.5rem;">
                            <div class="progress-fill" style="width: {prob_percent}%;"></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Translation and Audio
                if st.session_state.user_preferences['auto_translate'] and st.session_state.language != 'English':
                    st.markdown("### 🌐 Translated Advice")
                    try:
                        translator = Translator()
                        translated_treatment = translator.translate(
                            disease_info['treatment'], 
                            dest=LANGUAGES[st.session_state.language]
                        ).text
                        
                        st.info(f"**{st.session_state.language} Translation:** {translated_treatment}")
                        
                        # Audio generation
                        try:
                            tts = gTTS(translated_treatment, lang=LANGUAGES[st.session_state.language])
                            audio_buffer = io.BytesIO()
                            tts.write_to_fp(audio_buffer)
                            audio_buffer.seek(0)
                            st.audio(audio_buffer.read(), format="audio/mp3")
                        except Exception as e:
                            st.warning("🔊 Audio generation temporarily unavailable")
                    
                    except Exception as e:
                        st.warning("🌐 Translation service temporarily unavailable")
                
                # Download Report
                st.markdown("### 📥 Download Report")
                
    
                def clean_emoji(text):
                    """Remove emojis from text"""
                    return re.sub(r'[^\w\s-]', '', str(text)).strip()

                # Clean emoji fields
                clean_weather = clean_emoji(weather)
                clean_soil_type = clean_emoji(soil_type)

                # Generate CSV report
                report_data = [
                    ['Timestamp', datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                    ['Farmer_Name', farmer_name],
                    ['Location', location],
                    ['Weather', clean_weather],
                    ['Soil_Type', clean_soil_type],
                    ['Temperature_C', temperature],
                    ['Plant_Type', disease_info['plant']],
                    ['Disease_Detected', disease_info['name']],
                    ['Severity_Level', disease_info['severity']],
                    ['Confidence_Percentage', f"{confidence:.2f}%"],
                    ['Symptoms', disease_info['symptoms']],
                    ['Treatment', disease_info['treatment']],
                    ['Prevention', disease_info['prevention']]
                ]

                report_df = pd.DataFrame(report_data, columns=['Field', 'Value'])
                csv_data = report_df.to_csv(index=False)

                st.download_button(
                    label="📄 Download Detailed Report (CSV)",
                    data=csv_data,
                    file_name=f"plant_diagnosis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.error("❌ Analysis failed. Please check your API connection and try again.")
                
        elif not uploaded_file:
            st.markdown("""
            <div style="text-align: center; padding: 3rem; background: rgba(59, 130, 246, 0.1); border-radius: 15px; border: 2px dashed #3b82f6;">
                <h3 style="color: #60a5fa; margin-bottom: 1rem;">📸 Upload Plant Image</h3>
                <p style="color: #94a3b8; margin-bottom: 1.5rem;">Take a clear photo of the affected plant leaves for accurate analysis</p>
                <img src="https://images.unsplash.com/photo-1585320806297-9794b3e4eeae?ixlib=rb-4.0.3&w=400&q=80" 
                     style="width: 60%; border-radius: 10px; opacity: 0.7;">
            </div>
            """, unsafe_allow_html=True)

# FARM DASHBOARD PAGE
elif selected_page == texts["dashboard"]:
    st.markdown(f"<h1 style='text-align: center; color: #60a5fa; margin-bottom: 2rem;'>{texts['dashboard']}</h1>", unsafe_allow_html=True)
    
    # Dashboard Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    # Calculate statistics from analysis history
    total_analyses = len(st.session_state.analysis_history)
    healthy_count = sum(1 for analysis in st.session_state.analysis_history 
                       if 'healthy' in analysis.get('predicted_class', '').lower())
    critical_count = sum(1 for analysis in st.session_state.analysis_history 
                        if analysis.get('disease_info', {}).get('severity') == 'Critical')
    avg_confidence = np.mean([analysis.get('confidence', 0) for analysis in st.session_state.analysis_history]) if st.session_state.analysis_history else 95.5
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h2 style="color: #60a5fa; margin: 0;">{total_analyses}</h2>
            <p style="margin: 0.5rem 0;">🌱 Total Plants Analyzed</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        healthy_percentage = (healthy_count / total_analyses * 100) if total_analyses > 0 else 78
        st.markdown(f"""
        <div class="metric-card">
            <h2 style="color: #34d399; margin: 0;">{healthy_percentage:.1f}%</h2>
            <p style="margin: 0.5rem 0;">✅ Healthy Plants</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h2 style="color: #ef4444; margin: 0;">{critical_count}</h2>
            <p style="margin: 0.5rem 0;">🚨 Critical Cases</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <h2 style="color: #f59e0b; margin: 0;">{avg_confidence:.1f}%</h2>
            <p style="margin: 0.5rem 0;">📈 Avg Confidence</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Charts Section
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 Disease Distribution")
        
        if st.session_state.analysis_history:
            # Create disease distribution chart from actual data
            disease_counts = {}
            for analysis in st.session_state.analysis_history:
                disease = analysis.get('disease_info', {}).get('name', 'Unknown')
                disease_counts[disease] = disease_counts.get(disease, 0) + 1
            
            chart_df = pd.DataFrame(list(disease_counts.items()), columns=['Disease', 'Count'])
        else:
            # Sample data for demonstration
            chart_df = pd.DataFrame({
                'Disease': ['Healthy', 'Early Blight', 'Late Blight', 'Leaf Mold', 'Bacterial Spot', 'Others'],
                'Count': [156, 89, 67, 45, 34, 28]
            })
        
        fig = px.pie(chart_df, values='Count', names='Disease', 
                     title='Plant Health Distribution',
                     color_discrete_sequence=px.colors.qualitative.Set3)
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', 
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='white',
            title_font_color='#60a5fa'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### 📈 Health Trends (Last 30 Days)")
        
        # Generate trend data
        dates = [datetime.now() - timedelta(days=x) for x in range(30, 0, -1)]
        
        if len(st.session_state.analysis_history) >= 10:
            # Use real data if available
            daily_health = []
            for date in dates:
                day_analyses = [a for a in st.session_state.analysis_history 
                              if datetime.strptime(a.get('timestamp', ''), "%Y-%m-%d %H:%M:%S").date() == date.date()]
                if day_analyses:
                    healthy_ratio = sum(1 for a in day_analyses if 'healthy' in a.get('predicted_class', '').lower()) / len(day_analyses) * 100
                    daily_health.append(healthy_ratio)
                else:
                    daily_health.append(None)
        else:
            # Sample trend data
            np.random.seed(42)
            daily_health = 75 + np.random.normal(0, 10, 30)
            daily_health = np.clip(daily_health, 0, 100)
        
        trend_df = pd.DataFrame({
            'Date': dates,
            'Healthy_Percentage': daily_health
        })
        
        fig2 = px.line(trend_df, x='Date', y='Healthy_Percentage',
                      title='Plant Health Trend',
                      color_discrete_sequence=['#60a5fa'])
        fig2.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)', 
            font_color='white',
            title_font_color='#60a5fa'
        )
        fig2.update_traces(line_color='#60a5fa', line_width=3)
        st.plotly_chart(fig2, use_container_width=True)
    
    # Recent Analysis History
    st.markdown("### 📋 Recent Analysis History")
    
    if st.session_state.analysis_history:
        recent_analyses = st.session_state.analysis_history[-10:]  # Last 10 analyses
        
        for i, analysis in enumerate(reversed(recent_analyses)):
            disease_info = analysis.get('disease_info', {})
            
            st.markdown(f"""
            <div class="prediction-card">
                <div style="display: flex; justify-content: between; align-items: center;">
                    <div>
                        <h4 style="margin: 0; color: #60a5fa;">{disease_info.get('plant', 'Unknown')} - {disease_info.get('name', 'Unknown')}</h4>
                        <p style="margin: 0.5rem 0; color: #94a3b8;">
                            👨‍🌾 {analysis.get('farmer_name', 'Anonymous')} • 
                            📍 {analysis.get('location', 'Unknown')} • 
                            🕒 {analysis.get('timestamp', 'Unknown time')}
                        </p>
                    </div>
                    <div style="text-align: right;">
                        {severity_badge(disease_info.get('severity', 'Unknown'))}
                        <br><small style="color: #94a3b8;">{analysis.get('confidence', 0):.1f}% confidence</small>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("📝 No analysis history yet. Start analyzing plants to see your dashboard data!")

# GROWING GUIDE PAGE
elif selected_page == texts["guide"]:
    st.markdown(f"<h1 style='text-align: center; color: #60a5fa; margin-bottom: 2rem;'>{texts['guide']}</h1>", unsafe_allow_html=True)
    
    # Seasonal Planting Guide
    st.markdown("## 📅 Seasonal Planting Calendar (Kenya)")
    
    seasons_data = {
        "🌧️ Long Rains (March - May)": {
            "crops": ["Maize", "Beans", "Potatoes", "Tomatoes", "Peppers", "Sukuma Wiki"],
            "description": "Main growing season with reliable rainfall",
            "tips": ["Prepare land early", "Plant disease-resistant varieties", "Ensure good drainage"]
        },
        "☀️ Dry Season (June - September)": {
            "crops": ["Irrigation crops", "Greenhouse vegetables", "Drought-resistant varieties"],
            "description": "Irrigation-dependent season",
            "tips": ["Focus on water conservation", "Use mulching", "Monitor for pests closely"]
        },
        "🌦️ Short Rains (October - December)": {
            "crops": ["Quick-maturing maize", "Beans", "Vegetables", "Root crops"],
            "description": "Secondary growing season",
            "tips": ["Choose fast-maturing varieties", "Be ready for harvest", "Monitor weather closely"]
        }
    }
    
    for season, data in seasons_data.items():
        with st.expander(f"{season}", expanded=False):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"**Description:** {data['description']}")
                
                st.write("**Recommended Crops:**")
                for crop in data['crops']:
                    st.write(f"• {crop}")
                
                st.write("**Key Tips:**")
                for tip in data['tips']:
                    st.write(f"• {tip}")
            
            with col2:
                top_crops = data.get('crops', [])[:4]
                suitability_scores = [90, 85, 80, 75][:len(top_crops)]

                crop_df = pd.DataFrame({
                    'Crop': top_crops,
                    'Suitability': suitability_scores
                            })


                
                
                fig = px.bar(crop_df, x='Suitability', y='Crop', orientation='h',
                           title=f'Crop Suitability - {season.split("(")[0]}',
                           color='Suitability',
                           color_continuous_scale='Viridis')
                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font_color='white',
                    height=300
                )
                st.plotly_chart(fig, use_container_width=True)
    
    # Plant Care Guidelines
    st.markdown("## 🌱 Plant Care Guidelines")
    
    care_tabs = st.tabs(["🍅 Tomatoes", "🥔 Potatoes", "🌶️ Peppers"])
    
    with care_tabs[0]:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            ### 🍅 Tomato Care Guide
            
            **Planting:**
            - Start seeds indoors 6-8 weeks before last frost
            - Transplant when soil temperature reaches 60°F (15°C)
            - Space plants 24-36 inches apart
            
            **Watering:**
            - Deep, infrequent watering (1-2 inches per week)
            - Water at soil level to prevent leaf diseases
            - Mulch to retain moisture
            
            **Common Issues:**
            - Early Blight: Remove affected leaves, improve air circulation
            - Late Blight: Use fungicides preventively in humid conditions
            - Blossom End Rot: Ensure consistent watering and adequate calcium
            """)
        
        with col2:
            st.markdown("""
            ### 📊 Tomato Growth Stages
            """)
            
            growth_data = pd.DataFrame({
                'Stage': ['Seedling', 'Vegetative', 'Flowering', 'Fruiting', 'Harvest'],
                'Days': [14, 30, 45, 65, 85],
                'Care_Level': [8, 6, 9, 7, 5]
            })
            
            fig = px.line(growth_data, x='Days', y='Care_Level', 
                         title='Care Intensity Over Growth Stages',
                         markers=True)
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with care_tabs[1]:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            ### 🥔 Potato Care Guide
            
            **Planting:**
            - Plant seed potatoes 2-4 weeks before last frost
            - Plant 4 inches deep, 12 inches apart
            - Hill soil around plants as they grow
            
            **Watering:**
            - Regular watering during tuber formation
            - Reduce watering 2 weeks before harvest
            - Avoid overwatering to prevent rot
            
            **Common Issues:**
            - Early Blight: Remove infected foliage, use fungicides
            - Late Blight: Plant resistant varieties, avoid overhead irrigation
            - Colorado Potato Beetle: Hand-pick or use approved insecticides
            """)
        
        with col2:
            # Disease severity chart for potatoes
            disease_data = pd.DataFrame({
                'Disease': ['Early Blight', 'Late Blight', 'Scab', 'Blackleg'],
                'Frequency': [30, 25, 20, 15],
                'Severity': [7, 9, 5, 8]
            })
            
            fig = px.scatter(disease_data, x='Frequency', y='Severity', 
                           size='Frequency', color='Disease',
                           title='Potato Disease Risk Matrix')
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with care_tabs[2]:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            ### 🌶️ Pepper Care Guide
            
            **Planting:**
            - Start seeds indoors 8-10 weeks before last frost
            - Transplant when night temperatures stay above 55°F (13°C)
            - Space plants 18-24 inches apart
            
            **Watering:**
            - Consistent moisture, about 1 inch per week
            - Avoid water stress during flowering and fruiting
            - Good drainage is essential
            
            **Common Issues:**
            - Bacterial Spot: Use copper-based sprays, improve air circulation
            - Anthracnose: Remove infected fruits, apply fungicides
            - Aphids: Use insecticidal soap or beneficial insects
            """)
        
        with col2:
            # Pepper variety comparison
            pepper_data = pd.DataFrame({
                'Variety': ['Bell Pepper', 'Jalapeño', 'Habanero', 'Cayenne'],
                'Heat_Level': [0, 5, 9, 7],
                'Disease_Resistance': [7, 8, 6, 9],
                'Yield': [8, 9, 6, 7]
            })
            
        

            

            fig = px.line_polar(
                pepper_data,
                r='Disease_Resistance',
                theta='Variety',
                line_close=True,  # Closes the loop for radar shape
                title='🌶️ Pepper Variety Characteristics'
            )
            fig.update_traces(fill='toself')
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 100])  # Adjust range as needed
                ),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white'
            )
            st.plotly_chart(fig, use_container_width=True)



# EXPERT TIPS PAGE
elif selected_page == texts["tips"]:
    st.markdown(f"<h1 style='text-align: center; color: #60a5fa; margin-bottom: 2rem;'>{texts['tips']}</h1>", unsafe_allow_html=True)
    
    # Expert Tips Categories
    tip_categories = st.tabs(["🛡️ Disease Prevention", "🔬 Early Detection", "💊 Treatment Strategies", "🌱 Plant Health"])
    
    with tip_categories[0]:
        st.markdown("## 🛡️ Disease Prevention Strategies")
        
        prevention_tips = [
            {
                "title": "🌿 Crop Rotation",
                "description": "Rotate crops every 2-3 years to break disease cycles and improve soil health.",
                "implementation": ["Plan 3-4 year rotation cycles", "Avoid planting same family crops consecutively", "Keep detailed planting records"],
                "effectiveness": 85
            },
            {
                "title": "💧 Proper Irrigation",
                "description": "Use drip irrigation or soaker hoses to keep foliage dry and reduce disease pressure.",
                "implementation": ["Install drip irrigation systems", "Water early morning", "Avoid overhead sprinklers"],
                "effectiveness": 78
            },
            {
                "title": "🌱 Plant Spacing",
                "description": "Adequate spacing improves air circulation and reduces humid conditions that favor diseases.",
                "implementation": ["Follow recommended spacing guidelines", "Prune overcrowded areas", "Remove weeds regularly"],
                "effectiveness": 72
            },
            {
                "title": "🧹 Garden Sanitation",
                "description": "Remove plant debris and infected material to eliminate disease sources.",
                "implementation": ["Clean up fallen leaves", "Disinfect tools between plants", "Compost only healthy plant material"],
                "effectiveness": 80
            }
        ]
        
        for tip in prevention_tips:
            with st.expander(f"{tip['title']} - {tip['effectiveness']}% Effective"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**Description:** {tip['description']}")
                    st.write("**Implementation Steps:**")
                    for step in tip['implementation']:
                        st.write(f"• {step}")
                
                with col2:
                    # Effectiveness gauge
                    fig = go.Figure(go.Indicator(
                        mode = "gauge+number",
                        value = tip['effectiveness'],
                        title = {'text': "Effectiveness %"},
                        domain = {'x': [0, 1], 'y': [0, 1]},
                        gauge = {
                            'axis': {'range': [None, 100]},
                            'bar': {'color': "#3b82f6"},
                            'steps': [
                                {'range': [0, 50], 'color': "#ef4444"},
                                {'range': [50, 80], 'color': "#f59e0b"},
                                {'range': [80, 100], 'color': "#22c55e"}],
                            'threshold': {
                                'line': {'color': "red", 'width': 4},
                                'thickness': 0.75,
                                'value': 90}}))
                    
                    fig.update_layout(
                        height=200,
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font_color='white'
                    )
                    st.plotly_chart(fig, use_container_width=True)
    
    with tip_categories[1]:
        st.markdown("## 🔬 Early Detection Techniques")
        
        st.markdown("""
        ### 👁️ Visual Inspection Checklist
        
        **Daily Monitoring (5 minutes):**
        - Check for new spots or discoloration on leaves
        - Look for wilting or unusual leaf drop
        - Inspect undersides of leaves for pests or fungi
        - Monitor plant growth and vigor
        
        **Weekly Detailed Inspection (15 minutes):**
        - Photograph suspicious areas for comparison
        - Check soil moisture and drainage
        - Inspect stems and fruits for abnormalities
        - Document any changes in plant health journal
        
        **Environmental Monitoring:**
        - Track temperature and humidity levels
        - Monitor rainfall and irrigation amounts
        - Note changes in weather patterns
        - Record pest activity observations
        """)
        
        # Detection timing chart
        detection_data = pd.DataFrame({
            'Detection_Method': ['Visual Daily', 'Visual Weekly', 'AI Analysis', 'Lab Testing'],
            'Speed_Days': [1, 7, 0.1, 14],
            'Accuracy_Percent': [60, 75, 94, 99],
            'Cost_USD': [0, 0, 2, 50]
        })
        
        fig = px.scatter(detection_data, x='Speed_Days', y='Accuracy_Percent', 
                        size='Cost_USD', color='Detection_Method',
                        title='Detection Method Comparison',
                        labels={'Speed_Days': 'Detection Speed (Days)', 'Accuracy_Percent': 'Accuracy (%)'})
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='white'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with tip_categories[2]:
        st.markdown("## 💊 Treatment Strategies")
        
        treatment_approaches = {
            "🌿 Organic Treatments": {
                "methods": ["Neem oil spray", "Copper sulfate", "Bacillus thuringiensis", "Companion planting"],
                "pros": ["Environmentally friendly", "Safe for beneficial insects", "No chemical residues"],
                "cons": ["Slower acting", "May require repeated applications", "Less effective in severe cases"],
                "cost": "Low to Medium"
            },
            "🧪 Chemical Treatments": {
                "methods": ["Systemic fungicides", "Contact pesticides", "Soil drenches", "Seed treatments"],
                "pros": ["Fast acting", "High effectiveness", "Long-lasting protection"],
                "cons": ["Potential environmental impact", "Resistance development", "Higher cost"],
                "cost": "Medium to High"
            },
            "🔄 Integrated Approach": {
                "methods": ["Combine organic and chemical", "Rotate treatment types", "Use beneficial insects", "Cultural controls"],
                "pros": ["Balanced effectiveness", "Reduced resistance", "Sustainable long-term"],
                "cons": ["More complex management", "Requires more knowledge", "Higher planning needs"],
                "cost": "Medium"
            }
        }
        
        for approach, details in treatment_approaches.items():
            with st.expander(f"{approach} - Cost: {details['cost']}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write("**Methods:**")
                    for method in details['methods']:
                        st.write(f"• {method}")
                
                with col2:
                    st.write("**Advantages:**")
                    for pro in details['pros']:
                        st.write(f"✅ {pro}")
                
                with col3:
                    st.write("**Considerations:**")
                    for con in details['cons']:
                        st.write(f"⚠️ {con}")
    
    with tip_categories[3]:
        st.markdown("## 🌱 Overall Plant Health Optimization")
        
        health_factors = pd.DataFrame({
            'Factor': ['Nutrition', 'Watering', 'Light', 'Air Circulation', 'Soil Health', 'Pest Control'],
            'Current_Score': [7, 8, 9, 6, 7, 8],
            'Target_Score': [9, 9, 9, 8, 9, 9],
            'Priority': [2, 1, 3, 1, 2, 1]
        })
        
        fig = px.bar(health_factors, x='Factor', y=['Current_Score', 'Target_Score'],
                    title='Plant Health Optimization Targets',
                    barmode='group',
                    color_discrete_sequence=['#ef4444', '#22c55e'])
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='white'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("""
        ### 🎯 Quick Health Assessment
        
        Rate your current practices (1-10):
        """)
        
        col1, col2 = st.columns(2)
        with col1:
            nutrition_score = st.slider("🥗 Plant Nutrition", 1, 10, 7)
            watering_score = st.slider("💧 Watering Consistency", 1, 10, 8)
            light_score = st.slider("☀️ Light Exposure", 1, 10, 9)
        
        with col2:
            air_score = st.slider("🌬️ Air Circulation", 1, 10, 6)
            soil_score = st.slider("🌱 Soil Health", 1, 10, 7)
            pest_score = st.slider("🐛 Pest Management", 1, 10, 8)
        
        overall_score = (nutrition_score + watering_score + light_score + air_score + soil_score + pest_score) / 6
        
        st.markdown(f"""
        ### 📊 Your Plant Health Score: {overall_score:.1f}/10
        
        **Recommendations based on your scores:**
        """)
        
        if air_score < 7:
            st.warning("🌬️ **Improve Air Circulation:** Consider pruning, spacing plants better, or adding fans in greenhouse settings.")
        
        if nutrition_score < 8:
            st.info("🥗 **Enhance Nutrition:** Regular soil testing and balanced fertilization can improve plant health significantly.")
        
        if overall_score >= 8.5:
            st.success("🎉 **Excellent!** Your plant care practices are outstanding. Keep up the great work!")
        elif overall_score >= 7:
            st.info("👍 **Good Job!** You're doing well. Focus on the lower-scoring areas for improvement.")
        else:
            st.warning("📈 **Room for Improvement:** Consider focusing on the fundamental care aspects first.")

# SETTINGS PAGE
elif selected_page == texts["settings"]:
    st.markdown(f"<h1 style='text-align: center; color: #60a5fa; margin-bottom: 2rem;'>{texts['settings']}</h1>", unsafe_allow_html=True)
    
    # User Preferences
    st.markdown("## ⚙️ User Preferences")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🔔 Notifications")
        st.session_state.user_preferences['notifications'] = st.checkbox(
            "Enable notifications", 
            value=st.session_state.user_preferences['notifications']
        )
        
        st.markdown("### 🌐 Language Settings")
        st.session_state.user_preferences['auto_translate'] = st.checkbox(
            "Auto-translate treatment advice", 
            value=st.session_state.user_preferences['auto_translate']
        )
        
        st.markdown("### 💾 Data Management")
        st.session_state.user_preferences['save_history'] = st.checkbox(
            "Save analysis history", 
            value=st.session_state.user_preferences['save_history']
        )
    
    with col2:
        st.markdown("### 📊 Analysis History Management")
        
        if st.session_state.analysis_history:
            st.info(f"📈 You have {len(st.session_state.analysis_history)} saved analyses")
            
            if st.button("📥 Export All Data", type="primary"):
                    report_data = {
                        'Timestamp': [analysis.get('timestamp', '') for analysis in st.session_state.analysis_history],
                        'Disease_Detected': [analysis.get('disease_info', {}).get('name', 'Unknown') for analysis in st.session_state.analysis_history],
                        'Confidence': [f"{analysis.get('confidence', 0):.2f}%" for analysis in st.session_state.analysis_history]
                    }
                    
                    report_df = pd.DataFrame(report_data)
                    csv_data = report_df.to_csv(index=False)
                    
                    st.download_button(
                        label="📄 Download Complete Report",
                        data=csv_data,
                        file_name=f"plantcare_analysis_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )

        
    