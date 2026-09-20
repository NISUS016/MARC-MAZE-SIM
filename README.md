# MARC Micromouse Simulator

16×16 to 32×32 maze solver: flood-fill exploration (Phase 1) + A\* optimization
(Phase 2). Single codebase, shared `maze.py / robot.py / floodfill.py /
astar.py / simulator.py` between Pygame 2D and Ursina 3D views.

## Prereqs (for teammates testing this)

Repo: https://github.com/NISUS016/MARC-MAZE-SIM

1. Install **Python 3.10 or newer** from https://www.python.org/downloads/
   (Windows: tick **"Add python.exe to PATH"** during installation).
   Tested on: Windows, Python 3.14.2, pygame-ce 2.5.6.
2. Get the code: `git clone https://github.com/NISUS016/MARC-MAZE-SIM.git`
   or download the ZIP from that page and extract it.
3. Easiest launch — no terminal needed:
   - Windows: double-click **`start.bat`** (checks Python, installs pygame,
     opens the simulator).
   - macOS/Linux: run `chmod +x start.sh && ./start.sh`.
4. Manual alternative: `pip install -r requirements.txt`, then
   `python main.py --2d` (pygame; ursina only needed for `--3d`).

Troubleshooting:
- `"Python was not found"` → reinstall Python with the PATH checkbox ticked,
  then close and reopen the terminal / double-click `start.bat` again.
- `pip install` fails → check internet connection, then retry. On some Linux
  systems use `pip install --user -r requirements.txt` or a venv.
- Window doesn't maximize → harmless fallback; drag to resize, the layout
  re-centers automatically.

## Quickstart

```bash
python main.py --2d                        # start menu -> pick size, maze, seed
python main.py --2d --no-menu --size 32    # skip menu, straight to 32x32
python main.py --headless --size 24 --seed 7
python main.py --headless --algo dfs       # race the Tremaux DFS explorer
python main.py --3d --size 20              # Ursina view (best effort, no menu)
```

The window opens **maximized** and the layout re-centers on resize. Cell size
adapts to fill the screen (up to 64px on big boards, down to 12px); distance
numbers scale their font and stay centered so they read even on 32×32.

Every run deals a new solvable maze (DFS carve + loops, always connected).
The start menu offers sizes 16/20/24/28/32, Random vs Classic-16 layout, an
optional numeric seed (empty = fresh every race) and dark mode. Press
**New maze (X)** in the GUI for another board of the same size.

## Controls (2D — autonomous by default)

| Input | Action |
|-----|--------|
| Auto-run | ON at launch; mouse moves itself |
| Click Run/Pause | toggle autonomous mode |
| Click Step / SPACE | step once (explore or speedrun) |
| Click Skip to A\* / S | fast-forward exploration to A\* |
| Click Speed Run / T | replay A\* optimum from start |
| Click Reset / X | fresh random maze, restarts autonomously |
| Click Replay / Y | replay the SAME maze (same algorithm) |
| Click Compare / C | after a solve: race all selected algos on this maze, table overlay |
| Click row / 1-3 | in the table: load that algo's replay on the same maze |
| Click Menu / B | back to the start menu (current race is discarded) |
| Click - / + or - / + keys | speed 1–30 steps/s |
| Click toggles or N/G/E/P/M/D | numbers, gradient, explored shade, A\* path, maze ghost, dark mode |
| D | dark mode (all UI colours switch via theme table) |
| R | auto toggle |
| ESC | quit |

3D: SPACE step, R auto, S skip, ESC quit.

## Explorer algorithms (pick any in the start menu: F/T/W)

- **Flood-fill** (default) — lowest flood distance; fastest, always terminates.
- **Tremaux DFS** — depth-first + backtrack; complete but walks much further.
- **Left-wall follower** — left > straight > right; loops forever on loopy
  mazes, so a stuck detector ends the run and the badge shows STUCK. That
  failure is the demo: wall following is not a general solver.

The race runs the first selected algorithm; after solving, **Compare (C)**
races every selected algorithm on the identical maze and shows to-goal steps,
full walk, the shared optimum and wall-clock solve time side by side. Loading
a different algorithm flashes an **ALGORITHM SWITCHED** banner and halo in
that algorithm's color (blue flood, purple DFS, orange wall-follow). Replaying
never touches the maze — only fresh X deals a new one.

## Side panel

Phase (EXPLORE_TO_GOAL / RETURN_TO_START / OPTIMIZE / SPEEDRUN / DONE),
steps taken, cells explored, flood walk length vs A\* optimal length,
robot (x, y) with x east, y north, start (0,0) bottom-left. Below the
toggles:

- **TRAIL KEY** — blue explore, red revisit (wasted motion), orange sprint.
- **FLOOD KEY** — live gradient swatches from `0 · at goal` to the current
  farthest distance. The bar rescales as flood fill re-runs every step, so a
  shade means "this far from target *given what the mouse knows so far*",
  not an absolute scale — watch it shift when new walls are discovered.

When A\* finishes, a green **SHORTEST PATH FOUND** banner flashes — hit
**Speed Run (T)** and the mouse sprints the optimum at ~2x speed with a
flame-orange body, pulsing path glow, motion streaks, a pulsing grid
vignette and a red **SPEEDRUN** banner. Wall bumps flash an expanding
red ring; every newly sensed wall flashes gold for ~0.6s.

The heading arrow sweeps smoothly between turns (no snapping), and the
breadcrumb trail is colour-coded — blue explore, **red revisit** (wasted
motion, good §12 figure), orange sprint — with a legend in the sidebar.

## Project map

- `maze.py` — wall data (`vwalls`/`hwalls` shared edges), `discover()` fog-of-war
- `robot.py` — `x, y, heading`, `move_to()` teleport
- `floodfill.py` — `compute_distances()` BFS from target (§11), `choose_next()` min neighbour
- `astar.py` — A\* + Manhattan heuristic (§12)
- `simulator.py` — `Simulator.step()`: discover → re-propagate → move; phase machine
- `view_2d.py` / `view_3d.py` — render only, call `sim.step()`
- `mazes/simple_maze.py` — fixed sparse demo layout (16×16)
- `mazes/random_maze.py` — DFS carve + loops, any even size 16..32

## What this sim does NOT do

No motor/sensor simulation, no noise/timing, no diagonal moves, no speed
profiling, no maze editor, no 3D camera controls (fixed isometric).

## Doc references (§11/§12)

- §11: `floodfill.compute_distances` (BFS re-propagated every step),
  `simulator.Simulator.step` (discover-on-entry, return-to-start leg).
- §12: `astar.find_path` + `manhattan()`; compare `flood_len` vs `astar_len`
  printed by `--headless` — optimal ≤ exploration walk proves fog-of-war overhead.
