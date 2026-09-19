"""astar.py — Phase 2 optimizer (§12 reference). A* with Manhattan heuristic."""

import heapq

from maze import DIRS


def manhattan(x, y, goals):
    return min(abs(x - gx) + abs(y - gy) for gx, gy in goals)


def find_path(maze, start, goals):
    """A* on the (now complete) map. Returns list of cells start->goal, or []."""
    goals = set(goals)
    if start in goals:
        return [start]
    open_h = [(manhattan(start[0], start[1], goals), 0, start, [start])]
    best_g = {start: 0}
    while open_h:
        _, g, (x, y), path = heapq.heappop(open_h)
        if (x, y) in goals:
            return path
        if g > best_g.get((x, y), 1e9):
            continue
        for d, (dx, dy) in DIRS.items():
            nx, ny = x + dx, y + dy
            if not (0 <= nx < maze.w and 0 <= ny < maze.h):
                continue
            if maze.has_wall(x, y, d):
                continue
            ng = g + 1
            if ng < best_g.get((nx, ny), 1e9):
                best_g[(nx, ny)] = ng
                f = ng + manhattan(nx, ny, goals)
                heapq.heappush(open_h, (f, ng, (nx, ny), path + [(nx, ny)]))
    return []
