"""mazes/random_maze.py — random solvable maze every run (§11).

Iterative DFS (recursive backtracker) carves a PERFECT maze: start with all
interior walls up, knock walls down along a random DFS tree. A perfect maze
is always fully connected, so start->goal is guaranteed solvable.
Then knock ~24 extra random walls to add loops (micromouse-style, multiple
routes, flood-fill detours worth comparing against A* in §12).
"""
import random

from maze import Maze


def generate_random_maze(seed=None, extra_loops=None, size=16):
    rng = random.Random(seed)
    if extra_loops is None:
        extra_loops = size * size // 10  # denser loops on bigger boards
    m = Maze(size, size)
    W, H = m.w, m.h

    # Start solid: every interior edge walled.
    for x in range(W):
        for y in range(H):
            if x + 1 < W:
                m.add_wall_between(x, y, x + 1, y)
            if y + 1 < H:
                m.add_wall_between(x, y, x, y + 1)

    # DFS carve from start.
    visited = [[False] * H for _ in range(W)]
    stack = [(0, 0)]
    visited[0][0] = True
    while stack:
        x, y = stack[-1]
        options = []
        for dx, dy, d in ((0, 1, "N"), (0, -1, "S"), (1, 0, "E"), (-1, 0, "W")):
            nx, ny = x + dx, y + dy
            if 0 <= nx < W and 0 <= ny < H and not visited[nx][ny]:
                options.append((nx, ny, d))
        if not options:
            stack.pop()
            continue
        nx, ny, d = rng.choice(options)
        m.set_wall(x, y, d, False)  # knock down shared edge
        visited[nx][ny] = True
        stack.append((nx, ny))

    # Add loops: knock extra random interior walls (never border).
    knocked = 0
    tries = 0
    while knocked < extra_loops and tries < 2000:
        tries += 1
        x = rng.randrange(W)
        y = rng.randrange(H)
        d = rng.choice(["N", "E"])  # N/E covers every interior edge once
        nx, ny = (x, y + 1) if d == "N" else (x + 1, y)
        if not (0 <= nx < W and 0 <= ny < H):
            continue
        if (x, y) == (0, 0) or (nx, ny) == (0, 0):
            continue  # keep start cell character stable
        if m.has_wall(x, y, d):
            m.set_wall(x, y, d, False)
            knocked += 1
    return m
