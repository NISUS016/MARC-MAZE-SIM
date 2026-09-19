"""simulator.py — simulation loop, NO pygame/ursina imports (§11).

Both 2D and 3D views call Simulator.step(). Keeps algorithm testable headless.
Phases: EXPLORE_TO_GOAL -> RETURN_TO_START -> OPTIMIZE (A*) -> DONE.
"""
from astar import find_path
from floodfill import choose_next, compute_distances
from maze import START, center_goals
from robot import Robot


class Simulator:
    def __init__(self, true_maze, start=START, goals=None):
        self.true = true_maze
        self.start = start
        # goals default to the center 4 cells of whatever size maze this is
        self.goals = set(goals) if goals else set(center_goals(true_maze.w, true_maze.h))
        self.reset()

    def reset(self, new_maze=None):
        """Restart exploration. Pass a new maze to race a fresh random layout."""
        from robot import Robot  # local import: keeps module import order simple

        if new_maze is not None:
            self.true = new_maze

        self.known = self.true.blank_copy()  # fog of war: borders only
        self.robot = Robot(*self.start)
        self.phase = "EXPLORE_TO_GOAL"  # RETURN_TO_START / OPTIMIZE / SPEEDRUN / DONE
        self.steps = 0
        self.explored = set()  # cells ever entered
        self.explore_path = []  # full walk incl. detours
        self.optimal_path = []  # A* output
        self.flood_len = 0
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
                self.phase = "RETURN_TO_START"
                self.dist = compute_distances(self.known, {self.start})
                return self.phase
            if self.phase == "RETURN_TO_START":
                self._run_optimization()
                return self.phase
        nxt = choose_next(x, y, self.dist, self.known, self.robot.heading)
        if nxt is None:  # trapped on incomplete map: force re-propagate optimism
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

    def _run_optimization(self):
        """Phase 2: A* on the now-complete known map (§12)."""
        self.flood_len = len(self.explore_path) - 1
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
