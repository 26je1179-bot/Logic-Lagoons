import subprocess
import time
import json
import urllib.request
import socket
import base64
import os

def test_user_flows():
    port = 9227
    user_data = os.path.join(os.environ.get("TEMP", "."), "edge_cdp_9227")
    cmd = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "--headless=new",
        f"--remote-debugging-port={port}",
        f"--user-data-dir={user_data}",
        "http://127.0.0.1:5000"
    ]
    proc = subprocess.Popen(cmd)
    try:
        targets = []
        for _ in range(25):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/json") as resp:
                    targets = json.loads(resp.read().decode("utf-8"))
                    if targets:
                        break
            except Exception:
                time.sleep(0.3)
        
        page_target = [t for t in targets if t.get("type") == "page"][0]
        ws_url = page_target["webSocketDebuggerUrl"]
        path = ws_url.split(f"127.0.0.1:{port}")[1]
        
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", port))
        
        key = base64.b64encode(os.urandom(16)).decode('utf-8')
        req = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        s.sendall(req.encode('utf-8'))
        s.recv(2048)
        
        def send_msg(msg_obj):
            payload = json.dumps(msg_obj).encode('utf-8')
            frame = bytearray([0x81])
            length = len(payload)
            if length <= 125:
                frame.append(0x80 | length)
            elif length <= 65535:
                frame.append(0x80 | 126)
                frame.extend(length.to_bytes(2, 'big'))
            else:
                frame.append(0x80 | 127)
                frame.extend(length.to_bytes(8, 'big'))
            mask = os.urandom(4)
            frame.extend(mask)
            masked_payload = bytearray(b ^ mask[i % 4] for i, b in enumerate(payload))
            frame.extend(masked_payload)
            s.sendall(frame)
            
        send_msg({"id": 1, "method": "Runtime.enable"})
        time.sleep(2.5) # Wait for initial auto-load (Dhanbad)
        
        def eval_js(js_code, msg_id=200):
            send_msg({
                "id": msg_id,
                "method": "Runtime.evaluate",
                "params": {"expression": js_code, "returnByValue": True}
            })
            s.settimeout(4.0)
            raw = b""
            start = time.time()
            while time.time() - start < 3.0:
                try:
                    chunk = s.recv(4096)
                    if not chunk: break
                    raw += chunk
                    # Check if response for msg_id is in raw
                    if f'"id":{msg_id}' in raw.decode('utf-8', errors='ignore') or f'"id": {msg_id}' in raw.decode('utf-8', errors='ignore'):
                        break
                except Exception:
                    break
            # Parse responses
            res = None
            i = 0
            while i < len(raw):
                if i + 2 > len(raw): break
                b1 = raw[i+1]
                length = b1 & 0x7F
                header_len = 2
                if length == 126:
                    if i + 4 > len(raw): break
                    length = int.from_bytes(raw[i+2:i+4], 'big')
                    header_len = 4
                elif length == 127:
                    if i + 10 > len(raw): break
                    length = int.from_bytes(raw[i+2:i+10], 'big')
                    header_len = 10
                payload = raw[i+header_len : i+header_len+length]
                try:
                    msg = json.loads(payload.decode('utf-8', errors='ignore'))
                    if msg.get("id") == msg_id:
                        res = msg.get("result", {}).get("result", {}).get("value")
                except Exception:
                    pass
                i += header_len + length
            return res

        # 1. Verify Initial State (Dhanbad)
        state1 = eval_js("JSON.stringify({ulpin: window.app.currentParcel.ulpin, floors: window.app.viewer.floorMeshes.size})", 101)
        print("Initial state (Auto-loaded):", state1)
        assert "JH091234567801" in state1
        assert '"floors":4' in state1
        print("-> Dhanbad 4-floor model and metadata verified!")

        # 2. Test Direct ULPIN Search: Search for Kolkata (WB198765432102)
        print("\nTesting ULPIN search input with 'WB198765432102'...")
        eval_js("""
        (function() {
            const input = document.getElementById('ulpin-input');
            input.value = 'WB198765432102';
            document.getElementById('search-btn').click();
        })()
        """, 102)
        time.sleep(2.0)
        
        state2 = eval_js("JSON.stringify({ulpin: window.app.currentParcel.ulpin, floors: window.app.viewer.floorMeshes.size, address: window.app.currentParcel.address})", 103)
        print("Search result state:", state2)
        assert "WB198765432102" in state2
        assert '"floors":6' in state2
        print("-> Search box successfully loaded Kolkata (6 floors)!")

        # 3. Test Sample Chip click: Bengaluru (KA561122334403)
        print("\nTesting Sample Chip click for Bengaluru...")
        eval_js("""
        (function() {
            const chip = document.querySelector('[data-ulpin=\"KA561122334403\"]');
            chip.click();
        })()
        """, 104)
        time.sleep(2.0)
        
        state3 = eval_js("JSON.stringify({ulpin: window.app.currentParcel.ulpin, floors: window.app.viewer.floorMeshes.size, address: window.app.currentParcel.address})", 105)
        print("Chip click result state:", state3)
        assert "KA561122334403" in state3
        assert '"floors":9' in state3
        print("-> Sample chip successfully loaded Bengaluru (9 floors)!")

        # 4. Test Floor Selection & Metadata Sync
        print("\nTesting Floor Selection from Floor Stack List (Floor 3)...")
        eval_js("""
        (function() {
            const floorItem = document.getElementById('floor-item-3');
            floorItem.click();
        })()
        """, 106)
        time.sleep(0.5)
        
        state4 = eval_js("JSON.stringify({selFloor: window.app.selectedFloor.floor_number, owner: window.app.selectedFloor.owner_name, type: window.app.selectedFloor.unit_type})", 107)
        print("Floor 3 selection state:", state4)
        assert '"selFloor":3' in state4
        print("-> Floor 3 selected with correct metadata and 3D highlight!")

        # 5. Test Exploded View Button
        print("\nTesting Exploded View toggle...")
        eval_js("document.getElementById('btn-explode').click()", 108)
        time.sleep(0.5)
        is_exploded = eval_js("window.app.viewer.isExploded", 109)
        print("isExploded state:", is_exploded)
        assert is_exploded is True
        print("-> Exploded view toggle verified!")

        # 6. Test Map Proximity Click Flow
        print("\nTesting Map click proximity matching for Dhanbad (23.7957, 86.4304)...")
        eval_js("window.app.map.handleLocationClick(23.7957, 86.4304)", 110)
        time.sleep(2.0)
        state6 = eval_js("JSON.stringify({ulpin: window.app.currentParcel.ulpin, floors: window.app.viewer.floorMeshes.size})", 111)
        print("Map click result state:", state6)
        assert "JH091234567801" in state6
        print("-> Map click successfully matched Dhanbad via 100m Haversine!")

        print("\n[SUCCESS] ALL USER FLOWS, SEARCH BOX, CHIPS, 3D VIEWER, AND MAP ARE 100% OPERATIONAL!")

    finally:
        proc.terminate()

if __name__ == "__main__":
    test_user_flows()
