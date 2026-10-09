#!/usr/bin/env python3
"""DynaMesh Studio - first procedural node generator (v0.1).

Reads a list of nodes (name, population, x, z) and builds one mesh per node:

    population <  1,000,000  ->  optimized cylinder
    population >= 1,000,000  ->  tiered square ("mega-node") geometry

Outputs a Wavefront OBJ file and a JSON manifest, and validates every mesh
before writing anything. Standard library only.

Usage:
    python3 generate.py nodes.json -o out/
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from dataclasses import dataclass, field

from validate import validate_mesh

# ---- Tunable rules ---------------------------------------------------------
MEGA_THRESHOLD = 1_000_000   # population at which a node becomes a mega-node
REF_POP = 100_000            # population that maps to BASE_RADIUS
BASE_RADIUS = 10.0           # cylinder radius at REF_POP (map units)
BASE_HEIGHT = 8.0            # cylinder height at REF_POP (map units)
MIN_RADIUS = 2.0
CYL_SEGMENTS = 12            # sides of each cylinder (low = optimized)
MAX_TIERS = 6
TIER_SHRINK = 0.7            # each tier is 70% of the one below it
# ---------------------------------------------------------------------------


@dataclass
class Node:
    id: str
    name: str
    population: float
    x: float
    z: float


@dataclass
class Mesh:
    name: str
    vertices: list = field(default_factory=list)   # (x, y, z); y is up
    faces: list = field(default_factory=list)      # (a, b, c) 0-based triangles

    def add_vertex(self, x: float, y: float, z: float) -> int:
        self.vertices.append((x, y, z))
        return len(self.vertices) - 1


# ---- Input -----------------------------------------------------------------
def load_nodes(path: str) -> list[Node]:
    with open(path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    if not isinstance(raw, list) or not raw:
        raise ValueError("Input must be a non-empty JSON list of nodes.")
    nodes, seen = [], set()
    for i, item in enumerate(raw):
        for key in ("id", "name", "population", "x", "z"):
            if key not in item:
                raise ValueError(f"Node #{i} is missing '{key}'.")
        pop = item["population"]
        if not isinstance(pop, (int, float)) or isinstance(pop, bool) or pop < 0:
            raise ValueError(f"Node '{item['id']}': population must be a number >= 0.")
        if item["id"] in seen:
            raise ValueError(f"Duplicate node id '{item['id']}'.")
        seen.add(item["id"])
        nodes.append(Node(str(item["id"]), str(item["name"]), float(pop),
                          float(item["x"]), float(item["z"])))
    return nodes


# ---- Shape rule ------------------------------------------------------------
def shape_for(population: float) -> str:
    return "cylinder" if population < MEGA_THRESHOLD else "tiered_square"


# ---- Geometry --------------------------------------------------------------
def build_cylinder(node: Node) -> Mesh:
    scale = math.sqrt(max(node.population, 1.0) / REF_POP)
    radius = max(MIN_RADIUS, BASE_RADIUS * scale)
    height = BASE_HEIGHT * (1.0 + math.log10(1.0 + node.population / REF_POP))
    mesh = Mesh(node.id)
    n = CYL_SEGMENTS
    bottom, top = [], []
    for i in range(n):
        t = 2.0 * math.pi * i / n
        px = node.x + radius * math.cos(t)
        pz = node.z + radius * math.sin(t)
        bottom.append(mesh.add_vertex(px, 0.0, pz))
        top.append(mesh.add_vertex(px, height, pz))
    bc = mesh.add_vertex(node.x, 0.0, node.z)
    tc = mesh.add_vertex(node.x, height, node.z)
    for i in range(n):
        j = (i + 1) % n
        mesh.faces.append((bottom[i], top[j], bottom[j]))   # side (outward)
        mesh.faces.append((bottom[i], top[i], top[j]))
        mesh.faces.append((tc, top[j], top[i]))              # top cap (+y)
        mesh.faces.append((bc, bottom[i], bottom[j]))        # bottom cap (-y)
    return mesh


def _add_box(mesh: Mesh, x0, x1, y0, y1, z0, z1) -> None:
    """Add one closed box with its own 8 vertices and 12 outward triangles."""
    v = [
        mesh.add_vertex(x0, y0, z0), mesh.add_vertex(x1, y0, z0),
        mesh.add_vertex(x1, y0, z1), mesh.add_vertex(x0, y0, z1),
        mesh.add_vertex(x0, y1, z0), mesh.add_vertex(x1, y1, z0),
        mesh.add_vertex(x1, y1, z1), mesh.add_vertex(x0, y1, z1),
    ]
    mesh.faces += [
        (v[0], v[1], v[2]), (v[0], v[2], v[3]),   # bottom (-y)
        (v[4], v[6], v[5]), (v[4], v[7], v[6]),   # top (+y)
        (v[0], v[4], v[5]), (v[0], v[5], v[1]),   # front (-z)
        (v[2], v[6], v[7]), (v[2], v[7], v[3]),   # back (+z)
        (v[0], v[3], v[7]), (v[0], v[7], v[4]),   # left (-x)
        (v[1], v[6], v[2]), (v[1], v[5], v[6]),   # right (+x)
    ]


def tier_count(population: float) -> int:
    extra = int(math.log10(max(population / MEGA_THRESHOLD, 1.0)) * 3)
    return min(MAX_TIERS, 3 + extra)


def build_tiered_square(node: Node) -> Mesh:
    scale = math.sqrt(node.population / REF_POP)
    side = 2.0 * BASE_RADIUS * scale
    tier_h = BASE_HEIGHT * 1.5
    mesh = Mesh(node.id)
    y = 0.0
    for _ in range(tier_count(node.population)):
        half = side / 2.0
        _add_box(mesh, node.x - half, node.x + half, y, y + tier_h,
                 node.z - half, node.z + half)
        y += tier_h
        side *= TIER_SHRINK
    return mesh


def build_node(node: Node) -> Mesh:
    if shape_for(node.population) == "cylinder":
        return build_cylinder(node)
    return build_tiered_square(node)


# ---- Output ----------------------------------------------------------------
def write_obj(meshes: list[Mesh], path: str) -> None:
    offset = 0
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# DynaMesh Studio generator v0.1\n")
        for mesh in meshes:
            fh.write(f"o {mesh.name}\n")
            for x, y, z in mesh.vertices:
                fh.write(f"v {x:.4f} {y:.4f} {z:.4f}\n")
            for a, b, c in mesh.faces:
                fh.write(f"f {a + offset + 1} {b + offset + 1} {c + offset + 1}\n")
            offset += len(mesh.vertices)


def make_manifest(nodes: list[Node], meshes: list[Mesh]) -> dict:
    entries = []
    for node, mesh in zip(nodes, meshes):
        entries.append({
            "id": node.id, "name": node.name, "population": node.population,
            "shape": shape_for(node.population),
            "position": {"x": node.x, "z": node.z},
            "vertices": len(mesh.vertices), "triangles": len(mesh.faces),
        })
    return {"generator": "dynamesh-v0.1", "mega_threshold": MEGA_THRESHOLD,
            "nodes": entries}


# ---- Main ------------------------------------------------------------------
def run(input_path: str, out_dir: str) -> int:
    nodes = load_nodes(input_path)
    meshes = [build_node(n) for n in nodes]

    problems = []
    for mesh in meshes:
        for p in validate_mesh(mesh):
            problems.append(f"{mesh.name}: {p}")
    if problems:
        print("Validation FAILED, nothing written:", file=sys.stderr)
        for p in problems:
            print("  - " + p, file=sys.stderr)
        return 1

    os.makedirs(out_dir, exist_ok=True)
    write_obj(meshes, os.path.join(out_dir, "map.obj"))
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(make_manifest(nodes, meshes), fh, indent=2)

    cyl = sum(1 for n in nodes if shape_for(n.population) == "cylinder")
    print(f"OK: {len(nodes)} nodes ({cyl} cylinders, {len(nodes) - cyl} mega-nodes)")
    print(f"Wrote {out_dir}/map.obj and {out_dir}/manifest.json")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="DynaMesh node generator")
    ap.add_argument("input", help="nodes JSON file")
    ap.add_argument("-o", "--out", default="out", help="output directory")
    args = ap.parse_args()
    try:
        return run(args.input, args.out)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
