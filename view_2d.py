"""view_2d.py — Pygame 2D view: start menu, maximized window, autonomous mouse.

Flow: start menu (maze size 16..32, random/classic, seed, dark mode) -> main
loop. The mouse runs by itself; the sidebar shows live status, buttons,
settings toggles, a trail key and a flood-gradient key — all clickable.
Keys: SPACE step, R auto, S skip, T speedrun, X new maze, B back to menu,
N/G/E/P/M/D toggles, +/- speed, ESC quit.
"""
import math
import pygame

from algos import ALGOS, ALGO_ORDER
from collections import deque
from floodfill import INF

PANEL_W = 360
SIZES = [16, 20, 24, 28, 32]

# ---- themes: every UI colour goes through THEMES[mode] so dark mode is ----
# ---- a one-flag switch, not a pile of if/else in the draw code.        ----
THEMES = {
    "light": {
        "bg": (245, 245, 245), "panel": (250, 250, 252),
        "cell": (255, 255, 255), "explored": (235, 235, 235),
        "grid": (228, 228, 232), "ghost": (120, 120, 132),
        "wall": (20, 20, 20), "text": (30, 30, 30), "muted": (110, 110, 110),
        "btn": (235, 238, 245), "btn_hov": (214, 222, 240),
        "div": (220, 220, 228), "dis_btn": (230, 230, 232),
        "goal": (140, 230, 140), "card": (255, 255, 255),
    },
    "dark": {
        "bg": (16, 19, 26), "panel": (24, 28, 38),
        "cell": (34, 40, 53), "explored": (46, 54, 71),
        "grid": (58, 65, 84), "ghost": (105, 113, 138),
        "wall": (235, 238, 245), "text": (235, 238, 245), "muted": (150, 160, 178),
        "btn": (44, 51, 68), "btn_hov": (60, 70, 95),
        "div": (58, 65, 84), "dis_btn": (36, 42, 56),
        "goal": (46, 140, 90), "card": (30, 35, 48),
    },
}
PATH_GREEN = (40, 180, 80)
PATH_DARK = (50, 220, 110)
ROBOT_BLUE = (50, 120, 220)
ROBOT_SPRINT = (235, 90, 40)   # speedrun flame-orange
BACKTRACK_RED = (235, 70, 80)  # trail dots where the mouse revisits cells
DISCOVER_GOLD = (255, 210, 60)  # sensor flash on newly learned walls
BUMP_RED = (230, 60, 60)
BTN_ACC = (50, 120, 220)
WHITE = (255, 255, 255)

# screen-space arrow angles (y grows down, so N = -90 deg)
HEADING_ANG = {"E": 0.0, "S": math.pi / 2, "W": math.pi, "N": -math.pi / 2}

PHASE_COLORS = {
    "EXPLORE_TO_GOAL": (220, 120, 40),
    "RETURN_TO_START": (150, 100, 220),
    "OPTIMIZE": (40, 160, 80),
    "SPEEDRUN": (220, 60, 60),
    "DONE": (100, 100, 100),
}


def dist_color(d, dmax, base):
    """Warm (red/orange) near goal -> cool (blue) far. Undiscovered = base."""
    if d >= INF or dmax <= 0:
        return base
    t = min(1.0, d / max(1, dmax))
    if t < 0.5:
        k = t / 0.5
        return (255, int(120 + 100 * k), int(80 * (1 - k)))
    k = (t - 0.5) / 0.5
    return (int(255 * (1 - k) + 120 * k), int(220 * (1 - k) + 170 * k), 255)


def _maximize_window():
    """Open maximized (best effort: falls back to the requested size)."""
    try:
        from pygame._sdl2.video import Window
        Window.from_display_module().maximize()
    except Exception:
        pass


class Button:
    algo_key = ""  # optional tag (start-menu algorithm buttons use it)

    def __init__(self, rect, label, action, enabled_fn=None, accent=False):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.action = action
        self.enabled_fn = enabled_fn or (lambda: True)
        self.accent = accent

    def enabled(self):
        try:
            return bool(self.enabled_fn())
        except Exception:
            return True

    def draw(self, screen, font, mouse, T):
        en = self.enabled()
        hov = en and self.rect.collidepoint(mouse)
        if not en:
            col = T["dis_btn"]
        elif self.accent:
            col = (70, 135, 235) if hov else BTN_ACC
        elif hov:
            col = T["btn_hov"]
        else:
            col = T["btn"]
        pygame.draw.rect(screen, col, self.rect, border_radius=6)
        pygame.draw.rect(screen, T["div"], self.rect, 1, border_radius=6)
        fg = WHITE if (self.accent and en) else (T["text"] if en else T["muted"])
        img = font.render(self.label, True, fg)
        screen.blit(img, img.get_rect(center=self.rect.center))

    def click(self, pos):
        if self.enabled() and self.rect.collidepoint(pos):
            self.action()
            return True
        return False


# --------------------------------------------------------------------------
# Start menu: maze size 16..32, random/classic, seed box, dark mode.
# --------------------------------------------------------------------------
def show_menu(screen, clock, fonts, defaults):
    from algos import ALGOS, ALGO_ORDER

    font, small, big, banner = fonts
    size = defaults.get("size", 16)
    maze_kind = defaults.get("maze_kind", "random")
    seed_txt = "" if defaults.get("seed") is None else str(defaults["seed"])
    dark = defaults.get("dark", False)
    seed_focus = False
    picked = list(defaults.get("algos") or [defaults.get("algo", "flood")])
    picked = [a for a in ALGO_ORDER if a in picked] or ["flood"]

    def cfg():
        seed = int(seed_txt) if seed_txt.isdigit() else None
        ordered = [a for a in ALGO_ORDER if a in picked]
        return {"size": size, "maze_kind": maze_kind, "seed": seed, "dark": dark,
                "algos": ordered, "algo": ordered[0]}

    size_btns = [Button((0, 0, 0, 0), str(s), lambda: None) for s in SIZES]

    def _set_size(s):
        nonlocal size, maze_kind
        size = s
        if maze_kind == "simple":
            maze_kind = "random"  # classic layout only exists at 16

    for b, s in zip(size_btns, SIZES):
        b.action = (lambda s=s: _set_size(s))

    type_btns = [
        Button((0, 0, 0, 0), "Random (fresh)", lambda: _set_kind("random")),
        Button((0, 0, 0, 0), "Classic 16", lambda: _set_kind("simple")),
    ]

    def _set_kind(k):
        nonlocal maze_kind, size
        maze_kind = k
        if k == "simple":
            size = 16

    def _toggle_algo(key):
        nonlocal picked
        if key in picked:
            if len(picked) > 1:  # always keep at least one algorithm
                picked = [a for a in picked if a != key]
        else:
            picked = [a for a in ALGO_ORDER if a in (picked + [key])]

    algo_btns = []
    for _key in ALGO_ORDER:
        _b = Button((0, 0, 0, 0), "%s (%s)" % (ALGOS[_key].label,
                                               ALGOS[_key].menu_key),
                    lambda _k=_key: _toggle_algo(_k))
        _b.algo_key = _key
        algo_btns.append(_b)

    dark_btn = Button((0, 0, 0, 0), "Dark: OFF", lambda: _toggle_dark())

    def _toggle_dark():
        nonlocal dark
        dark = not dark
        dark_btn.label = "Dark: ON" if dark else "Dark: OFF"

    start_btn = Button((0, 0, 0, 0), "START RACE  (Enter)", lambda: None, accent=True)
    seed_box = pygame.Rect(0, 0, 0, 0)
    running, result = True, None

    while running:
        dt = clock.tick(60) / 1000.0  # noqa: F841 (keeps frame pacing stable)
        T = THEMES["dark" if dark else "light"]
        ww, hh = screen.get_size()
        mouse = pygame.mouse.get_pos()

        # layout: centered card, buttons positioned every frame (cheap)
        cw, ch = min(620, ww - 60), min(620, hh - 40)
        cx, cy = (ww - cw) // 2, (hh - ch) // 2
        y = cy + 24
        for i, b in enumerate(size_btns):
            bw = (cw - 48 - 4 * 8) // 5
            b.rect = pygame.Rect(cx + 24 + i * (bw + 8), y + 76, bw, 34)
        type_btns[0].rect = pygame.Rect(cx + 24, y + 138, (cw - 48 - 8) // 2, 34)
        type_btns[1].rect = pygame.Rect(cx + 24 + (cw - 48 - 8) // 2 + 8, y + 138,
                                        (cw - 48 - 8) // 2, 34)
        for i, b in enumerate(algo_btns):
            aw = (cw - 48 - 2 * 8) // 3
            b.rect = pygame.Rect(cx + 24 + i * (aw + 8), y + 198, aw, 34)
        seed_box = pygame.Rect(cx + 24, y + 258, 220, 32)
        dark_btn.rect = pygame.Rect(cx + 24 + 220 + 12, y + 258, cw - 48 - 232, 32)
        start_btn.rect = pygame.Rect(cx + 24, cy + ch - 70, cw - 48, 44)

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return None
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if seed_box.collidepoint(e.pos):
                    seed_focus = True
                else:
                    seed_focus = False
                    for b in size_btns + type_btns + algo_btns + [dark_btn]:
                        if b.click(e.pos):
                            break
                    else:
                        if start_btn.click(e.pos):
                            result = cfg()
                            running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    return None
                elif e.key == pygame.K_RETURN:
                    result = cfg()
                    running = False
                elif e.key == pygame.K_d:
                    _toggle_dark()
                elif e.key == pygame.K_r:
                    _set_kind("random")
                elif e.key == pygame.K_c:
                    _set_kind("simple")
                elif e.key == pygame.K_f and not seed_focus:
                    _toggle_algo("flood")
                elif e.key == pygame.K_t and not seed_focus:
                    _toggle_algo("dfs")
                elif e.key == pygame.K_w and not seed_focus:
                    _toggle_algo("wall")
                elif seed_focus and e.key == pygame.K_BACKSPACE:
                    seed_txt = seed_txt[:-1]
                elif seed_focus and e.unicode.isdigit() and len(seed_txt) < 6:
                    seed_txt += e.unicode
                elif not seed_focus and e.unicode in "12345"[: len(SIZES)]:
                    _set_size(SIZES[int(e.unicode) - 1])

        # ---- draw ----
        screen.fill(T["bg"])
        card = pygame.Rect(cx, cy, cw, ch)
        pygame.draw.rect(screen, T["card"], card, border_radius=12)
        pygame.draw.rect(screen, T["div"], card, 2, border_radius=12)
        screen.blit(banner.render("MARC Micromouse", True, T["text"]), (cx + 24, y))
        screen.blit(small.render("flood-fill explorer + A* optimizer  —  pick your race",
                                 True, T["muted"]), (cx + 24, y + 30))
        screen.blit(font.render("MAZE SIZE  (keys 1-5)", True, T["muted"]), (cx + 24, y + 56))
        for b in size_btns:
            b.accent = (int(b.label) == size)
            b.draw(screen, small, mouse, T)
        screen.blit(font.render("MAZE TYPE  (R random / C classic)", True, T["muted"]),
                    (cx + 24, y + 118))
        for b in type_btns:
            b.accent = ((b.label.startswith("Random") and maze_kind == "random") or
                        (b.label.startswith("Classic") and maze_kind == "simple"))
            b.draw(screen, small, mouse, T)
        screen.blit(font.render("ALGORITHMS  (F/T/W — race first, compare rest later)",
                                True, T["muted"]), (cx + 24, y + 178))
        for b in algo_btns:
            b.accent = (b.algo_key in picked)
            b.draw(screen, small, mouse, T)
        screen.blit(font.render("SEED  (empty = fresh maze every race)", True, T["muted"]),
                    (cx + 24, y + 238))
        pygame.draw.rect(screen, T["btn"], seed_box, border_radius=6)
        pygame.draw.rect(screen, BTN_ACC if seed_focus else T["div"], seed_box,
                         2 if seed_focus else 1, border_radius=6)
        shown = seed_txt if (seed_txt or seed_focus) else "random"
        screen.blit(font.render(shown, True, T["text"] if seed_txt else T["muted"]),
                    (seed_box.x + 10, seed_box.y + 8))
        dark_btn.draw(screen, small, mouse, T)
        screen.blit(font.render("HOW A RUN GOES", True, T["muted"]), (cx + 24, y + 300))
        for j, (dot, txt) in enumerate((
                ((220, 120, 40), "1 Explore — chosen algorithm learns walls cell by cell"),
                ((150, 100, 220), "2 Return — flood logic drives it back to start"),
                ((40, 160, 80), "3 Sprint — A* replays the shortest known route"))):
            pygame.draw.circle(screen, dot, (cx + 30, y + 322 + j * 20), 5)
            screen.blit(small.render(txt, True, T["text"]), (cx + 42, y + 316 + j * 20))
        screen.blit(small.render("SPACE step · R auto · T sprint · X new maze · D dark",
                                 True, T["muted"]), (cx + 24, cy + ch - 108))
        start_btn.draw(screen, font, mouse, T)
        pygame.display.flip()
    return result


# --------------------------------------------------------------------------
# Main loop (autonomous mouse + sidebar). Maze dims read from sim.true.
# --------------------------------------------------------------------------
def run_main(screen, clock, fonts, sim, cfg):
    font, small, big, banner = fonts
    W, H = sim.true.w, sim.true.h
    total_cells = W * H

    auto = True
    speed = 8.0
    show_numbers = True
    show_gradient = True
    show_explored = True
    show_path = True
    show_maze = True
    dark = cfg.get("dark", False)
    acc = 0.0
    show_compare = False  # comparison table overlay (C after a solved race)
    compare_rows = []  # clickable row rects, rebuilt every frame while open

    lay = {}  # ox/oy/px/cell/grid, recomputed when the window size changes
    last_size = None

    def cell_rect(x, y):
        return pygame.Rect(lay["ox"] + x * lay["cell"],
                           lay["oy"] + (H - 1 - y) * lay["cell"],
                           lay["cell"], lay["cell"])

    start_c = None
    anim_xy = [0.0, 0.0]
    arrow_ang = HEADING_ANG[sim.robot.heading]
    trail = deque(maxlen=24)
    bump_until = 0
    bump_cell = sim.pos
    discover_until = 0
    discover_walls = []
    flash_until = 0
    prev_phase = sim.phase

    px = 0
    buttons, toggle_rects, toggles = [], [], []

    def relayout():
        nonlocal px, buttons, toggle_rects, toggles, start_c
        ww, hh = screen.get_size()
        size = sim.true.w
        # Fill the window: grow cells on big/maximized screens (up to 64px),
        # shrink on small ones (down to 12px). Old cap of 40 left the maze
        # floating in empty space on maximized windows.
        cell = min(64, (hh - 60) // size, (ww - PANEL_W - 80) // size)
        cell = max(12, cell)
        grid = cell * size
        # Sidebar content needs ~666px vertically; never let the panel end up
        # shorter than its content (happens on small windows / big boards).
        panel_h = max(grid, 666)
        ox = max(8, (ww - (grid + PANEL_W + 40)) // 2)
        oy = max(8, (hh - panel_h) // 2)
        lay.update(cell=cell, grid=grid, ox=ox, oy=oy, panel_h=panel_h)
        px = ox + grid + 20

        bw = (PANEL_W - 16 - 8) // 2
        buttons = [
            Button((px, oy + 240, bw, 28), "Pause", toggle_auto),
            Button((px + bw + 8, oy + 240, bw, 28), "Step", do_step),
            Button((px, oy + 274, bw, 28), "Skip to A* (S)", do_skip, exploring),
            Button((px + bw + 8, oy + 274, bw, 28), "Speed Run (T)", do_speedrun,
                   can_speedrun, accent=True),
            Button((px, oy + 308, bw, 28), "New maze (X)", do_reset),
            Button((px + bw + 8, oy + 308, bw, 28), "Menu (B)", do_menu),
            Button((px, oy + 342, bw, 28), "Replay (Y)", do_replay),
            Button((px + bw + 8, oy + 342, bw, 28), "Compare (C)", do_compare,
                   can_compare, accent=True),
            Button((px, oy + 414, 70, 24), "- speed", lambda: None),
            Button((px + 78, oy + 414, 70, 24), "+ speed", lambda: None),
        ]
        buttons[8].action = speed_down
        buttons[9].action = speed_up
        toggle_rects[:] = [pygame.Rect(px + (i % 2) * ((PANEL_W - 16 + 8) // 2),
                                       oy + 474 + (i // 2) * 26,
                                       (PANEL_W - 16 - 8) // 2, 22)
                           for i in range(6)]
        if start_c is None:
            c = cell_rect(*sim.pos).center
            anim_xy[0], anim_xy[1] = float(c[0]), float(c[1])
            start_c = True

    def exploring():
        return sim.phase in ("EXPLORE_TO_GOAL", "RETURN_TO_START")

    def can_speedrun():
        return sim.phase == "OPTIMIZE" and bool(sim.optimal_path)

    def speed_down():
        nonlocal speed
        speed = max(1.0, speed - 1.0)

    def speed_up():
        nonlocal speed
        speed = min(30.0, speed + 1.0)

    def advance():
        nonlocal bump_until, bump_cell, discover_until, discover_walls
        before, steps_before = sim.pos, sim.steps
        explored_before = set(sim.explored)
        kv_before = [row[:] for row in sim.known.vwalls]
        kh_before = [row[:] for row in sim.known.hwalls]

        def had_wall(x, y, d):
            if d == "N":
                return kh_before[x][y + 1]
            if d == "S":
                return kh_before[x][y]
            if d == "E":
                return kv_before[x + 1][y]
            return kv_before[x][y]

        if sim.phase == "SPEEDRUN":
            sim.step_speedrun()
        elif exploring():
            sim.step()
        else:
            return False
        if sim.pos != before:
            r = cell_rect(*before).center
            if sim.phase == "SPEEDRUN":
                kind = "sprint"
            elif sim.pos in explored_before:
                kind = "backtrack"
            else:
                kind = "explore"
            trail.append((r[0], r[1], kind))
            nx, ny = sim.pos
            new_w = []
            for cx in range(max(0, nx - 1), min(W, nx + 2)):
                for cy in range(max(0, ny - 1), min(H, ny + 2)):
                    for d in ("N", "S", "E", "W"):
                        if sim.known.has_wall(cx, cy, d) and not had_wall(cx, cy, d):
                            new_w.append((cx, cy, d))
            if new_w:
                discover_walls = new_w
                discover_until = pygame.time.get_ticks() + 650
            return True
        if sim.steps != steps_before:
            bump_until = pygame.time.get_ticks() + 450
            bump_cell = before
        return False

    def toggle_auto():
        nonlocal auto
        auto = not auto

    def do_step():
        advance()

    def do_skip():
        if exploring():
            for _ in range(20000):
                if not exploring():
                    break
                advance()

    def do_speedrun():
        nonlocal auto
        if can_speedrun():
            sim.start_speedrun()
            auto = True

    def do_menu():
        """Leave the race and go back to the start menu (state is discarded)."""
        nonlocal running, result
        result = "menu"
        running = False

    def can_compare():
        return sim.phase in ("OPTIMIZE", "DONE")

    def _after_fresh_start():
        """Resync view animation with a freshly reset sim (replay/load/new)."""
        nonlocal auto, acc, arrow_ang, prev_phase
        trail.clear()
        discover_walls.clear()
        c = cell_rect(*sim.pos).center
        anim_xy[0], anim_xy[1] = float(c[0]), float(c[1])
        arrow_ang = HEADING_ANG[sim.robot.heading]
        prev_phase = sim.phase
        auto = True
        acc = 0.0

    def do_reset():
        nonlocal W, H, total_cells, show_compare
        from mazes.random_maze import generate_random_maze
        if cfg.get("maze_kind") == "simple":
            sim.reset()
        else:
            sim.reset(generate_random_maze(size=W))
        W, H = sim.true.w, sim.true.h
        total_cells = W * H
        show_compare = False
        compare_rows.clear()
        _after_fresh_start()

    def do_replay():
        """Replay the SAME maze with the SAME algorithm (X deals a fresh one)."""
        nonlocal show_compare
        sim.set_algorithm(sim.algorithm)
        show_compare = False
        compare_rows.clear()
        _after_fresh_start()

    def do_compare():
        """Race every menu-selected algorithm on THIS maze (fresh sims, so the
        watched race is untouched) and show the comparison table."""
        nonlocal show_compare
        if sim.phase not in ("OPTIMIZE", "DONE"):
            return
        if not show_compare and not sim.compare_results:
            from simulator import Simulator
            names = list(cfg.get("algos") or [])
            if len(names) < 2:
                names = list(ALGO_ORDER)
            sim.compare_results = [Simulator(sim.true, algorithm=n).run_to_completion(n)
                                   for n in names]
        show_compare = not show_compare

    def do_load(i):
        """Load comparison row i: same maze, that algorithm, auto-run it."""
        nonlocal show_compare
        if not sim.compare_results or not (0 <= i < len(sim.compare_results)):
            return
        sim.set_algorithm(sim.compare_results[i]["algo"])
        show_compare = False
        compare_rows.clear()
        _after_fresh_start()

    def toggle_setting(i):
        nonlocal show_numbers, show_gradient, show_explored, show_path
        nonlocal show_maze, dark
        if i == 0:
            show_numbers = not show_numbers
        elif i == 1:
            show_gradient = not show_gradient
        elif i == 2:
            show_explored = not show_explored
        elif i == 3:
            show_path = not show_path
        elif i == 4:
            show_maze = not show_maze
        elif i == 5:
            dark = not dark

    toggles = [
        ("Numbers (N)", lambda: show_numbers),
        ("Gradient (G)", lambda: show_gradient),
        ("Explored (E)", lambda: show_explored),
        ("A* path (P)", lambda: show_path),
        ("Maze ghost (M)", lambda: show_maze),
        ("Dark mode (D)", lambda: dark),
    ]
    run_btn = step_btn = None
    num_font_cache = {}  # fs -> SysFont, for cell-size-scaled distance numbers
    running = True
    result = "quit"  # do_menu() flips this to "menu" to return to start menu

    relayout()
    run_btn, step_btn = buttons[0], buttons[1]
    last_size = screen.get_size()

    while running:
        dt = clock.tick(60) / 1000.0
        now = pygame.time.get_ticks()
        if screen.get_size() != last_size:
            last_size = screen.get_size()
            relayout()
            run_btn, step_btn = buttons[0], buttons[1]
        T = THEMES["dark" if dark else "light"]
        path_col = PATH_DARK if dark else PATH_GREEN
        cell = lay["cell"]
        SC = cell / 40.0  # scale robot/trail/widths with zoom level
        W, H = sim.true.w, sim.true.h
        ox, oy, grid = lay["ox"], lay["oy"], lay["grid"]
        mouse = pygame.mouse.get_pos()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if show_compare and any(r.collidepoint(e.pos) for r in compare_rows):
                    for i, r in enumerate(compare_rows):
                        if r.collidepoint(e.pos):
                            do_load(i)
                            break
                else:
                    for b in buttons:
                        if b.click(e.pos):
                            break
                    else:
                        for i, r in enumerate(toggle_rects):
                            if r.collidepoint(e.pos):
                                toggle_setting(i)
                                break
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    running = False
                elif e.key == pygame.K_SPACE:
                    do_step()
                elif e.key == pygame.K_r:
                    toggle_auto()
                elif e.key == pygame.K_s:
                    do_skip()
                elif e.key == pygame.K_t:
                    do_speedrun()
                elif e.key == pygame.K_x:
                    do_reset()
                elif e.key == pygame.K_y:
                    do_replay()
                elif e.key == pygame.K_c:
                    do_compare()
                elif e.key in (pygame.K_1, pygame.K_2, pygame.K_3) and show_compare:
                    do_load(e.key - pygame.K_1)
                elif e.key == pygame.K_b:
                    do_menu()
                elif e.key == pygame.K_n:
                    show_numbers = not show_numbers
                elif e.key == pygame.K_g:
                    show_gradient = not show_gradient
                elif e.key == pygame.K_e:
                    show_explored = not show_explored
                elif e.key == pygame.K_p:
                    show_path = not show_path
                elif e.key == pygame.K_m:
                    show_maze = not show_maze
                elif e.key == pygame.K_d:
                    dark = not dark
                elif e.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    speed_up()
                elif e.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    speed_down()

        # ---- autonomous stepping (speedrun sprints ~2x, min 12 steps/s) ----
        run_btn.label = "Pause (R)" if auto else "Run (R)"
        step_btn.label = "Step (Spc)"
        if sim.phase == "OPTIMIZE" and prev_phase != "OPTIMIZE":
            flash_until = now + 4000
        prev_phase = sim.phase
        if auto:
            eff = min(30.0, max(speed * 2.0, 12.0)) if sim.phase == "SPEEDRUN" else speed
            interval = 1.0 / eff
            acc += dt
            while acc >= interval:
                acc -= interval
                if sim.phase == "SPEEDRUN":
                    advance()
                    if sim.phase != "SPEEDRUN":
                        auto = False
                        break
                elif exploring():
                    advance()
                    if sim.phase == "OPTIMIZE":
                        acc = 0.0
                        break
                else:
                    acc = 0.0
                    break

        # ---- smooth glide toward the robot's cell (no teleporting) ----
        tgt = cell_rect(*sim.pos).center
        k = min(1.0, dt * (4.0 + speed * 1.2))
        anim_xy[0] += (tgt[0] - anim_xy[0]) * k
        anim_xy[1] += (tgt[1] - anim_xy[1]) * k
        if abs(tgt[0] - anim_xy[0]) < 0.5 and abs(tgt[1] - anim_xy[1]) < 0.5:
            anim_xy[0], anim_xy[1] = float(tgt[0]), float(tgt[1])

        # ---- arrow sweep (shortest arc, no snapping) ----
        target_ang = HEADING_ANG[sim.robot.heading]
        diff = (target_ang - arrow_ang + math.pi) % (2 * math.pi) - math.pi
        max_turn = 12.0 * dt
        arrow_ang += max(-max_turn, min(max_turn, diff))

        # ---- draw ----
        screen.fill(T["bg"])
        panel_h = lay.get("panel_h", grid)
        pygame.draw.rect(screen, T["panel"], (px - 8, oy, PANEL_W, panel_h))
        pygame.draw.rect(screen, T["div"], (px - 8, oy, PANEL_W, panel_h), 1)

        dmax = 0
        for yy in range(H):
            for xx in range(W):
                d = sim.dist[xx][yy]
                if d < INF:
                    dmax = max(dmax, d)

        show_num_eff = show_numbers and cell >= 16
        num_font = font
        if show_num_eff:
            # Font scales with zoom: 18px on huge cells, 8px on 32x32 boards.
            # Cached per size (creating a SysFont every frame would stutter).
            fs = max(8, min(18, cell * 13 // 40))
            num_font = num_font_cache.get(fs)
            if num_font is None:
                num_font = pygame.font.SysFont("consolas", fs)
                num_font_cache[fs] = num_font
        wall_w = 3 if cell >= 24 else 2
        for yy in range(H):
            for xx in range(W):
                r = cell_rect(xx, yy)
                if (xx, yy) in sim.goals:
                    pygame.draw.rect(screen, T["goal"], r)
                elif show_explored and (xx, yy) in sim.explored:
                    pygame.draw.rect(screen, T["explored"], r)
                    if show_gradient and sim.dist[xx][yy] < INF:
                        pygame.draw.rect(screen, dist_color(sim.dist[xx][yy], dmax,
                                                            T["explored"]), r)
                else:
                    pygame.draw.rect(screen, T["cell"], r)
                if show_num_eff and sim.dist[xx][yy] < INF and (xx, yy) in sim.explored:
                    img = num_font.render(str(sim.dist[xx][yy]), True, T["text"])
                    screen.blit(img, img.get_rect(center=r.center))
                pygame.draw.rect(screen, T["grid"], r, 1)

        sprinting = sim.phase == "SPEEDRUN"
        if show_path and sim.optimal_path:
            pts = [cell_rect(x, y).center for x, y in sim.optimal_path]
            pw = max(2, int(4 * SC + (2 if sprinting and
                                      abs(math.sin(now / 180.0)) > 0.5 else 0)))
            if len(pts) > 1:
                if sprinting:
                    pygame.draw.lines(screen, (255, 150, 60), False, pts, pw + 5)
                pygame.draw.lines(screen, path_col, False, pts, pw)
            for p in pts:
                pygame.draw.circle(screen, path_col, p, max(3, int(7 * SC)))

        TRAIL_COLS = {"explore": ROBOT_BLUE, "sprint": (255, 140, 50),
                      "backtrack": BACKTRACK_RED}
        n_trail = len(trail)
        for i, (tx, ty, kind) in enumerate(trail):
            f = (i + 1) / max(1, n_trail)
            rad = max(1, int((2 + 4 * f) * SC) + (1 if kind == "backtrack" else 0))
            pygame.draw.circle(screen, TRAIL_COLS.get(kind, ROBOT_BLUE),
                               (int(tx), int(ty)), rad)

        for yy in range(H):
            for xx in range(W):
                r = cell_rect(xx, yy)
                if show_maze:
                    if sim.true.has_wall(xx, yy, "N"):
                        pygame.draw.line(screen, T["ghost"], r.topright, r.topleft, wall_w)
                    if sim.true.has_wall(xx, yy, "S"):
                        pygame.draw.line(screen, T["ghost"], r.bottomright, r.bottomleft, wall_w)
                    if sim.true.has_wall(xx, yy, "E"):
                        pygame.draw.line(screen, T["ghost"], r.topright, r.bottomright, wall_w)
                    if sim.true.has_wall(xx, yy, "W"):
                        pygame.draw.line(screen, T["ghost"], r.topleft, r.bottomleft, wall_w)
                if (xx, yy) in sim.explored:
                    if sim.known.has_wall(xx, yy, "N"):
                        pygame.draw.line(screen, T["wall"], r.topright, r.topleft, wall_w)
                    if sim.known.has_wall(xx, yy, "S"):
                        pygame.draw.line(screen, T["wall"], r.bottomright, r.bottomleft, wall_w)
                    if sim.known.has_wall(xx, yy, "E"):
                        pygame.draw.line(screen, T["wall"], r.topright, r.bottomright, wall_w)
                    if sim.known.has_wall(xx, yy, "W"):
                        pygame.draw.line(screen, T["wall"], r.topleft, r.bottomleft, wall_w)
        pygame.draw.rect(screen, T["wall"], (ox - 2, oy - 2, grid + 4, grid + 4), 3)

        # ---- robot ----
        rc = (int(anim_xy[0]), int(anim_xy[1]))
        R = max(6, int(13 * SC))
        AL = max(7, int(12 * SC))
        rcol = ROBOT_SPRINT if sprinting else ROBOT_BLUE
        if sprinting:
            pygame.draw.circle(screen, (255, 150, 60), rc, R + 4)
        pygame.draw.circle(screen, rcol, rc, R)
        pygame.draw.circle(screen, WHITE, rc, R, 2)
        ex = rc[0] + AL * math.cos(arrow_ang)
        ey = rc[1] + AL * math.sin(arrow_ang)
        pygame.draw.line(screen, WHITE, rc, (ex, ey), 3)
        for a in (arrow_ang + 2.6, arrow_ang - 2.6):
            pygame.draw.line(screen, WHITE, (ex, ey),
                             (ex - max(4, int(5 * SC)) * math.cos(a),
                              ey - max(4, int(5 * SC)) * math.sin(a)), 2)
        if sprinting:
            for off in (-8, 0, 8):
                so = int(off * SC) if SC < 1 else off
                if sim.robot.heading in ("E", "W"):
                    s = -1 if sim.robot.heading == "E" else 1
                    pygame.draw.line(screen, (255, 170, 90),
                                     (rc[0] + s * (R + 1), rc[1] + so),
                                     (rc[0] + s * (R + 13), rc[1] + so), 2)
                else:
                    s = 1 if sim.robot.heading == "N" else -1
                    pygame.draw.line(screen, (255, 170, 90),
                                     (rc[0] + so, rc[1] + s * (R + 1)),
                                     (rc[0] + so, rc[1] + s * (R + 13)), 2)

        if now < bump_until:
            prog = 1.0 - (bump_until - now) / 450.0
            bc = cell_rect(*bump_cell).center
            pygame.draw.circle(screen, BUMP_RED, bc, int((10 + 18 * prog) * max(SC, 0.7)), 3)

        if now < discover_until and discover_walls:
            fade = (discover_until - now) / 650.0
            w = 2 + int(3 * fade)
            for (cx, cy, d) in discover_walls:
                r = cell_rect(cx, cy)
                seg = {"N": (r.topright, r.topleft),
                       "S": (r.bottomright, r.bottomleft),
                       "E": (r.topright, r.bottomright),
                       "W": (r.topleft, r.bottomleft)}[d]
                pygame.draw.line(screen, DISCOVER_GOLD, seg[0], seg[1], w)
            pygame.draw.rect(screen, DISCOVER_GOLD, cell_rect(*sim.pos), 2)

        if sprinting:
            vpulse = abs(math.sin(now / 200.0))
            pygame.draw.rect(screen, (255, 120, 40),
                             (ox - 6, oy - 6, grid + 12, grid + 12),
                             3 + int(4 * vpulse), border_radius=4)

        # ---- banners ----
        def grid_banner(text, sub, pulse_col):
            tw = min(460, grid - 30)
            rect = pygame.Rect(ox + (grid - tw) // 2, oy + 12, tw, 52)
            pulse = abs(math.sin(now / 220.0))
            fill = tuple(min(255, int(c * (0.85 + 0.3 * pulse))) for c in pulse_col)
            pygame.draw.rect(screen, fill, rect, border_radius=10)
            pygame.draw.rect(screen, WHITE, rect, 2, border_radius=10)
            img = banner.render(text, True, WHITE)
            screen.blit(img, img.get_rect(center=(rect.centerx, rect.centery - 9)))
            img2 = small.render(sub, True, WHITE)
            screen.blit(img2, img2.get_rect(center=(rect.centerx, rect.centery + 13)))

        if sprinting:
            grid_banner("SPEEDRUN — SPRINTING THE OPTIMUM", "fastest known route, full speed",
                        (200, 50, 40))
        elif sim.phase == "DONE":
            grid_banner("DONE — OPTIMAL REPLAY COMPLETE", "press X for a fresh random maze",
                        (70, 130, 80))
        elif now < flash_until and sim.phase == "OPTIMIZE":
            grid_banner("SHORTEST PATH FOUND", "press T (or Speed Run) to sprint it",
                        (40, 150, 80))

        # ---- comparison overlay (same maze, every selected algorithm) ----
        compare_rows.clear()
        if show_compare and sim.compare_results:
            rows = sim.compare_results
            tw = min(560, grid - 30)
            rh = 30
            th = 100 + len(rows) * (rh + 6)
            rect = pygame.Rect(ox + (grid - tw) // 2, oy + (grid - th) // 2, tw, th)
            pygame.draw.rect(screen, (8, 8, 12), rect.inflate(8, 8), border_radius=12)
            pygame.draw.rect(screen, T["panel"], rect, border_radius=10)
            pygame.draw.rect(screen, path_col, rect, 2, border_radius=10)
            title = font.render("SAME MAZE — ALGORITHM SHOOTOUT", True, T["text"])
            screen.blit(title, title.get_rect(center=(rect.centerx, rect.y + 20)))
            sub = small.render("to-goal: steps at first arrival · walk: full explore+return",
                               True, T["muted"])
            screen.blit(sub, sub.get_rect(center=(rect.centerx, rect.y + 40)))
            for i, row in enumerate(rows):
                rr = pygame.Rect(rect.x + 16, rect.y + 58 + i * (rh + 6), tw - 32, rh)
                hov = rr.collidepoint(mouse)
                pygame.draw.rect(screen, T["btn_hov"] if hov else T["btn"], rr,
                                 border_radius=6)
                pygame.draw.rect(screen, T["div"], rr, 1, border_radius=6)
                goal = str(row["to_goal"]) if row["to_goal"] is not None else "—"
                mark = "STUCK" if row["stuck"] else "ok"
                txt = "%d. %-14s goal:%-5s walk:%-5s opt:%-4s %s" % (
                    i + 1, row["label"][:14], goal, row["walk"],
                    row["optimal"], mark)
                img = small.render(txt, True, BACKTRACK_RED if row["stuck"] else T["text"])
                screen.blit(img, (rr.x + 8, rr.y + 8))
                compare_rows.append(rr)
            hint = small.render("click a row or press 1-%d to replay it · C closes" % len(rows),
                                True, T["muted"])
            screen.blit(hint, hint.get_rect(center=(rect.centerx, rect.bottom - 12)))

        # ---- sidebar ----
        screen.blit(big.render("MARC Micromouse", True, T["text"]), (px, oy + 12))
        screen.blit(small.render("%s explorer + A*  ·  %dx%d" % (
            ALGOS[sim.algorithm].label, W, H), True, T["muted"]), (px, oy + 36))
        pcol = PHASE_COLORS.get(sim.phase, T["text"])
        badge = pygame.Rect(px, oy + 56, PANEL_W - 16, 30)
        pygame.draw.rect(screen, pcol, badge, border_radius=6)
        img = font.render(
            f"{'● RUNNING' if auto and exploring() or sprinting and auto else '○ PAUSED'}"
            f"  |  {sim.phase}{' · STUCK' if sim.stuck else ''}", True, WHITE)
        screen.blit(img, img.get_rect(center=badge.center))

        stats = [
            f"Steps: {sim.steps}",
            f"Explored: {len(sim.explored)}/{total_cells}",
            f"Flood walk: {sim.flood_len if sim.flood_len else '…'}",
            f"A* optimal: {sim.astar_len if sim.optimal_path else '…'}",
            f"Pos: {sim.pos}  hd:{sim.robot.heading}",
            f"Speed: {speed:.0f} steps/s{' x2 SPRINT' if sprinting else ''}",
        ]
        y0 = oy + 94
        for s in stats:
            screen.blit(font.render(s, True, T["text"]), (px, y0))
            y0 += 20
        pygame.draw.line(screen, T["div"], (px, oy + 222), (px + PANEL_W - 16, oy + 222), 1)
        screen.blit(font.render("CONTROLS", True, T["muted"]), (px, oy + 226))
        for b in buttons[:8]:
            b.draw(screen, small, mouse, T)

        screen.blit(font.render("SETTINGS", True, T["muted"]), (px, oy + 378))
        screen.blit(font.render(f"Speed: {speed:.0f} steps/s  ([-]/[+])", True, T["text"]),
                    (px, oy + 396))
        for b in buttons[8:]:
            b.draw(screen, small, mouse, T)
        screen.blit(small.render("Auto-run is ON at launch. SPACE steps,", True, T["muted"]),
                    (px, oy + 444))
        screen.blit(small.render("R pauses. B menu. D dark. Toggles:", True, T["muted"]),
                    (px, oy + 458))
        for i, (label, get) in enumerate(toggles):
            r = toggle_rects[i]
            on = get()
            hov = r.collidepoint(mouse)
            pygame.draw.rect(screen, T["btn_hov"] if hov else T["btn"], r, border_radius=6)
            pygame.draw.rect(screen, T["div"] if not on else path_col, r, 2 if on else 1,
                             border_radius=6)
            dot = "◉ " if on else "○ "
            screen.blit(small.render(dot + label, True, T["text"]), (r.x + 8, r.y + 4))

        # trail key (moved out of the grid overlay into the sidebar)
        screen.blit(font.render("TRAIL KEY", True, T["muted"]), (px, oy + 550))
        tx = px
        for label, col in (("explore", ROBOT_BLUE), ("revisit", BACKTRACK_RED),
                           ("sprint", (255, 140, 50))):
            pygame.draw.circle(screen, col, (tx + 4, oy + 570), 4)
            img = small.render(label, True, T["text"])
            screen.blit(img, (tx + 11, oy + 564))
            tx += 11 + img.get_width() + 16

        # flood-gradient key: live swatches + what the shades mean right now
        screen.blit(font.render("FLOOD KEY — distance to target", True, T["muted"]),
                    (px, oy + 590))
        nsw, bx0, by0 = 10, px, oy + 608
        sw = (PANEL_W - 16) // nsw
        for i in range(nsw):
            v = i * dmax / max(1, nsw - 1)
            pygame.draw.rect(screen, dist_color(v, dmax, T["explored"]),
                             (bx0 + i * sw, by0, sw + 1, 12))
        pygame.draw.rect(screen, T["div"], (bx0, by0, sw * nsw + 1, 12), 1)
        screen.blit(small.render("0 · at goal", True, T["text"]), (bx0, by0 + 14))
        lab = f"{dmax} · farthest known" if dmax else "no distances yet"
        img = small.render(lab, True, T["text"])
        screen.blit(img, (bx0 + sw * nsw + 1 - img.get_width(), by0 + 14))
        screen.blit(small.render("recomputed every step — shades shift as walls are found",
                                 True, T["muted"]), (px, oy + 640))

        screen.blit(small.render("ESC quit", True, T["muted"]),
                    (px, oy + lay.get("panel_h", grid) - 20))
        pygame.display.flip()
    return result


def _build_sim(cfg):
    from mazes.random_maze import generate_random_maze
    from mazes.simple_maze import build_simple_maze
    from simulator import Simulator
    algo = cfg.get("algo", "flood")
    if cfg.get("maze_kind") == "simple":
        return Simulator(build_simple_maze(), algorithm=algo)  # classic is 16x16
    return Simulator(generate_random_maze(cfg.get("seed"), size=cfg.get("size", 16)),
                     algorithm=algo)


def run_2d(sim=None, maze_kind="random", size=16, seed=None, dark_init=False,
           use_menu=True, algo="flood"):
    """Entry point for 2D mode. Loops menu -> race -> menu until quit."""
    pygame.init()
    pygame.display.set_caption("MARC Micromouse — 2D (autonomous)")
    screen = pygame.display.set_mode((1280, 800), pygame.RESIZABLE)
    _maximize_window()
    clock = pygame.time.Clock()
    fonts = (pygame.font.SysFont("consolas", 13),
             pygame.font.SysFont("consolas", 12),
             pygame.font.SysFont("consolas", 17, bold=True),
             pygame.font.SysFont("consolas", 20, bold=True))
    cfg = {"size": size, "maze_kind": maze_kind, "seed": seed, "dark": dark_init,
           "algos": [algo], "algo": algo}
    show_it = use_menu
    while True:
        if show_it:
            picked = show_menu(screen, clock, fonts, cfg)
            if picked is None:
                break  # window closed / ESC on menu -> quit app
            cfg = picked
            sim = None  # fresh race from the new menu choices
        if sim is None:
            sim = _build_sim(cfg)
        if run_main(screen, clock, fonts, sim, cfg) != "menu":
            break  # ESC / window close -> quit app
        show_it = True  # Menu button / B key -> back to start menu
    pygame.quit()
