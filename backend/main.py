"""FastAPI backend for AquaGuard."""
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from pathlib import Path
from PIL import Image
import torch
import numpy as np
import os

from ml.train_pipeline import SimpleCNN
from alerts.notifier import AlertNotifier
from app.services.water_quality_service import WaterQualityService
from backend.db import init_db, persist_water_quality_reading, persist_disease_prediction, get_alerts_for_farm

app = FastAPI(title="AquaGuard - Aquaculture Monitoring API")

# CORS: restrict to the frontend development origins.
# Allows the browser-served dashboard (localhost) to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# Initialize components
model = None
notifier = AlertNotifier()
wq_service = WaterQualityService()

# Label mapping
LABEL_MAP = {
    0: 'healthy',
    1: 'red_paste',
    2: 'fungus',
    3: 'bacterial',
    4: 'parasitic'
}


@app.on_event("startup")
async def startup():
    """Initialize model, notifier, and database on startup."""
    global model
    print("Initializing AquaGuard backend...")

    # Initialize SQLite database
    try:
        init_db()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Warning: Database initialization failed: {e}")
        raise

    model_path = Path("models/disease_classifier.pt")
    if model_path.exists():
        model = SimpleCNN(num_classes=5)
        model.load_state_dict(torch.load(str(model_path), map_location="cpu"))
        model.eval()
        print("Model loaded successfully!")
    else:
        print("Model not found - training a new one...")
        # Train a new model
        from ml.train_pipeline import train_model
        model = train_model()
    print("Backend initialized")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "aqua-guard"}


@app.post("/disease")
async def classify_disease(image_file: UploadFile = File(...),
                           farm_id: str = "default"):
    """
    Classify disease in a pond image.

    Args:
        image_file: Image file to classify
        farm_id: Identifier for the farmer/farm

    Returns:
        Classification result with confidence score

    Predictions are persisted to the database after successful classification.
    """
    if not model:
        raise HTTPException(status_code=503, detail="Model not loaded")

    # Load image
    image = Image.open(image_file.file).convert('RGB')
    image = image.resize((64, 64))

    # Convert to tensor
    img_array = np.array(image).astype(np.float32) / 255.0
    img_tensor = torch.from_numpy(img_array).permute(2, 0, 1).unsqueeze(0)

    # Predict
    with torch.no_grad():
        output = model(img_tensor)
        probabilities = torch.softmax(output, dim=1)
        predicted_class = torch.argmax(probabilities, dim=1).item()
        confidence = probabilities[0][predicted_class].item()

    predicted_label = LABEL_MAP[predicted_class]

    # Persist the prediction to the database. Both farm creation and
    # prediction insertion happen in a single transaction.
    try:
        persist_disease_prediction(
            farm_id=farm_id,
            predicted_disease=predicted_label,
            confidence=float(confidence),
            pond_id=None,  # No pond provided by the existing API
            model_version=None  # Version tracking can be added later
        )
        print(f"Disease prediction persisted for farm {farm_id}: {predicted_label} ({confidence:.2%})")
    except Exception as e:
        # Log the actual exception; do not expose internals to the frontend
        print(f"ERROR: Failed to persist disease prediction for farm {farm_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to persist disease prediction. Please try again later."
        ) from e

    return {
        "farm_id": farm_id,
        "prediction": predicted_label,
        "confidence": float(confidence),
        "class_id": predicted_class
    }


@app.post("/water-quality")
async def analyze_water_quality(ph: float = 7.2,
                                 dissolved_oxygen: float = 6.5,
                                 ammonia: float = 0.1,
                                 temperature: float = 26.0,
                                 farm_id: str = "default"):
    """Analyze water quality readings and return risk assessment.

    Submitted readings are persisted to the database after successful analysis.
    """
    readings = {
        "ph": ph,
        "dissolved_oxygen": dissolved_oxygen,
        "ammonia": ammonia,
        "temperature": temperature
    }
    analysis = wq_service.analyze(readings)

    # Persist the reading to the database. Both farm creation and reading
    # insertion happen in a single transaction. If persistence fails, the
    # endpoint returns HTTP 500 rather than pretending the reading was saved.
    try:
        persist_water_quality_reading(
            farm_id=farm_id,
            ph=ph,
            dissolved_oxygen=dissolved_oxygen,
            ammonia=ammonia,
            temperature=temperature,
            risk_level=analysis['risk_level'],
            risk_score=analysis['risk_score'],
            pond_id=None  # No pond provided by the existing API
        )
        print(f"Water quality reading persisted for farm {farm_id}")
    except Exception as e:
        # Log the actual exception on the backend; do not expose internals
        print(f"ERROR: Failed to persist water quality reading for farm {farm_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to persist water quality reading. Please try again later."
        ) from e

    # Send alert if needed
    if analysis['risk_level'] in ['high', 'critical']:
        notifier.send_alert(
            farm_id=farm_id,
            disease="water_quality",
            severity=analysis['risk_level'],
            message=f"Water quality alert: {analysis['risk_level']} risk detected"
        )

    return {
        "farm_id": farm_id,
        "readings": readings,
        "analysis": analysis
    }


@app.post("/alerts")
async def create_alert(farm_id: str, disease: str, severity: str, message: str):
    """Create a new alert for a farmer.

    Returns the actual inserted alert row ID (not a hardcoded value).
    Raises HTTP 500 if the database write fails.
    """
    try:
        alert_id = notifier.send_alert(farm_id, disease, severity, message)
        return {"success": True, "alert_id": alert_id}
    except Exception as e:
        print(f"ERROR: Failed to create alert for farm {farm_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create alert. Please try again later."
        ) from e


@app.get("/alerts/{farm_id}")
async def get_farm_alerts(farm_id: str):
    """Get all alerts for a farm using named-column access.

    Fixes the previous column-mapping bug by using an explicit SELECT list
    and named-column access (sqlite3.Row).
    """
    alerts = get_alerts_for_farm(farm_id)
    return alerts


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)