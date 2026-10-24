#!/usr/bin/env python3
"""Independently audit node/content coverage against the captured MCP records."""
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]
def load(relative):
    return json.loads((BASE/relative).read_text(encoding="utf-8"))
def walk(n):
    yield n
    for child in n["children"]:
        yield from walk(child)

manifest=load("manifest.json")
library=load("library.json")
summary=load("provenance/转换摘要.json")
documents=[load(e["file"]) for e in manifest["documents"]]
nodes=[n for d in documents for n in walk(d["tree"])]
source_rows={}
for source in manifest["sources"]:
    if source["uri"].startswith("provenance/节点/"):
        raw=(BASE/source["uri"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==source["sha256"],source["uri"]
        for row in json.loads(raw):
            source_rows[(source["id"],row["data"]["id"])]=row
target_rows={(n["source"]["sourceId"],n["source"]["nodeId"]):n for n in nodes if n["source"]}
missing=set(source_rows)-set(target_rows)
declared_merged={m["sourceNodeId"] for m in summary["normalizationMap"]}
assert {key[1] for key in missing}==declared_merged,sorted(missing)
assert len(missing)==5
assert len(source_rows)==984
assert len(target_rows)==979
assert len(nodes)==1003
text_count=0
for key,row in source_rows.items():
    if row["data"]["type"]=="text":
        target=target_rows[key]
        assert target["content"]["value"]==row["data"].get("content",""),key
        expected=row["data"].get("fontFamily","Inter")
        assert library["styles"][target["styleRef"]]["typography"]["fontFamilies"]==[expected],key
        text_count+=1
assert text_count==405
svg_count=0
for asset in library["assets"].values():
    if asset["kind"]=="vector":
        content=(BASE/asset["file"]).read_text(encoding="utf-8")
        root=ET.fromstring(content)
        assert root.tag.split("}")[-1]=="svg",asset["file"]
        assert "viewBox" in root.attrib,asset["file"]
        assert "href=" not in content and "<image" not in content,asset["file"]
        svg_count+=1
for style in library["styles"].values():
    ext=style["extensions"]
    if "fontAssetRef" in ext:
        assert ext["fontAssetRef"] in library["assets"]
    if "strokePaint" in ext:
        assert style["stroke"] is None
        assert ext["strokePaint"]["paints"]
    for geom in ext.get("fillGeometry",[]):
        assert style["fills"][geom["layer"]]["type"]=="linear-gradient"
calendar=next(d for d in documents if d["title"]=="11-日历")
grids=[n for n in walk(calendar["tree"]) if n["layout"] and n["layout"]["type"]=="grid"]
assert len(grids)==2
assert all(len(n["layout"]["columns"])==7 for n in grids)
date_grid=next(n for n in grids if n["name"]=="日期七列网格")
assert len(date_grid["children"])==35
assert not any(n["placement"]["mode"]!="flow" for n in nodes)
assert sum(n["overflow"]["y"]=="scroll" for n in nodes)==23
source_consistency=load("provenance/来源一致性检查.json")
assert source_consistency["status"]=="passed"
report={"status":"passed","scope":"source coverage and portable assets; no visual rendering performed",
        "sourceNodes":984,"retainedSourceNodes":979,"consolidatedWeekRows":5,"syntheticNodes":24,
        "normalizedNodes":1003,"exactTextRecords":text_count,"portableSvgAssets":svg_count,
        "vectorUses":sum(n["kind"]=="vector" for n in nodes),
        "componentRefs":sum(n["componentRef"] is not None for n in nodes),
        "calendarDates":35,"calendarColumns":7,"mainScrollRegions":23,
        "sourceArtboardsRechecked":len(source_consistency["checks"]),
        "unavailableCriticalFonts":[k for k,a in library["assets"].items() if a["kind"]=="font" and a["critical"] and a["availability"]!="available"],
        "baselineVisual":"not-tested","responsiveVisual":"not-tested"}
(BASE/"provenance"/"覆盖审计.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(report,ensure_ascii=False))
