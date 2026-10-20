"""
AquaGuard Demo Script
======================
This script demonstrates the complete AquaGuard pipeline:
1. Train the disease classifier
2. Analyze water quality
3. Send alerts
4. Display results
"""
import sys
import os

# Fix Windows Unicode encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from ml.train_pipeline import train_model, predict_disease
from app.services.water_quality_service import WaterQualityService
from alerts.notifier import AlertNotifier


def run_demo():
    """Run the complete AquaGuard demo."""
    print("=" * 60)
    print("AquaGuard - Aquaculture Monitoring Demo")
    print("=" * 60)

    # Step 1: Train the model
    print("\n[1/4] Training Disease Classifier...")
    print("-" * 40)
    model = train_model()

    # Step 2: Test prediction
    print("\n[2/4] Testing Disease Detection...")
    print("-" * 40)
    test_image = Path("data/samples/train/class_0/sample_0_0.jpg")
    if test_image.exists():
        result = predict_disease(str(test_image))
        print(f"  Image: {test_image.name}")
        print(f"  Diagnosis: {result['disease'].upper()}")
        print(f"  Confidence: {result['confidence']*100:.1f}%")
    else:
        print("  Warning: Test image not found")

    # Step 3: Analyze water quality
    print("\n[3/4] Analyzing Water Quality...")
    print("-" * 40)
    wq_service = WaterQualityService()

    # Simulate water quality readings
    readings = {
        "ph": 7.2,
        "dissolved_oxygen": 6.5,
        "ammonia": 0.1,
        "temperature": 26.0
    }

    analysis = wq_service.analyze(readings)
    print(f"  Risk Level: {analysis['risk_level'].upper()}")
    print(f"  Risk Score: {analysis['risk_score']}/8")
    print(f"  Recommendations:")
    for rec in analysis['recommendations']:
        print(f"     - {rec}")

    # Step 4: Send alert (if needed)
    print("\n[4/4] Alert System Test...")
    print("-" * 40)
    notifier = AlertNotifier()

    if analysis['risk_level'] in ['high', 'critical']:
        alert_msg = f"Water quality alert: {analysis['risk_level']} risk detected"
        notifier.send_alert(
            farm_id="demo-farm-001",
            disease="water_quality",
            severity=analysis['risk_level'],
            message=alert_msg
        )
        print("  ALERT sent!")
    else:
        print("  No alerts needed - water quality is good")

    # Summary
    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Run the backend: python -m uvicorn app.main:app --reload")
    print("  2. Open dashboard: http://localhost:8000/dashboard/")
    print("  3. Check API docs: http://localhost:8000/docs")


if __name__ == "__main__":
    run_demo()