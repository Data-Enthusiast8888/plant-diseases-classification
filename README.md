# 🌱 Plant Disease Classifier: Potato, Pepper & Tomato

A modular image classification system built for diagnosing **crop diseases** in real-world agricultural settings. With support for **potato**, **pepper**, and **tomato**, this tool bridges robust machine learning with emotionally resonant, field-friendly UX.

Whether you're a researcher, extension officer, or developer focused on food security, this repo offers a reproducible, deployable workflow that feels both local and scalable.

---

## 🔍 Model Summary

- **Detected Classes**:
  - *Healthy plants*
  - *Early & Late Blight, Bacterial Spot, Mosaic Virus* (varying by crop)
- **Frameworks**:
  - `TensorFlow` + `Keras`
  - `FastAPI` for serving
  - UI: `Streamlit` or `React`
  - Containerization via `Docker`

---

## 📁 Repo Structure

Here’s how the folders are organized based on your workspace layout:

| Folder/File                   | Description                                                |
|------------------------------|------------------------------------------------------------|
| `quick_fix.py`               | Script to auto-create project folders and test model setup |
| `backend/`                   | FastAPI endpoints for model inference                      |
| `frontend/`                  | Streamlit/React-based interface for user interaction       |
| `models/`                    | Directory for trained models and checkpoints               |
| `main.py`                    | Central script for initializing API or running tests       |
| `streamlit_app.py`           | Streamlit app entry point                                  |
| `plant_disease_model.h5`     | Pretrained model weights                                   |
| `plant_disease_classification.png` | Sample output or visual explainer                          |
| `requirements.txt`           | Python dependencies for setup                              |
| `README.md`                  | Project overview and instructions                          |

---

## 🚀 Quickstart

```bash
# Clone the repo
git clone https://github.com/Data-Enthusiast8888/plant-diseases-classification.git

# Run quick setup script
python quick_fix.py

# Start backend (FastAPI)
cd backend
uvicorn main:app --reload

# Launch frontend (Streamlit)
cd ../frontend
streamlit run streamlit_app.py

🌍 Why It Matters
Crop diseases silently undermine yields. This tool empowers users to detect issues early, with an interface that feels grounded, multilingual, and emotionally intuitive.

Use Cases:
    🌾 Field diagnosis for extension officers
    
    📱 Mobile dashboards for farmers
    
    🔬 Prototyping new AI-agronomy models

🤝 Contribute & Collaborate
Looking to grow with:

      -Local image datasets or disease labels
      
      -UX additions in Kiswahili or other languages
      
      -Model benchmarking & confidence scoring
      
      -Engaged policy conversations around agricultural tech

Let’s make the invisible visible—and intelligible.

📬 Maintainer
Crafted by Odhiambo Okeyi, intelligent systems designer blending machine learning, local empathy, and narrative clarity.
