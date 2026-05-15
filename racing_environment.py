"""
Traffic Racing Game - Full Environment Generator (Single Mesh)
==============================================================
Run inside Blender Scripting tab.
Imports shared functionality from base_environment.py.

P1 features: road curbs, ground plane.
"""

import sys, os, bpy

# Determine directory containing this script
# Handles __file__ (direct execution), bpy context (Text Editor), and fallbacks
try:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    SCRIPT_DIR = None
    try:
        filepath = bpy.context.space_data.text.filepath
        if filepath:
            SCRIPT_DIR = os.path.dirname(os.path.abspath(filepath))
    except (AttributeError, TypeError):
        pass
    if not SCRIPT_DIR:
        SCRIPT_DIR = os.getcwd()

if SCRIPT_DIR not in sys.path:
    sys.path.append(SCRIPT_DIR)

from base_environment import *

import math, random
from mathutils import Vector

# ============================================================
# CONFIGURATION (overrides base defaults)
# ============================================================
ROAD_LENGTH = 300
ROAD_WIDTH = 12
LANE_COUNT = 3
TERRAIN_WIDTH = 45
SIDEWALK_WIDTH = 2
DECIMATE_RATIO = 0.6
BARRIER_HEIGHT = 0.8
BUILDING_MIN_H = 5
BUILDING_MAX_H = 25
TREE_COUNT = 40
BUILDING_COUNT = 18
LIGHT_SPACING = 25
SEED = 42
random.seed(SEED)


# ============================================================
# ROAD PATH (racing-specific: wider curves + tunnel dip)
# ============================================================
def get_road_points(count=150):
    """Generate road center points with S-curves, bridge bump, and tunnel dip."""
    pts = []
    for i in range(count):
        t = i / (count - 1)
        y = -ROAD_LENGTH/2 + ROAD_LENGTH * t
        x = 15 * math.sin(t * math.pi * 2) * (0.3 + 0.7 * math.sin(t * math.pi))
        if 0.4 < t < 0.5:
            z = 6 * math.sin((t - 0.4) / 0.1 * math.pi)
        elif 0.7 < t < 0.8:
            z = -3 * math.sin((t - 0.7) / 0.1 * math.pi)
        else:
            z = 0
        pts.append(Vector((x, y, z)))
    return pts


# Override the base version
road_pts = get_road_points


# ============================================================
# BARRIERS ALONG CURVED ROAD
# ============================================================
def create_curved_barriers(pts, side):
    """Add metal guardrail barriers along one side of the road."""
    objs = []
    hw = ROAD_WIDTH/2 - 0.3
    m_bar = get_mat('metal', make_metal_tex)
    step = max(1, len(pts) // 30)

    # Posts
    for i in range(0, len(pts), step):
        p = pts[i]
        _, right, _ = get_road_frame(pts, i)
        pos = p + right * side * hw
        o = cube(pos + Vector((0,0,BARRIER_HEIGHT/2)), (0.06,0.06,BARRIER_HEIGHT/2), m_bar)
        objs.append(o)

    # Rails
    for i in range(0, len(pts)-step, step):
        p1 = pts[i]; p2 = pts[min(i+step, len(pts)-1)]
        _, r1, _ = get_road_frame(pts, i)
        pos1 = p1 + r1 * side * hw; pos2 = p2 + r1 * side * hw
        mid = (pos1 + pos2) / 2 + Vector((0,0,BARRIER_HEIGHT*0.7))
        diff = pos2 - pos1; ln = diff.length
        angle = math.atan2(diff.x, diff.y)
        bpy.ops.mesh.primitive_cube_add(size=1)
        o = bpy.context.active_object
        o.scale = (0.04, ln/2, 0.05); o.location = mid
        o.rotation_euler.z = -angle; apply_obj(o)
        o.data.materials.append(m_bar); objs.append(o)
    return objs


# ============================================================
# BRIDGE
# ============================================================
def create_bridge(pts):
    """Add bridge supports and railings where road is elevated."""
    objs = []
    m_concrete = get_mat('concrete', make_concrete)
    m_rail = get_mat('metal', make_metal_tex)

    for i, p in enumerate(pts):
        if p.z < 1.0: continue
        _, right, _ = get_road_frame(pts, i)

        if i % 8 == 0:
            for side in [-1, 1]:
                pos = p + right * side * (ROAD_WIDTH/2 - 1)
                objs.append(cube(Vector((pos.x, pos.y, p.z/2)), (0.5, 0.5, p.z/2), m_concrete))
            objs.append(cube(Vector((p.x, p.y, p.z - 0.3)), (ROAD_WIDTH/2 + 0.5, 0.4, 0.3), m_concrete))

        if i % 3 == 0:
            for side in [-1, 1]:
                pos = p + right * side * (ROAD_WIDTH/2 + 0.1)
                objs.append(cube(pos + Vector((0,0,0.6)), (0.05, 0.05, 0.6), m_rail))
    return objs


# ============================================================
# TUNNEL
# ============================================================
def create_tunnel(pts):
    """Add tunnel structure where road dips below ground."""
    objs = []
    m_tunnel = get_mat('concrete', make_concrete)
    m_light = mat("Tunnel_Light", (1.0,0.9,0.6,1), emit=5.0)

    for i, p in enumerate(pts):
        if p.z >= -0.5: continue
        _, right, _ = get_road_frame(pts, i)

        if i % 3 == 0:
            for side in [-1, 1]:
                pos = p + right * side * (ROAD_WIDTH/2 + 0.5)
                objs.append(cube(pos + Vector((0,0,3)), (0.4, 0.6, 3), m_tunnel))
            objs.append(cube(Vector((p.x, p.y, p.z + 6.2)), (ROAD_WIDTH/2 + 1, 0.6, 0.3), m_tunnel))

        if i % 10 == 0:
            objs.append(cube(Vector((p.x, p.y, p.z + 5.8)), (0.3, 0.1, 0.05), m_light))
    return objs


# ============================================================
# HIGHWAY OVERPASS
# ============================================================
def create_overpass(pts):
    """Add a highway overpass crossing above the road at a flat section."""
    objs = []
    m_concrete = get_mat('concrete', make_concrete)
    m_asphalt = get_mat('asphalt', make_asphalt)
    m_rail = get_mat('metal', make_metal_tex)
    m_barrier = mat("Overpass_Barrier", (0.75, 0.75, 0.8, 1), rough=0.7)

    idx = int(0.22 * len(pts))
    p = pts[idx]
    fwd, right, up = get_road_frame(pts, idx)
    angle = math.atan2(right.x, right.y)

    OH = 6.5; OW = ROAD_WIDTH + 10; DT = 0.4

    # 4 support pillars
    for side_x in [-1, 1]:
        for side_z in [-1, 1]:
            pos = p + right * side_x * (ROAD_WIDTH/2 + 2) + fwd * side_z * 2
            objs.append(cube(pos + Vector((0, 0, OH/2)), (0.5, 0.5, OH/2), m_concrete))
            objs.append(cube(pos + Vector((0, 0, 0.15)), (0.7, 0.7, 0.15), m_concrete))
            objs.append(cube(pos + Vector((0, 0, OH - 0.15)), (0.6, 0.6, 0.15), m_concrete))

    # Deck
    bpy.ops.mesh.primitive_cube_add(size=2)
    deck = bpy.context.active_object
    deck.scale = (OW/2, 0.4, DT/2)
    deck.location = Vector((p.x, p.y, OH + DT/2))
    deck.rotation_euler.z = -angle; apply_obj(deck)
    deck.data.materials.append(m_asphalt); objs.append(deck)

    # Cross beams
    for fwd_off in [-2.0, 0, 2.0]:
        bpy.ops.mesh.primitive_cube_add(size=2)
        o = bpy.context.active_object
        o.scale = (OW/2 - 1.5, 0.12, 0.15)
        bp = p + fwd * fwd_off; bp.z = OH - 0.05
        o.location = bp; o.rotation_euler.z = -angle; apply_obj(o)
        o.data.materials.append(m_concrete); objs.append(o)

    # Guard railings
    for side in [-1, 1]:
        for fwd_off in range(-3, 4):
            pp = p + right * side * (OW/2 - 0.3) + fwd * fwd_off
            pp.z = OH + DT + 0.4
            objs.append(cube(pp, (0.04, 0.04, 0.7), m_rail))

        for rail_h in [0.3, 0.6]:
            bpy.ops.mesh.primitive_cube_add(size=2)
            o = bpy.context.active_object
            o.scale = (OW/2, 0.04, 0.03)
            rp = p + right * side * (OW/2 - 0.3); rp.z = OH + DT + rail_h
            o.location = rp; o.rotation_euler.z = -angle; apply_obj(o)
            o.data.materials.append(m_rail); objs.append(o)

    # Jersey barriers
    for side in [-1, 1]:
        bpy.ops.mesh.primitive_cube_add(size=2)
        o = bpy.context.active_object
        o.scale = (OW/2 - 0.3, 0.08, 0.15)
        bp = p + right * side * (OW/2 - 0.15); bp.z = OH + DT + 0.15
        o.location = bp; o.rotation_euler.z = -angle; apply_obj(o)
        o.data.materials.append(m_barrier); objs.append(o)

    # Approach ramps
    RAMP_LEN = 14; RAMP_W = 4.5; segs = 6
    for side in [-1, 1]:
        for s in range(segs):
            t0 = s/segs; t1 = (s+1)/segs; tm = (t0+t1)/2
            sh = OH * (t1 - t0) / 2; sch = OH * tm / 2
            rp = p + right * side * (OW/2 + tm * RAMP_LEN); rp.z = sch
            sl = RAMP_LEN / segs

            bpy.ops.mesh.primitive_cube_add(size=2)
            o = bpy.context.active_object
            o.scale = (sl/2, RAMP_W/2, max(sh, 0.05))
            o.location = rp; o.rotation_euler.z = -angle; apply_obj(o)
            o.data.materials.append(m_asphalt); objs.append(o)

            for rs in [-1, 1]:
                bpy.ops.mesh.primitive_cube_add(size=2)
                o = bpy.context.active_object
                o.scale = (sl/2, 0.06, max(sh, 0.05))
                wp = rp + fwd * rs * (RAMP_W/2 + 0.1); wp.z = sch
                o.location = wp; o.rotation_euler.z = -angle; apply_obj(o)
                o.data.materials.append(m_concrete); objs.append(o)

        ep = p + right * side * (OW/2 + RAMP_LEN); ep.z = 0.2
        objs.append(cube(ep, (0.3, RAMP_W/2, 0.2), m_concrete))

        for rs in [-1, 1]:
            for si in range(segs):
                t = (si + 0.5) / segs
                pp = p + right * side * (OW/2 + t * RAMP_LEN) + fwd * rs * (RAMP_W/2 + 0.05)
                pp.z = OH * t / 2 + 0.3
                objs.append(cube(pp, (0.04, 0.04, 0.4), m_rail))

    return objs


# ============================================================
# TRAFFIC SIGNS
# ============================================================
def create_traffic_signs(pts):
    objs = []
    m_pole = mat("Sign_Pole", (0.35,0.35,0.38,1), metal=0.8)
    sign_mats = [
        mat("Sign_Speed", (1.0,0.1,0.1,1)),
        mat("Sign_Warn", (1.0,0.8,0.0,1)),
        mat("Sign_Info", (0.1,0.4,0.9,1)),
        mat("Sign_Green", (0.1,0.7,0.2,1)),
    ]

    sign_interval = len(pts) // 12
    for idx in range(12):
        i = idx * sign_interval
        if i >= len(pts): break
        p = pts[i]
        if abs(p.z) > 1: continue

        _, right, _ = get_road_frame(pts, i)
        side = 1 if idx % 2 == 0 else -1
        pos = p + right * side * (ROAD_WIDTH/2 + SIDEWALK_WIDTH + 0.5)

        objs.append(cyl(pos + Vector((0,0,1.5)), 0.04, 3, 6, m_pole))
        sign_type = idx % 4
        if sign_type == 0:
            objs.append(cyl(pos + Vector((0,0,3.2)), 0.35, 0.03, 12, sign_mats[0]))
        elif sign_type == 1:
            o = cube(pos + Vector((0,0,3.2)), (0.3,0.03,0.3), sign_mats[1])
            o.rotation_euler.y = math.radians(45); apply_obj(o)
            objs.append(o)
        elif sign_type == 2:
            objs.append(cube(pos + Vector((0,0,3.2)), (0.4,0.03,0.25), sign_mats[2]))
        else:
            objs.append(cube(pos + Vector((0,0,3.2)), (0.6,0.03,0.3), sign_mats[3]))

        if idx % 4 == 0:
            for s in [-1, 1]:
                gp = p + right * s * (ROAD_WIDTH/2 + 0.5)
                objs.append(cyl(gp + Vector((0,0,4)), 0.08, 8, 6, m_pole))
            objs.append(cube(Vector((p.x, p.y, 8)), (ROAD_WIDTH/2 + 1, 0.1, 0.1), m_pole))
            objs.append(cube(Vector((p.x, p.y, 7.5)), (ROAD_WIDTH/2, 0.05, 0.8), sign_mats[3]))
    return objs


# ============================================================
# TREES, BUILDINGS, STREET LIGHTS
# ============================================================
def create_tree_at(pos, scale=1.0):
    objs = []
    m_bark = get_mat('bark', make_bark_tex)
    m_leaf1 = get_mat('leaf0', lambda: make_leaf_tex(0))
    m_leaf2 = get_mat('leaf1', lambda: make_leaf_tex(1))
    objs.append(cyl(pos + Vector((0,0,1*scale)), 0.2*scale, 2*scale, 6, m_bark))
    objs.append(cone(pos + Vector((0,0,2.5*scale)), 1.8*scale, 2*scale, 6, m_leaf1))
    objs.append(cone(pos + Vector((0,0,3.8*scale)), 1.3*scale, 1.8*scale, 6, m_leaf2))
    return objs


def place_trees(pts):
    objs = []
    for side in [-1, 1]:
        for _ in range(TREE_COUNT):
            i = random.randint(5, len(pts)-6)
            p = pts[i]
            if abs(p.z) > 0.5: continue
            _, right, _ = get_road_frame(pts, i)
            dist = ROAD_WIDTH/2 + SIDEWALK_WIDTH + random.uniform(3, TERRAIN_WIDTH - 5)
            pos = p + right * side * dist; pos.z = 0
            objs.extend(create_tree_at(pos, random.uniform(0.6, 1.4)))
    return objs


def place_buildings(pts):
    objs = []
    m_brick = get_mat('brick', make_brick)
    m_roof = mat("Roof", (0.15,0.15,0.18,1))
    m_window = mat("Window", (0.5,0.7,0.9,1), metal=0.3)

    spacing = len(pts) // BUILDING_COUNT
    for side in [-1, 1]:
        for bi in range(BUILDING_COUNT):
            i = bi * spacing + random.randint(0, max(1, spacing//2))
            if i >= len(pts): continue
            p = pts[i]
            if abs(p.z) > 0.5: continue
            _, right, _ = get_road_frame(pts, i)
            dist = ROAD_WIDTH/2 + SIDEWALK_WIDTH + random.uniform(12, 25)
            pos = p + right * side * dist; pos.z = 0

            w = random.uniform(4, 9); d = random.uniform(4, 9)
            h = random.uniform(BUILDING_MIN_H, BUILDING_MAX_H)

            objs.append(cube(pos + Vector((0,0,h/2)), (w/2, d/2, h/2), m_brick))
            objs.append(cube(pos + Vector((0,0,h+0.15)), (w/2+0.1, d/2+0.1, 0.15), m_roof))
            for wh in range(2, int(h), 5):
                objs.append(cube(pos + Vector((0, side*d/2+side*0.01, wh)),
                                 (w/2-0.3, 0.02, 0.5), m_window))
    return objs


def place_street_lights(pts):
    objs = []
    m_pole = get_mat('metal', make_metal_tex)
    m_head = mat("LightHead", (1.0,0.95,0.7,1), emit=3.0)

    step = max(1, len(pts) // (ROAD_LENGTH // LIGHT_SPACING))
    for i in range(0, len(pts), step):
        p = pts[i]; _, right, _ = get_road_frame(pts, i)
        for side in [-1, 1]:
            pos = p + right * side * (ROAD_WIDTH/2 + SIDEWALK_WIDTH - 0.5)
            if abs(pos.z) > 1: continue
            pos.z = max(pos.z, 0)
            objs.append(cyl(pos + Vector((0,0,2.5)), 0.06, 5, 6, m_pole))
            arm = -side
            objs.append(cube(pos + Vector((arm*0.8, 0, 5)), (0.8, 0.06, 0.06), m_pole))
            objs.append(cube(pos + Vector((arm*1.5, 0, 4.9)), (0.25, 0.12, 0.06), m_head))
    return objs


# ============================================================
# ROAD MEDIAN STRIP
# ============================================================
def create_median(pts):
    """Small raised median divider down the road center."""
    objs = []
    m_med = get_mat('concrete', make_concrete)
    step = max(1, len(pts) // 40)
    for i in range(0, len(pts)-step, step):
        p = pts[i]; p2 = pts[min(i+step, len(pts)-1)]
        mid = (p + p2) / 2 + Vector((0,0,0.06))
        diff = p2 - p; ln = diff.length
        angle = math.atan2(diff.x, diff.y)
        bpy.ops.mesh.primitive_cube_add(size=1)
        o = bpy.context.active_object
        o.scale = (0.08, ln/2, 0.06); o.location = mid
        o.rotation_euler.z = -angle; apply_obj(o)
        o.data.materials.append(m_med); objs.append(o)
    return objs


# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 50)
    print("Generating Racing Environment with Textures...")
    print("=" * 50)
    _mat_cache.clear()
    clear_scene()

    # Apply artist profile settings from BlenderMCP panel
    cfg = apply_profile_config()
    print(f"  Export Format: {cfg['export_format']}")
    print(f"  Naming Prefix: {cfg['naming_prefix']}")

    pts = get_road_points(150)

    print("[1/15] Road surface..."); create_road_mesh(pts)
    print("[2/15] Lane markings..."); create_curved_markings(pts, LANE_COUNT)
    print("[3/15] Median..."); create_median(pts)
    print("[4/15] Sidewalks...")
    for s in [-1, 1]: create_sidewalk_side(pts, s)
    print("[5/15] Road curbs..."); create_road_curbs(pts)
    print("[6/15] Ground plane..."); create_ground_plane()
    print("[7/15] Terrain...")
    for s in [-1, 1]: create_terrain_side(pts, s)
    print("[8/15] Barriers...")
    for s in [-1, 1]: create_curved_barriers(pts, s)
    print("[9/15] Bridge..."); create_bridge(pts)
    print("[10/15] Tunnel..."); create_tunnel(pts)
    print("[11/15] Overpass..."); create_overpass(pts)
    print("[12/15] Traffic signs..."); create_traffic_signs(pts)
    print("[13/15] Scenery (trees, buildings, lights)...")
    place_trees(pts); place_buildings(pts); place_street_lights(pts)
    print("[14/15] Traffic props..."); place_traffic_props(pts)
    print("[15/15] Joining into single mesh...")

    result = join_all("RacingEnvironment_SingleMesh")

    if result:
        v = len(result.data.vertices); f = len(result.data.polygons)
        m = len(result.data.materials)
        print(f"\n{'='*50}")
        print(f"DONE! '{result.name}' — Verts: {v} | Faces: {f} | Mats: {m}")
        print(f"{'='*50}")

    setup_scene(use_profile=True)
    print("\nExport: File > Export > FBX or glTF")

if __name__ == "__main__":
    main()
