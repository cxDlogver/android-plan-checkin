#!/usr/bin/env python3
"""Build this project's UI package from authorized MCP snapshots and plan exports."""
import argparse
import copy
import hashlib
import json
import math
import re
from collections import Counter
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

VERSION = "2.0.0"

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def encode(value):
    return (json.dumps(value,ensure_ascii=False,indent=2)+"\n").encode("utf-8")

def size(mode="content",value=None,min_value=None,max_value=None):
    return {"mode":mode,"value":value,"min":min_value,"max":max_value}

def padding(value):
    if isinstance(value,(int,float)):
        return [value]*4
    if value is None:
        return [0]*4
    if len(value)==2:
        return [value[0],value[1],value[0],value[1]]
    return value

def sides(value):
    if isinstance(value,(int,float)):
        return [value]*4
    return [(value or {}).get(k,0) for k in ("top","right","bottom","left")]

def flex(direction="column",gap=0,pad=None,align="start",justify="start"):
    return {"type":"flex","direction":direction,"wrap":"nowrap","justify":justify,
            "align":align,"gap":gap,"padding":pad or [0,0,0,0]}

def flow():
    return {"mode":"flow","anchorId":None,"insets":dict.fromkeys(("top","right","bottom","left")),
            "zIndex":0,"grow":0,"shrink":0,"basis":"auto","gridArea":None}

def nid(ident):
    return "n-"+ident.replace("/","__")

class NamedHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.nodes=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if "data-pencil-name" in a:
            self.nodes.append((tag,a))
    def handle_startendtag(self,tag,attrs):
        self.handle_starttag(tag,attrs)

def source_svgs(text):
    result=[]
    for match in re.finditer(r"<svg\b[^>]*>.*?</svg>",text,re.S):
        svg=match.group(0)
        parser=NamedHTML();parser.feed(svg)
        a=parser.nodes[0][1]
        svg=re.sub(r"\s+(?:data-[\w-]+|style)=\"[^\"]*\"","",svg)
        result.append((a,svg))
    return result

class Builder:
    def __init__(self,root):
        self.root=root
        self.out=root/"plan"/"ui-spec"
        self.source=root/"plan"/"source-resource"/"ui"
        self.styles={}
        self.assets={}
        self.documents=[]
        self.sources=[]
        self.issues=[]
        self.mapping=[]
        self.stats=[]
        self.style_counts=Counter()
        self.icon_uses=0
        self.original_nodes=0

    def issue(self,ident,message,critical=False,document=None):
        if ident not in {i["id"] for i in self.issues}:
            self.issues.append({"id":ident,"documentId":document,"message":message,"critical":critical,
                                "status":"open","resolution":None})

    def paint(self,value):
        if not value:
            return []
        if isinstance(value,str):
            return [{"type":"solid","color":value}]
        if isinstance(value,list):
            return [p for v in value for p in self.paint(v)]
        if value.get("enabled") is False:
            return []
        if value.get("type")=="color":
            return [{"type":"solid","color":value["color"]}]
        if value.get("type")=="gradient" and value.get("gradientType","linear")=="linear":
            return [{"type":"linear-gradient","angle":(-value.get("rotation",0))%360,
                     "stops":[{"position":v["position"],"color":v["color"]} for v in value.get("colors",[])]}]
        raise ValueError("Unsupported source paint: "+str(value))

    def geometry(self,value):
        items=value if isinstance(value,list) else [value]
        result=[]
        for index,v in enumerate(items):
            if isinstance(v,dict) and v.get("type")=="gradient":
                result.append({"layer":index,"coordinateSpace":"normalized-bounds",
                               "center":[v.get("center",{}).get("x",0.5),v.get("center",{}).get("y",0.5)],
                               "size":[v.get("size",{}).get("width",1),v.get("size",{}).get("height",1)],
                               "rotationCCW":v.get("rotation",0)})
        return result

    def style(self,n):
        ext={}
        st=None
        if n.get("stroke") is not None and any(sides(n.get("strokeWidth",0))):
            paint=self.paint(n["stroke"])
            if len(paint)==1 and paint[0]["type"]=="solid":
                st={"widths":sides(n.get("strokeWidth",0)),"color":paint[0]["color"],
                    "alignment":n.get("strokeAlignment","center")}
            else:
                ext["strokePaint"]={"widths":sides(n.get("strokeWidth",0)),
                                    "alignment":n.get("strokeAlignment","center"),
                                    "paints":paint,"geometry":self.geometry(n["stroke"])}
        geom=self.geometry(n.get("fill"))
        if geom:
            ext["fillGeometry"]=geom
        typ=None
        if n["type"]=="text":
            family=n.get("fontFamily","Inter")
            typ={"fontFamilies":[family],"fontSize":n.get("fontSize",16),
                 "fontWeight":int({"normal":400,"bold":700}.get(n.get("fontWeight"),n.get("fontWeight","400"))),"fontStyle":n.get("fontStyle","normal"),
                 "lineHeight":{"mode":"multiplier","value":n["lineHeight"]} if n.get("lineHeight") else {"mode":"font-metrics","value":None},
                 "letterSpacing":n.get("letterSpacing",0),
                 "align":{"left":"start","right":"end"}.get(n.get("textAlign","left"),n.get("textAlign"))}
            ext["fontAssetRef"]="font-noto-sans-sc" if family=="Noto Sans SC" else "font-inter"
        effects=n.get("effect",[])
        if not isinstance(effects,list):
            effects=[effects]
        eff=[]
        for e in effects:
            if e.get("enabled") is False:
                continue
            p={k:v for k,v in e.items() if k not in ("type","enabled")}
            if e["type"]=="shadow":
                p={"shadowType":"outer","offset":{"x":0,"y":0},"blur":0,"blendMode":"normal",**p}
            eff.append({"type":e["type"],"parameters":p})
        style={"fills":self.paint(n.get("fill")),"stroke":st,"radii":padding(n.get("cornerRadius",0)),
               "effects":eff,"opacity":n.get("opacity",1),"typography":typ,"extensions":ext}
        key="s-"+sha(json.dumps(style,sort_keys=True,ensure_ascii=False).encode("utf-8"))[:16]
        self.styles[key]=style;self.style_counts[key]+=1
        return key

    def asset_svg(self,n,svgs,document):
        candidates=[(a,svg) for a,svg in svgs if a.get("data-pencil-name")==n.get("name")
                    and a.get("data-icon-name")==n.get("icon")
                    and a.get("data-icon-set")==n.get("library")]
        colors=self.paint(n.get("fill"))
        color=colors[0].get("color") if colors else None
        matching=[(a,svg) for a,svg in candidates if not color or color.lower() in svg.lower()]
        if matching:
            candidates=matching
        distinct={svg for a,svg in candidates}
        if len(distinct)!=1:
            self.issue("icon-"+nid(n["id"]),"Icon geometry is missing or ambiguous for "+n.get("name",n["id"]),True,document)
            raise ValueError("Cannot resolve exact exported SVG for "+n["id"])
        svg=next(iter(distinct))
        raw=svg.encode("utf-8");key="vector-"+sha(raw)[:16]
        relative="assets/vectors/"+key+".svg"
        full=self.out/relative;full.parent.mkdir(parents=True,exist_ok=True);full.write_bytes(raw)
        self.assets[key]={"kind":"vector","file":relative,"embedded":None,"sha256":sha(raw),
                          "availability":"available","critical":True}
        self.icon_uses+=1
        return key

    def convert(self,rows,filename,kind,source_id,svgs):
        byid={r["data"]["id"]:r for r in rows}
        childmap={}
        for r in rows:
            childmap.setdefault(r["parentId"],[]).append(r)
        docid="ui-"+rows[0]["data"]["id"]
        source_root=rows[0]["data"]
        def build(r,environment=False):
            n=r["data"];b=r["bounds"];ident=nid(n["id"])
            environment=environment or n.get("name") in ("安卓状态栏","安卓手势安全区")
            is_frame=n["type"]=="frame"
            parent=byid.get(r["parentId"])
            parent_dir=parent["data"].get("layout","horizontal") if parent else None
            width=n.get("width")
            height=n.get("height")
            text=n["type"]=="text"
            if text:
                w=size("fill") if width=="fill_container" else size("fixed",width) if isinstance(width,(int,float)) else size()
                h=size()
            else:
                w=size("fill") if width=="fill_container" else size("fixed",width) if isinstance(width,(int,float)) else size()
                h=size("fill") if height=="fill_container" else size("fixed",height) if isinstance(height,(int,float)) else size()
            if is_frame and isinstance(height,(int,float)) and not environment:
                h=size("content",min_value=height)
            if n["id"]==source_root["id"]:
                if kind=="screen":
                    w=size("fill",max_value=480);h=size("fill")
                elif kind=="component":
                    w=size("fill");h=size("content",min_value=b["height"])
            place=flow()
            if parent and ((width=="fill_container" and parent_dir=="horizontal") or (height=="fill_container" and parent_dir=="vertical")):
                place["grow"]=1;place["basis"]=0
            if width=="fill_container" and parent and parent_dir=="horizontal":
                w=size("fraction",1)
            if text:
                # Natural-width badges keep their source sizing; body/title text can wrap within allocated width.
                constrained=width=="fill_container" or n.get("textGrowth") in ("fixed-width","fixed-width-height")
                cont={"type":"text","value":n.get("content",""),"wrap":"nowrap" if environment and not constrained else "wrap",
                      "overflow":"visible","maxLines":None,"scaleWithSystem":not environment}
                node_kind="text"
            elif n["type"]=="icon":
                cont={"type":"vector","assetRef":self.asset_svg(n,svgs,docid)};node_kind="vector"
            else:
                cont=None;node_kind="container" if is_frame else "shape"
            layout=None
            if is_frame:
                layout=flex("column" if n.get("layout","horizontal")=="vertical" else "row",
                            n.get("gap",0),padding(n.get("padding")),n.get("alignItems","start"),
                            n.get("justifyContent","start").replace("_","-"))
            if text and not environment:
                place["shrink"]=1
            decision=["source-visual","flow-layout"]
            if text and not environment:
                decision.append("text-flow")
            if is_frame and isinstance(height,(int,float)) and not environment:
                decision.append("content-min-height")
            if n.get("name")=="页面内容":
                decision.append("main-scroll")
            extensions={}
            if text and not environment:
                extensions["textFlow"]={"breakPolicy":"grapheme","maxWidth":"allocated-parent-content"}
            if n.get("metadata"):
                extensions["sourceMetadata"]=n["metadata"]
            if n["type"]=="icon":
                extensions["iconIdentity"]={"library":n.get("library"),"name":n.get("icon")}
            if n.get("name") in ("安卓状态栏","安卓手势安全区"):
                extensions["environmentRegion"]={"edge":"top" if n["name"]=="安卓状态栏" else "bottom",
                    "referenceExtent":height,"rendering":"reference-only; runtime host consumes actual inset once"}
                decision.append("environment-regions")
            node={"id":ident,"name":n.get("name",ident),"kind":node_kind,"role":None,
                  "variant":{"state":n.get("metadata",{}).get("screenKey"),"properties":{}},
                  "parentId":nid(r["parentId"]) if r["parentId"] else None,
                  "ownership":"platform" if environment else "application","componentRef":None,
                  "layout":layout,"sizing":{"width":w,"height":h},"placement":place,
                  "overflow":{"x":"clip" if n.get("clip") else "visible",
                              "y":"scroll" if n.get("name")=="页面内容" else "clip" if n.get("clip") else "visible"},
                  "styleRef":self.style(n),"content":cont,
                  "semantics":{"role":None,"label":None,"actionRef":None},
                  "policy":{"locked":["styleRef","layout","sizing","placement","overflow","content","children"],"adaptive":[]},
                  "responsive":[],"source":{"sourceId":source_id,"nodeId":n["id"],"evidence":"extracted","referenceBounds":b},
                  "decisionRefs":list(dict.fromkeys(decision)),"extensions":extensions,"children":[]}
            node["children"]=[build(c,environment) for c in sorted(childmap.get(n["id"],[]),key=lambda x:x["index"])]
            direct_ids={c["data"]["id"] for c in childmap.get(n["id"],[])}
            if n["id"]+"/vufPs" in direct_ids:
                node["componentRef"]="ui-YbZvd"
            elif {n["id"]+"/le4zI",n["id"]+"/en7rq",n["id"]+"/W7dyk"}.issubset(direct_ids):
                node["componentRef"]="ui-jbAsr"
            # Fixed progress value is made proportional to its source track, preserving the current sample.
            if n["type"]=="rectangle" and parent and n.get("name")=="已完成进度":
                node["sizing"]["width"]=size("percent",r["bounds"]["width"]/parent["bounds"]["width"])
                node["decisionRefs"].append("progress-proportion")
            if is_frame and n.get("name")=="月历":
                weeks=[c for c in node["children"] if re.fullmatch("第\\d+周",c["name"])]
                if weeks:
                    dates=[c for week in weeks for c in week["children"]]
                    grid_id=ident+"-dates"
                    date_grid=copy.deepcopy(node)
                    date_grid.update(id=grid_id,name="日期七列网格",parentId=ident,source=None,
                                     decisionRefs=["calendar-grid"],extensions={})
                    date_grid["layout"]={"type":"grid","columns":[{"mode":"fraction","value":1} for _ in range(7)],
                                         "rowGap":node["layout"]["gap"],"columnGap":2,"padding":[0,0,0,0]}
                    date_grid["sizing"]={"width":size("fill"),"height":size()}
                    date_grid["styleRef"]=self.style({"type":"frame"})
                    date_grid["children"]=dates
                    for date in dates:
                        date["parentId"]=grid_id;date["placement"]["grow"]=0;date["placement"]["basis"]="auto"
                        date["sizing"]["width"]=size("fill")
                    removed={week["id"] for week in weeks}
                    node["children"]=[c for c in node["children"] if c["id"] not in removed]+[date_grid]
                    for week in weeks:
                        self.mapping.append({"sourceNodeId":week["source"]["nodeId"],"targetNodeId":grid_id,
                                             "reason":"week row consolidated into deterministic seven-column Grid"})
                    node["decisionRefs"].append("calendar-grid")
                    weekday=next(c for c in node["children"] if c["name"]=="星期")
                    weekday["layout"]={"type":"grid","columns":[{"mode":"fraction","value":1} for _ in range(7)],
                                       "rowGap":0,"columnGap":2,"padding":[0,0,0,0]}
                    weekday["decisionRefs"].append("calendar-grid")
                    for cell in weekday["children"]:
                        cell["sizing"]["width"]=size("fill")
                        cell["placement"]["grow"]=0;cell["placement"]["basis"]="auto"
            return node
        tree=build(rows[0])
        if kind=="screen":
            tree["parentId"]="viewport-"+source_root["id"]
            tree["decisionRefs"].append("mobile-window")
            tree["placement"]["grow"]=1;tree["placement"]["basis"]=0
            wrapper={"id":"viewport-"+source_root["id"],"name":"可用窗口与手机画布","kind":"container","role":None,
                     "variant":{"state":None,"properties":{}},"parentId":None,"ownership":"application","componentRef":None,
                     "layout":flex(align="center"),"sizing":{"width":size("viewport"),"height":size("viewport")},
                     "placement":flow(),"overflow":{"x":"clip","y":"clip"},
                     "styleRef":self.style({"type":"frame","fill":"#E8ECF0"}),"content":None,
                     "semantics":{"role":None,"label":None,"actionRef":None},
                     "policy":{"locked":["styleRef","layout","sizing","placement","overflow","children"],"adaptive":[]},
                     "responsive":[],"source":None,"decisionRefs":["mobile-window"],"extensions":{},"children":[tree]}
            tree=wrapper
        return {"schemaVersion":VERSION,"kind":kind,"id":docid,"title":filename[:-5],"profileId":"mobile",
                "referenceSize":{"width":rows[0]["bounds"]["width"],"height":rows[0]["bounds"]["height"]},
                "issues":[],"tree":tree}

    def run(self):
        self.out.joinpath("documents").mkdir(exist_ok=True)
        captures=sorted((self.out/"provenance"/"节点").glob("*.json"))
        for capture in captures:
            rows=json.loads(capture.read_text(encoding="utf-8"))
            title=capture.stem
            kind="component" if title.startswith("组件-") else "reference" if title.startswith("Android ") else "screen"
            text=(self.source/(title+".html")).read_text(encoding="utf-8")
            parsed=NamedHTML();parsed.feed(text)
            source_names=[r["data"].get("name") for r in rows]
            exported_names=[a.get("data-pencil-name") for tag,a in parsed.nodes]
            if source_names!=exported_names:
                raise ValueError("MCP/HTML named-node order mismatch: "+title)
            source_id="source-"+rows[0]["data"]["id"]
            self.sources.append({"id":source_id,"uri":"provenance/节点/"+capture.name,
                                 "revision":"MCP snapshot of plan/source-resource/ui/ui.pen#"+rows[0]["data"]["id"],"sha256":sha(capture.read_bytes())})
            self.sources.append({"id":source_id+"-svg","uri":"plan/source-resource/ui/"+title+".html",
                                 "revision":"HTML export captured in current plan scope","sha256":sha((self.source/(title+".html")).read_bytes())})
            doc=self.convert(rows,title+".json",kind,source_id,source_svgs(text))
            self.documents.append(doc);self.original_nodes+=len(rows)
            self.stats.append({"title":title,"id":doc["id"],"kind":kind,"sourceNodes":len(rows),
                               "width":doc["referenceSize"]["width"],"height":doc["referenceSize"]["height"],
                               "sourceLayoutProblems":[{"id":r["data"]["id"],"name":r["data"]["name"],"problem":r["problems"]} for r in rows if r["problems"]]})
        font=self.out/"assets"/"fonts"/"NotoSansSC-VF.ttf"
        self.assets["font-noto-sans-sc"]={"kind":"font","file":"assets/fonts/NotoSansSC-VF.ttf","embedded":None,
                                         "sha256":sha(font.read_bytes()),"availability":"available","critical":True}
        self.assets["font-inter"]={"kind":"font","file":None,"embedded":None,"sha256":None,
                                   "availability":"missing","critical":True}
        self.issue("FONT-INTER","Inter用于日历日期/汇总等业务文字及环境时间。本地未找到；HTML引用的远程字体当前无法解析DNS，尚未取得可随包使用的字体文件与版本哈希。",True)
        self.issue("DESKTOP-NOT-PROVIDED","没有W>=768的桌面端页面；桌面端不在本包覆盖范围，不将手机UI放大作为桌面规范。")
        self.issue("PROGRESS-LABEL-GEOMETRY","02、13页文案2/3对应的进度条实测203.333/321=63.34%，并非66.67%；当前JSON保留原稿几何比例并改为percent计算，不擅自修正文案或业务值。")
        for doc in self.documents:
            if doc["title"] in ("02-今日","13-运动"):
                doc["issues"].append("PROGRESS-LABEL-GEOMETRY")
            if doc["kind"]=="screen":
                doc["issues"].append("FONT-INTER")
        for doc in self.documents:
            raw=encode(doc);rel="documents/"+doc["title"]+".json"
            (self.out/rel).write_bytes(raw)
        self.write_outputs()
        return self

    def write_outputs(self):
        decisions={
          "source-visual":{"statement":"原生节点取值、样例文字和视觉配方严格保存；矢量从当前plan导出的同名同库SVG取得，逐页核对全部节点名称与顺序。","origin":"source","evidence":"26份MCP节点快照及对应plan HTML"},
          "flow-layout":{"statement":"一维容器唯一采用Flex；fill_container在横向主轴按等权fraction=1分配，其余填充明确父级区域。普通流不使用原图x/y定位。","origin":"normalized","evidence":"435个原生frame均为vertical/horizontal，未发现覆盖或绝对定位"},
          "content-min-height":{"statement":"非环境容器的源数值高度转换为content+相同min；基准不压缩，文字放大和换行可增高；图标和形状保持fixed。","origin":"normalized","evidence":"源按钮48、页头92、导航70及日期格48；长文字不能裁剪"},
          "main-scroll":{"statement":"页面内容是唯一业务纵向滚动区，填满页头/导航/环境区域外的剩余高度；其内部子节点不收缩。表单保存按钮保留在正文流中，不擅自吸底。","origin":"normalized","evidence":"23个页面均有名为页面内容的fill_container容器"},
          "mobile-window":{"statement":"W<768选择mobile；画布宽min(W,480)，在可用窗口居中，画布高填满窗口。W>=768不提供页面。480只限宽、不改变端型。参考Size仍保存原稿393及各画板高度。","origin":"normalized","evidence":"当前23屏宽393；plan中既有阅读限宽约定480；本次按两端独立规则修正适用范围"},
          "calendar-grid":{"statement":"月历日期统一为7等权列、5行Grid，列距2、行距12；星期同样7等权列。去除5个冗余周行，日期顺序、填充、描边与内容全部保留。","origin":"normalized","evidence":"11-日历：星期+第0至4周，35日期格，原周距12、格距2"},
          "environment-regions":{"statement":"系统状态/手势示例归环境所有；参考图使用36/24，实际只由宿主处理一次对应insets，样例子节点不在业务层重复绘制。","origin":"normalized","evidence":"所有页面的状态栏36、底部环境区域24"},
          "text-flow":{"statement":"业务文字保留基准字体，宽度不足按字素换行，content宽不超过父级分配区域，横向文本可收缩且高度按内容增加；环境样例不随业务字体缩放。","origin":"normalized","evidence":"窄屏与fontScale检查需要明确文字溢出策略；源文字及参考边界完整保留"},
          "progress-proportion":{"statement":"两处进度填充宽度按203.33333333333331/321=0.6334371754932502计算父轨道百分比，保持源393宽时的几何，不解释为业务完成比例。","origin":"normalized","evidence":"02、13页已完成进度及进度条的原生bounds；文案2/3单独保留为已知设计差异"},
          "continuous-mobile":{"statement":"当前稿件无需类内布局断点，modes为空。保持单列、等权按钮与7列日期；主文案换行与content撑高，字号图标不随宽度缩放。","origin":"normalized","evidence":"当前所有页面仅有393宽样例，未提供可据以切换结构的另一组设计"}
        }
        cases=[{"width":w,"height":h,"fontScale":f,"theme":"light","orientation":"portrait" if h>=w else "landscape"}
               for w,h,f in [(320,640,1),(360,800,1),(393,852,1),(480,852,1),(767,852,1),
                             (393,600,1),(393,852,1.3),(320,640,1.3),(393,500,1.3)]]
        rules={"schemaVersion":VERSION,"kind":"rules",
               "classification":{"breakpoint":768,"unit":"logical-px","mobile":"0 < width < 768","desktop":"width >= 768"},
               "decisions":decisions,
               "profiles":{"mobile":{"formFactor":"mobile","units":{"layout":"logical-px","typography":"logical-px"},
                    "environment":{"baselineWidth":393,"baselineHeight":852,"fontScale":1,"locale":"zh-CN","theme":"light",
                      "safeAreaPolicy":"宿主处理环境区域一次；参考top=36、bottom=24，实际取环境insets",
                      "keyboardPolicy":"键盘缩小正文可用高度；滚动页面内容以显示焦点字段及保存按钮，不移动到画面外",
                      "scrollPolicy":"仅页面内容纵向滚动；页头、导航、环境区域在其外"},
                    "modes":[],"validationCases":cases,
                    "extensions":{"supportedWidth":{"min":320,"maxExclusive":768},"contentMaxWidth":480,
                                  "unprovidedProfile":"desktop","validationCasesStatus":"planned-not-executed",
                                  "fontScalePolicy":"scaleWithSystem=true时字号及长度型行高乘fontScale；倍率型行高保持倍率",
                                  "provenance":"源画板均为393；320为当前规范化验收下限，低于320未纳入已声明适配范围",
                                  "breakpointBoundaryCases":[{"width":767,"expectedProfile":"mobile"},{"width":768,"expectedProfile":"desktop","coverage":"not-provided"}]}}}}
        library={"schemaVersion":VERSION,"kind":"library","styles":self.styles,"assets":self.assets}
        artifacts={}
        for name,data in (("rules",rules),("library",library)):
            raw=encode(data);rel=name+".json";(self.out/rel).write_bytes(raw)
            artifacts[name]={"file":rel,"sha256":sha(raw)}
        entries=[]
        for doc in self.documents:
            rel="documents/"+doc["title"]+".json"
            entries.append({k:doc[k] for k in ("id","title","kind","profileId")} | {"file":rel,"sha256":sha((self.out/rel).read_bytes())})
        manifest={"schemaVersion":VERSION,"kind":"manifest","authority":"draft",
                  "sources":self.sources,"documents":entries,"artifacts":artifacts,"issues":self.issues,
                  "verification":{"baselineVisual":"not-tested","responsiveVisual":"not-tested","evidence":[]}}
        (self.out/"manifest.json").write_bytes(encode(manifest))
        summary={"sourceNodes":self.original_nodes,"documents":self.stats,"styles":len(self.styles),
                 "assets":len(self.assets),"iconUses":self.icon_uses,"normalizationMap":self.mapping,
                 "excluded":["resource/**","不存在的旧plan/ui-spec产物"],"sourceFilesReadByValidation":False}
        (self.out/"provenance"/"转换摘要.json").write_bytes(encode(summary))
        (self.out/"schema").mkdir(exist_ok=True)
        schema=self.root/"plan"/"skill"/"ui-spec-normalizer"/"assets"/"ui-spec.schema.json"
        (self.out/"schema"/"ui-spec.schema.json").write_bytes(schema.read_bytes())
        print(json.dumps({k:summary[k] for k in ("sourceNodes","styles","assets","iconUses")},ensure_ascii=False))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root",type=Path)
    args=parser.parse_args()
    Builder(args.root.resolve()).run()

if __name__=="__main__":
    main()
