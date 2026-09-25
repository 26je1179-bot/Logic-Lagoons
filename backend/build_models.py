"""
Script to generate GLB models with embedded custom properties using Blender bpy.
Generates:
  backend/models/parcel_1.glb (Dhanbad, 4 floors, 12.4m)
  backend/models/parcel_2.glb (Kolkata, 6 floors, 19.0m)
  backend/models/parcel_3.glb (Bengaluru, 9 floors, 32.0m)
"""
import bpy
import bmesh
import os
import math

try:
    _dir = os.path.dirname(__file__)
except NameError:
    _dir = r"c:\Users\Paras patil\OneDrive\Desktop\SIH NIKHIL\backend"
MODELS_DIR = os.path.abspath(os.path.join(_dir, "models"))
os.makedirs(MODELS_DIR, exist_ok=True)

def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def create_material(name, diffuse_color, roughness=0.4, metallic=0.0):
    mat = bpy.data.materials.get(name)
    if not mat:
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = diffuse_color
            bsdf.inputs["Roughness"].default_value = roughness
            bsdf.inputs["Metallic"].default_value = metallic
    return mat

def create_box_mesh(name, min_pt, max_pt, mat):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    
    # 8 vertices
    x0, y0, z0 = min_pt
    x1, y1, z1 = max_pt
    verts = [
        bm.verts.new((x0, y0, z0)),
        bm.verts.new((x1, y0, z0)),
        bm.verts.new((x1, y1, z0)),
        bm.verts.new((x0, y1, z0)),
        bm.verts.new((x0, y0, z1)),
        bm.verts.new((x1, y0, z1)),
        bm.verts.new((x1, y1, z1)),
        bm.verts.new((x0, y1, z1)),
    ]
    bm.verts.ensure_lookup_table()
    
    # 6 faces
    faces = [
        [0, 1, 2, 3], # bottom
        [4, 7, 6, 5], # top
        [0, 4, 5, 1], # front
        [1, 5, 6, 2], # right
        [2, 6, 7, 3], # back
        [3, 7, 4, 0], # left
    ]
    for f in faces:
        bm.faces.new([verts[i] for i in f])
        
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    if mat:
        obj.data.materials.append(mat)
    return obj

def add_box_to_bmesh(bm, min_pt, max_pt):
    x0, y0, z0 = min_pt
    x1, y1, z1 = max_pt
    v0 = bm.verts.new((x0, y0, z0))
    v1 = bm.verts.new((x1, y0, z0))
    v2 = bm.verts.new((x1, y1, z0))
    v3 = bm.verts.new((x0, y1, z0))
    v4 = bm.verts.new((x0, y0, z1))
    v5 = bm.verts.new((x1, y0, z1))
    v6 = bm.verts.new((x1, y1, z1))
    v7 = bm.verts.new((x0, y1, z1))
    
    faces = [
        [v0, v1, v2, v3],
        [v4, v7, v6, v5],
        [v0, v4, v5, v1],
        [v1, v5, v6, v2],
        [v2, v6, v7, v3],
        [v3, v7, v4, v0],
    ]
    created = []
    for f in faces:
        created.append(bm.faces.new(f))
    return created

def build_parcel_1():
    """Dhanbad - 4 floors (12.4m total):
       FL0: 3.0m Parking (open pillars)
       FL1: 3.2m Residential
       FL2: 3.2m Residential
       FL3: 3.0m Residential + roof parapet
    """
    reset_scene()
    
    mat_parking = create_material("Mat_Parking", (0.35, 0.38, 0.40, 1.0), roughness=0.8)
    mat_res1 = create_material("Mat_Res1", (0.82, 0.72, 0.60, 1.0), roughness=0.5)
    mat_res2 = create_material("Mat_Res2", (0.78, 0.68, 0.56, 1.0), roughness=0.5)
    mat_res3 = create_material("Mat_Res3", (0.85, 0.75, 0.62, 1.0), roughness=0.5)
    mat_accent = create_material("Mat_Accent", (0.3, 0.25, 0.2, 1.0), roughness=0.6)
    
    width = 12.0
    depth = 10.0
    half_w = width / 2.0
    half_d = depth / 2.0
    
    floors_data = [
        {"num": 0, "h": 3.0, "type": "parking", "area": 150.0, "owner": "", "mat": mat_parking},
        {"num": 1, "h": 3.2, "type": "residential", "area": 110.0, "owner": "A. Sharma", "mat": mat_res1},
        {"num": 2, "h": 3.2, "type": "residential", "area": 110.0, "owner": "R. Verma", "mat": mat_res2},
        {"num": 3, "h": 3.0, "type": "residential", "area": 105.0, "owner": "S. Iyer", "mat": mat_res3},
    ]
    
    cur_z = 0.0
    for fl in floors_data:
        z0 = cur_z
        z1 = cur_z + fl["h"]
        
        mesh = bpy.data.meshes.new(f"FloorMesh_{fl['num']}")
        bm = bmesh.new()
        
        if fl["type"] == "parking":
            # Slab base
            add_box_to_bmesh(bm, (-half_w, -half_d, z0), (half_w, half_d, z0 + 0.25))
            # 6 Pillars
            pillar_r = 0.4
            for px in [-half_w + 1.0, 0.0, half_w - 1.0]:
                for py in [-half_d + 1.0, half_d - 1.0]:
                    add_box_to_bmesh(bm, (px - pillar_r, py - pillar_r, z0 + 0.25), 
                                         (px + pillar_r, py + pillar_r, z1 - 0.25))
            # Rear wall for security/utility
            add_box_to_bmesh(bm, (-half_w, half_d - 0.4, z0 + 0.25), (half_w, half_d, z1 - 0.25))
            # Ceiling slab
            add_box_to_bmesh(bm, (-half_w, -half_d, z1 - 0.25), (half_w, half_d, z1))
        else:
            # Main floor body
            add_box_to_bmesh(bm, (-half_w + 0.2, -half_d + 0.2, z0), (half_w - 0.2, half_d - 0.2, z1))
            # Front balcony
            add_box_to_bmesh(bm, (-half_w + 1.5, -half_d - 0.8, z0), (half_w - 1.5, -half_d + 0.2, z0 + 0.2))
            add_box_to_bmesh(bm, (-half_w + 1.5, -half_d - 0.8, z0 + 0.2), (half_w - 1.5, -half_d - 0.6, z0 + 1.1))
            add_box_to_bmesh(bm, (-half_w + 1.5, -half_d - 0.8, z0 + 0.2), (-half_w + 1.7, -half_d + 0.2, z0 + 1.1))
            add_box_to_bmesh(bm, (half_w - 1.7, -half_d - 0.8, z0 + 0.2), (half_w - 1.5, -half_d + 0.2, z0 + 1.1))
            # Slab trim
            add_box_to_bmesh(bm, (-half_w - 0.1, -half_d - 0.1, z1 - 0.2), (half_w + 0.1, half_d + 0.1, z1))
            
            # If top floor, add rooftop parapet and stairhead
            if fl["num"] == 3:
                # Parapet
                add_box_to_bmesh(bm, (-half_w, -half_d, z1), (half_w, -half_d + 0.3, z1 + 0.9))
                add_box_to_bmesh(bm, (-half_w, half_d - 0.3, z1), (half_w, half_d, z1 + 0.9))
                add_box_to_bmesh(bm, (-half_w, -half_d, z1), (-half_w + 0.3, half_d, z1 + 0.9))
                add_box_to_bmesh(bm, (half_w - 0.3, -half_d, z1), (half_w, half_d, z1 + 0.9))
                # Overhead water tank / room
                add_box_to_bmesh(bm, (-2.0, 1.0, z1), (2.0, 4.0, z1 + 2.0))
        
        bm.to_mesh(mesh)
        bm.free()
        
        obj = bpy.data.objects.new(f"Floor_{fl['num']}", mesh)
        bpy.context.collection.objects.link(obj)
        obj.data.materials.append(fl["mat"])
        
        # Add custom properties required by the specification
        obj["floor_number"] = fl["num"]
        obj["height_m"] = round(fl["h"], 2)
        obj["unit_type"] = fl["type"]
        obj["area_sqm"] = fl["area"]
        obj["owner_name"] = fl["owner"]
        
        cur_z = z1
        
    out_path = os.path.join(MODELS_DIR, "parcel_1.glb")
    bpy.ops.export_scene.gltf(
        filepath=out_path,
        export_format='GLB',
        export_extras=True,
        export_materials='EXPORT',
        export_apply=True
    )
    print(f"Exported parcel_1.glb to {out_path} (Z={cur_z}m)")

def build_parcel_2():
    """Kolkata - 6 floors (19.0m total):
       FL0: 3.5m Retail
       FL1: 3.5m Commercial
       FL2-5: 3.0m Residential (x4)
    """
    reset_scene()
    
    mat_retail = create_material("Mat_Retail", (0.15, 0.25, 0.35, 1.0), roughness=0.2, metallic=0.3)
    mat_commercial = create_material("Mat_Comm", (0.3, 0.45, 0.6, 1.0), roughness=0.3, metallic=0.5)
    mat_res = create_material("Mat_ResKolkata", (0.9, 0.85, 0.78, 1.0), roughness=0.6)
    mat_glass = create_material("Mat_Glass", (0.2, 0.6, 0.8, 0.9), roughness=0.1, metallic=0.8)
    
    width = 14.0
    depth = 11.0
    half_w = width / 2.0
    half_d = depth / 2.0
    
    floors_data = [
        {"num": 0, "h": 3.5, "type": "retail", "area": 200.0, "owner": "", "mat": mat_retail},
        {"num": 1, "h": 3.5, "type": "commercial", "area": 180.0, "owner": "", "mat": mat_commercial},
        {"num": 2, "h": 3.0, "type": "residential", "area": 140.0, "owner": "P. Banerjee", "mat": mat_res},
        {"num": 3, "h": 3.0, "type": "residential", "area": 140.0, "owner": "M. Das", "mat": mat_res},
        {"num": 4, "h": 3.0, "type": "residential", "area": 135.0, "owner": "K. Chatterjee", "mat": mat_res},
        {"num": 5, "h": 3.0, "type": "residential", "area": 130.0, "owner": "T. Roy", "mat": mat_res},
    ]
    
    cur_z = 0.0
    for fl in floors_data:
        z0 = cur_z
        z1 = cur_z + fl["h"]
        
        mesh = bpy.data.meshes.new(f"FloorMesh_{fl['num']}")
        bm = bmesh.new()
        
        if fl["type"] == "retail":
            # Ground floor retail with grand entrance and glass display boxes
            add_box_to_bmesh(bm, (-half_w, -half_d, z0), (half_w, half_d, z1))
            # Storefront canopy
            add_box_to_bmesh(bm, (-half_w - 0.5, -half_d - 1.2, z1 - 0.4), (half_w + 0.5, -half_d, z1 - 0.1))
            # Display frame pillars
            for px in [-half_w + 0.5, -half_w / 3, half_w / 3, half_w - 0.5]:
                add_box_to_bmesh(bm, (px - 0.3, -half_d - 0.1, z0), (px + 0.3, -half_d + 0.1, z1 - 0.4))
        elif fl["type"] == "commercial":
            # Commercial ribbon glass level
            add_box_to_bmesh(bm, (-half_w, -half_d, z0), (half_w, half_d, z1))
            # Continuous decorative sunshade / louver
            add_box_to_bmesh(bm, (-half_w - 0.3, -half_d - 0.6, z0 + fl["h"] * 0.5), 
                                 (half_w + 0.3, -half_d, z0 + fl["h"] * 0.5 + 0.15))
        else:
            # Residential with tiered balconies
            add_box_to_bmesh(bm, (-half_w, -half_d, z0), (half_w, half_d, z1))
            # Corner balconies
            add_box_to_bmesh(bm, (-half_w - 0.8, -half_d - 0.8, z0), (-half_w + 2.5, -half_d, z0 + 0.2))
            add_box_to_bmesh(bm, (-half_w - 0.8, -half_d - 0.8, z0 + 0.2), (-half_w + 2.5, -half_d - 0.6, z0 + 1.0))
            add_box_to_bmesh(bm, (half_w - 2.5, -half_d - 0.8, z0), (half_w + 0.8, -half_d, z0 + 0.2))
            add_box_to_bmesh(bm, (half_w - 2.5, -half_d - 0.8, z0 + 0.2), (half_w + 0.8, -half_d - 0.6, z0 + 1.0))
            
            if fl["num"] == 5:
                # Rooftop parapet & terrace lounge
                add_box_to_bmesh(bm, (-half_w, -half_d, z1), (half_w, half_d, z1 + 1.0))
                # Lift motor room
                add_box_to_bmesh(bm, (-2.5, -1.0, z1), (2.5, 3.0, z1 + 2.5))
        
        bm.to_mesh(mesh)
        bm.free()
        
        obj = bpy.data.objects.new(f"Floor_{fl['num']}", mesh)
        bpy.context.collection.objects.link(obj)
        obj.data.materials.append(fl["mat"])
        
        obj["floor_number"] = fl["num"]
        obj["height_m"] = round(fl["h"], 2)
        obj["unit_type"] = fl["type"]
        obj["area_sqm"] = fl["area"]
        obj["owner_name"] = fl["owner"]
        
        cur_z = z1
        
    out_path = os.path.join(MODELS_DIR, "parcel_2.glb")
    bpy.ops.export_scene.gltf(
        filepath=out_path,
        export_format='GLB',
        export_extras=True,
        export_materials='EXPORT',
        export_apply=True
    )
    print(f"Exported parcel_2.glb to {out_path} (Z={cur_z}m)")

def build_parcel_3():
    """Bengaluru - 9 floors (32.0m total):
       FL0: 4.0m Lobby
       FL1-8: 3.5m Office (x8)
    """
    reset_scene()
    
    mat_lobby = create_material("Mat_Lobby", (0.1, 0.15, 0.2, 1.0), roughness=0.1, metallic=0.8)
    mat_tower = create_material("Mat_TowerGlass", (0.2, 0.45, 0.65, 1.0), roughness=0.2, metallic=0.7)
    mat_spandrel = create_material("Mat_Spandrel", (0.15, 0.18, 0.22, 1.0), roughness=0.4, metallic=0.8)
    
    width = 16.0
    depth = 14.0
    half_w = width / 2.0
    half_d = depth / 2.0
    
    floors_data = [
        {"num": 0, "h": 4.0, "type": "lobby", "area": 300.0, "owner": ""},
        {"num": 1, "h": 3.5, "type": "office", "area": 280.0, "owner": "TechCorp Pvt Ltd"},
        {"num": 2, "h": 3.5, "type": "office", "area": 280.0, "owner": "TechCorp Pvt Ltd"},
        {"num": 3, "h": 3.5, "type": "office", "area": 280.0, "owner": "Nimbus Analytics"},
        {"num": 4, "h": 3.5, "type": "office", "area": 280.0, "owner": "Nimbus Analytics"},
        {"num": 5, "h": 3.5, "type": "office", "area": 280.0, "owner": "Orbit Software"},
        {"num": 6, "h": 3.5, "type": "office", "area": 280.0, "owner": "Orbit Software"},
        {"num": 7, "h": 3.5, "type": "office", "area": 275.0, "owner": "Vertex Studios"},
        {"num": 8, "h": 3.5, "type": "office", "area": 275.0, "owner": "Vertex Studios"},
    ]
    
    cur_z = 0.0
    for fl in floors_data:
        z0 = cur_z
        z1 = cur_z + fl["h"]
        
        mesh = bpy.data.meshes.new(f"FloorMesh_{fl['num']}")
        bm = bmesh.new()
        
        if fl["type"] == "lobby":
            # Grand high entrance lobby
            add_box_to_bmesh(bm, (-half_w, -half_d, z0), (half_w, half_d, z1))
            # Grand Entrance Portico / Canopy
            add_box_to_bmesh(bm, (-half_w * 0.6, -half_d - 3.0, z0 + 3.2), (half_w * 0.6, -half_d, z0 + 3.6))
            # Support columns for canopy
            col_r = 0.35
            for cx in [-half_w * 0.5, half_w * 0.5]:
                add_box_to_bmesh(bm, (cx - col_r, -half_d - 2.8, z0), (cx + col_r, -half_d - 2.8 + col_r*2, z0 + 3.2))
            # Architectural slab floor separator
            add_box_to_bmesh(bm, (-half_w - 0.4, -half_d - 0.4, z1 - 0.3), (half_w + 0.4, half_d + 0.4, z1))
        else:
            # Modern Curtain Wall office floor
            # Core floor plate
            add_box_to_bmesh(bm, (-half_w, -half_d, z0), (half_w, half_d, z1))
            # Horizontal metallic spandrel ribbon
            add_box_to_bmesh(bm, (-half_w - 0.2, -half_d - 0.2, z0), (half_w + 0.2, half_d + 0.2, z0 + 0.7))
            add_box_to_bmesh(bm, (-half_w - 0.2, -half_d - 0.2, z1 - 0.4), (half_w + 0.2, half_d + 0.2, z1))
            # Vertical architectural mullions / fins
            for mx in range(int(-half_w) + 2, int(half_w) - 1, 3):
                add_box_to_bmesh(bm, (mx - 0.1, -half_d - 0.35, z0), (mx + 0.1, -half_d, z1))
                add_box_to_bmesh(bm, (mx - 0.1, half_d, z0), (mx + 0.1, half_d + 0.35, z1))
            
            # Top floor: Architectural Crown and Helipad/Equipment plant
            if fl["num"] == 8:
                # Crown parapet
                add_box_to_bmesh(bm, (-half_w - 0.3, -half_d - 0.3, z1), (half_w + 0.3, half_d + 0.3, z1 + 1.8))
                # HVAC chiller & elevator machine structure
                add_box_to_bmesh(bm, (-4.0, -3.5, z1), (4.0, 3.5, z1 + 3.5))
                # Antenna / Spire
                add_box_to_bmesh(bm, (-0.2, -0.2, z1 + 3.5), (0.2, 0.2, z1 + 8.0))
        
        bm.to_mesh(mesh)
        bm.free()
        
        obj = bpy.data.objects.new(f"Floor_{fl['num']}", mesh)
        bpy.context.collection.objects.link(obj)
        
        mat = mat_lobby if fl["type"] == "lobby" else mat_tower
        obj.data.materials.append(mat)
        
        obj["floor_number"] = fl["num"]
        obj["height_m"] = round(fl["h"], 2)
        obj["unit_type"] = fl["type"]
        obj["area_sqm"] = fl["area"]
        obj["owner_name"] = fl["owner"]
        
        cur_z = z1
        
    out_path = os.path.join(MODELS_DIR, "parcel_3.glb")
    bpy.ops.export_scene.gltf(
        filepath=out_path,
        export_format='GLB',
        export_extras=True,
        export_materials='EXPORT',
        export_apply=True
    )
    print(f"Exported parcel_3.glb to {out_path} (Z={cur_z}m)")

if __name__ == "__main__":
    print("Building 3D models with Blender...")
    build_parcel_1()
    build_parcel_2()
    build_parcel_3()
    print("All models generated successfully!")
