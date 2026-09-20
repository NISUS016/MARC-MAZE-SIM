"""main.py — entry point.
python main.py --headless [--maze random|simple] [--size N] [--seed N] [--algo X]
python main.py --2d [--maze ...] [--size N] [--seed N] [--algo X] [--no-menu]
python main.py --3d ...   (3D skips the menu, uses CLI options)
Default: fresh RANDOM maze every run. --seed N reproduces one for the report.
"""
import argparse


def build_sim(maze="random", seed=None, size=16, algorithm="flood"):
    from mazes.random_maze import generate_random_maze
    from mazes.simple_maze import build_simple_maze
    from simulator import Simulator
    if maze == "simple":
        if size != 16:
            print(f"note: classic layout is 16x16; ignoring --size {size}")
        return Simulator(build_simple_maze(), algorithm=algorithm)
    return Simulator(generate_random_maze(seed, size=size), algorithm=algorithm)


def run_headless(maze, seed, size, algorithm):
    sim = build_sim(maze, seed, size, algorithm)
    while sim.phase not in ("OPTIMIZE", "DONE"):
        sim.step()
    print(f"maze       : {maze} {size}x{size} seed={seed} algo={algorithm}")
    print(f"phase      : {sim.phase}  stuck={sim.stuck}")
    print(f"steps taken: {sim.steps}")
    print(f"to goal    : {sim.steps_to_goal}")
    print(f"cells explored: {len(sim.explored)}/{size * size}")
    print(f"flood exploration path len: {sim.flood_len}")
    print(f"A* optimal path len       : {sim.astar_len}")
    if not sim.stuck:
        assert sim.astar_len > 0, "A* must find a path on complete map"
        assert sim.astar_len <= sim.flood_len, "optimal <= exploration walk"
        print("OK: reached goal + returned; A* shorter or equal.")
    else:
        print("NOTE: explorer got stuck (expected for wall-follower on loopy mazes).")


def main():
    ap = argparse.ArgumentParser(description="MARC Micromouse Simulator")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--headless", action="store_true")
    g.add_argument("--2d", dest="two_d", action="store_true")
    g.add_argument("--3d", dest="three_d", action="store_true")
    ap.add_argument("--maze", choices=["random", "simple"], default="random",
                    help="random = fresh every run (default); simple = fixed demo")
    ap.add_argument("--size", type=int, default=16, choices=[16, 20, 24, 28, 32],
                    help="maze size (default 16; start menu can change it in --2d)")
    ap.add_argument("--seed", type=int, default=None,
                    help="reproduce a maze, e.g. --seed 7")
    ap.add_argument("--algo", choices=["flood", "dfs", "wall"], default="flood",
                    help="explorer algorithm (default flood)")
    ap.add_argument("--no-menu", action="store_true",
                    help="skip the start menu in --2d, use CLI options directly")
    args = ap.parse_args()
    if args.headless:
        run_headless(args.maze, args.seed, args.size, args.algo)
    elif args.two_d:
        from view_2d import run_2d
        run_2d(maze_kind=args.maze, size=args.size, seed=args.seed,
               use_menu=not args.no_menu, algo=args.algo)
    elif args.three_d:
        from view_3d import run_3d
        run_3d(build_sim(args.maze, args.seed, args.size))


if __name__ == "__main__":
    main()
