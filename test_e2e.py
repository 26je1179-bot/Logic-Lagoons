import urllib.request
import urllib.error
import json
import sys

base = 'http://127.0.0.1:5000'

def check(url, expected_code=200):
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
            status = resp.status
            result = "PASS" if status == expected_code else "FAIL"
            print(f"[{result}] {url} -> {status} (bytes: {len(data)})")
            return status, data
    except urllib.error.HTTPError as e:
        result = "PASS" if e.code == expected_code else "FAIL"
        print(f"[{result}] {url} -> {e.code}")
        return e.code, e.read()

def main():
    print("Testing static frontend files...")
    check(f"{base}/")
    check(f"{base}/style.css")
    check(f"{base}/js/viewer.js")
    check(f"{base}/js/map.js")
    check(f"{base}/js/search.js")
    check(f"{base}/js/api.js")

    print("\nTesting /api/parcels...")
    _, d = check(f"{base}/api/parcels")
    parcels = json.loads(d)
    assert len(parcels) == 3, f"Expected 3 parcels, got {len(parcels)}"
    print(f"  -> Count: {len(parcels)}")

    print("\nTesting /api/parcels/by-ulpin...")
    for u in ['JH091234567801', 'WB198765432102', 'KA561122334403']:
        _, d = check(f"{base}/api/parcels/by-ulpin/{u}")
        p = json.loads(d)
        print(f"  -> {u}: {p['address']} | Floors: {len(p['floors'])} | Height: {p['total_height_m']}m")
        assert len(p['floors']) == p['total_floors']

    print("\nTesting /api/parcels/by-location (within 100m)...")
    # Dhanbad
    _, d1 = check(f"{base}/api/parcels/by-location?lat=23.7957&lng=86.4304")
    p1 = json.loads(d1)
    assert p1['ulpin'] == 'JH091234567801'
    print(f"  -> Near Dhanbad: Matched {p1['ulpin']} (dist: {p1['matched_distance_m']}m)")

    # Kolkata
    _, d2 = check(f"{base}/api/parcels/by-location?lat=22.5263&lng=88.3650")
    p2 = json.loads(d2)
    assert p2['ulpin'] == 'WB198765432102'
    print(f"  -> Near Kolkata: Matched {p2['ulpin']} (dist: {p2['matched_distance_m']}m)")

    # Bengaluru
    _, d3 = check(f"{base}/api/parcels/by-location?lat=12.9759&lng=77.6046")
    p3 = json.loads(d3)
    assert p3['ulpin'] == 'KA561122334403'
    print(f"  -> Near Bengaluru: Matched {p3['ulpin']} (dist: {p3['matched_distance_m']}m)")

    print("\nTesting /api/parcels/by-location (far away, > 100m, expecting 404)...")
    code, err_data = check(f"{base}/api/parcels/by-location?lat=10.0&lng=70.0", 404)
    assert code == 404
    err_json = json.loads(err_data)
    print(f"  -> 404 Error message: '{err_json.get('error')}'")

    print("\nTesting 3D Models serving...")
    for m in ['parcel_1.glb', 'three_floor_building.glb', 'parcel_3.glb']:
        _, data = check(f"{base}/models/{m}")
        assert len(data) > 1000

    print("\nALL SERVER ENDPOINTS AND STATIC ASSETS VERIFIED SUCCESSFULLY!")

if __name__ == '__main__':
    main()
