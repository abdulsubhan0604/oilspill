# OILTRACE AI — SIH 26143 Prototype

Prototype for SIH 2026 Problem Statement 26143:
"Leveraging satellite imagery to determine Oil spills at sea along with AIS data correlations to identify vessel responsible for the spill."

## What this prototype demonstrates

1. Satellite/SAR incident ingestion (demo SAR image included)
2. Oil-spill detection + characterization
3. Spill geometry and confidence
4. Backward/forward drift simulation (demo ocean current + wind vectors)
5. Probable origin zone and time window
6. AIS vessel filtering
7. Spatio-temporal vessel attribution scoring
8. Explainable suspect ranking
9. Investigation dashboard

## Important prototype note

This is a DEMO / MVP implementation. The detection, drift and attribution modules are intentionally modular. The included demo mode uses deterministic synthetic incident/AIS/ocean data so the complete workflow can be demonstrated without waiting for large satellite datasets or live AIS feeds.

For production/research:
- Replace `detect_spill_demo()` with a trained Sentinel-1 segmentation model.
- Replace the demo drift vectors with gridded ocean-current/wind data.
- Replace `data/ais_demo.csv` with historical AIS data.
- Add PostGIS for large-scale spatial queries.
- Add model calibration and validation against labeled test data.

## Tech stack

- Frontend: HTML/CSS/JavaScript + Leaflet
- Backend: Python + FastAPI
- Data: CSV/JSON for prototype
- Spatial/scientific utilities: NumPy, Pandas, Shapely
- Optional ML upgrade: PyTorch/U-Net

## Run

### 1. Create environment

Windows:
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements.txt
```

Linux/macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### 2. Start backend

```bash
uvicorn backend.app.main:app --reload
```

Open:
http://127.0.0.1:8000

The FastAPI backend serves the frontend automatically.

### 3. Demo flow

- Open the dashboard.
- Click `Run Demo Analysis`.
- Review the detected slick.
- Click `Run Hindcast`.
- Click `Correlate AIS`.
- Open a vessel to inspect its evidence.
- Use `Generate Investigation Report` to create a printable report.

## Prototype API

- `GET /api/health`
- `GET /api/incident`
- `POST /api/analyze`
- `POST /api/hindcast`
- `POST /api/correlate-ais`
- `GET /api/vessels/{mmsi}`
- `GET /api/report`

## Data sources for the next upgrade

SIH PS 26143 asks for satellite/SAR/EO detection, oceanographic and meteorological drift reconstruction, historical AIS correlation and suspect ranking.

A public Sentinel-1 SAR oil-spill dataset is available on Zenodo. Part I contains 1,200 oil-spill training/validation images with corresponding masks; Part II contains no-oil and look-alike scenes; Part III contains test scenes. These are large datasets, so do not download them for the first UI prototype.

Official SIH problem statement:
https://sih.gov.in/sih2026PS

Sentinel-1 oil-spill dataset:
https://zenodo.org/records/8346860

## Suggested production architecture

Satellite -> preprocessing -> oil segmentation -> geometry -> drift hindcast/forecast -> origin probability -> AIS spatial-temporal query -> anomaly features -> calibrated attribution score -> investigator UI.
