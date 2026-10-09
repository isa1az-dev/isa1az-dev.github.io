import json
import os
import tempfile
import unittest

import generate
from generate import Node, build_node, shape_for, MEGA_THRESHOLD
from validate import validate_mesh, signed_volume


def node(pop, x=0.0, z=0.0, nid="t"):
    return Node(nid, nid, float(pop), x, z)


class ShapeRuleTests(unittest.TestCase):
    def test_just_below_threshold_is_cylinder(self):
        self.assertEqual(shape_for(MEGA_THRESHOLD - 1), "cylinder")

    def test_at_threshold_is_tiered_square(self):
        self.assertEqual(shape_for(MEGA_THRESHOLD), "tiered_square")

    def test_zero_population_is_cylinder(self):
        self.assertEqual(shape_for(0), "cylinder")


class MeshValidityTests(unittest.TestCase):
    def test_many_populations_produce_valid_meshes(self):
        for pop in (0, 1, 1_000, 85_000, 999_999, 1_000_000,
                    2_400_000, 8_500_000, 50_000_000, 5_000_000_000):
            with self.subTest(pop=pop):
                mesh = build_node(node(pop))
                self.assertEqual(validate_mesh(mesh), [])
                self.assertGreater(signed_volume(mesh), 0)

    def test_mega_node_has_multiple_tiers(self):
        mesh = build_node(node(2_400_000))
        # each tier is one box: 8 vertices, 12 triangles
        self.assertGreaterEqual(len(mesh.faces) // 12, 3)

    def test_larger_population_is_not_smaller(self):
        small = build_node(node(100_000))
        large = build_node(node(900_000))
        width = lambda m: max(v[0] for v in m.vertices) - min(v[0] for v in m.vertices)
        self.assertGreater(width(large), width(small))

    def test_generation_is_deterministic(self):
        a = build_node(node(250_000, 5, 7))
        b = build_node(node(250_000, 5, 7))
        self.assertEqual(a.vertices, b.vertices)
        self.assertEqual(a.faces, b.faces)

    def test_validator_catches_broken_mesh(self):
        mesh = build_node(node(100_000))
        mesh.faces.pop()                      # open the mesh
        self.assertNotEqual(validate_mesh(mesh), [])
        mesh = build_node(node(100_000))
        mesh.faces[0] = (0, 0, 1)             # degenerate triangle
        self.assertNotEqual(validate_mesh(mesh), [])
        mesh = build_node(node(100_000))
        mesh.faces = [(a, c, b) for a, b, c in mesh.faces]   # flipped
        self.assertNotEqual(validate_mesh(mesh), [])
        mesh = build_node(node(100_000))
        mesh.faces[0] = (0, 1, 99999)         # bad index
        self.assertNotEqual(validate_mesh(mesh), [])


class InputTests(unittest.TestCase):
    def write(self, data):
        fh = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(data, fh)
        fh.close()
        self.addCleanup(os.remove, fh.name)
        return fh.name

    def test_rejects_negative_population(self):
        path = self.write([{"id": "a", "name": "A", "population": -5, "x": 0, "z": 0}])
        with self.assertRaises(ValueError):
            generate.load_nodes(path)

    def test_rejects_missing_field(self):
        path = self.write([{"id": "a", "name": "A", "population": 5, "x": 0}])
        with self.assertRaises(ValueError):
            generate.load_nodes(path)

    def test_rejects_duplicate_ids(self):
        item = {"id": "a", "name": "A", "population": 5, "x": 0, "z": 0}
        with self.assertRaises(ValueError):
            generate.load_nodes(self.write([item, dict(item)]))

    def test_rejects_empty_list(self):
        with self.assertRaises(ValueError):
            generate.load_nodes(self.write([]))


class OutputTests(unittest.TestCase):
    def test_end_to_end_writes_valid_obj_and_manifest(self):
        with tempfile.TemporaryDirectory() as out:
            self.assertEqual(generate.run("nodes.json", out), 0)
            with open(os.path.join(out, "manifest.json")) as fh:
                manifest = json.load(fh)
            with open(os.path.join(out, "map.obj")) as fh:
                lines = fh.read().splitlines()
            vcount = sum(1 for l in lines if l.startswith("v "))
            faces = [l.split()[1:] for l in lines if l.startswith("f ")]
            self.assertEqual(vcount, sum(n["vertices"] for n in manifest["nodes"]))
            for f in faces:
                for idx in f:
                    self.assertTrue(1 <= int(idx) <= vcount)
            shapes = {n["id"]: n["shape"] for n in manifest["nodes"]}
            self.assertEqual(shapes["p04"], "cylinder")        # 999,999
            self.assertEqual(shapes["p05"], "tiered_square")   # 1,000,000


if __name__ == "__main__":
    unittest.main()
