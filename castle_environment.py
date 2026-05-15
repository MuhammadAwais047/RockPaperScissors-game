"""
European Castle Environment - Medieval Fortress Generator
=========================================================
Run inside Blender Scripting tab.
Imports shared functionality from base_environment.py.

Features:
- Square castle with crenellated walls and round corner towers
- Central keep with pitched roof and tower
- Gatehouse with portcullis and drawbridge
- Cobblestone courtyard
- Medieval village houses outside the walls
- Castle flags and banners
- Stone well, market stalls
- Surrounding forest
"""

import sys, os, bpy, math, random
from mathutils import Vector

# Determine directory containing this script
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

# ============================================================
# CASTLE CONFIGURATION
# ============================================================
CASTLE_SIZE = 30          # Half-width of castle wall square
WALL_HEIGHT = 8           # Main wall height
WALL_THICKNESS = 1.2      # Wall thickness
TOWER_RADIUS = 2.5        # Corner tower radius
TOWER_HEIGHT = 14         # Corner tower height
KEEP_WIDTH = 10           # Keep half-width
KEEP_DEPTH = 8            # Keep half-depth
KEEP_HEIGHT = 10          # Keep height
BATTLEMENT_COUNT = 36     # Number of crenellations per wall side
MOAT_WIDTH = 4            # Moat half-width
VILLAGE_HOUSE_COUNT = 8   # Number of village houses
TREE_COUNT = 30           # Number of surrounding trees
SEED = 42
random.seed(SEED)

# ============================================================
# CASTLE-SPECIFIC MATERIALS
# ============================================================

def make_castle_stone():
    """Rough gray castle stone with mortar lines."""
    m = bpy.data.materials.new("Castle_Stone"); m.use_nodes = True
    nt = m.node_tree; nodes = nt.nodes; links = nt.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs['Roughness'].default_value = 0.92
    tc = nodes.new('ShaderNodeTexCoord'); tc.location = (-800, 0)
    n = nodes.new('ShaderNodeTexNoise'); n.location = (-600, 100)
    n.inputs['Scale'].default_value = 3.5; n.inputs['Detail'].default_value = 8
    n2 = nodes.new('ShaderNodeTexNoise'); n2.location = (-600, -100)
    n2.inputs['Scale'].default_value = 20; n2.inputs['Detail'].default_value = 3
    cr = nodes.new('ShaderNodeValToRGB'); cr.location = (-400, 0)
    cr.color_ramp.elements[0].color = (0.35, 0.33, 0.3, 1)
    cr.color_ramp.elements[1].color = (0.45, 0.42, 0.38, 1)
    mx = nodes.new('ShaderNodeMixRGB'); mx.location = (-200, 0)
    mx.inputs['Fac'].default_value = 0.4
    mx.inputs['Color1'].default_value = (0.38, 0.36, 0.32, 1)
    links.new(tc.outputs['Object'], n.inputs['Vector'])
    links.new(n.outputs['Fac'], cr.inputs['Fac'])
    links.new(cr.outputs['Color'], mx.inputs['Color1'])
    links.new(n2.outputs['Fac'], mx.inputs['Fac'])
    links.new(mx.outputs['Color'], bsdf.inputs['Base Color'])
    bp = nodes.new('ShaderNodeBump'); bp.location = (-200, -250)
    bp.inputs['Strength'].default_value = 0.6
    links.new(n.outputs['Fac'], bp.inputs['Height'])
    links.new(bp.outputs['Normal'], bsdf.inputs['Normal'])
    # Add mortar line effect via brick texture
    brick = nodes.new('ShaderNodeTexBrick'); brick.location = (-600, -300)
    brick.inputs['Scale'].default_value = 4
    brick.inputs['Mortar'].default_value = (0.25, 0.23, 0.2, 1)
    brick.inputs['Mortar Size'].default_value = 0.025
    links.new(tc.outputs['Object'], brick.inputs['Vector'])
    mx2 = nodes.new('ShaderNodeMixRGB'); mx2.location = (0, -200)
    mx2.inputs['Fac'].default_value = 0.15
    links.new(brick.outputs['Color'], mx2.inputs['Color2'])
    links.new(mx.outputs['Color'], mx2.inputs['Color1'])
    links.new(mx2.outputs['Color'], bsdf.inputs['Base Color'])
    return m

mat_castle_stone = make_castle_stone

def make_roof_tile():
    """Red/brown clay roof tile texture."""
    m = bpy.data.materials.new("Roof_Tile"); m.use_nodes = True
    nt = m.node_tree; nodes = nt.nodes; links = nt.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs['Roughness'].default_value = 0.85
    tc = nodes.new('ShaderNodeTexCoord'); tc.location = (-700, 0)
    n = nodes.new('ShaderNodeTexNoise'); n.location = (-500, 0)
    n.inputs['Scale'].default_value = 15; n.inputs['Detail'].default_value = 6
    n2 = nodes.new('ShaderNodeTexNoise'); n2.location = (-500, -200)
    n2.inputs['Scale'].default_value = 6; n2.inputs['Detail'].default_value = 4
    cr = nodes.new('ShaderNodeValToRGB'); cr.location = (-300, 0)
    cr.color_ramp.elements[0].color = (0.5, 0.18, 0.08, 1)
    cr.color_ramp.elements[1].color = (0.65, 0.25, 0.1, 1)
    links.new(tc.outputs['Object'], n.inputs['Vector'])
    links.new(n.outputs['Fac'], cr.inputs['Fac'])
    links.new(cr.outputs['Color'], bsdf.inputs['Base Color'])
    bp = nodes.new('ShaderNodeBump'); bp.location = (-100, -200)
    bp.inputs['Strength'].default_value = 0.3
    links.new(n2.outputs['Fac'], bp.inputs['Height'])
    links.new(bp.outputs['Normal'], bsdf.inputs['Normal'])
    return m

mat_roof_tile = make_roof_tile

def make_cobblestone():
    """Cobblestone courtyard texture."""
    m = bpy.data.materials.new("Cobblestone"); m.use_nodes = True
    nt = m.node_tree; nodes = nt.nodes; links = nt.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs['Roughness'].default_value = 0.95
    tc = nodes.new('ShaderNodeTexCoord'); tc.location = (-800, 0)
    n = nodes.new('ShaderNodeTexNoise'); n.location = (-600, 0)
    n.inputs['Scale'].default_value = 15; n.inputs['Detail'].default_value = 7
    v = nodes.new('ShaderNodeTexVoronoi'); v.location = (-600, -200)
    v.inputs['Scale'].default_value = 8
    cr = nodes.new('ShaderNodeValToRGB'); cr.location = (-400, 0)
    cr.color_ramp.elements[0].color = (0.3, 0.28, 0.25, 1)
    cr.color_ramp.elements[1].color = (0.5, 0.47, 0.42, 1)
    mx = nodes.new('ShaderNodeMixRGB'); mx.location = (-200, 0)
    mx.inputs['Fac'].default_value = 0.5
    links.new(tc.outputs['Object'], n.inputs['Vector'])
    links.new(tc.outputs['Object'], v.inputs['Vector'])
    links.new(n.outputs['Fac'], cr.inputs['Fac'])
    links.new(cr.outputs['Color'], mx.inputs['Color1'])
    mx.inputs['Color2'].default_value = (0.4, 0.37, 0.33, 1)
    links.new(v.outputs['Distance'], mx.inputs['Fac'])
    links.new(mx.outputs['Color'], bsdf.inputs['Base Color'])
    bp = nodes.new('ShaderNodeBump'); bp.location = (-200, -300)
    bp.inputs['Strength'].default_value = 0.2
    links.new(n.outputs['Fac'], bp.inputs['Height'])
    links.new(bp.outputs['Normal'], bsdf.inputs['Normal'])
    return m

mat_cobblestone = make_cobblestone

def make_dark_wood():
    """Dark aged wood for doors, beams, drawbridge."""
    m = bpy.data.materials.new("Dark_Wood"); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs['Roughness'].default_value = 0.95
    add_noise_texture(nt, bsdf, (0.2, 0.12, 0.06, 1), scale=6, detail=8, mix_fac=0.4)
    return m

mat_dark_wood = make_dark_wood

def make_banner_red():
    """Red banner with gold trim."""
    return mat("Banner_Red", (0.75, 0.08, 0.05, 1), rough=0.6)

def make_banner_blue():
    """Blue banner with gold trim."""
    return mat("Banner_Blue", (0.1, 0.3, 0.6, 1), rough=0.6)

def make_banner_gold():
    """Gold trim/embroidery."""
    return mat("Banner_Gold", (0.85, 0.65, 0.1, 1), rough=0.4, metal=0.6)

def make_iron():
    """Dark iron for portcullis, hinges."""
    return mat("Castle_Iron", (0.12, 0.12, 0.14, 1), rough=0.5, metal=0.9)

def make_plaster():
    """White/yellow plaster for village houses."""
    m = bpy.data.materials.new("Plaster"); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs['Roughness'].default_value = 0.95
    add_noise_texture(nt, bsdf, (0.85, 0.78, 0.65, 1), scale=8, detail=4, mix_fac=0.2)
    return m

mat_plaster = make_plaster

def make_thatched_roof():
    """Straw/thatched roof for village houses."""
    m = bpy.data.materials.new("Thatch"); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs['Roughness'].default_value = 1.0
    add_noise_texture(nt, bsdf, (0.5, 0.4, 0.2, 1), scale=3, detail=10, mix_fac=0.5)
    return m

mat_thatch = make_thatched_roof

# Material caches for this module
_mat_cache = {}

def get_castle_mat(key, creator):
    if key not in _mat_cache:
        _mat_cache[key] = creator()
    return _mat_cache[key]

# ============================================================
# CASTLE ELEMENT GENERATORS
# ============================================================

def make_battlement(pos, width, height):
    """Create a single crenellation (battlement tooth).
    
    Args:
        pos: Vector - center base position
        width: float - half-width of the merlon
        height: float - height of the merlon
    Returns:
        list of objects
    """
    m_stone = get_castle_mat('stone', make_castle_stone)
    objs = []
    # Merlon (raised block)
    objs.append(cube(pos + Vector((0, 0, height/2)), (width, WALL_THICKNESS/2, height/2), m_stone))
    return objs


def create_wall_section(start_pos, end_pos, height, inner_offset=0):
    """Create a wall section with battlements between two points.
    
    Args:
        start_pos: Vector - start of wall
        end_pos: Vector - end of wall
        height: float - wall height
        inner_offset: float - offset toward interior for double wall
    Returns:
        list of objects
    """
    objs = []
    m_stone = get_castle_mat('stone', make_castle_stone)
    
    mid = (start_pos + end_pos) / 2
    diff = end_pos - start_pos
    length = diff.length
    if length < 0.1:
        return objs
    
    direction = diff.normalized()
    angle = math.atan2(direction.x, direction.y)
    
    # Wall body
    bpy.ops.mesh.primitive_cube_add(size=2)
    wall = bpy.context.active_object
    wall.scale = (length/2, WALL_THICKNESS/2, height/2)
    wall.location = mid
    wall.rotation_euler.z = -angle
    apply_obj(wall)
    wall.data.materials.append(m_stone)
    objs.append(wall)
    
    # Battlements (crenellations)
    num_merlons = max(2, int(length / 1.5))
    for i in range(num_merlons):
        t = (i + 0.5) / num_merlons
        bp = start_pos.lerp(end_pos, t)
        bp.z = height  # base of merlon is at wall top
        merlon_width = length / (num_merlons * 2.5)
        is_merlon = i % 2 == 0
        if is_merlon:
            objs.append(cube(bp + Vector((0, 0, 0.6)), (merlon_width*0.8, WALL_THICKNESS/2+0.05, 0.6), m_stone))
    
    return objs


def create_tower(pos, radius, height, num_sides=8, has_flag=True):
    """Create a round castle tower with conical roof and optional flag.
    
    Args:
        pos: Vector - center base position
        radius: float - tower radius
        height: float - tower wall height
        num_sides: int - cylinder sides (8=good balance)
        has_flag: bool - add flag on top
    Returns:
        list of objects
    """
    objs = []
    m_stone = get_castle_mat('stone', make_castle_stone)
    m_roof = get_castle_mat('roof', make_roof_tile)
    
    # Tower body (cylindrical)
    objs.append(cyl(pos + Vector((0, 0, height/2)), radius, height, num_sides, m_stone))
    
    # Stone base ring
    objs.append(cyl(pos + Vector((0, 0, 0.15)), radius + 0.2, 0.3, num_sides, m_stone))
    
    # Conical roof
    roof_base = pos.z + height
    objs.append(cone(pos + Vector((0, 0, roof_base + 1.5)), radius * 0.85, 3.0, num_sides, m_roof))
    
    # Roof finial (small ball on top)
    objs.append(cyl(pos + Vector((0, 0, roof_base + 3.3)), 0.08, 0.15, num_sides, m_roof))
    
    # Battlements at top of tower
    num_merlons = 8
    for i in range(num_merlons):
        ang = (i / num_merlons) * math.pi * 2
        bp = pos + Vector((math.cos(ang) * (radius + 0.1), math.sin(ang) * (radius + 0.1), height))
        objs.append(cube(bp + Vector((0, 0, 0.5)), (0.25, 0.15, 0.5), m_stone))
    
    # Window slits (arrow loops)
    for i in range(3):
        ang = (i / 3) * math.pi * 2 + 0.3
        w_x = math.cos(ang) * (radius + 0.02)
        w_y = math.sin(ang) * (radius + 0.02)
        w_h = random.uniform(0.8, 1.5)
        objs.append(cube(pos + Vector((w_x, w_y, height * 0.6)), (0.04, 0.04, w_h/2),
                         get_castle_mat('iron', make_iron)))
    
    # Flag on top
    if has_flag:
        flag_color = random.choice(['red', 'blue'])
        m_flag = get_castle_mat(f'banner_{flag_color}',
                                make_banner_red if flag_color == 'red' else make_banner_blue)
        m_pole = get_castle_mat('iron', make_iron)
        
        flagpole_top = roof_base + 3.5
        # Pole
        objs.append(cyl(pos + Vector((0, 0, flagpole_top + 0.5)), 0.03, 1.0, 4, m_pole))
        # Flag cloth
        bpy.ops.mesh.primitive_cube_add(size=2)
        flag = bpy.context.active_object
        flag.scale = (0.5, 0.02, 0.25)
        flag.location = pos + Vector((0.3, 0, flagpole_top + 0.6))
        apply_obj(flag)
        flag.data.materials.append(m_flag)
        objs.append(flag)
    
    return objs


def create_keep(center):
    """Create the central keep (main fortress building).
    
    Args:
        center: Vector - center position of the keep
    Returns:
        list of objects
    """
    objs = []
    m_stone = get_castle_mat('stone', make_castle_stone)
    m_roof = get_castle_mat('roof', make_roof_tile)
    m_wood = get_castle_mat('wood', make_dark_wood)
    
    kw = KEEP_WIDTH
    kd = KEEP_DEPTH
    kh = KEEP_HEIGHT
    
    # Main keep body
    objs.append(cube(center + Vector((0, 0, kh/2)), (kw, kd, kh/2), m_stone))
    
    # Stone base trim
    objs.append(cube(center + Vector((0, 0, 0.2)), (kw+0.2, kd+0.2, 0.2), m_stone))
    
    # Central tower rising from keep (taller keep tower)
    tower_h = kh * 0.6
    objs.append(cyl(center + Vector((0, 0, kh + tower_h/2)), kw*0.25, tower_h, 8, m_stone))
    
    # Small roof on keep tower
    objs.append(cone(center + Vector((0, 0, kh + tower_h + 0.5)), kw*0.25*0.85, 1.5, 8, m_roof))
    
    # Keep roof (pitched)
    # Two roof halves
    for side in [-1, 1]:
        bpy.ops.mesh.primitive_cube_add(size=2)
        roof = bpy.context.active_object
        roof.scale = (kw * 0.55, kd/2, 0.5)
        roof.location = center + Vector((side * kw * 0.4, 0, kh))
        roof.rotation_euler.x = math.radians(side * 35)
        apply_obj(roof)
        roof.data.materials.append(m_roof)
        objs.append(roof)
    
    # Roof ridge beam
    objs.append(cube(center + Vector((0, 0, kh + 0.6)), (0.2, kd/2, 0.1), m_wood))
    
    # Windows on keep
    for side in [-1, 1]:
        for wi in range(3):
            w_x = (wi - 1) * kw * 0.4
            objs.append(cube(center + Vector((w_x, side * kd * 0.85, kh * 0.5)),
                             (0.4, 0.04, 0.6), get_castle_mat('iron', make_iron)))
    
    # Main door (arched)
    door_pos = center + Vector((0, -kd, 0))
    objs.append(cube(door_pos + Vector((0, 0.02, 1.2)), (0.6, 0.02, 1.2), m_wood))
    # Door arch
    objs.append(cube(door_pos + Vector((0, 0.02, 2.5)), (0.8, 0.03, 0.15), m_stone))
    # Door iron hinge details
    for hi in [-0.4, 0.4]:
        objs.append(cube(door_pos + Vector((hi*0.8, 0.04, 1.0)), (0.02, 0.01, 0.06), get_castle_mat('iron', make_iron)))
    
    # Banner on keep tower
    m_banner = get_castle_mat('banner_gold', make_banner_gold)
    objs.append(cyl(center + Vector((0, 0, kh + tower_h + 2)), 0.02, 2, 4, get_castle_mat('iron', make_iron)))
    bpy.ops.mesh.primitive_cube_add(size=2)
    flag = bpy.context.active_object
    flag.scale = (0.6, 0.02, 0.3)
    flag.location = center + Vector((0.4, 0, kh + tower_h + 2.5))
    apply_obj(flag)
    flag.data.materials.append(m_banner)
    objs.append(flag)
    
    return objs


def create_gatehouse(pos, facing_dir):
    """Create a gatehouse with portcullis and drawbridge.
    
    Args:
        pos: Vector - center position of gatehouse
        facing_dir: Vector - direction gate faces (outward)
    Returns:
        list of objects
    """
    objs = []
    m_stone = get_castle_mat('stone', make_castle_stone)
    m_wood = get_castle_mat('wood', make_dark_wood)
    m_iron = get_castle_mat('iron', make_iron)
    m_roof = get_castle_mat('roof', make_roof_tile)
    
    # Angle from facing direction
    angle = math.atan2(facing_dir.x, facing_dir.y)
    
    # Gatehouse walls (two flanking towers)
    tower_spacing = 2.5
    for side in [-1, 1]:
        t_pos = pos + Vector((side * tower_spacing, 0, 0))
        # Flanking tower
        objs.append(cyl(t_pos + Vector((0, 0, 4)), 1.0, 8, 8, m_stone))
        objs.append(cone(t_pos + Vector((0, 0, 8.5)), 0.8, 1.5, 8, m_roof))
    
    # Arch over gateway
    arch_pos = pos + Vector((0, 0, 4))
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=1.5, depth=1.5)
    o = bpy.context.active_object
    o.scale = (1.0, 1.0, 0.05)
    o.location = arch_pos
    o.rotation_euler.x = math.radians(90)
    apply_obj(o)
    o.data.materials.append(m_stone)
    objs.append(o)
    
    # Gateway walls (above arch)
    objs.append(cube(pos + Vector((0, 0, 5.5)), (1.5, 0.4, 1.5), m_stone))
    
    # Portcullis (iron bars)
    for bi in range(5):
        bx = (bi - 2) * 0.25
        objs.append(cyl(pos + Vector((bx, 0.02, 2)), 0.02, 4, 6, m_iron))
    # Horizontal bars
    for hh in [0.5, 1.5, 2.5]:
        objs.append(cube(pos + Vector((0, 0.02, hh)), (0.6, 0.02, 0.03), m_iron))
    # Portcullis frame
    objs.append(cube(pos + Vector((0, 0.03, 2.5)), (0.75, 0.02, 0.06), m_iron))
    objs.append(cube(pos + Vector((0, 0.03, 0.5)), (0.75, 0.02, 0.06), m_iron))
    
    # Drawbridge (angled plank)
    bpy.ops.mesh.primitive_cube_add(size=2)
    bridge = bpy.context.active_object
    bridge.scale = (0.8, 0.5, 0.04)
    bridge.location = pos + Vector((0, -1, -0.5))
    bridge.rotation_euler.x = math.radians(-25)
    apply_obj(bridge)
    bridge.data.materials.append(m_wood)
    objs.append(bridge)
    
    # Drawbridge chains (two thin cylinders angled down)
    for side in [-1, 1]:
        bpy.ops.mesh.primitive_cylinder_add(vertices=3, radius=0.01, depth=1.5)
        chain = bpy.context.active_object
        chain.location = pos + Vector((side * 0.4, 0, 3))
        chain.rotation_euler.x = math.radians(45 * side)
        apply_obj(chain)
        chain.data.materials.append(m_iron)
        objs.append(chain)
    
    return objs


def create_courtyard(center, size):
    """Create a cobblestone courtyard floor.
    
    Args:
        center: Vector - center of courtyard
        size: float - half-size of courtyard square
    Returns:
        list of objects
    """
    m_cobble = get_castle_mat('cobblestone', make_cobblestone)
    return [cube(center + Vector((0, 0, -0.02)), (size, size, 0.02), m_cobble)]


def create_well(pos):
    """Create a medieval stone well.
    
    Args:
        pos: Vector - center position
    Returns:
        list of objects
    """
    objs = []
    m_stone = get_castle_mat('stone', make_castle_stone)
    m_wood = get_castle_mat('wood', make_dark_wood)
    m_iron = get_castle_mat('iron', make_iron)
    
    # Well ring (stone circle)
    objs.append(cyl(pos + Vector((0, 0, 0.3)), 0.5, 0.6, 8, m_stone))
    objs.append(cyl(pos + Vector((0, 0, 0.25)), 0.35, 0.5, 8, get_castle_mat('roof', make_roof_tile)))
    
    # Support posts
    for ang in [0, math.pi/2]:
        px = pos.x + math.cos(ang) * 0.3
        py = pos.y + math.sin(ang) * 0.3
        objs.append(cyl(Vector((px, py, 0.8)), 0.03, 1.6, 4, m_wood))
    
    # Cross beam
    objs.append(cube(pos + Vector((0, 0, 1.55)), (0.35, 0.03, 0.03), m_wood))
    
    # Rope (thin cylinder)
    objs.append(cyl(pos + Vector((0, 0, 0.8)), 0.005, 0.8, 3, m_iron))
    
    # Bucket (small cylinder)
    objs.append(cyl(pos + Vector((0, 0, 0.2)), 0.08, 0.2, 5, m_wood))
    objs.append(cyl(pos + Vector((0, 0, 0.2)), 0.1, 0.02, 5, get_castle_mat('iron', make_iron)))
    
    return objs


def create_market_stall(pos, rot=0):
    """Create a medieval market stall with canopy.
    
    Args:
        pos: Vector - center position
        rot: float - Z rotation
    Returns:
        list of objects
    """
    objs = []
    m_wood = get_castle_mat('wood', make_dark_wood)
    m_roof = get_castle_mat('roof', make_roof_tile)
    
    # Table
    bpy.ops.mesh.primitive_cube_add(size=2)
    table = bpy.context.active_object
    table.scale = (0.5, 0.3, 0.4)
    table.location = pos + Vector((0, 0, 0.4))
    table.rotation_euler.z = rot
    apply_obj(table)
    table.data.materials.append(m_wood)
    objs.append(table)
    
    # Canopy posts
    for x in [-0.4, 0.4]:
        for y in [-0.25, 0.25]:
            pp = pos + Vector((x, y, 0))
            objs.append(cyl(pp + Vector((0, 0, 0.85)), 0.02, 0.85, 4, m_wood))
    
    # Canopy roof
    bpy.ops.mesh.primitive_cube_add(size=2)
    canopy = bpy.context.active_object
    canopy.scale = (0.55, 0.35, 0.03)
    canopy.location = pos + Vector((0, 0, 1.3))
    canopy.rotation_euler.z = rot
    apply_obj(canopy)
    canopy.data.materials.append(m_roof)
    objs.append(canopy)
    
    # Small items on table (colored cubes as goods)
    for gi in range(3):
        gx = (gi - 1) * 0.15
        goods_color = random.choice([(0.8, 0.6, 0.1, 1), (0.6, 0.1, 0.1, 1), (0.1, 0.5, 0.1, 1)])
        mg = mat(f"Goods_{gi}", goods_color, rough=0.8)
        objs.append(cube(pos + Vector((gx, 0, 0.65)), (0.06, 0.06, 0.04), mg))
    
    return objs


def create_village_house(pos, scale=1.0, rot=0):
    """Create a medieval village house with thatched roof.
    
    Args:
        pos: Vector - center position
        scale: float - size multiplier
        rot: float - Z rotation
    Returns:
        list of objects
    """
    objs = []
    m_plaster = get_castle_mat('plaster', make_plaster)
    m_wood = get_castle_mat('wood', make_dark_wood)
    m_thatch = get_castle_mat('thatch', make_thatched_roof)
    
    hw = 1.5 * scale  # half-width
    hd = 1.2 * scale  # half-depth
    hh = 1.2 * scale  # half-height
    
    # House body
    bpy.ops.mesh.primitive_cube_add(size=2)
    body = bpy.context.active_object
    body.scale = (hw, hd, hh)
    body.location = pos + Vector((0, 0, hh))
    body.rotation_euler.z = rot
    apply_obj(body)
    body.data.materials.append(m_plaster)
    objs.append(body)
    
    # Timber frame beams (dark wood criss-cross)
    for bx in [-1, 1]:
        objs.append(cube(pos + Vector((bx * hw * 0.85, 0, hh)), (0.04, hd*0.8, hh/2), m_wood))
    for by in [-1, 1]:
        objs.append(cube(pos + Vector((0, by * hd * 0.85, hh)), (hw*0.8, 0.04, hh/2), m_wood))
    
    # Cross beams (diagonal)
    objs.append(cube(pos + Vector((0.3*scale, 0, hh*0.5)), (0.04, hd*0.8, 0.04), m_wood))
    objs.append(cube(pos + Vector((-0.3*scale, 0, hh*1.5)), (0.04, hd*0.8, 0.04), m_wood))
    
    # Thatched roof (A-frame)
    for side in [-1, 1]:
        bpy.ops.mesh.primitive_cube_add(size=2)
        roof = bpy.context.active_object
        roof.scale = (hw * 1.1, hd/2, 0.5 * scale)
        roof.location = pos + Vector((side * hw * 0.3, 0, hh * 1.6))
        roof.rotation_euler.x = math.radians(side * 40)
        apply_obj(roof)
        roof.data.materials.append(m_thatch)
        objs.append(roof)
    
    # Ridge pole
    objs.append(cube(pos + Vector((0, 0, hh * 1.8)), (0.04, hd/2, 0.04), m_wood))
    
    # Door
    objs.append(cube(pos + Vector((0, hd * 0.85, hh * 0.4)), (0.2, 0.02, hh * 0.6), m_wood))
    
    # Window
    objs.append(cube(pos + Vector((hw * 0.35, hd * 0.85, hh * 0.7)), (0.15, 0.02, 0.15), get_castle_mat('iron', make_iron)))
    objs.append(cube(pos + Vector((hw * 0.35, hd * 0.87, hh * 0.7)), (0.1, 0.01, 0.1),
                     mat("Window_Glow", (0.8, 0.7, 0.4, 1), emit=2.0)))
    
    # Chimney (small stack)
    objs.append(cube(pos + Vector((0.8*scale, 0, hh*2.2*scale)), (0.1, 0.1, 0.6*scale), m_plaster))
    objs.append(cube(pos + Vector((0.8*scale, 0, hh*2.5*scale)), (0.12, 0.12, 0.04), m_wood))
    
    # Stone foundation
    objs.append(cube(pos + Vector((0, 0, 0.08)), (hw*1.1, hd*1.1, 0.08), get_castle_mat('stone', make_castle_stone)))
    
    return objs


def create_berry_bush(pos, scale=1.0):
    """Create a small green bush for courtyard."""
    mb = mat("Bush", (0.08, 0.3, 0.06, 1), rough=1.0)
    objs = []
    r = 0.2 * scale
    bpy.ops.mesh.primitive_uv_sphere_add(segments=6, ring_count=4)
    o = bpy.context.active_object
    o.scale = (r, r, r * 0.7)
    o.location = pos + Vector((0, 0, r * 0.5))
    apply_obj(o)
    o.data.materials.append(mb)
    objs.append(o)
    return objs


def create_tree_at(pos, scale=1.0):
    """Create a low-poly tree at the given position."""
    objs = []
    m_bark = get_mat('bark', make_bark_tex)
    m_leaf1 = get_mat('leaf0', lambda: make_leaf_tex(0))
    m_leaf2 = get_mat('leaf1', lambda: make_leaf_tex(1))
    objs.append(cyl(pos + Vector((0, 0, 1 * scale)), 0.2 * scale, 2 * scale, 6, m_bark))
    objs.append(cone(pos + Vector((0, 0, 2.5 * scale)), 1.8 * scale, 2 * scale, 6, m_leaf1))
    objs.append(cone(pos + Vector((0, 0, 3.8 * scale)), 1.3 * scale, 1.8 * scale, 6, m_leaf2))
    return objs


# ============================================================
# MAIN CASTLE GENERATION
# ============================================================

def main():
    print("=" * 50)
    print("  Generating European Castle Environment...")
    print("=" * 50)
    
    _mat_cache.clear()
    clear_scene()
    
    # Apply artist profile settings from BlenderMCP panel
    cfg = apply_profile_config()
    print(f"  Export Format: {cfg['export_format']}")
    print(f"  Naming Prefix: {cfg['naming_prefix']}")
    
    # Castle center
    cc = Vector((0, 0, 0))
    cs = CASTLE_SIZE
    wh = WALL_HEIGHT
    tr = TOWER_RADIUS
    
    print("[1/12] Courtyard...")
    create_courtyard(cc, cs + 1)
    
    print("[2/12] Corner towers...")
    # Four corner towers
    corners = [
        Vector((-cs + tr, -cs + tr, 0)),
        Vector(( cs - tr, -cs + tr, 0)),
        Vector(( cs - tr,  cs - tr, 0)),
        Vector((-cs + tr,  cs - tr, 0)),
    ]
    for ci, c in enumerate(corners):
        create_tower(c, tr, TOWER_HEIGHT, has_flag=True)
    
    print("[3/12] Curtain walls...")
    # Four wall sections connecting towers
    wall_pairs = [
        (Vector((-cs, -cs, 0)), Vector(( cs, -cs, 0))),  # South
        (Vector(( cs, -cs, 0)), Vector(( cs,  cs, 0))),  # East
        (Vector(( cs,  cs, 0)), Vector((-cs,  cs, 0))),  # North
        (Vector((-cs,  cs, 0)), Vector((-cs, -cs, 0))),  # West
    ]
    for i, (start, end) in enumerate(wall_pairs):
        # Leave gap on south wall for gatehouse
        if i == 0:  # South wall - split into two sections around gate
            gap_half = 3.0
            create_wall_section(start, Vector((-gap_half, -cs, 0)), wh)
            create_wall_section(Vector((gap_half, -cs, 0)), end, wh)
        else:
            create_wall_section(start, end, wh)
    
    print("[4/12] Gatehouse...")
    create_gatehouse(Vector((0, -cs, 0)), Vector((0, -1, 0)))
    
    print("[5/12] Central keep...")
    create_keep(Vector((0, 0, 0)))
    
    print("[6/12] Stone well...")
    create_well(Vector((cs * 0.3, cs * 0.35, 0)))
    
    print("[7/12] Market stalls...")
    # Stalls along the inner walls
    for si in range(4):
        stall_pos = Vector((random.uniform(-cs*0.4, cs*0.4), random.uniform(-cs*0.4, cs*0.4), 0))
        create_market_stall(stall_pos, random.uniform(0, math.pi*2))
    
    print("[8/12] Courtyard bushes...")
    # Small bushes
    for _ in range(6):
        bx = random.uniform(-cs*0.6, cs*0.6)
        by = random.uniform(-cs*0.6, cs*0.6)
        # Don't place on top of keep or well
        if abs(bx) < 4 and abs(by) < 3:
            continue
        create_berry_bush(Vector((bx, by, 0)), random.uniform(0.8, 1.3))
    
    print("[9/12] Village houses...")
    # Houses outside the castle walls
    for hi in range(VILLAGE_HOUSE_COUNT):
        side = random.choice(['north', 'east', 'west'])
        if side == 'north':
            hx = random.uniform(-cs*2.5, cs*2.5)
            hy = cs + random.uniform(2.5, 6)
        elif side == 'east':
            hx = cs + random.uniform(2.5, 6)
            hy = random.uniform(-cs*1.5, cs*1.5)
        else:  # west
            hx = -cs - random.uniform(2.5, 6)
            hy = random.uniform(-cs*1.5, cs*1.5)
        
        # Don't place too close to gatehouse (south side)
        if side == 'south' or (abs(hx) < 5 and hy < -cs - 1):
            continue
        
        create_village_house(Vector((hx, hy, 0)), random.uniform(0.7, 1.2), random.uniform(-0.3, 0.3))
    
    print("[10/12] Moat (water)...")
    # Moat - a flat water plane outside walls (partially under ground plane)
    moat_outer = cs + 2 + MOAT_WIDTH * 2
    m_water = mat("Moat_Water", (0.1, 0.25, 0.3, 1), rough=0.1, metal=0.2)
    bpy.ops.mesh.primitive_cube_add(size=2)
    moat = bpy.context.active_object
    moat.scale = (moat_outer, moat_outer, 0.005)
    moat.location = Vector((0, 0, -0.05))
    apply_obj(moat)
    moat.data.materials.append(m_water)
    
    print("[11/12] Surrounding forest...")
    # Trees placed around the outside
    for _ in range(TREE_COUNT):
        angle = random.uniform(0, math.pi * 2)
        dist = cs + MOAT_WIDTH * 2 + random.uniform(4, 20)
        tx = math.cos(angle) * dist
        ty = math.sin(angle) * dist
        
        # Skip if too close to village houses
        if any(abs(tx - hx) < 2 and abs(ty - hy) < 2 
               for hx, hy in []):  # no easy access to house positions
            continue
        
        tree_scale = random.uniform(0.5, 1.2)
        create_tree_at(Vector((tx, ty, 0)), tree_scale)
    
    print("[12/12] Joining & scene setup...")
    
    # Place ground plane
    create_ground_plane(size=500)
    
    # Join everything
    result = join_all("EuropeanCastle_SingleMesh")
    
    if result:
        v = len(result.data.vertices)
        f = len(result.data.polygons)
        m = len(result.data.materials)
        print(f"  Verts: {v:,} | Faces: {f:,} | Mats: {m}")
    
    # Scene setup with warm golden hour lighting for castle
    setup_scene(camera_loc=(55, -65, 30), sun_color=(1.0, 0.88, 0.7), use_profile=True)
    print("  DONE! Export: File > Export > FBX/glTF")
    print("=" * 50)


if __name__ == "__main__":
    main()
