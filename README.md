# 🌱 KilimoGlow – AI Crop Disease Detection

KilimoGlow is an **AI-powered crop disease detection platform** designed to help **smallholder farmers quickly diagnose plant diseases** using a simple smartphone camera.

Built for the **AgriTech CIO × GDG Datathon**, the system uses computer vision to analyze plant leaf images and provide **instant disease diagnosis and treatment recommendations**.

---

# 🌍 Problem

Plant diseases cause **up to 40% crop losses globally**, and many farmers lack fast access to agricultural experts.

In rural areas, diagnosing crop diseases often involves:

- Waiting for extension officers
- Misidentifying symptoms
- Applying incorrect treatments

Early detection can significantly **improve yields and reduce losses**.

---

# 💡 Solution

KilimoGlow allows farmers to:

1. 📷 Take a photo of a plant leaf  
2. 🤖 AI analyzes the image  
3. 🔎 Detect the disease  
4. 🌿 Receive simple treatment recommendations  

The system focuses on **practical field usability** with a simple and intuitive interface.

---

# 🧠 Model Capabilities

Supported crops:

- 🌽 Potato
- 🌶 Pepper
- 🍅 Tomato

Detected conditions include:

- Healthy plants
- Early Blight
- Late Blight
- Bacterial Spot
- Mosaic Virus

Built with:

- **TensorFlow / Keras**
- **FastAPI**
- **Streamlit / React**
- **Docker**

---

# 🏗 System Architecture

Leaf Image
↓
Frontend (Streamlit / React)
↓
FastAPI Backend
↓
Deep Learning Model
↓
Prediction + Treatment Recommendation


---

# 📁 Project Structure

| Folder | Description |
|------|-------------|
| `backend/` | FastAPI service for model inference |
| `frontend/` | Streamlit or React interface |
| `models/` | Trained model files |
| `main.py` | API initialization |
| `streamlit_app.py` | Frontend demo application |
| `requirements.txt` | Python dependencies |

---

# 🚀 Running the Project

Clone the repository:

```bash
git clone https://github.com/Data-Enthusiast8888/plant-diseases-classification.git
cd plant-diseases-classification

Install dependencies:
pip install -r requirements.txt

Run backend:

cd backend
uvicorn main:app --reload


Run frontend:

cd ../frontend
streamlit run streamlit_app.py

