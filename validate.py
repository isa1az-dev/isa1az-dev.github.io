"""Mesh validation for DynaMesh Studio generator (v0.1).

Checks that each mesh is a sound, closed, outward-facing triangle mesh:
  - face indices are in range
  - no degenerate (zero-area) triangles
  - every edge is shared by exactly two faces with opposite direction
    (closed and consistently oriented)
  - total signed volume is positive (normals point outward)
"""
from __future__ import annotations

from collections import Counter

EPS = 1e-9


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def triangle_area(v0, v1, v2) -> float:
    c = _cross(_sub(v1, v0), _sub(v2, v0))
    return 0.5 * (c[0] ** 2 + c[1] ** 2 + c[2] ** 2) ** 0.5


def signed_volume(mesh) -> float:
    total = 0.0
    for a, b, c in mesh.faces:
        v0, v1, v2 = mesh.vertices[a], mesh.vertices[b], mesh.vertices[c]
        total += _dot(v0, _cross(v1, v2)) / 6.0
    return total


def validate_mesh(mesh) -> list[str]:
    problems: list[str] = []
    n = len(mesh.vertices)

    if n == 0 or not mesh.faces:
        return ["mesh is empty"]

    for i, face in enumerate(mesh.faces):
        if any(idx < 0 or idx >= n for idx in face):
            problems.append(f"face {i} has an out-of-range vertex index")
    if problems:
        return problems   # later checks would crash on bad indices

    for i, (a, b, c) in enumerate(mesh.faces):
        if triangle_area(mesh.vertices[a], mesh.vertices[b], mesh.vertices[c]) < EPS:
            problems.append(f"face {i} is degenerate (zero area)")

    directed = Counter()
    for a, b, c in mesh.faces:
        directed[(a, b)] += 1
        directed[(b, c)] += 1
        directed[(c, a)] += 1
    for (a, b), count in directed.items():
        if count != 1:
            problems.append(f"edge {a}->{b} used {count} times (expected 1)")
        elif directed.get((b, a), 0) != 1:
            problems.append(f"edge {a}->{b} has no matching opposite edge (open or flipped)")
    if len(problems) > 10:
        problems = problems[:10] + ["... more edge problems omitted"]

    if signed_volume(mesh) <= EPS:
        problems.append("signed volume is not positive (faces point inward)")

    return problems
