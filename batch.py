"""batch.py — multi-seed algorithm shootout for report-grade evidence.

Races every explorer on the SAME random mazes (one immutable true maze per
seed, fresh Simulator per race — identical methodology to Compare (C) in the
GUI) and writes:
  results.csv   one row per race (size, seed, algo, metrics...)
  summary.json  means/stds, win counts, verdict
  fig_means.png grouped mean bars (to-goal, walk, compute time) with std bars
  fig_box.png   walk/optimal efficiency distribution per algo
  fig_wins.png  seeds won per algorithm
  fig_scale.png mean walk vs board size (only with multiple --sizes)

Usage:
  python batch.py                              # 100 seeds, 16x16 (~1 min)
  python batch.py --seeds 200 --sizes 16 24 32 # bigger evidence, slower
Seeds are 0..N-1, so any run is exactly reproducible.
"""
import argparse
import csv
import json
import os
import statistics
import sys

import matplotlib

matplotlib.use("Agg")  # headless: no display needed
import matplotlib.pyplot as plt  # noqa: E402  (after backend selection)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from algos import ALGO_ORDER, ALGOS  # noqa: E402
from mazes.random_maze import generate_random_maze  # noqa: E402
from simulator import Simulator  # noqa: E402

ALGO_COLORS = {
    "flood": "#3278dc",      # same accents as the app UI
    "dijkstra": "#2dbeaf",
    "dfs": "#9664dc",
}


def race_all(true_maze, algos):
    """Race each algorithm on one maze. Returns list of metric dicts."""
    out = []
    for name in algos:
        out.append(Simulator(true_maze, algorithm=name).run_to_completion(name))
    return out


def summarize(rows):
    """Aggregate per (size, algo): means, stds, wins. Returns nested dict."""
    per_key = {}
    for r in rows:
        per_key.setdefault((r["size"], r["algo"]), []).append(r)
    summary = {}
    for (size, algo), rs in sorted(per_key.items()):
        solved = [r for r in rs if not r["stuck"] and r["to_goal"] is not None]
        eff = [r["walk"] / r["optimal"] for r in rs if r["optimal"]]
        summary[f"{size}/{algo}"] = {
            "size": size, "algo": algo, "label": ALGOS[algo].label,
            "races": len(rs), "solved": len(solved),
            "stuck": sum(1 for r in rs if r["stuck"]),
            "mean_goal": statistics.mean([r["to_goal"] for r in solved]) if solved else None,
            "std_goal": statistics.stdev([r["to_goal"] for r in solved]) if len(solved) > 1 else 0.0,
            "mean_walk": statistics.mean([r["walk"] for r in rs]),
            "std_walk": statistics.stdev([r["walk"] for r in rs]) if len(rs) > 1 else 0.0,
            "mean_eff": statistics.mean(eff) if eff else None,
            "mean_time": statistics.mean([r["solve_time"] for r in rs]),
            "mean_explored": statistics.mean([r["explored"] for r in rs]),
        }
    # wins: fewest to-goal steps per seed (ties share the win)
    wins = {a: 0 for a in ALGO_ORDER}
    seeds = sorted({(r["size"], r["seed"]) for r in rows})
    for size, seed in seeds:
        cand = [(r["to_goal"], r["algo"]) for r in rows
                if r["size"] == size and r["seed"] == seed and r["to_goal"] is not None]
        if not cand:
            continue
        best = min(t for t, _ in cand)
        for t, a in cand:
            if t == best:
                wins[a] += 1
    return summary, wins, len(seeds)


def _labels(sizes):
    return ["%s\n%dx%d" % (ALGOS[a].label, s, s) for s in sizes for a in ALGO_ORDER]


def fig_means(summary, sizes, out):
    xs = list(range(len(sizes) * len(ALGO_ORDER)))
    mg = [summary[f"{s}/{a}"]["mean_goal"] or 0 for s in sizes for a in ALGO_ORDER]
    sg = [summary[f"{s}/{a}"]["std_goal"] for s in sizes for a in ALGO_ORDER]
    mw = [summary[f"{s}/{a}"]["mean_walk"] for s in sizes for a in ALGO_ORDER]
    sw = [summary[f"{s}/{a}"]["std_walk"] for s in sizes for a in ALGO_ORDER]
    mt = [summary[f"{s}/{a}"]["mean_time"] for s in sizes for a in ALGO_ORDER]
    cols = [ALGO_COLORS[a] for _ in sizes for a in ALGO_ORDER]
    fig, ax = plt.subplots(1, 3, figsize=(13, 4.2))
    ax[0].bar(xs, mg, yerr=sg, capsize=3, color=cols, edgecolor="black", linewidth=0.5)
    ax[0].set_title("Mean steps to first goal (±std)")
    ax[0].set_xticks(xs)
    ax[0].set_xticklabels(_labels(sizes), fontsize=7)
    ax[1].bar(xs, mw, yerr=sw, capsize=3, color=cols, edgecolor="black", linewidth=0.5)
    ax[1].set_title("Mean full walk incl. return (±std)")
    ax[1].set_xticks(xs)
    ax[1].set_xticklabels(_labels(sizes), fontsize=7)
    ax[2].bar(xs, mt, color=cols, edgecolor="black", linewidth=0.5)
    ax[2].set_title("Mean compute time, s (machine-dependent)")
    ax[2].set_xticks(xs)
    ax[2].set_xticklabels(_labels(sizes), fontsize=7)
    ax[2].set_yscale("log")
    fig.suptitle("Algorithm shootout — means over shared seeds (lower is better)")
    fig.tight_layout()
    fig.savefig(os.path.join(out, "fig_means.png"), dpi=130)
    plt.close(fig)


def fig_box(rows, sizes, out):
    n = len(sizes)
    fig, ax = plt.subplots(1, n, figsize=(4.2 * n + 1, 4.2), sharey=True)
    if n == 1:
        ax = [ax]
    for i, s in enumerate(sizes):
        data = [[r["walk"] / r["optimal"] for r in rows
                 if r["size"] == s and r["algo"] == a and r["optimal"]] for a in ALGO_ORDER]
        bp = ax[i].boxplot(data, tick_labels=[ALGOS[a].label for a in ALGO_ORDER],
                            patch_artist=True)
        for patch, a in zip(bp["boxes"], ALGO_ORDER):
            patch.set_facecolor(ALGO_COLORS[a])
        ax[i].set_title(f"{s}x{s}: walk / optimum")
        ax[i].axhline(1.0, color="black", linestyle="--", linewidth=1)
    fig.suptitle("Efficiency distribution (1.0 = optimal; lower is better)")
    fig.tight_layout()
    fig.savefig(os.path.join(out, "fig_box.png"), dpi=130)
    plt.close(fig)


def fig_wins(wins, nseeds, out):
    names = [ALGOS[a].label for a in ALGO_ORDER]
    vals = [wins[a] for a in ALGO_ORDER]
    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar(names, vals, color=[ALGO_COLORS[a] for a in ALGO_ORDER],
                  edgecolor="black", linewidth=0.5)
    ax.set_title(f"Seeds won per algorithm (fewest to-goal steps, n={nseeds})")
    ax.set_ylabel("seeds won (ties shared)")
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.5, str(v),
                ha="center", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "fig_wins.png"), dpi=130)
    plt.close(fig)


def fig_scale(summary, sizes, out):
    if len(sizes) < 2:
        return
    fig, ax = plt.subplots(figsize=(6, 4))
    for a in ALGO_ORDER:
        ys = [summary[f"{s}/{a}"]["mean_walk"] for s in sizes]
        ax.plot([s * s for s in sizes], ys, "o-", color=ALGO_COLORS[a],
                label=ALGOS[a].label)
    ax.set_title("Mean full walk vs board cells")
    ax.set_xlabel("cells (size squared)")
    ax.set_ylabel("mean walk (steps)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out, "fig_scale.png"), dpi=130)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description="Multi-seed algorithm shootout.")
    ap.add_argument("--seeds", type=int, default=100)
    ap.add_argument("--sizes", type=int, nargs="+", default=[16])
    ap.add_argument("--out", default="batch_results")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    rows = []
    total = len(args.sizes) * args.seeds * len(ALGO_ORDER)
    done = 0
    for size in args.sizes:
        for seed in range(args.seeds):
            true_maze = generate_random_maze(seed, size=size)
            for r in race_all(true_maze, ALGO_ORDER):
                rows.append({"size": size, "seed": seed, **r})
                done += 1
            if (seed + 1) % 20 == 0 or seed == args.seeds - 1:
                print(f"  size {size}: {seed + 1}/{args.seeds} mazes "
                      f"({done}/{total} races)", flush=True)

    # history traces are for the in-app dashboard; too big for CSV
    for r in rows:
        r.pop("history", None)
    with open(os.path.join(args.out, "results.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["size", "seed", "algo", "to_goal", "walk",
                                          "return_steps", "optimal", "solve_time",
                                          "stuck", "explored", "bumps", "revisits",
                                          "deadends", "finished"])
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if v is None else v) for k, v in r.items()
                        if k in w.fieldnames})

    summary, wins, nseeds = summarize(rows)
    order = sorted(ALGO_ORDER,
                   key=lambda a: sum(summary[f"{s}/{a}"]["mean_goal"] or 10 ** 9
                                     for s in args.sizes))
    means = ", ".join(f"{ALGOS[a].label} {sum(summary[f'{s}/{a}']['mean_goal'] or 0 for s in args.sizes) / len(args.sizes):.1f}"
                      for a in order)
    wsplit = "/".join(str(wins[a]) for a in ALGO_ORDER)
    verdict = (f"{ALGOS[order[0]].label} is the pick: lowest mean to-goal "
               f"({means}) over {nseeds} shared seeds; seed wins "
               f"flood/dijkstra/dfs = {wsplit} (ties shared — flood and "
               f"Dijkstra tie outright wherever their greedy cores agree).")
    with open(os.path.join(args.out, "summary.json"), "w") as f:
        json.dump({"seeds": args.seeds, "sizes": args.sizes, "summary": summary,
                   "wins": wins, "verdict": verdict}, f, indent=2)

    fig_means(summary, args.sizes, args.out)
    fig_box(rows, args.sizes, args.out)
    fig_wins(wins, nseeds, args.out)
    fig_scale(summary, args.sizes, args.out)

    print("\n== per board / algo: mean_goal ± std | mean_walk | wins ==")
    for s in args.sizes:
        for a in ALGO_ORDER:
            d = summary[f"{s}/{a}"]
            g = "—" if d["mean_goal"] is None else f"{d['mean_goal']:.1f}±{d['std_goal']:.1f}"
            print(f"  {s}x{s} {d['label']:14s} goal {g:>14s}  "
                  f"walk {d['mean_walk']:.1f}  eff {d['mean_eff']:.2f}x")
    print(f"\nwins: { {ALGOS[a].label: wins[a] for a in ALGO_ORDER} }")
    print("VERDICT:", verdict)
    print(f"wrote {args.out}/results.csv, summary.json, fig_*.png")


if __name__ == "__main__":
    main()
