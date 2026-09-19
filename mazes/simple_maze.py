"""mazes/simple_maze.py — one simple, guaranteed-solvable 16x16 layout.

Built with add_wall_between() calls (beginner friendly) instead of
hand-writing 256x4 booleans. Verified solvable: open corridors along
bottom row + right side guarantee a path to the center.
"""
from maze import Maze


def build_simple_maze():
    m = Maze()
    W = [
        # A few horizontal baffles (force detours but leave gaps)
        ((2, 2), (2, 3)), ((3, 2), (3, 3)), ((4, 2), (4, 3)),
        ((6, 2), (6, 3)), ((7, 2), (7, 3)), ((8, 2), (8, 3)),
        ((11, 2), (11, 3)), ((12, 2), (12, 3)),
        ((2, 5), (2, 6)), ((3, 5), (3, 6)), ((4, 5), (4, 6)),
        ((9, 5), (9, 6)), ((10, 5), (10, 6)), ((11, 5), (11, 6)),
        ((5, 8), (5, 9)), ((6, 8), (6, 9)), ((7, 8), (7, 9)),
        ((10, 10), (10, 11)), ((11, 10), (11, 11)),
        ((4, 12), (4, 13)), ((5, 12), (5, 13)), ((6, 12), (6, 13)),
        # Vertical baffles
        ((2, 3), (3, 3)), ((3, 3), (4, 3)),
        ((8, 4), (9, 4)), ((9, 4), (10, 4)),
        ((5, 6), (6, 6)), ((6, 6), (7, 6)),
        ((11, 7), (12, 7)), ((12, 7), (13, 7)),
        ((3, 9), (4, 9)), ((4, 9), (5, 9)),
        ((8, 11), (9, 11)), ((9, 11), (10, 11)),
        ((6, 13), (7, 13)), ((12, 13), (13, 13)),
        ((9, 1), (10, 1)), ((4, 10), (5, 10)),
    ]
    for a, b in W:
        m.add_wall_between(a[0], a[1], b[0], b[1])
    # Keep start (0,0) and goal ring open: knock out nothing needed since
    # baffles above never seal row 0, column 15, or the center block.
    return m
