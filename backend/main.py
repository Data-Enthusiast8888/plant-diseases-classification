# main.py - FastAPI Backend for PlantCare AI
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import tensorflow as tf
import numpy as np
from PIL import Image
import io
import uvicorn
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="PlantCare AI Backend",
    description="AI-powered plant disease detection API",
    version="2.0.0"
)

# Configure CORS to allow Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your Streamlit URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Disease class mapping (matches your Streamlit app)
CLASS_NAMES = [
    'Pepper__bell___Bacterial_spot',
    'Pepper__bell___healthy',
    'Potato___Early_blight',
    'Potato___Late_blight',
    'Potato___healthy',
    'Tomato_Bacterial_spot',
    'Tomato_Early_blight',
    'Tomato_Late_blight',
    'Tomato_Leaf_Mold',
    'Tomato_Septoria_leaf_spot',
    'Tomato_Spider_mites_Two_spotted_spider_mite',
    'Tomato__Target_Spot',
    'Tomato__Tomato_YellowLeaf__Curl_Virus',
    'Tomato__Tomato_mosaic_virus',
    'Tomato___healthy'
]

# Global model variable
model = None

def load_model():
    """Load the trained model"""
    global model
    try:
        # Replace with your actual model path
        model_path = "models/plant_disease_model.h5"  # or .keras
        model = tf.keras.models.load_model(model_path)
        logger.info(f"Model loaded successfully from {model_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to load model: {str(e)}")
        return False

def preprocess_image(image: Image.Image, target_size=(256, 256)):
    """Preprocess image for model prediction"""
    try:
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Resize image
        image = image.resize(target_size)
        
        # Convert to numpy array and normalize
        img_array = np.array(image)
        img_array = img_array.astype('float32') / 255.0
        
        # Add batch dimension
        img_array = np.expand_dims(img_array, axis=0)
        
        return img_array
    except Exception as e:
        logger.error(f"Image preprocessing failed: {str(e)}")
        raise HTTPException(status_code=400, detail="Image preprocessing failed")

@app.on_event("startup")
async def startup_event():
    """Load model on startup"""
    logger.info("Starting PlantCare AI Backend...")
    if not load_model():
        logger.error("Failed to load model during startup")
    else:
        logger.info("Backend started successfully")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "PlantCare AI Backend",
        "version": "2.0.0",
        "status": "online",
        "endpoints": {
            "health": "/health",
            "predict": "/predict",
            "model_info": "/model/info"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    model_status = "loaded" if model is not None else "not_loaded"
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "model_status": model_status,
        "supported_classes": len(CLASS_NAMES)
    }

@app.get("/model/info")
async def model_info():
    """Get model information"""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        return {
            "model_loaded": True,
            "input_shape": model.input_shape,
            "output_shape": model.output_shape,
            "total_params": model.count_params(),
            "classes": CLASS_NAMES,
            "num_classes": len(CLASS_NAMES)
        }
    except Exception as e:
        logger.error(f"Error getting model info: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving model information")

@app.post("/predict")
async def predict_disease(file: UploadFile = File(...)):
    """Main prediction endpoint"""
    
    # Check if model is loaded
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded. Please check server logs.")
    
    # Validate file type
    #if not file.content_type.startswith('image/'):
    if not (file.content_type and file.content_type.startswith('image/')):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        # Read and process image
        logger.info(f"Processing image: {file.filename}")
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data))
        
        # Preprocess image
        processed_image = preprocess_image(image)
        
        # Make prediction
        logger.info("Making prediction...")
        predictions = model.predict(processed_image)
        
        # Get prediction results
        predicted_class_index = np.argmax(predictions[0])
        predicted_class = CLASS_NAMES[predicted_class_index]
        confidence = float(predictions[0][predicted_class_index])
        
        # Create all predictions dictionary
        all_predictions = {}
        for i, class_name in enumerate(CLASS_NAMES):
            all_predictions[class_name] = float(predictions[0][i])
        
        logger.info(f"Prediction completed: {predicted_class} ({confidence:.3f})")
        
        return {
            "success": True,
            "predicted_class": predicted_class,
            "confidence": confidence,
            "all_predictions": all_predictions,
            "timestamp": datetime.now().isoformat(),
            "model_version": "2.0.0"
        }
        
    except Exception as e:
        logger.error(f"Prediction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

@app.post("/batch_predict")
async def batch_predict(files: list[UploadFile] = File(...)):
    """Batch prediction endpoint for multiple images"""
    
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    if len(files) > 10:  # Limit batch size
        raise HTTPException(status_code=400, detail="Maximum 10 images per batch")
    
    results = []
    
    for file in files:
        if not file.content_type.startswith('image/'):
            results.append({
                "filename": file.filename,
                "error": "File must be an image"
            })
            continue
        
        # try:
        #     # Process each image
        #     image_data = await file.read()
        #     image = Image.open(io.BytesIO(image_data))
        #     processed_image = preprocess_image(image)
            
        #     # Predict
        #     predictions = model.predict(processed_image)
        #     predicted_class_index = np.argmax(predictions[0])
        #     predicted_class = CLASS_NAMES[predicted_class_index]
        #     confidence = float(predictions[0][predicted_class_index])
            
        #     results.append({
        #         "filename": file.filename,
        #         "predicted_class": predicted_class,
        #         "confidence": confidence,
        #         "success": True
        #     })

        try:
            # Read image contents ONCE
            image_bytes = await file.read()
            
            # Decode image safely
            try:
                image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            except Exception as pil_err:
                raise ValueError(f"Cannot identify image file: {pil_err}")
            
            # Preprocess and predict
            processed_image = preprocess_image(image)
            predictions = model.predict(processed_image)

            predicted_class_index = np.argmax(predictions[0])
            predicted_class = CLASS_NAMES[predicted_class_index]
            confidence = float(predictions[0][predicted_class_index])

            results.append({
                "filename": file.filename,
                "predicted_class": predicted_class,
                "confidence": confidence,
                "success": True
            })

        except Exception as e:
            results.append({
                "filename": file.filename,
                "error": str(e),
                "success": False
            })

            
        # except Exception as e:
        #     results.append({
        #         "filename": file.filename,
        #         "error": str(e),
        #         "success": False
        #     })
    
    return {
        "results": results,
        "total_processed": len(files),
        "timestamp": datetime.now().isoformat()
    }

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Global exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )

if __name__ == "__main__":
    # Run the server
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )