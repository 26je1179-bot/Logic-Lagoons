import os
import math
import sqlite3
from flask import Flask, jsonify, request, send_from_directory, send_file
from flask_cors import CORS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "ulpin.db")
MODELS_DIR = os.path.join(BASE_DIR, "models")
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend"))

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
CORS(app, resources={r"/*": {"origins": "*"}})

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the great-circle distance between two points on the Earth (in meters)."""
    R = 6371000.0  # Earth's radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

def format_parcel_response(parcel_row, floors_rows, distance_m=None):
    res = {
        "id": parcel_row["id"],
        "ulpin": parcel_row["ulpin"],
        "address": parcel_row["address"],
        "state": parcel_row["state"],
        "district": parcel_row["district"],
        "latitude": parcel_row["latitude"],
        "longitude": parcel_row["longitude"],
        "model_url": f"/models/{parcel_row['glb_filename']}",
        "total_floors": parcel_row["total_floors"],
        "total_height_m": parcel_row["total_height_m"],
        "floors": [
            {
                "floor_number": f["floor_number"],
                "height_m": f["height_m"],
                "unit_type": f["unit_type"],
                "area_sqm": f["area_sqm"],
                "owner_name": f["owner_name"]
            }
            for f in floors_rows
        ]
    }
    if distance_m is not None:
        res["matched_distance_m"] = round(distance_m, 2)
    return res

@app.route("/api/parcels", methods=["GET"])
def get_all_parcels():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, ulpin, address, state, district, latitude, longitude,
               glb_filename, total_floors, total_height_m
        FROM parcels
        ORDER BY id ASC;
    """)
    rows = cursor.fetchall()
    conn.close()

    parcels = [
        {
            "id": r["id"],
            "ulpin": r["ulpin"],
            "address": r["address"],
            "state": r["state"],
            "district": r["district"],
            "latitude": r["latitude"],
            "longitude": r["longitude"],
            "model_url": f"/models/{r['glb_filename']}",
            "total_floors": r["total_floors"],
            "total_height_m": r["total_height_m"]
        }
        for r in rows
    ]
    return jsonify(parcels)

@app.route("/api/parcels/by-ulpin/<string:ulpin>", methods=["GET"])
def get_parcel_by_ulpin(ulpin):
    clean_ulpin = ulpin.strip()
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM parcels WHERE UPPER(ulpin) = UPPER(?);", (clean_ulpin,))
    parcel = cursor.fetchone()

    if not parcel:
        conn.close()
        return jsonify({"error": f"Parcel with ULPIN '{clean_ulpin}' not found"}), 404

    cursor.execute("""
        SELECT floor_number, height_m, unit_type, area_sqm, owner_name
        FROM floors
        WHERE parcel_id = ?
        ORDER BY floor_number ASC;
    """, (parcel["id"],))
    floors = cursor.fetchall()
    conn.close()

    return jsonify(format_parcel_response(parcel, floors))

@app.route("/api/parcels/by-location", methods=["GET"])
def get_parcel_by_location():
    lat_str = request.args.get("lat")
    lng_str = request.args.get("lng")

    if not lat_str or not lng_str:
        return jsonify({"error": "Query parameters 'lat' and 'lng' are required"}), 400

    try:
        query_lat = float(lat_str)
        query_lng = float(lng_str)
    except ValueError:
        return jsonify({"error": "Invalid 'lat' or 'lng' parameter. Must be numbers."}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM parcels;")
    all_parcels = cursor.fetchall()

    if not all_parcels:
        conn.close()
        return jsonify({"error": "No registered vertical parcel near this location"}), 404

    threshold_meters = 100.0
    nearest_parcel = None
    min_dist = float("inf")

    for parcel in all_parcels:
        dist = haversine_distance(query_lat, query_lng, parcel["latitude"], parcel["longitude"])
        if dist < min_dist:
            min_dist = dist
            nearest_parcel = parcel

    if min_dist <= threshold_meters and nearest_parcel is not None:
        cursor.execute("""
            SELECT floor_number, height_m, unit_type, area_sqm, owner_name
            FROM floors
            WHERE parcel_id = ?
            ORDER BY floor_number ASC;
        """, (nearest_parcel["id"],))
        floors = cursor.fetchall()
        conn.close()
        return jsonify(format_parcel_response(nearest_parcel, floors, distance_m=min_dist))
    else:
        conn.close()
        return jsonify({
            "error": "No registered vertical parcel near this location",
            "nearest_distance_m": round(min_dist, 1) if min_dist != float("inf") else None
        }), 404

@app.route("/api/verify-password", methods=["POST"])
def verify_password():
    data = request.json
    if not data or not data.get("ulpin") or not data.get("password"):
        return jsonify({"error": "ULPIN and password are required"}), 400

    ulpin = data.get("ulpin").strip()
    password = data.get("password").strip()

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE UPPER(ulpin) = UPPER(?) AND password = ?", (ulpin, password))
    user = cursor.fetchone()
    conn.close()

    if user:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "INCORRECT PASSWORD"}), 401

@app.route("/models/<path:filename>", methods=["GET"])
def serve_model(filename):
    file_path = os.path.join(MODELS_DIR, filename)
    if not os.path.isfile(file_path):
        return jsonify({"error": f"Model '{filename}' not found"}), 404
    return send_file(file_path, mimetype="model/gltf-binary")

# Frontend static serving
@app.route("/", methods=["GET"])
def serve_index():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/<path:path>", methods=["GET"])
def serve_static(path):
    full_path = os.path.join(FRONTEND_DIR, path)
    if os.path.isfile(full_path):
        return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(FRONTEND_DIR, "index.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting SIH26011 3D ULPIN Server on http://localhost:{port}...")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
