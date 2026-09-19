"""robot.py — robot state (§11 reference). No motors/sensors simulated."""

from maze import DIRS


class Robot:
    """Grid robot. Moves orthogonally, one cell per step. Teleports (no animation)."""

    # heading order for deterministic tie-breaks
    ORDER = ["N", "E", "S", "W"]

    def __init__(self, x=0, y=0, heading="N"):
        self.x = x
        self.y = y
        self.heading = heading

    @property
    def pos(self):
        return (self.x, self.y)

    def move_to(self, nx, ny):
        """Move to adjacent cell, update heading to direction of motion."""
        dx, dy = nx - self.x, ny - self.y
        for d, (ddx, ddy) in DIRS.items():
            if (dx, dy) == (ddx, ddy):
                self.heading = d
                break
        self.x, self.y = nx, ny
