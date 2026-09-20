# MARC Micromouse Simulator — Explainer & Presentation Reference

> Purpose: a single factual reference about this project. Give this file (plus
> `README.md`) to an AI assistant and ask it to quiz you, draft your slides, or
> prepare you for viva questions. Every claim below matches the code as built.

## 1. The 30-second pitch

"This is a 2D/3D simulator for a Micromouse-style maze-solving robot. The mouse
starts in a maze it has never seen, maps it with a flood-fill algorithm, drives
back to the start, then computes the shortest route with A* and sprints it. The
whole point the demo proves: exploring an unknown maze costs far more steps
than running the optimal path once you know it — e.g. 46 exploration steps vs a
21-step optimal sprint on the same board (seed 11)."

## 2. Problem statement

A Micromouse robot competes on a 16x16 grid maze. It starts in one corner with
**zero knowledge** of the walls, must reach the center, and is then scored on
how fast it can re-run the maze. The classic solution has two parts: (1) an
exploration strategy that guarantees reaching the goal without a map, and
(2) an optimization step that extracts the shortest path from the finished map.
This simulator demonstrates exactly that pipeline — no hardware required.

## 3. What the sim does (and does not do)

Does: random solvable mazes 16x16–32x32, fog-of-war exploration, flood-fill
navigation, A* shortest path, autonomous animated mouse, speed-run replay,
dark mode, headless (no-GUI) verification mode.

Does NOT do (deliberate scope cuts, good to state upfront in a presentation):
no motor/sensor simulation, no sensor noise or timing, no diagonal moves, no
speed profiling, no maze editor, no 3D camera controls (fixed isometric view).
Movement is cell-to-cell teleportation smoothed by animation — the project is
about **algorithms**, not physics.

## 4. Architecture (single codebase, two views)

```
main.py                CLI: --headless / --2d / --3d, --size, --seed, --maze, --algo
maze.py                wall data (shared-edge arrays), goals, coordinates
robot.py               position + heading only
algos.py               explorer strategies: flood-fill, Dijkstra, Tremaux DFS
floodfill.py           BFS distances + flood step choice (used by flood explorer)
astar.py               Phase 2: A* with Manhattan heuristic
simulator.py           simulation loop + phase state machine (NO GUI imports)
view_2d.py             Pygame: start menu, sidebar, animations, dark mode
view_3d.py             Ursina: same Simulator, 3D boxes (best effort)
mazes/random_maze.py   DFS carve + extra loops, any even size 16..32
mazes/simple_maze.py   fixed sparse 16x16 demo layout
```

Key design decision to mention: `simulator.py` never imports Pygame or Ursina.
Both views just call `sim.step()`. That separation is what makes `--headless`
testing possible and is the standard "logic vs presentation" split examiners
like to hear about.

Coordinates: x grows east (0..N-1), y grows north (0..N-1). Start is (0,0)
bottom-left. Goal is the center 4 cells. Each cell stores 4 wall booleans
(N/S/E/W); walls are shared between adjacent cells via two edge arrays, so a
wall can never be inconsistent between neighbours.

## 5. Algorithm, Phase 1 — flood-fill exploration

1. Maintain a distance grid: goal cells = 0, everything else = infinity, then
   breadth-first-search outward **through known-open walls only**.
2. The mouse always steps to the accessible neighbour with the lowest distance.
3. On entering a cell it learns ("discovers") that cell's four walls.
4. After every discovery the whole distance grid is recomputed (256–1024 cells:
   trivial cost, so full re-propagation instead of incremental updates).
5. Unknown walls are treated as **open** (optimistic). This is the crux: optimism
   lets the mouse keep moving, but it also walks into dead ends — which is why
   the exploration walk is much longer than the optimum.
6. Reaching the goal flips the target to the start; the same logic drives the
   mouse home (phase `RETURN_TO_START`).

Three realism rules worth mentioning:
- **Bump rule:** if the mouse tries to step through a wall the true maze has
  but it hasn't discovered yet, it stays put, learns the wall, and still burns
  a step — instead of ghosting through walls.
- **Tie-break:** on equal distances it prefers going straight and avoids
  180-degree reversals, which kills the back-and-forth oscillation naive
  flood-fill implementations show.
- **Fog of war:** the mouse learns walls only by entering cells — no lookahead.

## 6. Algorithm, Phase 2 — A* optimization

Once exploration + return finish, A* runs on the now-complete map with a
Manhattan-distance heuristic. Output: the optimal start-to-goal cell list,
drawn green over the exploration history. Flood-walk length vs A* length is
shown side by side in the sidebar and printed by `--headless`.

The question you WILL be asked: "aren't flood-fill distances already optimal,
making A* redundant?" Answer: yes — on a *fully known* map both agree. The
point is the comparison: the flood *walk* (what the mouse actually travelled
under fog of war, including detours, backtracks and the return leg) versus the
*optimal path length*. A* exists to compute and display that optimum cleanly,
and to drive the speed-run replay.

## 7. Verified results (reproduce with `python main.py --headless --size N --seed S`)

| Board | Seed | Exploration steps | A* optimum | Ratio |
|-------|------|-------------------|------------|-------|
| 16x16 | 5    | 50                | 19         | 2.6x  |
| 16x16 | 7    | 56                | 23         | 2.4x  |
| 16x16 | 1    | 84                | 32         | 2.6x  |
| 24x24 | 2    | 282               | 43         | 6.6x  |
| 32x32 | 3    | 264               | 54         | 4.9x  |

Takeaway line: "Exploration consistently costs 2–7x the optimal path, and the
gap grows with maze size — that gap IS the cost of not having a map."

## 7b. Same-maze algorithm shootout (seed 11, 16x16 — via Compare (C))

| Explorer | To goal | Full walk | Optimum | Solve time | Verdict |
|----------|---------|-----------|---------|------------|---------|
| Flood-fill | 25 | 46 | 21 | ~0.03s | solved, near-optimal |
| Dijkstra | 131 | 152 | 21 | ~0.13s | solved; optimal character, costlier search |
| Tremaux DFS | 153 | 174 | 21 | ~0.11s | solved, 6x the cost |

(On seed 7 flood and Dijkstra tie exactly at 23/56 — the twin result that
proves the point.) Solve times are wall-clock on a laptop — step counts are
the architecture-independent result; times just show all three finish
instantly. Loading a different row flashes an ALGORITHM SWITCHED banner plus
a halo in that explorer's color, so the audience always knows which brain is
driving.

Takeaway line: "Three algorithms, one maze: flood-fill wins on steps,
Dijkstra matches it on optimality at higher search cost, DFS pays 6x for
having no map." Replay any row with keys 1–3; Replay (Y) re-runs the same
maze, New maze (X) deals a fresh one.

## 8. Live demo script (5–7 minutes)

1. (30s) Double-click `start.bat`. Start menu appears: pick 16x16, Random,
   leave seed empty, toggle flood + Dijkstra (F/I). Say what each means:
   goal-anchored flood vs mouse-anchored Dijkstra.
2. (2 min) Press START. Flood races first with no further input: ghost maze,
   black discovered walls, numbers + gradient, blue trail, red revisit dots,
   gold sense-flashes, live stopwatch bottom-right. When it solves, the sprint
   auto-plays — then the tournament auto-loads Dijkstra with an ALGORITHM
   SWITCHED banner and runs it on the identical maze.
3. (30s) When race 2 finishes, the TOURNAMENT COMPLETE prompt appears — open
   the dashboard (H): head-to-head table, coverage curves, walk splits and
   incident bars, all live. Read the twin result aloud.
4. (1 min) Press C for the table, replay a row with 1–2, or X for a fresh
   maze. Optional: dark mode (D), 32x32 board.
5. (1 min) Close with limitations + one future-work item (Section 10).

## 9. Likely viva/Q&A questions (with answers)

1. *Why is the exploration path longer than A*?* Fog of war: optimistic
   unknown-as-open assumption causes dead ends, backtracks, plus the mandatory
   return-to-start leg. A* runs on the finished map.
2. *Why drive back to the start instead of stopping at the goal?* Real
   micromouse scoring includes the return/sprint from the start; architecturally
   it reuses the identical flood-to-target routine with a different target.
3. *Time/space complexity?* Flood BFS is O(cells) per step; A* is O(cells log
   cells). Boards are ≤1024 cells, so everything is instantaneous.
4. *Is the random maze always solvable?* Yes: recursive-backtracker carve makes
   a perfect maze (fully connected by construction), then extra walls are only
   *removed* to add loops — removal can't disconnect anything.
5. *Why Manhattan heuristic — is it admissible?* Yes: with 4-directional moves
   at unit cost, Manhattan never overestimates, so A* is optimal.
6. *What does the mouse do on ties/oscillation?* Straight-preference,
   reversal-last tie-break (see `floodfill.choose_next`).
7. *What happens on Quit/ESC vs Menu (B)?* ESC closes the app; B returns to the
   start menu, discarding the current race.
8. *How is this different from a real Micromouse?* No sensors, motors or
    inertia; sensing is perfect on entry; movement is discrete. The
    sim isolates decision-making from hardware.
9. *Biggest simplification?* Discovering a whole cell's walls on entry and
   teleport-style discrete motion.
10. *How did you test without the GUI?* `--headless` asserts goal-reached,
    return-to-start, A* found, and optimal ≤ exploration walk.
11. *Why two views?* Same `Simulator` proves the algorithm is GUI-independent;
    3D is explicitly best-effort/stretch.
12. *What would you add with more time?* Sensor-range simulation (see walls one
    cell ahead), maze editor, run statistics over many seeds, hardware port.
13. *Who did what?* (Fill in per teammate before presenting.)
14. *Why Python/Pygame?* Zero-install friction for the team, fast iteration,
    readable for beginners; performance is a non-issue at this scale.
15. *Why do flood-fill and Dijkstra finish so similarly?* Both are optimal
    greedy strategies on the known map — one propagates distances from the
    goal, the other searches from the mouse. Same finish, different search
    direction and tie-breaks; on seed 7 they tie exactly, on seed 11 the
    tie-breaks cost Dijkstra ~100 extra steps. That is the demo's subtle
    result: optimality of the *path* doesn't imply equality of the *search*.
16. *Is the comparison fair — same maze for all three?* Yes, that is the
    point of Compare (C) and the tournament: fresh Simulator instances share
    one immutable true maze, so to-goal steps are directly comparable and
    the optimum is shared.

## 10. Limitations & future work (say these before the examiner does)

Teleport-style discrete motion; perfect entry sensing; sparse-vs-dense maze
character is fixed by the generator; 3D view is best-effort; no statistics mode
yet. Natural next steps: lookahead sensing, editable mazes, batch runs with
seed sweeps and a results table, then a hardware abstraction layer.

## 11. Glossary (one-liners)

- Flood fill: distance-to-target field recomputed over known-open cells.
- Fog of war: undiscovered walls hidden/assumed open until visited.
- Bump: attempting a truly-walled move; costs a step, teaches the wall.
- Backtrack: revisiting an explored cell (red trail dots).
- Speed run: replaying the A* optimum at 2x for the demo finale.
- Seed: integer reproducing an exact random maze (`--seed 7`).
- Ghost maze: faint full-layout preview; black = confirmed by visit.
- Believed vs true optimum: the green sprint path and sidebar figure use the
  mapped-so-far maze (they may cut through still-unknown territory, e.g. 14
  believed vs 21 true on seed 11) — that is what the mouse itself would run.
  Shootout tables always use the ground-truth optimum as the shared yardstick.
- Dashboard panels: HEAD TO HEAD (every metric per algo), COVERAGE (cells
  mapped vs steps — steeper is smarter), WALK SPLIT (explore vs return with
  the optimum ticked), INCIDENTS (bumps/revisits/dead ends).

## 12. Code pointers (for "show me where…" questions)

- Flood BFS: `floodfill.compute_distances` · step choice: `floodfill.choose_next`
- Explorers: `algos.FloodExplorer/DijkstraExplorer/DfsExplorer.select` ·
  stuck guard: `simulator._note_cycle` · same-maze replay:
  `simulator.set_algorithm` · tournament: `view_2d._on_race_end`,
  dashboard: `view_2d.draw_dashboard` (H toggles race/dash)
- Bump + phases: `simulator.Simulator.step` · A*: `astar.find_path`, `manhattan`
- Headless races: `simulator.run_to_completion` · compare table: `view_2d.do_compare`
- Speed-run state: `simulator.start_speedrun/step_speedrun` · maze gen:
  `mazes/random_maze.generate_random_maze` · menu loop: `view_2d.run_2d`
