"""algos.py — explorer strategies with one shared interface (§11).

Each explorer answers a single question: given the simulator state, which
neighbour cell should the mouse enter next? The Simulator owns phases,
wall learning (fog of war + bump rule) and metrics; explorers only choose.

  FloodExplorer  classic flood-fill: step to the lowest-distance neighbour.
                 Fastest, near-optimal exploration. Always terminates.
  DfsExplorer    Tremaux-style depth-first search: push into unvisited cells,
                 backtrack along its stack from dead ends. Complete (always
                 terminates on a connected maze) but walks much further.
  WallExplorer   left-hand wall follower: left > straight > right > back.
                 Guaranteed only on simply-connected mazes (no loops). Our
                 random mazes HAVE loops, so this one can cycle forever --
                 the Simulator's stuck detector catches that, which is itself
                 a great demo of why wall following is not a general solver.
"""

from floodfill import choose_next


class Explorer:
    key = "?"            # CLI / config id
    label = "?"          # sidebar + table display name
    menu_key = None      # start-menu toggle key (pygame K_*)
    color = (200, 200, 200)  # UI accent: menu dots, switch banner, trail legend
    blurb = ""           # one-line description for menu/docs

    def select(self, sim):
        """Return (nx, ny) to enter next, or None if no move exists."""
        raise NotImplementedError


class FloodExplorer(Explorer):
    key = "flood"
    label = "Flood-fill"
    menu_key = "F"
    color = (50, 120, 220)
    blurb = "lowest flood distance; fastest, near-optimal"

    def select(self, sim):
        x, y = sim.pos
        return choose_next(x, y, sim.dist, sim.known, sim.robot.heading)


class DfsExplorer(Explorer):
    key = "dfs"
    label = "Tremaux DFS"
    menu_key = "T"
    color = (150, 100, 220)
    blurb = "depth-first + backtrack; complete but long-winded"

    def select(self, sim):
        pos = sim.pos
        st = sim.algo_state.setdefault("stack", [pos])
        # Resync: a bumped-into wall leaves an un-entered cell on the stack.
        # Trim back to reality (the bump already taught us that wall).
        if not st or st[-1] != pos:
            if pos in st:
                while st[-1] != pos:
                    st.pop()
            else:
                st.append(pos)
        # Forward: first known-open, never-visited neighbour (N/E/S/W).
        for nx, ny, d in sim.known.neighbours(*pos):
            if sim.known.has_wall(*pos, d):
                continue
            if (nx, ny) not in sim.explored:
                st.append((nx, ny))
                return (nx, ny)
        # Dead end: backtrack one cell along the stack.
        st.pop()  # leave current cell
        while st:
            back = st[-1]
            dx, dy = back[0] - pos[0], back[1] - pos[1]
            if abs(dx) + abs(dy) == 1:
                for nx, ny, d in sim.known.neighbours(*pos):
                    if (nx, ny) == back and not sim.known.has_wall(*pos, d):
                        return back
            st.pop()  # stale entry (shouldn't happen); keep unwinding
        return None


class WallExplorer(Explorer):
    key = "wall"
    label = "Left-wall follower"
    menu_key = "W"
    color = (235, 140, 50)
    blurb = "left > straight > right; loops forever on loopy mazes"

    _ORDER = {
        "N": ["W", "N", "E", "S"],
        "E": ["N", "E", "S", "W"],
        "S": ["E", "S", "W", "N"],
        "W": ["S", "W", "N", "E"],
    }

    def select(self, sim):
        x, y = sim.pos
        for d in self._ORDER[sim.robot.heading]:
            for nx, ny, dd in sim.known.neighbours(x, y):
                if dd == d and not sim.known.has_wall(x, y, d):
                    return (nx, ny)
        return None


ALGOS = {C.key: C() for C in (FloodExplorer, DfsExplorer, WallExplorer)}
ALGO_ORDER = ["flood", "dfs", "wall"]  # stable order for menus + tables
