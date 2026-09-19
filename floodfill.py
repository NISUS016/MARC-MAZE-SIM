"""floodfill.py — Phase 1 explorer (§11 reference).

Classic micromouse flood fill:
  dist[target] = 0, all others INF, BFS outward through KNOWN-OPEN walls.
Recomputed from scratch after every wall discovery (256 cells: trivial cost).
Robot always steps to the lowest-value accessible neighbour.
"""
from collections import deque

INF = 9999
# Fixed expansion order => deterministic behaviour for the report.
ORDER = ["N", "E", "S", "W"]


def compute_distances(known_maze, targets):
    """BFS distance grid to nearest cell in `targets` using known walls only.

    Unknown walls are treated as OPEN (optimistic) — this is why the
    exploration path is longer than the final A* optimum (§12 discussion).
    Sized from the maze itself so 16x16..32x32 all work.
    """
    W, H = known_maze.w, known_maze.h
    targets = set(targets)
    dist = [[INF] * H for _ in range(W)]
    q = deque()
    for tx, ty in targets:
        dist[tx][ty] = 0
        q.append((tx, ty))
    while q:
        x, y = q.popleft()
        for nx, ny, d in known_maze.neighbours(x, y):
            if known_maze.has_wall(x, y, d):
                continue  # known wall blocks propagation
            if dist[nx][ny] > dist[x][y] + 1:
                dist[nx][ny] = dist[x][y] + 1
                q.append((nx, ny))
    return dist


def choose_next(x, y, dist, known_maze, heading=None):
    """Lowest-dist accessible neighbour. Returns (nx, ny) or None if trapped.

    Tie-break: keep going straight (prefer current heading), never prefer a
    180-degree reversal unless it is strictly better. This stops the
    back-and-forth oscillation beginners always hit with naive N-E-S-W order.
    """
    from maze import OPPOSITE

    cands = []
    for d in ORDER:
        for nx, ny, dd in known_maze.neighbours(x, y):
            if dd != d:
                continue
            if known_maze.has_wall(x, y, d):
                continue
            cands.append((dist[nx][ny], d, (nx, ny)))
    if not cands:
        return None
    best_d = min(c[0] for c in cands)
    tied = [(d, pos) for dv, d, pos in cands if dv == best_d]
    if len(tied) == 1 or not heading:
        # deterministic fallback order
        for d in ORDER:
            for td, pos in tied:
                if td == d:
                    return pos
    # prefer straight, then non-reverse in fixed order, reverse last
    rev = OPPOSITE.get(heading) if heading else None
    for d, pos in tied:
        if d == heading:
            return pos
    for d in ORDER:
        for td, pos in tied:
            if td == d and td != rev:
                return pos
    for td, pos in tied:
        if td == rev:
            return pos
    return tied[0][1]
