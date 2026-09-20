"""simulator.py — simulation loop, NO pygame/ursina imports (§11).

Both 2D and 3D views call Simulator.step(). Keeps algorithm testable headless.
Phases: EXPLORE_TO_GOAL -> RETURN_TO_START -> OPTIMIZE (A*) -> DONE.
"""
from algos import ALGOS
from astar import find_path
from floodfill import choose_next, compute_distances
from maze import START, center_goals
from robot import Robot

import time as _time


class Simulator:
    def __init__(self, true_maze, start=START, goals=None, algorithm="flood"):
        if algorithm not in ALGOS:
            raise ValueError(f"unknown algorithm {algorithm!r}; pick {sorted(ALGOS)}")
        self.true = true_maze
        self.start = start
        # goals default to the center 4 cells of whatever size maze this is
        self.goals = set(goals) if goals else set(center_goals(true_maze.w, true_maze.h))
        self.algorithm = algorithm
        self.compare_results = []  # compare feature; cleared only on new maze
        self._reset_run()

    def reset(self, new_maze=None, algorithm=None):
        """Restart exploration. A new maze replaces the board (and results);
        otherwise the SAME maze is replayed (used for algo comparison)."""
        if new_maze is not None:
            self.true = new_maze
            self.compare_results = []
        if algorithm is not None:
            if algorithm not in ALGOS:
                raise ValueError(f"unknown algorithm {algorithm!r}")
            self.algorithm = algorithm
        self._reset_run()

    def set_algorithm(self, name):
        """Replay the SAME maze with a different explorer (comparison runs)."""
        self.reset(algorithm=name)

    def _reset_run(self):
        from robot import Robot  # local import: keeps module import order simple

        self.known = self.true.blank_copy()  # fog of war: borders only
        self.robot = Robot(*self.start)
        self.phase = "EXPLORE_TO_GOAL"  # RETURN_TO_START / OPTIMIZE / SPEEDRUN / DONE
        self.steps = 0
        self.explored = set()  # cells ever entered
        self.explore_path = []  # full walk incl. detours
        self.optimal_path = []  # A* output
        self.flood_len = 0
        self.algo_state = {}  # per-explorer memory (DFS stack, cycle counts)
        self.stuck = False  # True if the explorer looped / gave up
        self.steps_to_goal = None  # steps at first goal arrival (None if stuck)
        self.race_t0 = _time.perf_counter()  # wall-clock start of this race
        self.last_solve_time = None  # seconds explore+return took (set at OPTIMIZE)
        # Speed-run animation state (replays optimal_path after OPTIMIZE).
        self.speedrun_active = False
        self.speedrun_idx = 0
        self.dist = compute_distances(self.known, self.goals)
        self._discover()  # learn start cell walls immediately

    # -- internals ----------------------------------------------------------
    def _target(self):
        if self.phase == "EXPLORE_TO_GOAL":
            return self.goals
        if self.phase == "RETURN_TO_START":
            return {self.start}
        return set()

    def _discover(self):
        x, y = self.robot.pos
        self.known.discover(self.true, x, y)
        self.explored.add((x, y))
        if not self.explore_path or self.explore_path[-1] != (x, y):
            self.explore_path.append((x, y))

    # -- public API used by views -------------------------------------------
    def step(self):
        """Advance one cell. Returns phase (views just call this on SPACE/R)."""
        if self.phase in ("OPTIMIZE", "DONE"):
            return self.phase
        self._discover()
        self.dist = compute_distances(self.known, self._target())
        x, y = self.robot.pos
        if (x, y) in self._target():
            if self.phase == "EXPLORE_TO_GOAL":
                if self.steps_to_goal is None:
                    self.steps_to_goal = self.steps  # first arrival metric
                self.phase = "RETURN_TO_START"
                self.dist = compute_distances(self.known, {self.start})
                return self.phase
            if self.phase == "RETURN_TO_START":
                self._run_optimization()
                return self.phase
        if self.phase == "EXPLORE_TO_GOAL":
            # Movement choice belongs to the active explorer. The return leg
            # always uses flood guidance on the mapped-so-far maze.
            if self._note_cycle():  # looping without progress (wall follower)?
                self.stuck = True
                self._run_optimization()
                return self.phase
            nxt = ALGOS[self.algorithm].select(self)
            if nxt is None:  # fully explored yet goaless (shouldn't happen)
                self.stuck = True
                self._run_optimization()
                return self.phase
        else:
            nxt = choose_next(x, y, self.dist, self.known, self.robot.heading)
            if nxt is None:  # trapped on incomplete map: re-propagate optimism
                self.dist = compute_distances(self.known, self._target())
                nxt = choose_next(x, y, self.dist, self.known, self.robot.heading)
                if nxt is None:
                    self._run_optimization()  # give up exploring, show best known
                    return self.phase
        # Realism guard: known map is optimistic, true maze may have a wall
        # here. Bump (learn it, stay put) instead of ghosting through it.
        # Without this the mouse walks through undiscovered walls.
        nx, ny = nxt
        bump_dir = None
        for d in ("N", "S", "E", "W"):
            from maze import DIRS as _DIRS

            dx, dy = _DIRS[d]
            if (x + dx, y + dy) == (nx, ny):
                bump_dir = d
                break
        if bump_dir and self.true.has_wall(x, y, bump_dir):
            self.known.set_wall(x, y, bump_dir, True)  # learn the wall
            self.dist = compute_distances(self.known, self._target())
            self.steps += 1  # bumping still costs a step, but no cell change
            return self.phase
        self.robot.move_to(nx, ny)
        self.steps += 1
        self._discover()
        return self.phase

    def _note_cycle(self):
        """Loop guard for exploration. True when the explorer repeats the
        same (cell, heading) state over and over (wall follower in a loop)
        or blows past any reasonable step budget."""
        key = (self.robot.x, self.robot.y, self.robot.heading)
        counts = self.algo_state.setdefault("cycles", {})
        counts[key] = counts.get(key, 0) + 1
        if counts[key] > 8:
            return True
        if self.steps > 8 * self.true.w * self.true.h + 1000:
            return True
        return False

    def run_to_completion(self, name, cap=40000):
        """Race one algorithm headlessly on the CURRENT maze. The maze is
        kept; exploration state is reset. Returns a metrics dict for the
        comparison table."""
        self.set_algorithm(name)
        n = 0
        while self.phase not in ("OPTIMIZE", "DONE") and n < cap:
            self.step()
            n += 1
        # Reference optimum always comes from ground truth so every row of
        # the comparison table shares one yardstick (a stuck run only maps
        # part of the maze, so its known-map A* would under-read).
        true_path = find_path(self.true, self.start, self.goals)
        return {
            "algo": name,
            "label": ALGOS[name].label,
            "to_goal": self.steps_to_goal,
            "walk": self.flood_len if self.flood_len else self.steps,
            "optimal": max(0, len(true_path) - 1),
            "solve_time": self.last_solve_time if self.last_solve_time else 0.0,
            "stuck": self.stuck,
            "explored": len(self.explored),
            "finished": self.phase in ("OPTIMIZE", "DONE"),
        }

    def _run_optimization(self):
        """Phase 2: A* on the now-complete known map (§12)."""
        self.flood_len = len(self.explore_path) - 1
        self.last_solve_time = _time.perf_counter() - self.race_t0
        # By now known == true for all visited cells; assume full enough.
        # Fall back to true maze for guaranteed optimal display.
        self.optimal_path = find_path(self.known, self.start, self.goals) or \
            find_path(self.true, self.start, self.goals)
        self.phase = "OPTIMIZE" if self.optimal_path else "DONE"

    def finish_exploration(self, cap=20000):
        """S key: fast-forward stepping until OPTIMIZE/DONE."""
        n = 0
        while self.phase not in ("OPTIMIZE", "DONE") and n < cap:
            self.step()
            n += 1
        return self.phase

    # -- speed run: replay the A* optimum autonomously ----------------------
    def start_speedrun(self):
        """Enter SPEEDRUN phase; robot replays optimal_path from start."""
        if not self.optimal_path:
            return False
        self.phase = "SPEEDRUN"
        self.speedrun_active = True
        self.speedrun_idx = 0
        self.robot.move_to(*self.optimal_path[0])
        return True

    def step_speedrun(self):
        """Advance one cell along optimal_path. Returns True when finished."""
        if not self.speedrun_active or not self.optimal_path:
            return True
        self.speedrun_idx += 1
        if self.speedrun_idx >= len(self.optimal_path):
            self.speedrun_active = False
            self.phase = "DONE"
            return True
        self.robot.move_to(*self.optimal_path[self.speedrun_idx])
        return self.speedrun_idx >= len(self.optimal_path) - 1

    @property
    def astar_len(self):
        return max(0, len(self.optimal_path) - 1)

    @property
    def pos(self):
        return self.robot.pos
