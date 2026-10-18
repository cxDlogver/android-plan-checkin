"""Offline full Canvas graphs and source-backed visual requirement review."""
import json
import re
from collections import deque
from pathlib import Path
from review_layout import layout
from path_context import paths_for_start
from requirement_graph import requirement_graph


def entries(model):
    return list(dict.fromkeys(model.get("entryStateIds", [])))


def shortest_path(model, start, target):
    adjacency = {s["id"]: [] for s in model["states"]}
    if start not in adjacency or target not in adjacency:
        return None
    for edge in model["transitions"]:
        adjacency[edge["from"]].append(edge)
    parents, queue = {start: None}, deque([start])
    while queue and target not in parents:
        for edge in adjacency[queue.popleft()]:
            if edge["to"] not in parents:
                parents[edge["to"]] = edge
                queue.append(edge["to"])
    if target not in parents:
        return None
    route, current = [], target
    while current != start:
        edge = parents[current]
        route.append(edge["id"])
        current = edge["from"]
    return list(reversed(route))


def token_css(tokens):
    """Readable projection of explicit design values; no inferred layout numbers."""
    def number(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    def kebab(value):
        return re.sub(r"(?<!^)(?=[A-Z])", "-", value).lower()
    lines = ["/* 来自设计令牌；px列示原设计数值，平台dp/sp语义仍以原稿为准。 */", ":root {"]
    for key, value in tokens.get("colors", {}).items():
        if re.fullmatch(r"#[0-9A-Fa-f]{3,8}", str(value)):
            lines.append(f"  --{kebab(key)}: {value};")
    for key, value in tokens.get("font", {}).items():
        if number(value):
            unit = "" if "Weight" in key or "Ratio" in key else "px"
            lines.append(f"  --font-{kebab(key)}: {value}{unit};")
    for key, value in tokens.get("radius", {}).items():
        if number(value): lines.append(f"  --radius-{kebab(key)}: {value}px;")
    for key, value in tokens.get("layout", {}).items():
        if number(value): lines.append(f"  --{kebab(key)}: {value}px;")
    if number(tokens.get("minimumTouchTarget")):
        lines.append(f"  --minimum-touch-target: {tokens['minimumTouchTarget']}px;")
    lines.append("}")
    def rule(selector, declarations):
        if declarations: lines.extend([selector + " {"] + ["  " + d for d in declarations] + ["}"])
    colors, font, radii, sizes = tokens.get("colors", {}), tokens.get("font", {}), tokens.get("radius", {}), tokens.get("layout", {})
    base = []
    if "background" in colors: base.append("background: var(--background);")
    if "text" in colors: base.append("color: var(--text);")
    if "body" in font: base.append("font-size: var(--font-body);")
    if "lineHeightRatio" in font: base.append("line-height: var(--font-line-height-ratio);")
    if "preferredFamily" in font: base.append("font-family: " + json.dumps(font["preferredFamily"], ensure_ascii=False) + ", sans-serif;")
    if "pageInset" in sizes: base.append("padding-inline: var(--page-inset);")
    rule(".design-screen", base)
    rule(".design-title", [d for yes,d in [("title" in font,"font-size: var(--font-title);"),("titleWeight" in font,"font-weight: var(--font-title-weight);")] if yes])
    for selector,key,radius in [(".design-card","cardPadding","card"),(".design-control",None,"control"),(".design-panel",None,"panel"),(".design-tag",None,"tag")]:
        ds=[]
        if key in sizes:ds.append(f"padding: var(--{kebab(key)});")
        if radius in radii:ds.append(f"border-radius: var(--radius-{radius});")
        if selector==".design-control" and "minimumTouchTarget" in tokens:
            ds.extend(["min-width: var(--minimum-touch-target);","min-height: var(--minimum-touch-target);"])
        rule(selector,ds)
    if isinstance(sizes.get("inputPadding"), list) and all(number(v) for v in sizes["inputPadding"]):
        rule(".design-input",["padding: " + " ".join(str(v)+"px" for v in sizes["inputPadding"]) + ";"])
    for key,g in tokens.get("gradients",{}).items():
        if isinstance(g,dict) and number(g.get("rotation")):
            stops=[str(s["color"])+" "+str(round(s["position"]*100,4))+"%" for s in g.get("colors",[]) if isinstance(s,dict) and number(s.get("position")) and re.fullmatch(r"#[0-9A-Fa-f]{3,8}",str(s.get("color"))) ]
            if stops:rule(".design-gradient-"+kebab(key),["/* 角度与色标按设计令牌原值列示。 */","background-image: linear-gradient("+str(g["rotation"])+"deg, "+", ".join(stops)+");"])
    for key,items in tokens.get("effects",{}).items():
        shadows=[]
        for e in items if isinstance(items,list) else []:
            offset=e.get("offset",{})
            if e.get("type")=="shadow" and all(number(v) for v in [offset.get("x"),offset.get("y"),e.get("blur")]) and re.fullmatch(r"#[0-9A-Fa-f]{3,8}",str(e.get("color"))):
                shadows.append(("inset " if e.get("shadowType")=="inner" else "")+f"{offset['x']}px {offset['y']}px {e['blur']}px {e['color']}")
        if shadows:rule(".design-shadow-"+kebab(key),["box-shadow: "+", ".join(shadows)+";"])
    rule(".design-calendar-date",["font-size: var(--font-calendar-date);"] if "calendarDate" in font else [])
    rule(".design-calendar-fraction",[d for yes,d in [("calendarFraction" in font,"font-size: var(--font-calendar-fraction);"),("calendarFractionWeight" in font,"font-weight: var(--font-calendar-fraction-weight);"),("calendarProgress" in colors,"color: var(--calendar-progress);")] if yes])
    return "\n".join(lines)


def presentation(model, artifacts, media, designs=None):
    starts=entries(model)
    if model["states"] and not starts: raise ValueError("Canvas review requires a documented entry state")
    computed={start:paths_for_start(model,start) for start in starts}
    graph=requirement_graph(model)
    supplied=artifacts.get("requirement-graph.json")
    if supplied is not None:
        if any(supplied.get(key) != graph.get(key) for key in ("nodes", "edges", "reduction", "traversal")):
            raise ValueError("requirement graph differs from deterministic coverage routes")
    req_starts=graph["reduction"]["entryRequirementIds"]
    req_layout=layout({"states":graph["nodes"],"transitions":graph["edges"]},req_starts)
    visual_sources=[]
    for source_id,raw in (designs or {}).items():
        if isinstance(raw,dict) and isinstance(raw.get("colors"),dict) and isinstance(raw.get("font"),dict):
            visual_sources.append({"sourceId":source_id,"css":token_css(raw),"notes":raw.get("notes",[])})
    return {"phase":model["phase"],"scope":model["scope"],"states":model["states"],"transitions":model["transitions"],
            "requirements":model["requirements"],"features":model["features"],"sources":model["sources"],"questions":model["questions"],
            "starts":starts,"layout":layout(model,starts),"requirementGraph":graph,"requirementStarts":req_starts,"requirementLayout":req_layout,
            "routes":{start:computed[start][0] for start in starts},"routeChecks":{start:computed[start][1] for start in starts},
            "transitionValidation":artifacts["state-graph.json"].get("transitionValidation"),"pathContext":model.get("pathContext"),
            "semanticDigest":artifacts["state-graph.json"]["semanticDigest"],"media":media or {},"visualSources":visual_sources}


def render(model, artifacts, media=None, designs=None):
    payload=json.dumps(presentation(model,artifacts,media,designs),ensure_ascii=False)
    payload=payload.replace("<","\\u003c").replace("\u2028","\\u2028").replace("\u2029","\\u2029")
    template=(Path(__file__).resolve().parents[1]/"assets"/"review_canvas.html").read_text(encoding="utf-8")
    return template.replace("__PAYLOAD__",payload)
