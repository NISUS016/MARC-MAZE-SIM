"""algos.py — explorer strategies with one shared interface (§11).

Each explorer answers a single question: given the simulator state, which
neighbour cell should the mouse enter next? The Simulator owns phases,
wall learning (fog of war + bump rule) and metrics; explorers only choose.

  FloodExplorer     classic flood-fill: step to the lowest goal-distance
                    neighbour. Goal-anchored, near-optimal. Always terminates.
  DijkstraExplorer  uniform-cost search FROM the mouse TO the goal over the
                    known map, following its first step. Start-anchored twin
                    of flood-fill: same optimal character, different search
                    direction and tie-breaks. Always terminates.
  DfsExplorer       Tremaux-style depth-first search: push into unvisited
                    cells, backtrack along its stack from dead ends. Complete
                    (terminates on connected mazes) but walks much further.
"""

import heapq

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


class DijkstraExplorer(Explorer):
    key = "dijkstra"
    label = "Dijkstra"
    menu_key = "I"
    color = (45, 190, 175)
    blurb = "shortest-path search from the mouse; optimal, methodical"

    def select(self, sim):
        pos = sim.pos
        path = self._dijkstra_path(sim.known, pos, sim.goals)
        if path and len(path) > 1:
            return path[1]
        # Goal cut off by known walls (walled pocket): probe the unknown.
        for nx, ny, d in sim.known.neighbours(*pos):
            if not sim.known.has_wall(*pos, d) and (nx, ny) not in sim.explored:
                return (nx, ny)
        # Fully boxed in: nudge any known opening so the bump rule learns.
        for nx, ny, d in sim.known.neighbours(*pos):
            if not sim.known.has_wall(*pos, d):
                return (nx, ny)
        return None

    @staticmethod
    def _dijkstra_path(maze, start, goals):
        """Uniform-cost shortest path on the known map. Heap entries are
        (dist, cell) so ties break deterministically by coordinates."""
        goals = set(goals)
        if start in goals:
            return [start]
        best = {start: 0}
        prev = {}
        pq = [(0, start)]
        done = set()
        while pq:
            d, cur = heapq.heappop(pq)
            if cur in done:
                continue
            done.add(cur)
            if cur in goals:
                path = [cur]
                while path[-1] in prev:
                    path.append(prev[path[-1]])
                return path[::-1]
            x, y = cur
            for nx, ny, dd in maze.neighbours(x, y):
                if maze.has_wall(x, y, dd):
                    continue
                nd = d + 1
                if nd < best.get((nx, ny), 10 ** 9):
                    best[(nx, ny)] = nd
                    prev[(nx, ny)] = cur
                    heapq.heappush(pq, (nd, (nx, ny)))
        return []


ALGOS = {C.key: C() for C in (FloodExplorer, DijkstraExplorer, DfsExplorer)}
ALGO_ORDER = ["flood", "dijkstra", "dfs"]  # stable order for menus + tables
