"""
Japanese Racing Environment - Single Mesh for Blender
=====================================================
Run inside Blender Scripting tab.
Imports shared functionality from base_environment.py.

P1 features: sidewalks, road curbs, ground plane.
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
ROAD_LENGTH = 250
ROAD_WIDTH = 10
TERRAIN_WIDTH = 40
SIDEWALK_WIDTH = 2
DECIMATE_RATIO = 0.6
SEED = 42
random.seed(SEED)

# ============================================================
# JAPANESE-SPECIFIC MATERIALS
# ============================================================

def make_wood():
    """Dark wood texture (Japanese style). Already in base, kept for clarity."""
    m = bpy.data.materials.new("JP_Wood"); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs['Roughness'].default_value = 0.9
    add_noise_texture(nt, bsdf, (0.3, 0.18, 0.08, 1), scale=12, detail=8, mix_fac=0.4)
    return m

mt_wood = make_wood

def make_tile():
    """Stone tile texture (Japanese style). Already in base, kept for clarity."""
    m = bpy.data.materials.new("JP_Tile"); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs['Roughness'].default_value = 0.7
    add_noise_texture(nt, bsdf, (0.15, 0.15, 0.2, 1), scale=15, detail=5, mix_fac=0.2)
    return m

mt_tile = make_tile


# ============================================================
# JAPANESE DECORATIVE ELEMENTS
# ============================================================

def make_sakura(pos, sc=1.0):
    """Cherry blossom tree."""
    objs = []
    mb = get_mat('wood', make_wood)
    mp = mat("Sakura_Pink", (0.9, 0.5, 0.55, 1))
    mp2 = mat("Sakura_Lt", (0.95, 0.7, 0.72, 1))
    objs.append(cyl(pos + Vector((0,0,1.2*sc)), 0.15*sc, 2.4*sc, 5, mb))
    for ang in [0.5, 2.1, 3.7, 5.3]:
        bx_pos = pos + Vector((math.cos(ang)*0.8*sc, math.sin(ang)*0.8*sc, 2.2*sc))
        objs.append(cyl(bx_pos, 0.05*sc, 1.2*sc, 4, mb))
    objs.append(cone(pos + Vector((0,0,3.2*sc)), 2.0*sc, 1.8*sc, 5, mp))
    objs.append(cone(pos + Vector((0.5*sc,0,3.8*sc)), 1.5*sc, 1.5*sc, 5, mp2))
    objs.append(cone(pos + Vector((-0.4*sc,0.3*sc,3.5*sc)), 1.3*sc, 1.3*sc, 5, mp))
    return objs


def make_torii(pos, rot=0):
    """Torii gate (Japanese shrine gate)."""
    objs = []
    mr = mat("Torii_Red", (0.7, 0.05, 0.02, 1))
    mb = mat("Torii_Black", (0.05, 0.05, 0.05, 1))
    w = 4; h = 5
    for s in [-1, 1]:
        px = pos + Vector((s*w/2, 0, 0))
        objs.append(cyl(px + Vector((0,0,h/2)), 0.2, h, 5, mr))
    objs.append(cube(pos + Vector((0,0,h)), (w/2+0.5, 0.15, 0.2), mb))
    objs.append(cube(pos + Vector((0,0,h*0.75)), (w/2+0.1, 0.1, 0.12), mr))
    return objs


def make_jp_building(pos, w, d, h):
    """Japanese-style building with pagoda roof."""
    objs = []
    mwall = mat("JP_Wall", (0.9, 0.88, 0.82, 1), rough=0.9)
    mroof = get_mat('tile', make_tile)
    mframe = get_mat('wood', make_wood)
    objs.append(cube(pos + Vector((0,0,h/2)), (w/2, d/2, h/2), mwall))
    objs.append(cube(pos + Vector((0,0,h)), (w/2+0.05, d/2+0.05, 0.08), mframe))
    objs.append(cube(pos + Vector((0,0,0.1)), (w/2+0.05, d/2+0.05, 0.08), mframe))
    for tier in range(2):
        rh = h + 0.3 + tier*0.4
        rw = w/2 + 1.2 - tier*0.3
        rd_ = d/2 + 1.2 - tier*0.3
        objs.append(cube(pos + Vector((0,0,rh)), (rw, rd_, 0.15), mroof))
    objs.append(cone(pos + Vector((0,0,h+1.5)), w/2*0.5, 1.0, 4, mroof))
    return objs


def make_lantern(pos):
    """Japanese stone lantern."""
    objs = []
    ms = mat("Stone", (0.5, 0.48, 0.45, 1), rough=0.95)
    ml = mat("Lantern_Glow", (1.0, 0.8, 0.3, 1), emit=4.0)
    objs.append(cube(pos + Vector((0,0,0.1)), (0.25, 0.25, 0.1), ms))
    objs.append(cyl(pos + Vector((0,0,0.5)), 0.08, 0.6, 5, ms))
    objs.append(cube(pos + Vector((0,0,0.9)), (0.2, 0.2, 0.15), ml))
    objs.append(cone(pos + Vector((0,0,1.15)), 0.3, 0.3, 4, ms))
    return objs


def make_vending(pos):
    """Japanese vending machine."""
    mv = mat("Vend_Blue", (0.1, 0.2, 0.7, 1), metal=0.3)
    mg = mat("Vend_Glow", (0.3, 0.8, 1.0, 1), emit=2.0)
    objs = []
    objs.append(cube(pos + Vector((0,0,0.9)), (0.5, 0.35, 0.9), mv))
    objs.append(cube(pos + Vector((0,0.36,1.1)), (0.4, 0.01, 0.5), mg))
    return objs


def make_bamboo_fence(pos, length, rot=0):
    """Bamboo fence section."""
    objs = []
    mg = mat("Bamboo", (0.4, 0.5, 0.2, 1), rough=0.7)
    count = int(length / 0.4)
    for i in range(count):
        x = pos.x + i*0.4 - length/2
        h = random.uniform(1.5, 2.2)
        objs.append(cyl(Vector((x, pos.y, h/2)), 0.04, h, 4, mg))
    objs.append(cube(pos + Vector((0,0,0.5)), (length/2, 0.03, 0.03), mg))
    objs.append(cube(pos + Vector((0,0,1.2)), (length/2, 0.03, 0.03), mg))
    return objs


def make_neon_sign(pos):
    """Neon sign (Tokyo street style)."""
    colors = [(1,0.1,0.3,1), (0.1,0.5,1,1), (1,0.4,0.8,1), (0.2,1,0.5,1)]
    c = random.choice(colors)
    mn = mat("Neon", c, emit=6.0)
    md = mat("SignBG", (0.08, 0.08, 0.1, 1))
    objs = []
    objs.append(cube(pos, (0.8, 0.05, 0.5), md))
    objs.append(cube(pos + Vector((0,0.06,0)), (0.7, 0.02, 0.4), mn))
    return objs


# ============================================================
# BRIDGE (Japanese style with red rails)
# ============================================================
def make_bridge_supports(pts):
    """Japanese-styled bridge supports with red railings."""
    objs = []
    mc = mat("Bridge_C", (0.45, 0.43, 0.4, 1), rough=0.9)
    mr = mat("Bridge_R", (0.5, 0.1, 0.05, 1))
    for i, p in enumerate(pts):
        if p.z < 1: continue
        _, right, _ = get_road_frame(pts, i)
        if i % 10 == 0:
            for s in [-1, 1]:
                pp = p + right * s * (ROAD_WIDTH/2 - 1)
                objs.append(cube(Vector((pp.x, pp.y, p.z/2)), (0.4, 0.4, p.z/2), mc))
            objs.append(cube(Vector((p.x, p.y, p.z - 0.3)), (ROAD_WIDTH/2 + 0.3, 0.3, 0.25), mc))
        if i % 4 == 0:
            for s in [-1, 1]:
                pp = p + right * s * (ROAD_WIDTH/2 + 0.1)
                objs.append(cube(pp + Vector((0,0,0.5)), (0.04, 0.04, 0.5), mr))
    return objs


# ============================================================
# HIGHWAY OVERPASS (Japanese style)
# ============================================================
def create_overpass(pts):
    """Add a Japanese-themed highway overpass crossing above the road.
    Uses torii-inspired red pillars, dark wood railings, tile barriers,
    and stone lantern decorations.
    """
    objs = []
    m_asphalt = get_mat('asphalt', make_asphalt)
    m_wood = get_mat('wood', make_wood)
    m_tile = get_mat('tile', make_tile)
    m_pillar = mat("Overpass_Red", (0.5, 0.1, 0.05, 1), rough=0.85)
    m_beam = mat("Overpass_Dark", (0.05, 0.05, 0.05, 1), rough=0.9)

    idx = int(0.22 * len(pts))
    p = pts[idx]
    fwd, right, up = get_road_frame(pts, idx)
    angle = math.atan2(right.x, right.y)

    OH = 6.0; OW = ROAD_WIDTH + 10; DT = 0.35

    # 4 Torii-style support pillars
    for side_x in [-1, 1]:
        for side_z in [-1, 1]:
            pos = p + right * side_x * (ROAD_WIDTH/2 + 2) + fwd * side_z * 2
            objs.append(cyl(pos + Vector((0, 0, OH/2)), 0.25, OH, 6, m_pillar))
            objs.append(cube(pos + Vector((0, 0, 0.15)), (0.7, 0.7, 0.15), m_tile))
            objs.append(cube(pos + Vector((0, 0, OH - 0.1)), (0.6, 0.6, 0.1), m_beam))
            objs.append(cone(pos + Vector((0, 0, OH + 0.1)), 0.2, 0.3, 5, m_tile))

    # Main deck
    bpy.ops.mesh.primitive_cube_add(size=2)
    deck = bpy.context.active_object
    deck.scale = (OW/2, 0.35, DT/2)
    deck.location = Vector((p.x, p.y, OH + DT/2))
    deck.rotation_euler.z = -angle
    apply_obj(deck)
    deck.data.materials.append(m_asphalt)
    objs.append(deck)

    # Cross beams
    for fwd_off in [-2.0, 0, 2.0]:
        bpy.ops.mesh.primitive_cube_add(size=2)
        o = bpy.context.active_object
        o.scale = (OW/2 - 1.5, 0.1, 0.12)
        beam_pos = p + fwd * fwd_off
        beam_pos.z = OH - 0.05
        o.location = beam_pos
        o.rotation_euler.z = -angle
        apply_obj(o)
        o.data.materials.append(m_wood)
        objs.append(o)

    # Guard railings (dark wood)
    for side in [-1, 1]:
        for fwd_off in range(-3, 4):
            post_pos = p + right * side * (OW/2 - 0.3) + fwd * fwd_off
            post_pos.z = OH + DT + 0.35
            objs.append(cube(post_pos, (0.04, 0.04, 0.6), m_wood))

        for rail_h in [0.25, 0.5]:
            bpy.ops.mesh.primitive_cube_add(size=2)
            o = bpy.context.active_object
            o.scale = (OW/2, 0.04, 0.03)
            rail_pos = p + right * side * (OW/2 - 0.3)
            rail_pos.z = OH + DT + rail_h
            o.location = rail_pos
            o.rotation_euler.z = -angle
            apply_obj(o)
            o.data.materials.append(m_wood)
            objs.append(o)

    # Tile barriers
    for side in [-1, 1]:
        bpy.ops.mesh.primitive_cube_add(size=2)
        o = bpy.context.active_object
        o.scale = (OW/2 - 0.3, 0.08, 0.15)
        bp = p + right * side * (OW/2 - 0.15)
        bp.z = OH + DT + 0.15
        o.location = bp
        o.rotation_euler.z = -angle
        apply_obj(o)
        o.data.materials.append(m_tile)
        objs.append(o)

    # Approach ramps
    RAMP_LEN = 12; RAMP_W = 4.0; segs = 5
    for side in [-1, 1]:
        for s in range(segs):
            t0 = s/segs; t1 = (s+1)/segs; tm = (t0+t1)/2
            sh = OH * (t1 - t0) / 2; sch = OH * tm / 2
            rp = p + right * side * (OW/2 + tm * RAMP_LEN)
            rp.z = sch
            sl = RAMP_LEN / segs

            bpy.ops.mesh.primitive_cube_add(size=2)
            o = bpy.context.active_object
            o.scale = (sl/2, RAMP_W/2, max(sh, 0.05))
            o.location = rp; o.rotation_euler.z = -angle
            apply_obj(o)
            o.data.materials.append(m_asphalt)
            objs.append(o)

            for rs in [-1, 1]:
                bpy.ops.mesh.primitive_cube_add(size=2)
                o = bpy.context.active_object
                o.scale = (sl/2, 0.06, max(sh, 0.05))
                wp = rp + fwd * rs * (RAMP_W/2 + 0.1)
                wp.z = sch
                o.location = wp; o.rotation_euler.z = -angle
                apply_obj(o)
                o.data.materials.append(m_tile)
                objs.append(o)

        end_pos = p + right * side * (OW/2 + RAMP_LEN)
        end_pos.z = 0.15
        objs.append(cube(end_pos, (0.3, RAMP_W/2, 0.15), m_tile))

        for rs in [-1, 1]:
            for si in range(segs):
                t = (si + 0.5) / segs
                pp = p + right * side * (OW/2 + t * RAMP_LEN) + fwd * rs * (RAMP_W/2 + 0.05)
                pp.z = OH * t / 2 + 0.25
                objs.append(cube(pp, (0.04, 0.04, 0.35), m_wood))

    # Decorative elements
    for side in [-1, 1]:
        lantern_pos = p + right * side * (OW/2 + RAMP_LEN + 1.5)
        lantern_pos.z = 0
        objs.extend(make_lantern(lantern_pos))

        for s in [-1, 1]:
            sakura_pos = lantern_pos + fwd * s * 2.5
            sakura_pos.z = 0
            objs.extend(make_sakura(sakura_pos, random.uniform(0.8, 1.2)))

        for offset in [(2.0, 1.5), (-1.5, -2.0)]:
            sakura_pos = p + right * side * (OW/2 + RAMP_LEN + 3.0 + offset[0]) + fwd * offset[1]
            sakura_pos.z = 0
            objs.extend(make_sakura(sakura_pos, random.uniform(0.6, 1.1)))

    return objs


# ============================================================
# JAPANESE SCENERY PLACEMENT
# ============================================================
def place_scenery(pts):
    objs = []
    # Sakura trees
    for side in [-1, 1]:
        for _ in range(35):
            i = random.randint(5, len(pts)-6)
            p = pts[i]
            if abs(p.z) > 0.5: continue
            _, right, _ = get_road_frame(pts, i)
            d = ROAD_WIDTH/2 + 2 + random.uniform(3, TERRAIN_WIDTH - 8)
            pos = p + right * side * d; pos.z = 0
            objs.extend(make_sakura(pos, random.uniform(0.6, 1.3)))

    # Japanese buildings
    sp = len(pts) // 14
    for side in [-1, 1]:
        for bi in range(14):
            i = bi * sp + random.randint(0, max(1, sp//2))
            if i >= len(pts): continue
            p = pts[i]
            if abs(p.z) > 0.5: continue
            _, right, _ = get_road_frame(pts, i)
            d = ROAD_WIDTH/2 + 2 + random.uniform(10, 22); pos = p + right * side * d; pos.z = 0
            w = random.uniform(4, 8); dp = random.uniform(4, 8); h = random.uniform(4, 15)
            objs.extend(make_jp_building(pos, w, dp, h))
            if random.random() > 0.5:
                objs.extend(make_neon_sign(pos + Vector((0, side*dp/2+side*0.3, h*0.7))))

    # Torii gates
    for idx in [20, 60, 100]:
        if idx >= len(pts): continue
        p = pts[idx]; _, right, _ = get_road_frame(pts, idx)
        if abs(p.z) > 0.5: continue
        pos = p + right * 1 * (ROAD_WIDTH/2 + 2 + 5); pos.z = 0
        objs.extend(make_torii(pos))

    # Lanterns along sidewalk
    step = max(1, len(pts) // 20)
    for i in range(0, len(pts), step):
        p = pts[i]; _, right, _ = get_road_frame(pts, i)
        if abs(p.z) > 0.5: continue
        for s in [-1, 1]:
            pos = p + right * s * (ROAD_WIDTH/2 + 1.5); pos.z = max(pos.z, 0)
            objs.extend(make_lantern(pos))

    # Vending machines
    for _ in range(8):
        i = random.randint(10, len(pts)-10); p = pts[i]
        if abs(p.z) > 0.5: continue
        _, right, _ = get_road_frame(pts, i); s = random.choice([-1, 1])
        pos = p + right * s * (ROAD_WIDTH/2 + 2 + 1); pos.z = 0
        objs.extend(make_vending(pos))

    # Bamboo fences
    for _ in range(6):
        i = random.randint(10, len(pts)-10); p = pts[i]
        if abs(p.z) > 0.5: continue
        _, right, _ = get_road_frame(pts, i); s = random.choice([-1, 1])
        pos = p + right * s * (ROAD_WIDTH/2 + 2 + 8); pos.z = 0
        objs.extend(make_bamboo_fence(pos, random.uniform(3, 6)))

    return objs


# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 50)
    print("Generating Japanese Racing Environment with Textures...")
    print("=" * 50)
    _mat_cache.clear()
    random.seed(SEED)
    clear_scene()

    # Apply artist profile settings from BlenderMCP panel
    cfg = apply_profile_config()
    print(f"  Export Format: {cfg['export_format']}")
    print(f"  Naming Prefix: {cfg['naming_prefix']}")

    pts = get_road_points(120)

    print("[1/12] Road..."); create_road_mesh(pts)
    print("[2/12] Markings..."); create_curved_markings(pts, LANE_COUNT)
    print("[3/12] Sidewalks...")
    for s in [-1, 1]: create_sidewalk_side(pts, s)
    print("[4/12] Road curbs..."); create_road_curbs(pts)
    print("[5/12] Ground plane..."); create_ground_plane()
    print("[6/12] Terrain...")
    for s in [-1, 1]: create_terrain_side(pts, s)
    print("[7/12] Bridge..."); make_bridge_supports(pts)
    print("[8/12] Overpass..."); create_overpass(pts)
    print("[9/12] Scenery..."); place_scenery(pts)
    print("[10/12] Traffic props..."); place_traffic_props(pts)
    print("[11/12] Joining...")
    result = join_all("JapanRacing_SingleMesh")
    if result:
        v = len(result.data.vertices); f = len(result.data.polygons)
        m = len(result.data.materials)
        print(f"Verts: {v} | Faces: {f} | Mats: {m}")
    print("[12/12] Scene setup...")
    setup_scene(camera_loc=(35, -45, 20), sun_color=(1.0, 0.92, 0.85), use_profile=True)
    print("DONE! Export: File > Export > FBX/glTF")


if __name__ == "__main__":
    main()
