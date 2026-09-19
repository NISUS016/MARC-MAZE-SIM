"""maze.py — shared maze data structure (§11 reference).

16x16 grid. Each cell has 4 wall booleans N/S/E/W, shared between neighbours.
Implemented as two edge arrays so sharing is automatic (no sync bugs):
  vwalls[x][y] = wall on WEST side of cell (x, y). Shape (W+1, H).
  hwalls[x][y] = wall on SOUTH side of cell (x, y). Shape (W, H+1).

Coords: x grows east (0..15), y grows north (0..15).
Start = (0, 0) bottom-left. Goal = {(7,7),(7,8),(8,7),(8,8)} center.
"""

WIDTH = 16
HEIGHT = 16
START = (0, 0)
GOALS = frozenset({(7, 7), (7, 8), (8, 7), (8, 8)})


def center_goals(w, h):
    """Goal = center 4 cells for any even-sized maze (16..32)."""
    cx, cy = w // 2, h // 2
    return frozenset({(cx - 1, cy - 1), (cx - 1, cy), (cx, cy - 1), (cx, cy)})

# (dx, dy) for N/E/S/W. Used by floodfill, astar, simulator.
DIRS = {"N": (0, 1), "S": (0, -1), "E": (1, 0), "W": (-1, 0)}
OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E"}


class Maze:
    """One maze object. Used for BOTH ground truth and robot's known map.

    known map starts with only outer borders; walls are copied in via
    discover() when the robot enters a cell (fog of war, no lookahead).
    """

    def __init__(self, w=WIDTH, h=HEIGHT):
        self.w = w
        self.h = h
        # vwalls[x][y]: west edge of (x, y)
        self.vwalls = [[False] * h for _ in range(w + 1)]
        # hwalls[x][y]: south edge of (x, y)
        self.hwalls = [[False] * (h + 1) for _ in range(w)]
        # Outer borders always walled.
        for y in range(h):
            self.vwalls[0][y] = True
            self.vwalls[w][y] = True
        for x in range(w):
            self.hwalls[x][0] = True
            self.hwalls[x][h] = True

    # -- basic wall access -------------------------------------------------
    def has_wall(self, x, y, d):
        """True if cell (x,y) has a wall in direction d. Out of bounds = wall."""
        if not (0 <= x < self.w and 0 <= y < self.h):
            return True
        if d == "N":
            return self.hwalls[x][y + 1]
        if d == "S":
            return self.hwalls[x][y]
        if d == "E":
            return self.vwalls[x + 1][y]
        if d == "W":
            return self.vwalls[x][y]
        raise ValueError(d)

    def set_wall(self, x, y, d, val=True):
        """Set wall on cell (x,y) side d. Shared edge updates neighbour too."""
        if not (0 <= x < self.w and 0 <= y < self.h):
            return
        if d == "N":
            self.hwalls[x][y + 1] = val
        elif d == "S":
            self.hwalls[x][y] = val
        elif d == "E":
            self.vwalls[x + 1][y] = val
        elif d == "W":
            self.vwalls[x][y] = val

    def add_wall_between(self, x1, y1, x2, y2):
        """Add a wall between two orthogonally adjacent cells."""
        if x2 == x1 + 1 and y2 == y1:
            self.set_wall(x1, y1, "E")
        elif x2 == x1 - 1 and y2 == y1:
            self.set_wall(x1, y1, "W")
        elif y2 == y1 + 1 and x2 == x1:
            self.set_wall(x1, y1, "N")
        elif y2 == y1 - 1 and x2 == x1:
            self.set_wall(x1, y1, "S")
        else:
            raise ValueError(f"not adjacent: {(x1, y1)} {(x2, y2)}")

    def neighbours(self, x, y):
        """All in-bounds orthogonal neighbours with direction."""
        for d, (dx, dy) in DIRS.items():
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.w and 0 <= ny < self.h:
                yield nx, ny, d

    def open_neighbours(self, x, y):
        """Neighbours reachable (no wall between) in the CURRENT map."""
        for nx, ny, d in self.neighbours(x, y):
            if not self.has_wall(x, y, d):
                yield nx, ny, d

    # -- fog of war ---------------------------------------------------------
    def discover(self, true_maze, x, y):
        """Copy the 4 walls of cell (x,y) from ground truth. Called on entry."""
        for d in ("N", "S", "E", "W"):
            self.set_wall(x, y, d, true_maze.has_wall(x, y, d))

    def blank_copy(self):
        """Fresh known-map: same size, borders only."""
        return Maze(self.w, self.h)

    # -- helpers ------------------------------------------------------------
    def is_goal(self, x, y):
        return (x, y) in GOALS

    def walls_of(self, x, y):
        return {d: self.has_wall(x, y, d) for d in ("N", "S", "E", "W")}
