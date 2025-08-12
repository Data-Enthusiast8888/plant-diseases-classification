# main.py - FastAPI Backend for PlantCare AI (FIXED VERSION)
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
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="KilimoGlow Backend",
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
        
        # Clear any existing sessions
        tf.keras.backend.clear_session()
        
        model = tf.keras.models.load_model(model_path, compile=False)
        
        # Compile the model explicitly to ensure consistency
        model.compile(
            optimizer='adam',
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )
        
        logger.info(f"Model loaded successfully from {model_path}")
        logger.info(f"Model input shape: {model.input_shape}")
        logger.info(f"Model output shape: {model.output_shape}")
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
        
        # Resize image using LANCZOS for better quality
        image = image.resize(target_size, Image.Resampling.LANCZOS)
        
        # Convert to numpy array and normalize
        img_array = np.array(image, dtype=np.float32)
        
        # Normalize pixel values to [0, 1]
        img_array = img_array / 255.0
        
        # Add batch dimension
        img_array = np.expand_dims(img_array, axis=0)
        
        logger.info(f"Preprocessed image shape: {img_array.shape}")
        logger.info(f"Preprocessed image min/max: {img_array.min():.3f}/{img_array.max():.3f}")
        
        return img_array
    except Exception as e:
        logger.error(f"Image preprocessing failed: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Image preprocessing failed: {str(e)}")

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
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "health": "/health",
            "predict": "/predict",
            "model_info": "/model/info",
            "batch_predict": "/batch_predict"
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
        "supported_classes": len(CLASS_NAMES),
        "model_ready": model is not None
    }

@app.get("/model/info")
async def model_info():
    """Get model information"""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        return {
            "model_loaded": True,
            "input_shape": str(model.input_shape),
            "output_shape": str(model.output_shape),
            "total_params": int(model.count_params()),
            "classes": CLASS_NAMES,
            "num_classes": len(CLASS_NAMES),
            "model_summary": str(model.summary())
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
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # More flexible content type checking
    if file.content_type and not file.content_type.startswith('image/'):
        logger.warning(f"Unexpected content type: {file.content_type}, proceeding anyway")
    
    start_time = time.time()
    
    try:
        # Read and process image
        logger.info(f"Processing image: {file.filename} (Content-Type: {file.content_type})")
        
        # Read image data
        image_data = await file.read()
        logger.info(f"Read {len(image_data)} bytes from uploaded file")
        
        # Open image with error handling
        try:
            image = Image.open(io.BytesIO(image_data))
            logger.info(f"Original image: {image.size}, mode: {image.mode}")
        except Exception as img_error:
            logger.error(f"Failed to open image: {str(img_error)}")
            raise HTTPException(status_code=400, detail=f"Invalid image format: {str(img_error)}")
        
        # Preprocess image
        processed_image = preprocess_image(image)
        
        # Clear any previous session state
        tf.keras.backend.clear_session()
        
        # Make prediction with error handling
        logger.info("Making prediction...")
        try:
            predictions = model.predict(processed_image, verbose=0)
            logger.info(f"Raw predictions shape: {predictions.shape}")
            logger.info(f"Raw predictions sample: {predictions[0][:5]}")
        except Exception as pred_error:
            logger.error(f"Model prediction failed: {str(pred_error)}")
            raise HTTPException(status_code=500, detail=f"Model prediction failed: {str(pred_error)}")
        
        # Process predictions
        predicted_class_index = np.argmax(predictions[0])
        predicted_class = CLASS_NAMES[predicted_class_index]
        confidence = float(predictions[0][predicted_class_index])
        
        # Create all predictions dictionary with proper sorting
        all_predictions = {}
        prediction_scores = predictions[0]
        
        for i, class_name in enumerate(CLASS_NAMES):
            all_predictions[class_name] = float(prediction_scores[i])
        
        # Sort predictions by confidence
        sorted_predictions = dict(sorted(all_predictions.items(), key=lambda x: x[1], reverse=True))
        
        processing_time = time.time() - start_time
        
        result = {
            "success": True,
            "predicted_class": predicted_class,
            "confidence": confidence,
            "predicted_index": int(predicted_class_index),
            "all_predictions": sorted_predictions,
            "top_3_predictions": dict(list(sorted_predictions.items())[:3]),
            "processing_time": round(processing_time, 3),
            "timestamp": datetime.now().isoformat(),
            "model_version": "2.0.0",
            "image_info": {
                "filename": file.filename,
                "original_size": f"{image.size[0]}x{image.size[1]}",
                "processed_size": f"{processed_image.shape[1]}x{processed_image.shape[2]}",
                "channels": processed_image.shape[3]
            }
        }
        
        logger.info(f"Prediction completed: {predicted_class} ({confidence:.3f}) in {processing_time:.3f}s")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in prediction: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

@app.post("/batch_predict")
async def batch_predict(files: list[UploadFile] = File(...)):
    """Batch prediction endpoint for multiple images"""
    
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    if len(files) > 10:  # Limit batch size
        raise HTTPException(status_code=400, detail="Maximum 10 images per batch")
    
    if len(files) == 0:
        raise HTTPException(status_code=400, detail="No files provided")
    
    results = []
    start_time = time.time()
    
    for i, file in enumerate(files):
        file_start_time = time.time()
        
        if not file.filename:
            results.append({
                "index": i,
                "filename": "unnamed",
                "error": "No filename provided",
                "success": False
            })
            continue
        
        # More flexible content type checking for batch
        if file.content_type and not file.content_type.startswith('image/'):
            results.append({
                "index": i,
                "filename": file.filename,
                "error": f"Invalid content type: {file.content_type}",
                "success": False
            })
            continue
        
        try:
            # Read image contents
            image_bytes = await file.read()
            
            # Decode image safely
            try:
                image = Image.open(io.BytesIO(image_bytes))
                if image.mode != 'RGB':
                    image = image.convert('RGB')
            except Exception as pil_err:
                results.append({
                    "index": i,
                    "filename": file.filename,
                    "error": f"Cannot process image: {str(pil_err)}",
                    "success": False
                })
                continue
            
            # Preprocess and predict
            processed_image = preprocess_image(image)
            predictions = model.predict(processed_image, verbose=0)

            predicted_class_index = np.argmax(predictions[0])
            predicted_class = CLASS_NAMES[predicted_class_index]
            confidence = float(predictions[0][predicted_class_index])
            
            processing_time = time.time() - file_start_time

            results.append({
                "index": i,
                "filename": file.filename,
                "predicted_class": predicted_class,
                "confidence": confidence,
                "predicted_index": int(predicted_class_index),
                "processing_time": round(processing_time, 3),
                "success": True
            })

        except Exception as e:
            results.append({
                "index": i,
                "filename": file.filename,
                "error": str(e),
                "success": False
            })
    
    total_time = time.time() - start_time
    successful_predictions = sum(1 for r in results if r.get("success", False))
    
    return {
        "results": results,
        "total_files": len(files),
        "successful_predictions": successful_predictions,
        "failed_predictions": len(files) - successful_predictions,
        "total_processing_time": round(total_time, 3),
        "timestamp": datetime.now().isoformat()
    }

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Global exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error", 
            "error": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )

# Add a debug endpoint for testing
@app.post("/debug/test_prediction")
async def debug_prediction():
    """Debug endpoint to test model prediction without file upload"""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        # Create a dummy image for testing
        dummy_image = np.random.rand(1, 256, 256, 3).astype(np.float32)
        logger.info(f"Testing with dummy image shape: {dummy_image.shape}")
        
        predictions = model.predict(dummy_image, verbose=0)
        
        predicted_class_index = np.argmax(predictions[0])
        predicted_class = CLASS_NAMES[predicted_class_index]
        confidence = float(predictions[0][predicted_class_index])
        
        return {
            "success": True,
            "message": "Model is working correctly",
            "test_prediction": predicted_class,
            "test_confidence": confidence,
            "model_output_shape": str(predictions.shape),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Debug prediction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Debug prediction failed: {str(e)}")

if __name__ == "__main__":
    # Run the server
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )