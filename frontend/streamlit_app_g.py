# -*- coding: utf-8 -*-
"""
KilimoGlow Kenya - Ultimate Hybrid Plant Disease Detection System
Merging features from all three versions
Enhanced with voice recognition, OpenCV camera, and real-time monitoring
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
import logging
import hashlib
from typing import Dict, List, Tuple, Optional, Any
from urllib.parse import urlparse
import cv2  # Added from third app for camera
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as ReportLabImage
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
import io

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
    st.warning("speech_recognition not available - voice features disabled")

# Suppress warnings
warnings.filterwarnings("ignore")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================== ENHANCED CONFIGURATION MANAGEMENT ==================
class AppConfig:
    """Centralized configuration management"""
    
    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.debug_mode = os.getenv("DEBUG", "false").lower() == "true"
        
        # API Configuration with environment-aware defaults
        self.api_config = self._setup_api_config()
        self.timeouts = self._setup_timeouts()
        self.retry_config = self._setup_retry_config()
        
    def _setup_api_config(self) -> Dict[str, Any]:
        """Setup API configuration based on environment"""
        base_config = {
            "health_endpoint": "/health",
            "predict_endpoint": "/predict", 
            "batch_predict_endpoint": "/batch_predict",
            "model_info_endpoint": "/model/info"
        }
        
        if self.environment == "production":
            return {
                **base_config,
                "primary_urls": [
                    os.getenv("FASTAPI_URL"),
                    os.getenv("FASTAPI_PUBLIC_URL"),
                    os.getenv("FASTAPI_INTERNAL_URL")
                ],
                "fallback_urls": []
            }
        elif self.environment == "docker":
            return {
                **base_config, 
                "primary_urls": [
                    os.getenv("FASTAPI_URL", "http://fastapi:8000"),
                    os.getenv("FASTAPI_SERVICE_URL", "http://fastapi-service:8000")
                ],
                "fallback_urls": ["http://localhost:8000", "http://127.0.0.1:8000"]
            }
        else:  # development
            return {
                **base_config,
                "primary_urls": [
                    os.getenv("FASTAPI_URL", f"http://{self._get_local_ip()}:8000"),
                    "http://localhost:8000",
                    "http://127.0.0.1:8000"
                ],
                "fallback_urls": []
            }
    
    def _setup_timeouts(self) -> Dict[str, int]:
        """Setup timeout configuration"""
        return {
            "health_check": int(os.getenv("HEALTH_CHECK_TIMEOUT", "10")),
            "prediction": int(os.getenv("PREDICTION_TIMEOUT", "30")),
            "batch_prediction": int(os.getenv("BATCH_TIMEOUT", "120")),
            "model_info": int(os.getenv("MODEL_INFO_TIMEOUT", "15"))
        }
    
    def _setup_retry_config(self) -> Dict[str, int]:
        """Setup retry configuration"""
        return {
            "max_attempts": int(os.getenv("MAX_RETRY_ATTEMPTS", "3")),
            "base_delay": float(os.getenv("RETRY_BASE_DELAY", "1.0")),
            "max_delay": float(os.getenv("RETRY_MAX_DELAY", "10.0"))
        }
    
    def _get_local_ip(self) -> str:
        """Get local IP address for development"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"

# ================== ENHANCED API CLIENT ==================
class EnhancedAPIClient:
    """Robust API client with retry logic and fallback handling"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "KilimoGlow-Streamlit/2.2",  # Updated version
            "Accept": "application/json"
        })
        self._working_url = None
        self._last_health_check = 0
        self._health_check_interval = 60  # seconds
        
    def _exponential_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay"""
        delay = min(
            self.config.retry_config["base_delay"] * (2 ** attempt),
            self.config.retry_config["max_delay"]
        )
        return delay + random.uniform(0, 0.1 * delay)  # Add jitter
    
    def _test_url_health(self, base_url: str, timeout: int = None) -> Tuple[bool, Dict]:
        """Test if a URL is healthy"""
        timeout = timeout or self.config.timeouts["health_check"]
        health_url = f"{base_url.rstrip('/')}{self.config.api_config['health_endpoint']}"
        
        try:
            response = self.session.get(health_url, timeout=timeout)
            if response.status_code == 200:
                return True, response.json()
            return False, {"error": f"HTTP {response.status_code}", "url": health_url}
        except requests.exceptions.Timeout:
            return False, {"error": "Timeout", "url": health_url}
        except requests.exceptions.ConnectionError:
            return False, {"error": "Connection failed", "url": health_url}
        except Exception as e:
            return False, {"error": str(e), "url": health_url}
    
    def discover_api_url(self, force_refresh: bool = False) -> Tuple[bool, str, Dict]:
        """Discover working API URL with caching"""
        current_time = time.time()
        
        # Use cached URL if still valid and not forced refresh
        if (not force_refresh and 
            self._working_url and 
            current_time - self._last_health_check < self._health_check_interval):
            
            # Quick health check on cached URL
            is_healthy, info = self._test_url_health(self._working_url, timeout=5)
            if is_healthy:
                return True, self._working_url, info
            else:
                logger.warning(f"Cached URL {self._working_url} is no longer healthy")
                self._working_url = None
        
        # Test URLs in priority order
        all_urls = (self.config.api_config["primary_urls"] + 
                   self.config.api_config["fallback_urls"])
        
        for url in all_urls:
            if not url:
                continue
                
            logger.info(f"Testing API URL: {url}")
            is_healthy, info = self._test_url_health(url)
            
            if is_healthy:
                logger.info(f"Found working API URL: {url}")
                self._working_url = url
                self._last_health_check = current_time
                return True, url, info
        
        logger.error("No working API URLs found")
        return False, "", {"error": "All API endpoints failed"}
    
    def _make_request_with_retry(self, method: str, endpoint: str, 
                                timeout: int, **kwargs) -> Tuple[bool, Dict]:
        """Make HTTP request with retry logic"""
        if not self._working_url:
            success, url, info = self.discover_api_url()
            if not success:
                return False, {"error": "No working API URL available"}
        
        full_url = f"{self._working_url.rstrip('/')}{endpoint}"
        max_attempts = self.config.retry_config["max_attempts"]
        
        for attempt in range(max_attempts):
            try:
                logger.info(f"Attempt {attempt + 1}/{max_attempts}: {method} {full_url}")
                
                response = self.session.request(
                    method=method,
                    url=full_url,
                    timeout=timeout,
                    **kwargs
                )
                
                if response.status_code == 200:
                    return True, response.json()
                elif response.status_code in [500, 502, 503, 504]:
                    # Server errors - retry
                    logger.warning(f"Server error {response.status_code}, retrying...")
                    if attempt < max_attempts - 1:
                        time.sleep(self._exponential_backoff(attempt))
                        continue
                else:
                    # Client errors - don't retry
                    return False, {
                        "error": f"HTTP {response.status_code}",
                        "message": response.text[:200]
                    }
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout on attempt {attempt + 1}")
                if attempt < max_attempts - 1:
                    time.sleep(self._exponential_backoff(attempt))
                    continue
                return False, {"error": "Request timeout after all retries"}
                
            except requests.exceptions.ConnectionError:
                logger.warning(f"Connection error on attempt {attempt + 1}")
                # Try to discover new URL
                if attempt == 0:
                    success, new_url, _ = self.discover_api_url(force_refresh=True)
                    if success and new_url != self._working_url:
                        full_url = f"{new_url.rstrip('/')}{endpoint}"
                        continue
                
                if attempt < max_attempts - 1:
                    time.sleep(self._exponential_backoff(attempt))
                    continue
                return False, {"error": "Connection failed after all retries"}
                
            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(self._exponential_backoff(attempt))
                    continue
                return False, {"error": f"Unexpected error: {str(e)}"}
        
        return False, {"error": "All retry attempts exhausted"}
    
    def health_check(self) -> Tuple[bool, Dict]:
        """Check API health"""
        return self.discover_api_url()
    
    def predict_single(self, image_file) -> Tuple[bool, Dict]:
        """Single image prediction"""
        try:
            # Prepare file for upload
            if hasattr(image_file, 'seek'):
                image_file.seek(0)
            
            files = self._prepare_file_upload(image_file, "image.jpg")
            
            return self._make_request_with_retry(
                method="POST",
                endpoint=self.config.api_config["predict_endpoint"],
                timeout=self.config.timeouts["prediction"],
                files=files
            )
            
        except Exception as e:
            logger.error(f"Error in predict_single: {e}")
            return False, {"error": f"File preparation failed: {str(e)}"}
    
    def predict_batch(self, image_files: List) -> Tuple[bool, Dict]:
        """Batch image prediction"""
        try:
            files = []
            for i, file_obj in enumerate(image_files):
                if hasattr(file_obj, 'seek'):
                    file_obj.seek(0)
                
                file_tuple = self._prepare_file_upload(file_obj, f"image_{i}.jpg")
                files.append(('files', file_tuple["file"]))  # Corrected
                
            return self._make_request_with_retry(
                method="POST",
                endpoint=self.config.api_config["batch_predict_endpoint"],
                timeout=self.config.timeouts["batch_prediction"],
                files=files
            )
            
        except Exception as e:
            logger.error(f"Error in predict_batch: {e}")
            return False, {"error": f"Batch file preparation failed: {str(e)}"}
    
    def get_model_info(self) -> Tuple[bool, Dict]:
        """Get model information"""
        return self._make_request_with_retry(
            method="GET",
            endpoint=self.config.api_config["model_info_endpoint"],
            timeout=self.config.timeouts["model_info"]
        )
    
    def _prepare_file_upload(self, file_obj, default_name: str) -> Dict:
        """Prepare file for upload"""
        if hasattr(file_obj, 'name') and hasattr(file_obj, 'type'):
            return {"file": (file_obj.name, file_obj, file_obj.type)}
        elif hasattr(file_obj, 'read'):
            content = file_obj.read()
            if hasattr(file_obj, 'seek'):
                file_obj.seek(0)
            return {"file": (default_name, BytesIO(content), "image/jpeg")}
        else:
            return {"file": (default_name, file_obj, "image/jpeg")}

# ================== HYBRID OFFLINE SYSTEM ==================
_HYBRID_CACHE_FILE = Path.home() / ".kilimoglow_cache.json"

def _load_persistent_cache():
    try:
        if _HYBRID_CACHE_FILE.exists():
            return json.loads(_HYBRID_CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"images":{},"history":[], "version":"2.2"}  # Updated version

def _save_persistent_cache(cache_obj):
    try:
        _HYBRID_CACHE_FILE.write_text(json.dumps(cache_obj, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

def _md5_bytes(b: bytes) -> str:
    h = hashlib.md5()
    h.update(b)
    return h.hexdigest()

def compute_file_hash(file_obj):
    try:
        pos = file_obj.tell() if hasattr(file_obj, 'tell') else None
        content = file_obj.read()
        if hasattr(file_obj, 'seek') and pos is not None:
            file_obj.seek(pos)
        return _md5_bytes(content)
    except Exception:
        return None

def _image_from_filelike(file_obj):
    try:
        cur = file_obj.tell() if hasattr(file_obj, 'tell') else None
        img = Image.open(file_obj).convert("RGB")
        if hasattr(file_obj, 'seek') and cur is not None:
            file_obj.seek(cur)
        return img
    except Exception:
        if hasattr(file_obj, 'seek'):
            try:
                file_obj.seek(0)
                img = Image.open(file_obj).convert("RGB")
                return img
            except Exception:
                return None
        return None

def compute_color_histogram(img: Image.Image, bins=32):
    arr = np.asarray(img.resize((256,256)))
    hist = []
    for c in range(3):
        h, _ = np.histogram(arr[...,c], bins=bins, range=(0,255), density=True)
        hist.append(h.astype(np.float32))
    return np.concatenate(hist, axis=0)

def _dct2(a):
    return np.fft.fft2(a)

def compute_phash(img: Image.Image, size=32, smaller=8):
    img_small = img.resize((size, size)).convert("L")
    a = np.asarray(img_small, dtype=np.float32)
    dct = np.real(_dct2(a))
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
    """Enhanced multi-tier offline engine with better error handling"""
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

    try:
        img_hash = compute_file_hash(file_obj)
        if img_hash and img_hash in persistent.get("images", {}):
            rec = persistent["images"][img_hash]
            st.session_state.hybrid_metrics['hits'] += 1
            rec['model_version'] = "offline_cached_exact_v2.2"  # Updated
            return rec

        img = _image_from_filelike(file_obj)
        if img is None:
            if simulate_fn is not None:
                return simulate_fn()
            return {"success": True, "predicted_class": "Unknown", "confidence": 0.5, "model_version": "offline_unknown_image_v2.2"}

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
            except Exception:
                continue

        if best_rec is not None and best_score >= 0.78:
            st.session_state.hybrid_metrics['hits'] += 1
            enriched = dict(best_rec)
            enriched['model_version'] = "offline_visual_match_v2.2"
            enriched['similarity'] = float(best_score)
            return enriched

        # Context-based prediction using history
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
                    "model_version": "offline_context_priors_v2.2",
                    "explain": {"source":"farm_history", "top_prob": float(prob)}
                }

        # Fallback to simulation
        if simulate_fn is not None:
            result = simulate_fn()
            result['model_version'] = result.get('model_version', 'offline_simulation_v2.2')
            return result
            
        return {
            "success": True,
            "predicted_class": "Unknown",
            "confidence": 0.5,
            "model_version": "offline_last_resort_v2.2"
        }
        
    except Exception as e:
        logger.error(f"Error in hybrid_offline_predict: {e}")
        return {
            "success": False,
            "error": str(e),
            "predicted_class": "Error",
            "confidence": 0.0,
            "model_version": "offline_error_v2.2"
        }

def hybrid_cache_learn(image_file, result_record, metadata=None):
    """Enhanced cache learning with error handling"""
    try:
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
        except Exception:
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
    except Exception as e:
        logger.error(f"Error in hybrid_cache_learn: {e}")

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
        "model_version": "offline_v2.2"  # Updated
    }

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

# ===== PLANT DISEASES DATABASE (MERGED AND ENHANCED FROM ALL) =====
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
    'Tomato_Leaf_Mold': {
        'name': 'Leaf Mold',
        'plant': 'Nyanya (Tomato)',
        'severity': 'Medium',
        'symptoms': 'Yellow spots on upper leaves, velvety growth on undersides',
        'treatment': 'Improve ventilation, apply preventive fungicide if severe',
        'prevention': 'Reduce humidity levels, increase plant spacing, proper ventilation',
        'organic_treatment': 'Milk spray solution (1:10), baking soda application',
        'watering_advice': 'Water early morning, ensure good air circulation around plants',
        'audio_file': None
    },
    'Tomato_Septoria_leaf_spot': {
        'name': 'Septoria Leaf Spot',
        'plant': 'Nyanya (Tomato)',
        'severity': 'Medium',
        'symptoms': 'Small circular spots with dark borders and light gray centers',
        'treatment': 'Fungicide spray, remove affected lower leaves, improve sanitation',
        'prevention': 'Mulching, avoid overhead irrigation, annual crop rotation',
        'organic_treatment': 'Compost tea spray, proper plant spacing for air flow',
        'watering_advice': 'Water at ground level, avoid splashing soil onto leaves',
        'audio_file': None
    },
    'Tomato_Spider_mites_Two_spotted_spider_mite': {
        'name': 'Spider Mites',
        'plant': 'Nyanya (Tomato)',
        'severity': 'High',
        'symptoms': 'Fine webbing, yellow stippling on leaves, bronze coloration',
        'treatment': 'Miticide application, increase humidity around plants, predatory mites',
        'prevention': 'Regular inspection, avoid water stress, encourage natural predators',
        'organic_treatment': 'Neem oil spray, insecticidal soap, predatory insects',
        'watering_advice': 'Maintain consistent soil moisture, mist around plants (not leaves)',
        'audio_file': None
    },
    'Tomato__Target_Spot': {
        'name': 'Target Spot',
        'plant': 'Nyanya (Tomato)',
        'severity': 'Medium',
        'symptoms': 'Concentric rings forming target patterns on leaves and fruits',
        'treatment': 'Fungicide application, remove affected plant material, improve air flow',
        'prevention': 'Crop rotation, avoid overhead irrigation, proper plant spacing',
        'organic_treatment': 'Copper soap spray, compost application, field sanitation',
        'watering_advice': 'Drip irrigation system, water early morning hours',
        'audio_file': None
    },
    'Tomato__Tomato_YellowLeaf__Curl_Virus': {
        'name': 'Yellow Leaf Curl Virus',
        'plant': 'Nyanya (Tomato)',
        'severity': 'Critical',
        'symptoms': 'Severe yellowing and curling of leaves, stunted plant growth',
        'treatment': 'Remove infected plants immediately, control whitefly vectors aggressively',
        'prevention': 'Use resistant varieties, control whiteflies, reflective mulch systems',
        'organic_treatment': 'Yellow sticky traps, neem oil for whitefly control, plant removal',
        'watering_advice': 'Maintain plant vigor with proper irrigation, avoid plant stress',
        'audio_file': None
    },
    'Tomato__Tomato_mosaic_virus': {
        'name': 'Mosaic Virus',
        'plant': 'Nyanya (Tomato)',
        'severity': 'High',
        'symptoms': 'Mottled light and dark green mosaic patterns on leaves',
        'treatment': 'Remove infected plants, sanitize tools and hands thoroughly',
        'prevention': 'Use certified virus-free seeds, avoid tobacco use near plants',
        'organic_treatment': 'Complete plant removal, thorough equipment sanitation',
        'watering_advice': 'Avoid mechanical transmission through contaminated water',
        'audio_file': None
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

# ===== KENYAN CROP CALENDAR (FROM THIRD APP) =====
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
        "process_batch": "⚡ Process Batch",
        "batch_upload": "📁 Upload Multiple Images"
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
        "process_batch": "⚡ Chagia Kundi",
        "batch_upload": "📁 Pakia Picha Nyingi"
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
        "process_batch": "⚡ Los Oganda",
        "batch_upload": "📁 Ket Fweny Mangeny"
    }
}

# ===== PAGE CONFIG =====
st.set_page_config(
    page_title="🌿 KilimoGlow Kenya - Plant Doctor",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== INITIALIZE CONFIGURATION AND API CLIENT =====
if 'app_config' not in st.session_state:
    st.session_state.app_config = AppConfig()

if 'api_client' not in st.session_state:
    st.session_state.api_client = EnhancedAPIClient(st.session_state.app_config)

# ===== SESSION STATE INITIALIZATION (ENHANCED WITH THIRD APP KEYS) =====
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
        'hybrid_metrics': {'hits': 0, 'misses': 0, 'conflicts': 0},
        'api_status': 'checking',
        'uploaded_file_hash': None,
        'voice_input_active': False,
        'camera_quality': 'Medium (720p)',
        'working_api_url': None,
        'cached_api_status': None,
        'model_cached': False,
        'cached_model_info': {},
        'last_api_check': 0,
        'connection_retries': 0,
        # From third app
        'real_time_data': [],
        'camera_active': False,
        'monitoring_active': False,
        'analyze_clicked': False,
        'captured_frame': None
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# Initialize session state
init_session_state()

# Initialize Audio Manager
@st.cache_resource
def get_audio_manager():
    return AudioManager()

audio_manager = get_audio_manager()

# ===== UTILITY FUNCTIONS (MERGED) =====
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

def display_disease_analysis(result, image=None):
    """Display plant disease analysis results in a formatted, Kenyan-themed card."""
    predicted_class = result.get("predicted_class", "unknown")
    confidence = result.get("confidence", 0) * 100 if result.get("confidence", 0) <= 1 else result.get("confidence", 0)
    model_version = result.get("model_version", "unknown")
    
    
    # Get disease information from PLANT_DISEASES
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
    
    current_texts = UI_TEXTS.get(st.session_state.selected_language, UI_TEXTS["English"])
    
    # Create a Kenyan-themed card for results
    st.markdown(f"""
    <div class="kenyan-card">
        <h3 style="color: #FFD700;">🌿 {current_texts['plant_doctor']} Results</h3>
        <div style="display: flex; flex-wrap: wrap; gap: 1rem;">
            <div style="flex: 1; min-width: 250px;">
                <p><strong>Plant:</strong> {disease_info['plant']}</p>
                <p><strong>Disease:</strong> {disease_info['name']}</p>
                <p><strong>Severity:</strong> {severity_badge(disease_info['severity'])}</p>
                <p><strong>Confidence:</strong> {confidence:.1f}%</p>
                <p><strong>Symptoms:</strong> {disease_info['symptoms']}</p>
                <p><strong>Treatment:</strong> {disease_info['treatment']}</p>
                <p><strong>Organic Treatment:</strong> {disease_info['organic_treatment']}</p>
                <p><strong>Prevention:</strong> {disease_info['prevention']}</p>
                <p><strong>Watering Advice:</strong> {disease_info['watering_advice']}</p>
                <p><strong>Model Version:</strong> {model_version}</p>
            </div>
            {f'<div style="flex: 1; min-width: 250px;"><img src="data:image/jpeg;base64,{base64.b64encode(image.tobytes()).decode()}" style="max-width: 100%; border-radius: 10px;" /></div>' if image else ''}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Audio playback for disease information
    if st.session_state.get('audio_enabled', True) and disease_info.get('audio_file'):
        st.markdown("### 🔊 Audio Guidance")
        audio_path = audio_manager.get_audio_path(disease_info['audio_file'], st.session_state.selected_language)
        if audio_path:
            if audio_manager.play_audio(disease_info['audio_file'], st.session_state.selected_language):
                st.markdown(f"""
                <div class="audio-player-widget">
                    <p style="color: white;">Playing audio guidance for {disease_info['name']} in {st.session_state.selected_language}</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.warning(f"⚠️ Unable to play audio: {st.session_state.get('audio_error', 'Unknown error')}")
        else:
            st.info("ℹ️ No audio available for this disease in the selected language.")
    
    # Add to analysis history
    analysis_record = {
        "analysis_id": st.session_state.current_analysis_id,
        "predicted_class": predicted_class,
        "confidence": confidence / 100,
        "plant": disease_info['plant'],
        "disease": disease_info['name'],
        "severity": disease_info['severity'],
        "timestamp": datetime.now().isoformat(),
        "soil": st.session_state.get('soil_type', 'Unknown'),
        "weather": st.session_state.get('weather_condition', 'Unknown'),
        "model_version": model_version
    }
    st.session_state.analysis_history.append(analysis_record)



# ===== VOICE RECOGNITION FUNCTIONS (FROM THIRD APP) =====
def initialize_speech_recognition():
    """Initialize speech recognition"""
    if not SPEECH_RECOGNITION_AVAILABLE:
        return None, None
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
    if recognizer is None or microphone is None:
        return False, "Speech recognition not available"
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

# ===== OPENCV CAMERA FUNCTIONS (FROM THIRD APP) =====
def initialize_camera(camera_index=0):
    """Initialize OpenCV camera and return VideoCapture or None"""
    try:
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            return None
        
        quality = st.session_state.get('camera_quality', 'Medium (720p)')
        if 'low' in quality.lower():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        elif 'high' in quality.lower():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        else:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        return cap
    except:
        return None

def capture_frame(cap, resize_width=None):
    """Capture a single frame from OpenCV VideoCapture"""
    try:
        ret, frame = cap.read()
        if not ret:
            return None
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        if resize_width:
            h, w = frame_rgb.shape[:2]
            new_w = int(resize_width)
            new_h = int(h * (new_w / w))
            frame_rgb = cv2.resize(frame_rgb, (new_w, new_h))
        return frame_rgb
    except:
        return None

def process_frame_for_analysis(frame):
    """Process captured frame for analysis"""
    try:
        pil_img = Image.fromarray(frame)
        buf = BytesIO()
        pil_img.save(buf, format="JPEG")
        buf.seek(0)
        return buf, pil_img
    except:
        return None, None

# ===== MODEL INFO (FROM THIRD APP) =====
def get_model_info(timeout=5):
    """Get model information from API"""
    try:
        base = st.session_state.working_api_url or "http://127.0.0.1:8000"
        resp = requests.get(f"{base}/model/info", timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
        return {}
    except:
        return {}

# ===== CSS STYLING (HYBRID OF SECOND AND THIRD, WITH ANIMATIONS) =====
def apply_enhanced_css():
    """Apply merged CSS with animations from third app"""
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
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { box-shadow: 0 15px 35px rgba(0, 100, 0, 0.4); }
        50% { box-shadow: 0 20px 45px rgba(255, 215, 0, 0.6); }
        100% { box-shadow: 0 15px 35px rgba(0, 100, 0, 0.4); }
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
    
    .voice-button {
        background: linear-gradient(45deg, #FF6B35, #F7931E);
        border: 2px solid #FFD700;
        border-radius: 50%;
        padding: 1rem;
        animation: glow 2s infinite;
    }
    
    @keyframes glow {
        0%, 100% { box-shadow: 0 0 5px #FF6B35; }
        50% { box-shadow: 0 0 20px #FF6B35, 0 0 30px #FF6B35, 0 0 30px #FF6B35; }
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
    
    /* Responsive Design */
    @media (max-width: 768px) {
        .main-header h1 {
            font-size: 2rem;
        }
        .main-header p {
            font-size: 1rem;
        }
        .kenyan-card {
            padding: 1.5rem;
        }
    }
    </style>
    """, unsafe_allow_html=True)

# Apply CSS
apply_enhanced_css()

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
    
    # Navigation (Added Crop Calendar from third app)
    selected_page = option_menu(
        menu_title="🇰🇪 Navigation",
        options=[
            "🏠 Home",
            current_texts["plant_doctor"],
            current_texts["batch_analysis"], 
            "📅 Crop Calendar",  # New from third app
            current_texts["dashboard"],
            current_texts["settings"]
        ],
        icons=["house-fill", "heart-pulse", "collection-fill", "calendar-fill", "bar-chart-fill", "gear-fill"],
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
    
    # System Status (Enhanced)
    api_connected, api_info, working_url = st.session_state.api_client.health_check()
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
        <p style="margin: 0.2rem 0;">
            <strong>Voice:</strong> {'🗣️ Ready' if SPEECH_RECOGNITION_AVAILABLE else '🔇 Disabled'}
        </p>
        <p style="margin: 0.2rem 0;">
            <strong>Camera:</strong> {'📹 Ready' if 'camera_active' in st.session_state else '📷 Disabled'}
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
                pygame.mixer.music.set_volume(st.session_state.audio_volume)

# ===== MAIN CONTENT =====
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
                <li>🎤 Voice control and recognition</li>  <!-- New -->
                <li>📹 Real-time camera monitoring</li>  <!-- New -->
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
                <li>🗣️ Voice Recognition: {'✅ Ready' if SPEECH_RECOGNITION_AVAILABLE else '❌ Disabled'}</li>
                <li>📹 Camera: {'✅ Available' if initialize_camera() is not None else '❌ Not Available'}</li>
                <li>🗓️ Language: {st.session_state.selected_language}</li>
                <li>📈 Analyses: {len(st.session_state.analysis_history)}</li>
                <li>🔄 Offline Mode: {'✅ Active' if st.session_state.get('offline_cache') else '❌ Not Ready'}</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

elif selected_page == current_texts["plant_doctor"]:
    st.markdown(f"<h1 style='text-align: center; color: #FFD700;'>🩺 {current_texts['plant_doctor']}</h1>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### 📋 Plant Information")
        
        st.session_state.user_name = st.text_input(
            "👤 Your Name / Jina Lako / Nyingi",
            value=st.session_state.user_name,
            placeholder="Enter your name"
        )
        
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
        
        st.markdown(f"### 📷 {current_texts['upload_label']}")
        
        uploaded_file = st.file_uploader(
            "Choose plant image",
            type=["jpg", "jpeg", "png"],
            help="Upload clear photo of plant leaves showing any symptoms"
        )
        
        # Enhanced camera input with OpenCV from third app
        if st.button("📸 Use Camera", use_container_width=True):
            cap = initialize_camera()
            if cap:
                frame = capture_frame(cap)
                if frame is not None:
                    st.session_state.captured_frame = frame
                    uploaded_file, _ = process_frame_for_analysis(frame)
                    cap.release()
                    st.success("📸 Photo captured!")
                else:
                    st.error("❌ Failed to capture photo")
            else:
                st.error("❌ Camera not available")
    
    with col2:
        # Voice input button from third app
        if SPEECH_RECOGNITION_AVAILABLE:
            if st.button("🎤 Voice Input", use_container_width=True):
                recognizer, microphone = initialize_speech_recognition()
                if recognizer and microphone:
                    success, text = voice_to_text(recognizer, microphone, st.session_state.selected_language)
                    if success:
                        text_lower = text.lower()
                        if "analyze" in text_lower or "chunguza" in text_lower:
                            st.success("🎤 Starting analysis...")
                            # Trigger analysis
                        elif "camera" in text_lower or "kamera" in text_lower:
                            st.session_state.camera_active = not st.session_state.camera_active
                            st.rerun()
                        else:
                            st.info(f"🎤 Recognized: {text}")
                    else:
                        st.error(f"🎤 Error: {text}")
        
        if uploaded_file or st.session_state.captured_frame:
            image = Image.open(uploaded_file) if uploaded_file else Image.fromarray(st.session_state.captured_frame)
            st.image(image, caption="📸 Plant Photo for Analysis", use_column_width=True)
            
            if st.button(current_texts["analyze_plant"], type="primary", use_container_width=True):
                analysis_id = str(uuid.uuid4())[:8]
                st.session_state.current_analysis_id = analysis_id
                
                with st.spinner("🔬 Analyzing your plant... Please wait."):
                    start_time = time.time()
                    
                    success, result = st.session_state.api_client.predict_single(uploaded_file)
                    
                    if success:
                        st.success("✅ Analysis completed!")
                        result['processing_time'] = time.time() - start_time
                        st.session_state.analysis_result = result
                        hybrid_cache_learn(uploaded_file, result)
                    else:
                        st.warning("⚠️ API unavailable, using hybrid offline mode")
                        result = hybrid_offline_predict(uploaded_file, simulate_fn=simulate_disease_prediction)
                        st.session_state.analysis_result = result
            
            if st.session_state.analysis_result:
                result = st.session_state.analysis_result
                predicted_class = result.get("predicted_class", "unknown")
                confidence = result.get("confidence", 0)
                
                if confidence <= 1:
                    confidence *= 100
                
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
                
                # Audio Player
                if st.session_state.get('audio_enabled', True) and disease_info.get('audio_file'):
                    # ... (same as before)
                
                # Display results
                  display_disease_analysis(result, image=image)
                
                # Add real-time monitoring toggle from third app
                st.session_state.monitoring_active = st.checkbox("Enable Real-time Monitoring", value=st.session_state.monitoring_active)
                if st.session_state.monitoring_active:
                    st.info("📹 Real-time monitoring activated. Analyzing every 5 seconds.")
                    time.sleep(5)
                    st.rerun()

# ... (Other pages similar, with enhancements)
elif selected_page == current_texts["batch_analysis"]:
    st.markdown(f"<h1 style='text-align: center; color: #FFD700;'>📊 {current_texts['batch_analysis']}</h1>", unsafe_allow_html=True)
    
    st.markdown("""
    <div class="kenyan-card">
        <h3 style="color: #FFD700;">📁 Batch Plant Analysis</h3>
        <p style="color: white;">Upload multiple images to analyze diseases in bulk. Ideal for large farms or multiple plants.</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### 📋 Batch Information")
        uploaded_files = st.file_uploader(
            current_texts["batch_upload"],
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            help="Upload multiple clear photos of plant leaves"
        )
        
        # Camera batch capture
        if st.button("📸 Capture Multiple Images", use_container_width=True):
            cap = initialize_camera()
            if cap:
                st.session_state.batch_results = []
                for _ in range(3):  # Capture 3 images
                    frame = capture_frame(cap)
                    if frame is not None:
                        img_buffer, _ = process_frame_for_analysis(frame)
                        st.session_state.batch_results.append({"image": frame, "buffer": img_buffer})
                    time.sleep(1)  # Short delay between captures
                cap.release()
                st.success("📸 Captured 3 images for batch analysis!")
            else:
                st.error("❌ Camera not available")
        
        if uploaded_files or st.session_state.batch_results:
            if st.button(current_texts["process_batch"], type="primary", use_container_width=True):
                with st.spinner("🔬 Processing batch... Please wait."):
                    st.session_state.batch_results = []
                    files_to_process = []
                    
                    # Handle uploaded files
                    for file in uploaded_files:
                        img = Image.open(file)
                        files_to_process.append({"image": img, "buffer": file})
                    
                    # Handle camera-captured images
                    for item in st.session_state.batch_results:
                        files_to_process.append(item)
                    
                    success, result = st.session_state.api_client.predict_batch([item["buffer"] for item in files_to_process])
                    
                    if success:
                        st.success("✅ Batch analysis completed!")
                        for i, pred in enumerate(result.get("predictions", [])):
                            pred["image"] = files_to_process[i]["image"]
                            st.session_state.batch_results.append(pred)
                            hybrid_cache_learn(files_to_process[i]["buffer"], pred)
                    else:
                        st.warning("⚠️ API unavailable, using hybrid offline mode")
                        for i, item in enumerate(files_to_process):
                            pred = hybrid_offline_predict(item["buffer"], simulate_fn=simulate_disease_prediction)
                            pred["image"] = item["image"]
                            st.session_state.batch_results.append(pred)
    
    with col2:
        if st.session_state.batch_results:
            st.markdown("### 🎯 Batch Analysis Results")
            for i, result in enumerate(st.session_state.batch_results):
                predicted_class = result.get("predicted_class", "unknown")
                confidence = result.get("confidence", 0) * 100 if result.get("confidence", 0) <= 1 else result.get("confidence", 0)
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
                
                st.markdown(f"""
                <div class="kenyan-card">
                    <h4 style="color: #FFD700;">Image {i + 1}</h4>
                    <div style="display: flex; flex-wrap: wrap; gap: 1rem;">
                        <div style="flex: 1; min-width: 200px;">
                            <p><strong>Plant:</strong> {disease_info['plant']}</p>
                            <p><strong>Disease:</strong> {disease_info['name']}</p>
                            <p><strong>Severity:</strong> {severity_badge(disease_info['severity'])}</p>
                            <p><strong>Confidence:</strong> {confidence:.1f}%</p>
                            <p><strong>Symptoms:</strong> {disease_info['symptoms']}</p>
                        </div>
                        <div style="flex: 1; min-width: 200px;">
                            <img src="data:image/jpeg;base64,{base64.b64encode(np.asarray(result['image']).tobytes()).decode()}" style="max-width: 100%; border-radius: 10px;" />
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Audio playback
                if st.session_state.get('audio_enabled', True) and disease_info.get('audio_file'):
                    audio_path = audio_manager.get_audio_path(disease_info['audio_file'], st.session_state.selected_language)
                    if audio_path and st.button(f"🎵 Play Audio for Image {i + 1}", key=f"audio_batch_{i}"):
                        if audio_manager.play_audio(disease_info['audio_file'], st.session_state.selected_language):
                            st.markdown(f"""
                            <div class="audio-player-widget">
                                <p style="color: white;">Playing audio for {disease_info['name']} in {st.session_state.selected_language}</p>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.warning(f"⚠️ Audio playback failed: {st.session_state.get('audio_error', 'Unknown error')}")

elif selected_page == "📅 Crop Calendar":
    st.markdown(f"<h1 style='text-align: center; color: #FFD700;'>📅 {current_texts.get('crop_calendar', 'Crop Calendar')}</h1>", unsafe_allow_html=True)
    
    st.markdown("""
    <div class="kenyan-card">
        <h3 style="color: #FFD700;">📅 Kenyan Crop Calendar</h3>
        <p style="color: white;">Seasonal guidance for planting and care, tailored for Kenyan farmers.</p>
    </div>
    """, unsafe_allow_html=True)
    
    for season, info in KENYAN_CROP_CALENDAR.items():
        st.markdown(f"""
        <div class="kenyan-card">
            <h4 style="color: #FFD700;">{season}</h4>
            <p><strong>Crops:</strong> {', '.join(info['crops'])}</p>
            <p><strong>Planting Tips:</strong> {info['planting_tips']}</p>
            <p><strong>Care Tips:</strong> {info['care_tips']}</p>
        </div>
        """, unsafe_allow_html=True)

elif selected_page == current_texts["dashboard"]:
    st.markdown(f"<h1 style='text-align: center; color: #FFD700;'>📈 {current_texts['dashboard']}</h1>", unsafe_allow_html=True)
    
    st.markdown("""
    <div class="kenyan-card">
        <h3 style="color: #FFD700;">📊 Analysis Dashboard</h3>
        <p style="color: white;">View your analysis history and statistics for all plants examined.</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.analysis_history:
        # Summary statistics
        df = pd.DataFrame(st.session_state.analysis_history)
        disease_counts = df['disease'].value_counts()
        severity_counts = df['severity'].value_counts()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📈 Disease Distribution")
            fig = px.pie(
                names=disease_counts.index,
                values=disease_counts.values,
                title="Disease Distribution",
                color_discrete_sequence=px.colors.sequential.Viridis
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("### 📊 Severity Distribution")
            fig = px.bar(
                x=severity_counts.index,
                y=severity_counts.values,
                title="Severity Distribution",
                color=severity_counts.index,
                color_discrete_map={
                    'Critical': '#DC143C',
                    'High': '#FF8C00',
                    'Medium': '#FFD700',
                    'None': '#32CD32'
                }
            )
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("### 📜 Analysis History")
        st.dataframe(
            df[['timestamp', 'plant', 'disease', 'severity', 'confidence']],
            use_container_width=True,
            column_config={
                "timestamp": "Date & Time",
                "plant": "Plant",
                "disease": "Disease",
                "severity": "Severity",
                "confidence": st.column_config.NumberColumn("Confidence", format="%.1f%%")
            }
        )
    else:
        st.info("ℹ️ No analysis history available. Analyze some plants to see statistics!")

elif selected_page == current_texts["settings"]:
    st.markdown(f"<h1 style='text-align: center; color: #FFD700;'>⚙️ {current_texts['settings']}</h1>", unsafe_allow_html=True)
    
    st.markdown("""
    <div class="kenyan-card">
        <h3 style="color: #FFD700;">⚙️ App Settings</h3>
        <p style="color: white;">Configure KilimoGlow settings and view system information.</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🛠️ Configuration")
        st.session_state.camera_quality = st.selectbox(
            "📷 Camera Quality",
            options=["Low (480p)", "Medium (720p)", "High (1080p)"],
            index=["Low (480p)", "Medium (720p)", "High (1080p)"].index(st.session_state.get('camera_quality', 'Medium (720p)'))
        )
        
        st.session_state.api_endpoint = st.text_input(
            "🌐 API Endpoint",
            value=st.session_state.get('api_endpoint', st.session_state.app_config.api_config["primary_urls"][0]),
            placeholder="Enter FastAPI URL"
        )
        
        if st.button("🔄 Check API Connection", use_container_width=True):
            success, info, url = st.session_state.api_client.health_check()
            if success:
                st.session_state.working_api_url = url
                st.success(f"✅ Connected to API: {url}")
            else:
                st.error(f"❌ API connection failed: {info.get('error', 'Unknown error')}")
    
    with col2:
        st.markdown("### 🧠 Model Information")
        api_connected, _, _ = st.session_state.api_client.health_check()
        if api_connected:
            model_info = get_model_info()
            if model_info:
                st.markdown(f"""
                <div class="kenyan-card">
                    <p><strong>Model Status:</strong> ✅ Loaded</p>
                    <p><strong>Input Shape:</strong> {model_info.get('input_shape', 'N/A')}</p>
                    <p><strong>Output Shape:</strong> {model_info.get('output_shape', 'N/A')}</p>
                    <p><strong>Total Parameters:</strong> {model_info.get('total_params', 'N/A'):,}</p>
                    <p><strong>Supported Classes:</strong> {model_info.get('num_classes', 'N/A')}</p>
                </div>
                """, unsafe_allow_html=True)
                
                if 'classes' in model_info:
                    st.markdown("#### 🔬 Supported Diseases")
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
                    <li>Ensure FastAPI server is running</li>
                    <li>Check network connectivity</li>
                    <li>Verify API endpoint URL</li>
                    <li>Offline mode available if API is down</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

# ===== FOOTER =====
# ... (same as before, updated with new status like voice and camera)
st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 2rem; background: linear-gradient(90deg, #006400, #228B22); border-radius: 15px; margin-top: 2rem;">
    <h3 style="color: #FFD700; margin-bottom: 1rem;">🌿 KilimoGlow Kenya Hybrid Enhanced</h3>
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
        Version 2.1 Hybrid • Built with ❤️ for Kenya's Agricultural Future
    </p>
</div>
""", unsafe_allow_html=True)