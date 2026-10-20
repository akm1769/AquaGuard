# AquaGuard — Early Disease & Water-Quality Alerts for Small Aquaculture Farms

A hackathon prototype for affordable, AI-assisted monitoring of fish and shrimp farms.

## Problems Addressed
- Small farms lack real-time water-quality monitoring.
- Disease outbreaks are detected too late.
- No affordable early-warning system connects readings to actionable alerts.

## Proposed Solution
- Simulated water-quality readings analyzed by a FastAPI backend.
- SQLite persistence for farms, ponds, readings, predictions, and alerts.
- Prototype PyTorch disease classifier (synthetic training data).
- Simple HTML frontend with Monitoring, Marketplace preview, and Alerts views.
- Light/Dark theme support.

## Main Features
- Monitoring page with backend-calculated risk score (0–8) and recommendations.
- Marketplace category cards (Coming Soon — informational only).
- Alerts page loading from SQLite via `/alerts/{farm_id}`.
- Top navbar navigation; bottom tabs removed.
- Theme toggle.

## Technology Stack
- Frontend: plain HTML, CSS, JavaScript
- Backend: FastAPI (Python)
- Disease classifier: PyTorch prototype (`ml/classifier.py`, `models/disease_classifier.pt`)
- Database: SQLite (`alerts.db` — local file; schema initialized by `backend/db.py`)
- No PostgreSQL, Docker, or cloud database required

## Project Structure
```
A:\demo\DevHack/
  backend/main.py         # FastAPI app (endpoints, startup)
  backend/db.py           # SQLite module (schema, persistence, queries)
  app/services/water_quality_service.py  # Risk analysis logic
  alerts/notifier.py      # Alert storage and retrieval
  dashboard/frontend/     # index.html, style.css, script.js
  ml/                     # PyTorch model, dataset, trainer
  models/disease_classifier.pt  # Trained model (403 KB)
  alerts.db               # Local SQLite database (ignored in Git)
  requirements.txt        # Python dependencies
  design.md               # Project design notes
```

## Local Installation

Requires Python 3.9+ with the packages in `requirements.txt`. No Docker needed.

```powershell
# From any directory (use your clone path instead of A:\demo\DevHack if needed)
cd A:\demo\DevHack
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Startup (Windows PowerShell)

**Backend:**
```powershell
cd A:\demo\DevHack
python -m uvicorn backend.main:app --reload --port 8000
```

**Frontend:**
```powershell
cd A:\demo\DevHack
python -m http.server 8080 --directory "A:\demo\DevHack\dashboard\frontend"
```

Then open `http://localhost:8080/index.html` in a browser.

For users running from a different clone directory, replace `A:\demo\DevHack` with the clone folder path in both commands above. The backend uses relative imports (`from backend.db import ...`) and resolves paths from its own module location.

## API Endpoints

| Method | Route | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/water-quality` | Analyze water quality (query params: `ph`, `dissolved_oxygen`, `ammonia`, `temperature`, `farm_id`) |
| POST | `/disease` | Classify disease from image (`image_file` upload, `farm_id`) |
| GET | `/alerts/{farm_id}` | Retrieve alerts for a farm (correct named-column mapping) |
| POST | `/alerts` | Create a new alert |

**Response compatibility preserved:** `POST /water-quality` returns `{"farm_id", "readings", "analysis"}` with `risk_level`, `risk_score`, `recommendations`, `parameters`. `GET /alerts/{farm_id}` returns `[{"id", "disease", "severity", "message"}]`.

## Database Schema (SQLite — initialized by `backend/db.py`)
- `farms` (id TEXT PRIMARY KEY — preserves `demo-farm-001` string)
- `ponds` (id INTEGER, farm_id → farms)
- `water_quality_readings` (with nullable `pond_id`)
- `disease_predictions` (with nullable `pond_id`)
- `alerts` (existing, preserved unchanged)

A timestamped backup exists at `backups/alerts.db.backup-20261020-083920`. A fresh clone initializes schema automatically (`init_db()` on startup); it does not require the private `alerts.db`.

## Current Limitations (Disclosed)
- **Simulated water-quality readings:** The frontend sends demonstration inputs (`ph=7.2`, etc.), not live sensor measurements.
- **Disease classifier prototype:** Trained on synthetic data (`ml/dataset.py`). Accuracy has not been validated for real-world aquaculture. The model loads from `models/disease_classifier.pt`; if missing, the backend can train a new one.
- **Local SQLite storage:** `alerts.db` is a local file. No PostgreSQL, cloud database, or Docker container is used.
- **SMS/email alerts:** The `alerts/notifier.py` prints simulated alerts. There is no confirmed live SMS/Twilio integration.
- **Marketplace:** The `Marketplace` section is a `Coming Soon` informational preview with 4 category cards. It is not a live commerce platform.
- **No real sensor integration:** All water-quality cards are clearly labeled as simulated.

## Model File Note
`models/disease_classifier.pt` (403 KB) is included so the prototype runs out of the box. If repository size is a concern, it can be rebuilt via `ml/train_pipeline.py` or tracked with Git LFS. Do not delete it unless you plan to retrain.

## License / Usage
Hackathon prototype. Not intended for production aquaculture management without further validation, sensor integration, and security review.
