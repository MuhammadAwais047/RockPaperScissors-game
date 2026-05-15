# Traffic Racing Game - Project Context

## Overview
Building a traffic racing game with optimized 3D environments generated via Blender Python scripts.
All environments output a **single joined mesh** for game engine performance.

## Files

### Shared Module
- `base_environment.py` — Shared base module for all environment generators
  - Scene management (`clear_scene`, `setup_scene`)
  - Material helpers (`mat`, `add_noise_texture`, `get_mat`/`gm`)
  - Procedural material creators (`make_asphalt`, `make_grass`, `make_concrete`, `make_metal_tex`, `make_bark_tex`, `make_leaf_tex`, `make_brick`, `make_wood`, `make_tile`, `make_sand`, `make_red_rock`, `make_dirt`)
  - Primitive helpers (`cube`/`bx`, `cyl`/`cy`, `cone`/`cn`, `apply_obj`/`ap`)
  - Road path generation (`get_road_points`/`road_pts`, `get_road_frame`/`rd_frame`)
  - Road mesh (`create_road_mesh`/`make_road`)
  - Lane markings (`create_curved_markings`/`make_markings`)
  - Terrain (`create_terrain_side`/`make_terrain`)
  - **Sidewalks** (`create_sidewalk_side`) — raised concrete strips between road edge and terrain
  - **Road curbs** (`create_road_curbs`) — small raised curb edges (h=0.12) along both sides of the road
  - **Ground plane** (`create_ground_plane`) — large 500x500 quad at z=-0.05 as fallback
  - **Traffic props** (`place_traffic_props`) — places 5 prop types along roadsides:
    - `create_car()` — low-poly parked car (body, cabin, 4 wheels, headlights, taillights), random colors
    - `create_traffic_cone()` — orange cone with white reflective bands and square base
    - `create_water_barrier()` — orange/white barrier block with reflective stripes and fill hole
    - `create_bench()` — park bench (3 seat slats, backrest, metal legs)
    - `create_dumpster()` — green dumpster with lid and side ridges
  - Join & cleanup (`join_all`) — merge, remove doubles, UV smart project, decimate

### Theme Scripts
- `racing_environment.py` — Racing-themed environment (imports from `base_environment.py`)
  - Wider road (12m), 3 lanes, 300m length
  - S-curves with bridge bump + tunnel dip
  - Metal guardrail barriers, bridge supports, tunnel structure
  - Highway overpass with concrete pillars, Jersey barriers, approach ramps
  - Traffic signs, buildings, trees, street lights
  - Traffic props (cars, cones, benches, dumpsters, water barriers)
  - 15-step generation pipeline

- `japanese_environment.py` — Japanese-themed environment (imports from `base_environment.py`)
  - Standard road (10m), 250m length
  - S-curves with bridge bump
  - Japanese bridge with red rails
  - **Highway overpass** with torii-style red pillars, dark wood railings, tile barriers, stone lanterns, and sakura trees at ramp bases
  - **Sakura trees**, **torii gates**, **pagoda buildings**, **stone lanterns**, **vending machines**, **neon signs**, **bamboo fences**
  - Sidewalks, road curbs, ground plane included
  - Traffic props (cars, cones, benches, dumpsters, water barriers)
  - Warm sunset lighting
  - 12-step generation pipeline

- `desert_environment.py` — Desert-themed environment (imports from `base_environment.py`)
  - Standard road (10m), 2 lanes, 250m length — flat S-curves, no bridge/tunnel dip
  - **Sand terrain** using new `make_sand()` procedural texture (warm tan with wind-ripple noise)
  - **Adobe/mission bridge** with decorative arch details
  - **Desert overpass** with adobe pillars, red rock barriers, and wood railings
  - **Saguaro cacti** — tall branching trunks (0–3 arms) with green noise texture
  - **Prickly pear cacti** — clusters of oval pads
  - **Mesa rocks** — flat-topped rock formations with tapered bases (red rock texture)
  - **Dead trees** — twisted bare branch trees
  - **Tumbleweeds** — sparse dry brush balls
  - **Gas station** — adobe building with storefront window, canopy roof over 2 pumps, tall sign
  - **Desert road signs** — brown/green highway signs, diamond warning signs
  - **Props** — oil barrels, red/white road barriers
  - **Dirt paths** — 3 off-road dirt/gravel paths branching from the main road at ~15%, ~45%, ~75%:
    - Path 1 (right, ~15%) leads to a **campfire site** with stone ring, crossed logs, ember glow cones, scattered rocks
    - Path 2 (left, ~45%) leads to an **off-road driving course** with:
      - **Oval dirt track** (8×12m) — closed loop with packed dirt surface, bmesh face winding (CCW for upward normals)
      - **2 jump ramps** — dirt mounds on opposite sides of the oval, angled along track direction
      - **5-cone slalom** — orange cones with zigzag pattern along one arc
      - **8 edge barriers** — red marker blocks at 0.5× and 1.5× radial scale (inner/outer edges)
      - **Staging area** — dirt parking pad near the course entry
    - Path 3 (right, ~75%) ends at oil barrel cluster (2 barrels)
  - Warm orange sun lighting (1.0, 0.85, 0.65)
  - 13-step generation pipeline (no traffic props from base — uses desert-specific props instead)

### Known Issues / Fixes
- **`__file__` not defined in Blender Text Editor** — When running scripts from Blender's Scripting tab (Text Editor), the global `__file__` is not available, causing a `NameError`. Fixed with a fallback pattern:
  ```python
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
  ```
  - **Important:** Must check `if filepath:` before using it — `os.path.dirname(os.path.abspath(""))` returns the **parent** of CWD, not CWD itself, which causes `ModuleNotFoundError` for `base_environment`.
  - Applied to: `desert_environment.py`, `racing_environment.py`, `japanese_environment.py`
- **Blender Connector / uv installation** — The command `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"` installs `uv` (Astral's fast Python package manager), not Blender Connector directly. After `uv` is installed, use it to install the actual Blender Connector package.
  - Note: Terminal (WSL bash relay) had `/bin/bash` not found errors — couldn't execute from within Codebuff. Run manually in PowerShell as Administrator.
- **WSL Bash Environment Fixed** — Was broken with `execvpe(/bin/bash) failed: No such file or directory`. Root cause: only `docker-desktop` WSL distro was installed (no real Linux distro with `/bin/bash`). Fixed by:
  - Installing Ubuntu WSL distro: `wsl --install -d Ubuntu`
  - Setting it as default: `wsl --set-default Ubuntu`
  - Now all terminal commands work through the WSL relay again

## Architecture
- Road is generated from a spline path (`get_road_points()` / `road_pts()`)
- All objects placed relative to road center using `get_road_frame()` / `rd_frame()` for curved alignment
- Materials use Blender's Principled BSDF with procedural node textures (noise, voronoi, brick)
- Material caching via `_mat_cache` / `_mc` dict to avoid duplicates
- Theme scripts share ~60% code through the base module:
  - `from base_environment import *` imports shared helpers
  - Each theme overrides config constants as needed
  - Each theme defines its own scenery placement function(s)
  - Base handles: road, markings, terrain, sidewalks, curbs, ground plane, traffic props, join, decimate, scene setup
- Final step: join all objects → remove doubles → UV smart project → decimate modifier

## Key Design Decisions
- Primitives use low vertex counts (5-sided cylinders/cones)
- `DECIMATE_RATIO` controls final poly reduction (default 0.6 = 40% reduction)
- `cube()` uses `size=2` so scale values map directly to half-dimensions
- All scripts run in Blender's Scripting tab
- Overpass placed at ~22% along road (flat section before bridge bump) with approach ramps, guard railings, and side barriers
- Japanese overpass features torii-style red pillars, dark wood railings, tile barriers, stone lanterns, and sakura trees flanking ramp bases
- Desert overpass features adobe pillars, red rock barriers, and decorative arches
- `setup_scene()` accepts `sun_color` parameter — Japanese uses warm sunset (1.0, 0.92, 0.85), desert uses orange (1.0, 0.85, 0.65)
- Traffic props placed on flat sections only (skipping bridge/tunnel zones), with randomized positions/rotations for natural variation
- Desert theme uses its own `place_desert_props()` instead of base `place_traffic_props()` for thematic consistency
- Dirt paths use `create_dirt_path()` from base module to generate curved dirt strips branching perpendicular from the road edge with gentle S-curve meander
- `make_campfire()` creates a small destination feature (stone ring, crossed logs, ember glow cones) at the end of Path 1
- `make_off_road_course()` creates a full driving course (oval track, jumps, slalom, barriers, staging area) at the end of Path 2

## Game Engine Target
- Export as FBX (Unity/Unreal) or glTF (Godot/Web)
- Single mesh for draw call optimization
- Procedural textures need to be baked before export for game engines

## Environment Sizes & Optimization

### Measured Outputs

| Environment | Vertices | Faces | Physical Size (L×W) | Status |
|-------------|----------|-------|---------------------|--------|
| **Racing** | **7,831** | **9,692** | 300m × 40m | ✅ Generated at `DECIMATE_RATIO=0.6` |
| **Desert** | TBD | TBD | 250m × 40m | ⚠️ Blender crashed on join |
| **Japanese** | TBD | TBD | 250m × 40m | ❌ Not yet run |

### How to Reduce Scene Size

If the environment is too big (either polygon count or physical size), try:

| Tweak | Default → Reduced | Impact |
|-------|------------------|--------|
| `DECIMATE_RATIO` | 0.6 → 0.3–0.4 | Fewer polygons (racing: ~7.8K → ~4K) |
| `ROAD_LENGTH` | 250–300 → 150–200 | Shorter road, fewer objects placed |
| `TERRAIN_WIDTH` | 40 → 25 | Narrower terrain strips |
| Scenery counts | 40 cacti → 20 | Fewer decorative objects |
| Primitive verts | 5 → 3 | Lower-detail cylinders/cones |

### Optimization Settings
- `DECIMATE_RATIO = 0.6` — reduces poly count to 60% of original
- Primitives use low vertex counts (5-sided cylinders/cones)
- Final step: join all → remove doubles → UV smart project → decimate
- All materials are procedural: asphalt, grass, concrete, brick, metal, bark, leaf, sakura, wood, tile, sand, red_rock, adobe, cactus, dry_bush

### Blender-MCP Integration
- **blender-mcp** — AI assistant → Blender bridge via MCP (Model Context Protocol)
  - `uv 0.11.14` installed at `C:\Users\KLH\.local\bin\uv.exe`
  - `addon.py` downloaded to project root (2,635 lines) — needs to be installed in Blender via **Edit > Preferences > Add-ons > Install...**
  - MCP server config created at `.agents/mcp.json` for Codebuff:
    ```json
    {
      "mcpServers": {
        "blender": {
          "command": "cmd",
          "args": ["/c", "uvx", "blender-mcp"]
        }
      }
    }
    ```
  - **Usage:**
    1. Install `addon.py` in Blender (Edit > Preferences > Add-ons > Install... > select `addon.py` → enable "Blender MCP")
    2. In Blender, press **N** to open sidebar, go to **BlenderMCP** tab, click **Connect**
    3. Ask Codebuff to manipulate Blender objects

## P0 Game-Ready Scripts
- `bake_textures.py` — Bakes procedural materials to PNG textures (Diffuse, Normal, AO)
- `generate_collision.py` — Creates simplified collision mesh via decimate
- `generate_lod.py` — Generates 3 LOD levels (LOD0, LOD1, LOD2) with progressive decimation

### New: Dirt / Off-Road Path
- `base_environment.py`:
  - `make_dirt()` — warm brown dirt/gravel procedural texture (two noise layers, rough=1.0, bump=0.5)
  - `create_dirt_path(main_pts, branch_idx, side, path_len, path_width, curve_angle)` — generates a curved dirt strip branching from the main road edge with gentle S-curve meander; returns `(object, end_pos)` so destinations can be placed at the path's end
  - Aliases: `mat_dirt`/`mt_dirt`

## Recommended Workflow
1. Run `racing_environment.py`, `japanese_environment.py`, or `desert_environment.py` in Blender
2. Run `bake_textures.py` to bake procedural → image textures
3. Run `generate_collision.py` to add collision mesh
4. Run `generate_lod.py` to add LOD variants
5. Export all to FBX/glTF

---

## Session Notes — 2025-05-14: ClawTeam Real-Time Visualizer

### What We Built
- **`clawteam_bridge.py`** (new) — Three-tier adapter connecting the web UI to the real ClawTeam framework:
  - **RealAPIBridge 🏆** — Uses ClawTeam v0.2.0 Python API directly (`TeamManager.create_team()`, `add_member()`, `TaskStore`, `BoardCollector.collect_team()`)
  - **CLIBridge 🔧** — Falls back to `clawteam` CLI subprocess with `--json` output
  - **MockBridge 🔌** — Simulated pipeline when ClawTeam isn't installed
  - Factory function `get_bridge()` auto-selects best available mode

### What We Updated
- **`swarm_web.py`** — Added 3 new endpoints:
  - `/realtime/clawteam` — SSE stream that launches a real ClawTeam demo pipeline
  - `/realtime/clawteam/status` — JSON showing bridge mode (`"real"` / `"cli"` / `"mock"`)
  - `/realtime/clawteam/state` — JSON snapshot of live ClawTeam state
  - Footer banner now shows `REAL`, `CLI`, or `MOCK` based on detection

- **`clawteam_ui.html`** — 3-tier fallback when clicking Run Swarm:
  1. 🧠 **REAL ClawTeam** — connects to `/realtime/clawteam` SSE (live TeamManager API)
  2. 🔧 **CLI ClawTeam** — connects to `/events/clawteam` SSE (server-side mock)
  3. 🔌 **SIMULATED** — runs `FALLBACK_STEPS` client-side (no server needed)
  - Added bridge badge near Run button: green (`🧠 REAL`), amber (`🔧 CLI`), gray (`🔌 SIMULATED`)
  - `checkBridgeMode()` fetches `/realtime/clawteam/status` to detect availability
  - Button text: `⏳ Connecting…` → `⏳ Running…` → `▶ Run Swarm`
  - Heartbeat handler silences keep-alive events from real bridge

### Fixes Made
- **`TaskStore.list()` bug** (dead code) — `RealAPIBridge.launch_demo()` Phase 6 called `task_store.list(owner=aid)` but ClawTeam v0.2.0's `TaskStore` has no `.list()` method. Removed the unused `result = task_store.list(...)` line.
- **`_serve_html()` syntax error** — Docstring was on same line as function signature. Fixed by splitting to separate line.
