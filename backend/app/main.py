
from pathlib import Path
from datetime import datetime, timedelta, timezone
import math
import pandas as pd
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

BASE = Path(__file__).resolve().parents[2]
DATA = BASE / "data"
FRONTEND = BASE / "frontend"

app = FastAPI(title="SPILLTRACE AI", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

INCIDENT = {
    "id": "INC-26143-DEMO-001",
    "timestamp": "2026-08-28T14:20:00Z",
    "lat": 15.4321,
    "lon": 72.8123,
    "confidence": 94.2,
    "area_km2": 18.6,
    "perimeter_km": 27.4,
    "shape": "Elongated / wind-aligned",
    "estimated_age_hours": 14.2,
    "source": "Sentinel-1 SAR / Demo scene",
}

# Demo environmental vectors. Replace with gridded ocean/wind data in production.
ENV = {
    "current_u_mps": 0.32,
    "current_v_mps": 0.11,
    "wind_speed_knots": 12.0,
    "wind_direction_deg": 45.0,
    "windage_factor": 0.025,
}

class AnalysisRequest(BaseModel):
    mode: str = "demo"

def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dlon/2)**2
    return 2*r*math.asin(math.sqrt(a))

def project_point(lat, lon, east_km, north_km):
    lat2 = lat + north_km / 111.32
    lon2 = lon + east_km / (111.32 * math.cos(math.radians(lat)))
    return lat2, lon2

def drift_path(hours, backward=False, steps=8):
    # Simple demonstrator: current + windage. Sign reverses for hindcast.
    current_east_km_h = ENV["current_u_mps"] * 3.6
    current_north_km_h = ENV["current_v_mps"] * 3.6
    wind_knots = ENV["wind_speed_knots"]
    wind_kmh = wind_knots * 1.852
    wd = math.radians(ENV["wind_direction_deg"])
    wind_east_km_h = wind_kmh * math.sin(wd) * ENV["windage_factor"]
    wind_north_km_h = wind_kmh * math.cos(wd) * ENV["windage_factor"]

    total_e = current_east_km_h + wind_east_km_h
    total_n = current_north_km_h + wind_north_km_h
    sign = -1 if backward else 1

    path = []
    for i in range(steps + 1):
        t = (hours / steps) * i
        lat, lon = project_point(
            INCIDENT["lat"], INCIDENT["lon"],
            sign * total_e * t,
            sign * total_n * t
        )
        path.append({
            "step": i,
            "hours_from_observation": round(sign * t, 2),
            "lat": round(lat, 6),
            "lon": round(lon, 6),
        })
    return path

def detect_spill_demo():
    return {
        "detected": True,
        "confidence": INCIDENT["confidence"],
        "class": "Oil slick",
        "geometry": {
            "area_km2": INCIDENT["area_km2"],
            "perimeter_km": INCIDENT["perimeter_km"],
            "shape": INCIDENT["shape"],
            "centroid": {"lat": INCIDENT["lat"], "lon": INCIDENT["lon"]},
        },
        "estimated_age_hours": INCIDENT["estimated_age_hours"],
        "note": "Demo result. Replace with Sentinel-1 segmentation inference for live imagery.",
    }

def load_ais():
    return pd.read_csv(DATA / "ais_demo.csv", parse_dates=["timestamp"])

def score_vessel(row):
    distance = haversine_km(INCIDENT["lat"], INCIDENT["lon"], row.latitude, row.longitude)
    proximity = max(0, min(100, 100 * math.exp(-distance / 7.0)))
    # Demo trajectory alignment: use course relative to incident->vessel bearing.
    dlat = math.radians(row.latitude - INCIDENT["lat"])
    dlon = math.radians(row.longitude - INCIDENT["lon"])
    y = math.sin(dlon) * math.cos(math.radians(row.latitude))
    x = math.cos(math.radians(INCIDENT["lat"])) * math.sin(math.radians(row.latitude)) - \
        math.sin(math.radians(INCIDENT["lat"])) * math.cos(math.radians(row.latitude)) * math.cos(dlon)
    bearing = (math.degrees(math.atan2(y, x)) + 360) % 360
    angle = abs((row.course - bearing + 180) % 360 - 180)
    trajectory = max(0, 100 - angle * 1.8)

    event_time = pd.Timestamp(INCIDENT["timestamp"])
    delta_h = abs((row.timestamp - event_time).total_seconds()) / 3600
    time_corr = max(0, 100 * math.exp(-delta_h / 2.8))

    behaviour = float(row.behaviour_anomaly)
    ais_gap = float(row.ais_gap_score)

    final = (
        0.30 * proximity +
        0.25 * trajectory +
        0.20 * time_corr +
        0.15 * behaviour +
        0.10 * ais_gap
    )
    return {
        "distance_km": round(distance, 2),
        "proximity": round(proximity, 1),
        "trajectory": round(trajectory, 1),
        "time_correlation": round(time_corr, 1),
        "behaviour_anomaly": round(behaviour, 1),
        "ais_gap": round(ais_gap, 1),
        "score": round(final, 1),
        "time_delta_minutes": round(delta_h * 60, 1),
    }

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "SPILLTRACE AI"}

@app.get("/api/incident")
def incident():
    return {"incident": INCIDENT, "environment": ENV}

@app.post("/api/analyze")
def analyze(req: AnalysisRequest):
    return {"incident": INCIDENT, "detection": detect_spill_demo()}

@app.post("/api/hindcast")
def hindcast():
    path = drift_path(INCIDENT["estimated_age_hours"], backward=True)
    origin = path[-1]
    return {
        "mode": "demo-hindcast",
        "path": path,
        "origin": origin,
        "origin_confidence": 87.0,
        "origin_time": "2026-08-28T00:08:00Z",
        "environment": ENV,
        "note": "Demonstration vector-field model; replace with ocean reanalysis/forecast grids for operational use.",
    }

@app.post("/api/forecast")
def forecast():
    path = drift_path(12, backward=False)
    return {"path": path, "hours": 12}

@app.post("/api/correlate-ais")
def correlate_ais():
    df = load_ais()
    event_time = pd.Timestamp(INCIDENT["timestamp"])
    df["time_delta_h"] = (df["timestamp"] - event_time).abs().dt.total_seconds() / 3600
    df = df[df["time_delta_h"] <= 8].copy()

    scored = []
    for _, row in df.iterrows():
        metrics = score_vessel(row)
        if metrics["distance_km"] <= 25:
            item = row.to_dict()
            item["timestamp"] = item["timestamp"].isoformat()
            item.update(metrics)
            item["vessel_name"] = row["vessel_name"]
            item["type"] = row["ship_type"]
            scored.append(item)

    scored.sort(key=lambda x: x["score"], reverse=True)
    return {
        "total_ais_records": int(len(load_ais())),
        "time_window_candidates": int(len(df)),
        "spatial_candidates": int(len(scored)),
        "vessels": scored[:10],
    }

@app.get("/api/vessels/{mmsi}")
def vessel_detail(mmsi: str):
    df = load_ais()
    df = df[df["mmsi"].astype(str) == str(mmsi)].sort_values("timestamp")
    if df.empty:
        return {"error": "Vessel not found"}
    row = df.iloc[0]
    metrics = score_vessel(row)
    track = []
    for _, r in df.iterrows():
        track.append({
            "timestamp": r["timestamp"].isoformat(),
            "lat": float(r["latitude"]),
            "lon": float(r["longitude"]),
            "speed": float(r["speed_knots"]),
            "course": float(r["course"]),
        })
    return {
        "mmsi": str(mmsi),
        "vessel_name": row["vessel_name"],
        "ship_type": row["ship_type"],
        "metrics": metrics,
        "track": track,
        "evidence": [
            f"Distance to observed slick: {metrics['distance_km']} km",
            f"Time correlation: {metrics['time_delta_minutes']} minutes",
            f"Trajectory alignment score: {metrics['trajectory']}/100",
            f"Behaviour anomaly score: {metrics['behaviour_anomaly']}/100",
            f"AIS gap indicator: {metrics['ais_gap']}/100",
        ],
    }

@app.get("/api/report")
def report():
    df = load_ais()
    scored = []
    for _, row in df.iterrows():
        if abs((row["timestamp"] - pd.Timestamp(INCIDENT["timestamp"])).total_seconds()) <= 8*3600:
            m = score_vessel(row)
            if m["distance_km"] <= 25:
                scored.append((m["score"], row["vessel_name"], row["mmsi"], m))
    scored.sort(reverse=True)
    top = scored[:5]
    lines = [
        "SPILLTRACE AI — INCIDENT INVESTIGATION REPORT",
        f"Incident: {INCIDENT['id']}",
        f"Observed: {INCIDENT['timestamp']}",
        f"Spill confidence: {INCIDENT['confidence']}%",
        f"Area: {INCIDENT['area_km2']} km²",
        "",
        "TOP CANDIDATE VESSELS",
    ]
    for i, (score, name, mmsi, m) in enumerate(top, 1):
        lines.append(f"{i}. {name} ({mmsi}) — {score:.1f}% attribution score")
    lines += [
        "",
        "CAUTION: Attribution score is an investigative prioritization signal, not legal proof of responsibility.",
        "Prototype uses deterministic demo data and simplified drift calculations.",
    ]
    return {"report": "\n".join(lines)}

@app.get("/")
def home():
    return FileResponse(FRONTEND / "index.html")
