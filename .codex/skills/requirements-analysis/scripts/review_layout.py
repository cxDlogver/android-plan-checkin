"""Complete directed graph layout; no business nodes or edges are invented."""
from collections import Counter, deque
import math


def layout(model, starts):
    nodes = model["states"]
    edges = model["transitions"]
    outgoing = {node["id"]: [] for node in nodes}
    for edge in edges:
        outgoing[edge["from"]].append(edge)
    ranks = {start: 0 for start in starts}
    queue = deque(starts)
    while queue:
        current = queue.popleft()
        for edge in outgoing[current]:
            if edge["to"] not in ranks:
                ranks[edge["to"]] = ranks[current] + 1
                queue.append(edge["to"])
    last_rank = max(ranks.values(), default=-1) + 1
    layers = {}
    for node in nodes:
        layers.setdefault(ranks.get(node["id"], last_rank), []).append(node)
    sizes = {node["id"]: max(80, 30 + math.ceil(len(node["title"]) / 14) * 21) for node in nodes}
    layer_height = max((sum(sizes[n["id"]] + 30 for n in group) for group in layers.values()), default=200)
    backward_count = sum(ranks.get(e["to"], last_rank) < ranks.get(e["from"], last_rank) for e in edges)
    top = 90 + backward_count * 3
    positions = {}
    for rank, group in sorted(layers.items()):
        y = top + (layer_height - sum(sizes[n["id"]] + 30 for n in group)) / 2
        for node in group:
            positions[node["id"]] = {"x": 120 + rank * 460, "y": y,
                                      "w": 245, "h": sizes[node["id"]]}
            y += sizes[node["id"]] + 30
    curves, pair_count, back_index = [], {}, 0
    pair_totals = Counter((e["from"], e["to"]) for e in edges)
    for edge in edges:
        a, b = positions[edge["from"]], positions[edge["to"]]
        pair = (edge["from"], edge["to"])
        index = pair_count.get(pair, 0)
        pair_count[pair] = index + 1
        ay, by = a["y"] + a["h"] / 2, b["y"] + b["h"] / 2
        if a["x"] < b["x"]:
            ax, bx = a["x"] + a["w"], b["x"]
            count = pair_totals[pair]
            spacing = min(8, (min(a["h"], b["h"]) - 20) / count)
            offset = (index - (count - 1) / 2) * spacing
            d = f'M {ax} {ay+offset} C {ax+100} {ay+offset},{bx-100} {by+offset},{bx} {by+offset}'
            kind = "forward"
        elif a["x"] == b["x"]:
            ax, bx = a["x"] + a["w"], b["x"] + b["w"]
            rail = ax + 30 + index * 8
            if edge["from"] == edge["to"]:
                d = f'M {ax} {ay-15} C {rail+45} {ay-60},{rail+45} {ay+60},{bx} {by+15}'
            else:
                d = f'M {ax} {ay} C {rail+50} {ay},{rail+50} {by},{bx} {by}'
            kind = "return"
        else:
            rail_y = 35 + back_index * 3
            back_index += 1
            ax, bx = a["x"], b["x"]
            lane_a, lane_b = ax - 24 - index * 5, bx - 24 - index * 5
            d = f'M {ax} {ay} L {lane_a} {ay} L {lane_a} {rail_y} L {lane_b} {rail_y} L {lane_b} {by} L {bx} {by}'
            kind = "return"
        curves.append({"id": edge["id"], "d": d, "kind": kind})
    return {"positions": positions, "curves": curves,
            "width": max((p["x"] + p["w"] for p in positions.values()), default=500) + 160,
            "height": top + layer_height + 80,
            "unreachable": [n["id"] for n in nodes if n["id"] not in ranks]}
