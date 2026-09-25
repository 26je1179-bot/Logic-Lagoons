# 3D ULPIN Generation & Vertical Property Mapping System (SIH26011)

A full-stack prototype for Smart India Hackathon problem statement **SIH26011** (*"3D ULPIN Generation and Vertical Property Mapping System"*), developing high-precision 3D vertical property mapping and cadastral unit demarcation for urban multi-story buildings.

---

## 🌟 Key Features

1. **Two Unified Entry Points**:
   - **Interactive Map Pin Flow**: Click anywhere on the geographic map &rarr; computes Haversine distance to registered cadastral parcels &rarr; returns 2D ULPIN, coordinates, parcel metadata, and 3D GLB model URL if within 100m threshold.
   - **Direct ULPIN Search**: Type any 14-digit ULPIN (or click one of the quick-test parcel chips) &rarr; instant retrieval, 3D model loading, and map camera fly-to.

2. **Embedded Per-Floor 3D Cadastral Assets (Blender & glTF 2.0)**:
   - Hand-modeled architectural 3D building assets (`.glb`) with separate floor meshes.
   - Per-floor metadata (`floor_number`, `height_m`, `unit_type`, `area_sqm`, `owner_name`) is directly embedded into **glTF custom property extras**.
   - Three.js automatically copies extras into `mesh.userData`, eliminating custom parsing logic.

3. **Interactive 3D Cadastre (Three.js)**:
   - **Raycast Selection & Highlighting**: Clicking any floor mesh highlights it with an emissive amber glow and synchronizes with the metadata panel.
   - **Hover Tooltips**: Live 3D inspection tooltips showing floor level, unit type, height, and ownership.
   - **Exploded View (Vertical Demarcation)**: Expands all floors vertically along the elevation axis to visually inspect stacked unit boundaries.
   - **Structural Wireframe Mode**: Allows viewing internal structural boundaries and floor slabs.
   - **Reset Framing**: One-click re-centering and camera reset.

4. **3D ULPIN Standard Demarcation**:
   - Demonstrates vertical property identification extending 2D land-record ULPINs into 3D cadastral tokens:
     - 2D Base ULPIN: `JH091234567801`
     - 3D Vertical ULPIN: `JH091234567801-FL02` (Unit Floor 2)

5. **Resilient Dual Map Architecture**:
   - Supports Google Maps JavaScript API with built-in, graceful fallback to Leaflet / OpenStreetMap so evaluators and judges never encounter broken map boxes or missing API key blocks.

---

## 🏛️ Seeded Cadastral Parcels

| ULPIN | Address / City | State | Total Floors | Total Height | GLB Asset |
|---|---|---|---|---|---|
| `JH091234567801` | Green Residency, Wasseypur Road, Dhanbad | Jharkhand | 4 | 12.4 m | `parcel_1.glb` |
| `WB198765432102` | Lake View Apartments, Ballygunge, Kolkata | West Bengal | 6 | 19.0 m | `parcel_2.glb` |
| `KA561122334403` | Silicon Business Tower, MG Road, Bengaluru | Karnataka | 9 | 32.0 m | `parcel_3.glb` |

---

## 🏗️ Architecture & Folder Structure

```
SIH NIKHIL/
├── backend/
│   ├── app.py                  # Flask REST API + Static GLB and frontend server
│   ├── seed.py                 # SQLite database creation & seed data insertion
│   ├── build_models.py         # Blender script generating GLBs with custom properties
│   ├── models/                 # Hand-modeled GLB 3D assets
│   │   ├── parcel_1.glb        # 4-floor residential building (Dhanbad)
│   │   ├── parcel_2.glb        # 6-floor mixed-use building (Kolkata)
│   │   └── parcel_3.glb        # 9-floor commercial office tower (Bengaluru)
│   ├── ulpin.db                # SQLite database (parcels & floors)
│   └── requirements.txt        # Backend dependencies (Flask, Flask-CORS)
├── frontend/
│   ├── index.html              # Split layout UI (Map, 3D Canvas, Search & Metadata)
│   ├── style.css               # Modern DoLR / Cadastral styling with unit badges
│   └── js/
│       ├── api.js              # Fetch wrapper for backend endpoints
│       ├── map.js              # Map engine (Google Maps + Leaflet fallback)
│       ├── viewer.js           # Three.js 3D viewer, OrbitControls, GLTFLoader, raycasting
│       └── search.js           # ULPIN search, sample chips, event orchestration
├── test_e2e.py                 # Automated test suite for endpoints and assets
└── README.md
```

---

## 🚀 Getting Started

### 1. Requirements
- Python 3.10+
- Modern Web Browser (Chrome, Edge, Firefox, Safari) with WebGL enabled

### 2. Run the Application
The virtual environment and database are already initialized. Simply run:

```bash
.venv\Scripts\python backend\app.py
```

Open your browser and navigate to:
```
http://localhost:5000
```` 

---

## 📡 REST API Reference

| Endpoint | Method | Description |
|---|---|---|
| `GET /api/parcels` | `GET` | List all registered parcels (`id`, `ulpin`, `address`, `lat`, `lng`, etc.) |
| `GET /api/parcels/by-ulpin/<ulpin>` | `GET` | Fetch full parcel record and per-floor vertical units |
| `GET /api/parcels/by-location?lat=<lat>&lng=<lng>` | `GET` | Proximity match within 100m using Haversine distance, else returns 404 |
| `GET /models/<filename>` | `GET` | Serves binary 3D assets (`.glb`) with `model/gltf-binary` MIME type |

---

## ⚖️ Hackathon Design Note (Simulation vs. Production)

> **Important Note for Evaluators / Judges**:
> In this prototype, the 2D cadastral boundary lookup is simulated using an exact Haversine proximity query (100m radius threshold) against the local SQLite cadastral database. In a production state or national deployment, this endpoint hooks directly into the **DoLR / SVAMITVA / DILRMP Land Records Gateway API** to authenticate legal parcel bounds and land title registries.
