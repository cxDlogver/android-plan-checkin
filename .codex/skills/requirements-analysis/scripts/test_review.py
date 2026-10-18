"""Meaningful graph regressions; no claims of browser or human acceptance."""
import copy
import json
import re
import unittest

from render_review import entries, presentation, render, shortest_path
from review_layout import layout


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.model = {
            "phase": "analyzing", "entryStateIds": ["A", "E"], "scope": {"objective": "合成流程"},
            "features": [{"id": "F", "title": "功能", "entryStateIds": ["A", "E"]}],
            "states": [{"id": x, "title": title, "facts": [title], "status": "draft",
                        "sourceIds": [], "uiRefs": []}
                       for x, title in zip("ABCDEZ", ["入口", "编辑中", "确认中", "已保存", "另一个入口", "隔离状态"])],
            "transitions": [{"id": tid, "from": a, "to": b, "event": "继续",
                             "guard": "true", "requirementId": "R" + tid}
                            for tid, a, b in [("AB", "A", "B"), ("BC", "B", "C"),
                                              ("CD", "C", "D"), ("AD", "A", "D"),
                                              ("BA", "B", "A"), ("BB", "B", "B"),
                                              ("EC", "E", "C")]],
            "requirements": [], "sources": [], "questions": [], "rounds": [{"private": "internal audit"}],
        }
        self.artifacts = {"state-graph.json": {"semanticDigest": "fixture-only"}}

    def test_shortest_is_not_click_history_or_depth_first(self):
        self.assertEqual(["AD"], shortest_path(self.model, "A", "D"))

    def test_target_stops_at_selected_state(self):
        self.assertEqual(["AB", "BC"], shortest_path(self.model, "A", "C"))

    def test_entry_is_zero_steps_even_with_cycle(self):
        self.assertEqual([], shortest_path(self.model, "A", "A"))

    def test_unreachable_has_no_fabricated_route(self):
        self.assertIsNone(shortest_path(self.model, "A", "Z"))

    def test_different_entry_recomputes_path(self):
        self.assertEqual(["EC", "CD"], shortest_path(self.model, "E", "D"))

    def test_parallel_and_equal_length_ties_are_stable(self):
        model = copy.deepcopy(self.model)
        model["transitions"].insert(4, {"id": "AD2", "from": "A", "to": "D"})
        self.assertEqual(["AD"], shortest_path(model, "A", "D"))

    def test_declared_entry_not_zero_indegree_guess(self):
        self.assertEqual(["A", "E"], entries(self.model))

    def test_empty_entry_not_silently_invented(self):
        self.model["entryStateIds"] = []
        with self.assertRaisesRegex(ValueError, "documented entry"):
            presentation(self.model, self.artifacts, {})

    def test_all_computed_paths_are_contiguous_and_end_at_target(self):
        data = presentation(self.model, self.artifacts, {})
        lookup = {e["id"]:e for e in self.model["transitions"]}
        for start, paths in data["routes"].items():
            for target, route in paths.items():
                if route is None:
                    continue
                current = start
                visited = {start}
                for edge_id in route:
                    edge = lookup[edge_id]
                    self.assertEqual(current, edge["from"])
                    current = edge["to"]
                    self.assertNotIn(current, visited)
                    visited.add(current)
                self.assertEqual(target, current)

    def test_audit_fields_not_copied_into_review_payload(self):
        data = presentation(self.model, self.artifacts, {})
        self.assertNotIn("rounds", data)
        self.assertNotIn("artifacts", data)

    def test_full_layout_keeps_every_state_and_transition(self):
        data = layout(self.model, entries(self.model))
        self.assertEqual({s["id"] for s in self.model["states"]}, set(data["positions"]))
        self.assertEqual({e["id"] for e in self.model["transitions"]}, {e["id"] for e in data["curves"]})
        self.assertEqual(["Z"], data["unreachable"])
        boxes = list(data["positions"].values())
        for i, a in enumerate(boxes):
            for b in boxes[i+1:]:
                self.assertFalse(a["x"] < b["x"]+b["w"] and b["x"] < a["x"]+a["w"] and a["y"] < b["y"]+b["h"] and b["y"] < a["y"]+a["h"])

    def test_entry_change_invalidates_semantic_digest(self):
        import model_tools
        before = model_tools.model_digest(self.model)
        self.model["entryStateIds"] = ["E"]
        self.assertNotEqual(before, model_tools.model_digest(self.model))

    def test_source_text_remains_inert_embedded_data(self):
        self.model["states"][0]["title"] = "</script><script>alert(1)</script>"
        html = render(self.model, self.artifacts)
        encoded = re.search(r'<script id="data" type="application/json">(.*?)</script>', html, re.S).group(1)
        self.assertNotIn("<", encoded)
        self.assertEqual(self.model["states"][0]["title"], json.loads(encoded)["states"][0]["title"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
