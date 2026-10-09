#!/usr/bin/env python3
"""Top-down preview of generated nodes (needs matplotlib: pip install matplotlib).

Usage:
    python3 preview.py out/manifest.json -o preview.png
"""
import argparse
import json
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle

import generate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("-o", "--out", default="preview.png")
    args = ap.parse_args()

    with open(args.manifest) as fh:
        manifest = json.load(fh)

    fig, ax = plt.subplots(figsize=(8, 8), dpi=140)
    for n in manifest["nodes"]:
        x, z, pop = n["position"]["x"], n["position"]["z"], n["population"]
        scale = math.sqrt(max(pop, 1.0) / generate.REF_POP)
        if n["shape"] == "cylinder":
            r = max(generate.MIN_RADIUS, generate.BASE_RADIUS * scale)
            ax.add_patch(Circle((x, z), r, fc="#5b8dff", ec="#0b3aa8", lw=1.5))
        else:
            side = 2 * generate.BASE_RADIUS * scale
            for t in range(generate.tier_count(pop)):
                half = side / 2
                shade = 0.35 + 0.1 * t
                ax.add_patch(Rectangle((x - half, z - half), side, side,
                                       fc=(0.95, 0.5, 0.1, shade), ec="#9a4b00", lw=1.2))
                side *= generate.TIER_SHRINK
        ax.annotate(f"{n['name']}\n{int(pop):,}", (x, z), ha="center", va="center",
                    fontsize=6.5, color="black")

    ax.set_aspect("equal")
    ax.autoscale_view()
    ax.margins(0.12)
    ax.set_title("DynaMesh Studio - generator v0.1 (top view)\n"
                 "blue = cylinder (<1,000,000)   orange = tiered square (>=1,000,000)",
                 fontsize=10)
    ax.set_xlabel("x"); ax.set_ylabel("z")
    ax.grid(alpha=0.25)
    fig.savefig(args.out, bbox_inches="tight")
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
