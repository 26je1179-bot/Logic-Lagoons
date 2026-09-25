import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "ulpin.db")

def init_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"Removed existing database at {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE parcels (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        ulpin         TEXT UNIQUE NOT NULL,
        address       TEXT NOT NULL,
        state         TEXT,
        district      TEXT,
        latitude      REAL NOT NULL,
        longitude     REAL NOT NULL,
        glb_filename  TEXT NOT NULL,
        total_floors  INTEGER,
        total_height_m REAL
    );
    """)

    cursor.execute("""
    CREATE TABLE floors (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        parcel_id     INTEGER NOT NULL REFERENCES parcels(id),
        floor_number  INTEGER NOT NULL,
        height_m      REAL NOT NULL,
        unit_type     TEXT,        -- parking / residential / commercial / retail / office / lobby
        area_sqm      REAL,
        owner_name    TEXT
    );
    """)

    
    cursor.execute("""
    INSERT INTO parcels (ulpin, address, state, district, latitude, longitude, glb_filename, total_floors, total_height_m)
    VALUES ('JH091234567801', 'Green Residency, Wasseypur Road, Dhanbad', 'Jharkhand', 'Dhanbad', 23.7957, 86.4304, 'parcel_1.glb', 4, 12.4);
    """)
    parcel_1_id = cursor.lastrowid

    p1_floors = [
        (parcel_1_id, 0, 3.0, 'parking',     150, None),
        (parcel_1_id, 1, 3.2, 'residential', 110, 'A. Sharma'),
        (parcel_1_id, 2, 3.2, 'residential', 110, 'R. Verma'),
        (parcel_1_id, 3, 3.0, 'residential', 105, 'S. Iyer'),
    ]
    cursor.executemany("""
    INSERT INTO floors (parcel_id, floor_number, height_m, unit_type, area_sqm, owner_name)
    VALUES (?, ?, ?, ?, ?, ?);
    """, p1_floors)

    
    cursor.execute("""
    INSERT INTO parcels (ulpin, address, state, district, latitude, longitude, glb_filename, total_floors, total_height_m)
    VALUES ('WB198765432102', 'Lake View Apartments, Ballygunge, Kolkata', 'West Bengal', 'Kolkata', 22.5262, 88.3649, 'three_floor_building.glb', 3, 9.0);
    """)
    parcel_2_id = cursor.lastrowid

    p2_floors = [
        (parcel_2_id, 1, 3.0, 'residential', 94, 'Owner 1'),
        (parcel_2_id, 2, 3.0, 'residential', 94, 'Owner 2'),
        (parcel_2_id, 3, 3.0, 'residential', 94, 'Owner 3'),
    ]
    cursor.executemany("""
    INSERT INTO floors (parcel_id, floor_number, height_m, unit_type, area_sqm, owner_name)
    VALUES (?, ?, ?, ?, ?, ?);
    """, p2_floors)

    
    cursor.execute("""
    INSERT INTO parcels (ulpin, address, state, district, latitude, longitude, glb_filename, total_floors, total_height_m)
    VALUES ('KA561122334403', 'Silicon Business Tower, MG Road, Bengaluru', 'Karnataka', 'Bengaluru Urban', 12.9758, 77.6045, 'parcel_3.glb', 9, 32.0);
    """)
    parcel_3_id = cursor.lastrowid

    p3_floors = [
        (parcel_3_id, 0, 4.0, 'lobby',  300, None),
        (parcel_3_id, 1, 3.5, 'office', 280, 'TechCorp Pvt Ltd'),
        (parcel_3_id, 2, 3.5, 'office', 280, 'TechCorp Pvt Ltd'),
        (parcel_3_id, 3, 3.5, 'office', 280, 'Nimbus Analytics'),
        (parcel_3_id, 4, 3.5, 'office', 280, 'Nimbus Analytics'),
        (parcel_3_id, 5, 3.5, 'office', 280, 'Orbit Software'),
        (parcel_3_id, 6, 3.5, 'office', 280, 'Orbit Software'),
        (parcel_3_id, 7, 3.5, 'office', 275, 'Vertex Studios'),
        (parcel_3_id, 8, 3.5, 'office', 275, 'Vertex Studios'),
    ]
    cursor.executemany("""
    INSERT INTO floors (parcel_id, floor_number, height_m, unit_type, area_sqm, owner_name)
    VALUES (?, ?, ?, ?, ?, ?);
    """, p3_floors)

    conn.commit()
    
    cursor.execute("""
    CREATE TABLE users (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        ulpin         TEXT UNIQUE NOT NULL REFERENCES parcels(ulpin),
        password      TEXT NOT NULL
    );
    """)

    users = [
        ('WB198765432102', '1234'),
        ('JH091234567801', '5678'),
        ('KA561122334403', '1000'),
    ]
    cursor.executemany("""
    INSERT INTO users (ulpin, password)
    VALUES (?, ?);
    """, users)

    conn.commit()
    conn.close()
    print(f"Database seeded successfully at {DB_PATH} with 3 parcels, 19 floors, and 3 users.")

if __name__ == "__main__":
    init_db()
