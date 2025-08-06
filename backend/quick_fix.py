# quick_fix.py - Run this to quickly set up everything
import os
import requests
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Conv2D, MaxPooling2D, Flatten, Dropout

def create_directories():
    """Create necessary directories"""
    os.makedirs("models", exist_ok=True)
    os.makedirs("backend", exist_ok=True)
    os.makedirs("frontend", exist_ok=True)
    print("✅ Directories created")

def create_test_model():
    """Create a test model"""
    CLASS_NAMES = [
        'Pepper__bell___Bacterial_spot', 'Pepper__bell___healthy',
        'Potato___Early_blight', 'Potato___Late_blight', 'Potato___healthy',
        'Tomato_Bacterial_spot', 'Tomato_Early_blight', 'Tomato_Late_blight',
        'Tomato_Leaf_Mold', 'Tomato_Septoria_leaf_spot',
        'Tomato_Spider_mites_Two_spotted_spider_mite', 'Tomato__Target_Spot',
        'Tomato__Tomato_YellowLeaf__Curl_Virus', 'Tomato__Tomato_mosaic_virus',
        'Tomato___healthy'
    ]
    
    model = Sequential([
        Conv2D(32, (3, 3), activation='relu', input_shape=(224, 224, 3)),
        MaxPooling2D(2, 2),
        Conv2D(64, (3, 3), activation='relu'),
        MaxPooling2D(2, 2),
        Flatten(),
        Dense(512, activation='relu'),
        Dense(len(CLASS_NAMES), activation='softmax')
    ])
    
    model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
    model.save("models/plant_disease_model.h5")
    print("✅ Test model created")

def test_api_connection():
    """Test if FastAPI is running"""
    try:
        response = requests.get("http://127.0.0.1:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ FastAPI backend is running")
            return True
        else:
            print(f"❌ FastAPI returned status: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ FastAPI backend is not running")
        print("💡 Start it with: python main.py")
        return False
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

def main():
    print("🔧 PlantCare AI Quick Fix")
    print("=" * 30)
    
    # Step 1: Create directories
    create_directories()
    
    # Step 2: Create test model if it doesn't exist
    if not os.path.exists("models/plant_disease_model.h5"):
        print("📝 Creating test model...")
        create_test_model()
    else:
        print("✅ Model file already exists")
    
    # Step 3: Test API connection
    print("🔍 Testing API connection...")
    test_api_connection()
    
    print("\n🎯 Next Steps:")
    print("1. Make sure FastAPI is running: python main.py")
    print("2. Start Streamlit: streamlit run streamlit_app.py")
    print("3. Upload an image and test the prediction")

if __name__ == "__main__":
    main()