#!/usr/bin/env python3
"""Executable contracts for synthetic mobile and desktop UI packages."""
import copy
import argparse
import subprocess
import sys
import hashlib
import json
import re
import tempfile
import unittest
from pathlib import Path
from validate_spec import validate_package, classify_width

TEST_TEMP_ROOT = None

SCHEMA = Path(__file__).resolve().parents[1]/"assets"/"ui-spec.schema.json"

def size(mode="content",value=None):
    return {"mode":mode,"value":value,"min":None,"max":None}

def flow():
    return {"mode":"flow","anchorId":None,"insets":dict.fromkeys(("top","right","bottom","left")),
            "zIndex":0,"grow":0,"shrink":1,"basis":"auto","gridArea":None}

def flex(direction="column"):
    return {"type":"flex","direction":direction,"wrap":"nowrap","justify":"start",
            "align":"stretch","gap":12,"padding":[16,16,16,16]}

def grid():
    return {"type":"grid","columns":[{"mode":"fixed","value":220},{"mode":"fraction","value":1}],
            "rowGap":16,"columnGap":24,"padding":[24,24,24,24]}

def node(ident,parent=None,text=None):
    return {
        "id":ident,"name":ident,"kind":"text" if text is not None else "container",
        "role":None,"variant":{"state":None,"properties":{}},"parentId":parent,"ownership":"application","componentRef":None,
        "layout":None if text is not None else flex(),
        "sizing":{"width":size("fill"),"height":size()},
        "placement":flow(),"overflow":{"x":"visible","y":"visible"},"styleRef":"body",
        "content":None if text is None else {
            "type":"text","value":text,"wrap":"wrap","overflow":"visible",
            "maxLines":None,"scaleWithSystem":True},
        "semantics":{"role":None,"label":None,"actionRef":None},
        "policy":{"locked":["styleRef","children"],"adaptive":["sizing","layout"]},
        "responsive":[],"source":None,"decisionRefs":["layout"],"extensions":{},"children":[]
    }

def fixture(category="desktop"):
    mobile = category == "mobile"
    width,height = (360,800) if mobile else (1280,720)
    root = node("root")
    root["layout"] = flex() if mobile else grid()
    root["children"] = [node("title","root","Example heading")]
    profile = {
        "formFactor":category,
        "units":{"layout":"logical-px","typography":"logical-px"},
        "environment":{"baselineWidth":width,"baselineHeight":height,
                       "fontScale":1,"locale":"en","theme":"light",
                       "safeAreaPolicy":"consume declared insets once",
                       "keyboardPolicy":"keep focused content visible","scrollPolicy":"document-defined"},
        "modes":[],"validationCases":[{"width":width,"height":height,
                                      "fontScale":1,"theme":"light","orientation":"portrait" if mobile else "landscape"}],
        "extensions":{}
    }
    return {
        "manifest":{"schemaVersion":"2.0.0","kind":"manifest","authority":"canonical",
                    "sources":[{"id":"brief","uri":"user:synthetic-brief","revision":"fixture-v2","sha256":None}],
                    "documents":[],"artifacts":{},"issues":[],
                    "verification":{"baselineVisual":"not-tested","responsiveVisual":"not-tested","evidence":[]}},
        "rules":{"schemaVersion":"2.0.0","kind":"rules",
                 "classification":{"breakpoint":768,"unit":"logical-px","mobile":"0 < width < 768","desktop":"width >= 768"},
                 "decisions":{"layout":{"statement":"Choose one layout for the stated fixture",
                                         "origin":"normalized","evidence":"Synthetic test brief"}},
                 "profiles":{category:profile}},
        "library":{"schemaVersion":"2.0.0","kind":"library",
                   "styles":{"body":{"fills":[{"type":"solid","color":"#334455"}],"stroke":None,
                                     "radii":[4,4,4,4],"effects":[],"opacity":1,
                                     "typography":{"fontFamilies":["sans-serif"],"fontSize":16,"fontWeight":400,
                                                   "fontStyle":"normal","lineHeight":{"mode":"multiplier","value":1.5},
                                                   "letterSpacing":0,"align":"start"},"extensions":{}}},
                   "assets":{}},
        "document":{"schemaVersion":"2.0.0","kind":"screen","id":"example","title":"Example interface",
                    "profileId":category,"referenceSize":{"width":width,"height":height},
                    "issues":[],"tree":root}
    }

def write_fixture(directory,data):
    directory.mkdir(exist_ok=True)
    (directory/"schema").mkdir(exist_ok=True)
    (directory/"schema"/"ui-spec.schema.json").write_bytes(SCHEMA.read_bytes())
    (directory/"UI规范.md").write_text("# Synthetic specification\n",encoding="utf-8")
    (directory/"documents").mkdir(exist_ok=True)
    def write(name,value):
        raw=(json.dumps(value,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
        (directory/name).write_bytes(raw)
        return {"file":name,"sha256":hashlib.sha256(raw).hexdigest()}
    manifest=copy.deepcopy(data["manifest"])
    manifest["artifacts"]={k:write(k+".json",data[k]) for k in ("rules","library")}
    documents=data.get("documents",[data["document"]])
    manifest["documents"]=[{"id":doc["id"],"title":doc["title"],"kind":doc["kind"],"profileId":doc["profileId"],
                            **write("documents/"+doc["title"]+".json",doc)} for doc in documents]
    write("manifest.json",manifest)

class ContractTests(unittest.TestCase):
    def evaluate(self,data,after=None):
        with tempfile.TemporaryDirectory(prefix="ui-spec-normalizer-tests-",dir=TEST_TEMP_ROOT) as folder:
            base=Path(folder).resolve()
            self.assertTrue(base.name.startswith("ui-spec-normalizer-tests-"))
            write_fixture(base,data)
            if after:
                after(base)
            return validate_package(base,SCHEMA)
    def assert_valid(self,data):
        report=self.evaluate(data)
        self.assertEqual(report["structure"]["status"],"passed",report)
        self.assertEqual(report["baselineVisual"],"not-tested")
        self.assertFalse(report["sourceFilesRead"])
    def test_desktop_grid(self):
        self.assert_valid(fixture())
    def test_mobile_flex(self):
        self.assert_valid(fixture("mobile"))
    def test_fixed_breakpoint_boundaries(self):
        for width,expected in [(0.5,"mobile"),(375,"mobile"),(767,"mobile"),
                               (767.999,"mobile"),(768,"desktop"),(768.001,"desktop"),(1440,"desktop")]:
            with self.subTest(width=width):
                self.assertEqual(classify_width(width),expected)
                data=fixture(expected)
                data["document"]["referenceSize"]["width"]=width
                self.assert_valid(data)
    def test_invalid_classification_width_rejected(self):
        for width in [0,-1,True,False,"768",None,float("nan"),float("inf"),-float("inf")]:
            with self.subTest(width=width):
                with self.assertRaises(ValueError):
                    classify_width(width)
    def test_screen_width_category_mismatch_rejected(self):
        for category,width in [("mobile",768),("desktop",767.999)]:
            with self.subTest(category=category):
                data=fixture(category);data["document"]["referenceSize"]["width"]=width
                self.assertEqual(self.evaluate(data)["structure"]["status"],"failed")
    def test_profile_baseline_category_mismatch_rejected(self):
        data=fixture("mobile")
        data["rules"]["profiles"]["mobile"]["environment"]["baselineWidth"]=768
        self.assertEqual(self.evaluate(data)["structure"]["status"],"failed")
    def test_validation_width_category_mismatch_rejected(self):
        data=fixture()
        data["rules"]["profiles"]["desktop"]["validationCases"][0]["width"]=767
        self.assertEqual(self.evaluate(data)["structure"]["status"],"failed")
    def test_third_profile_rejected(self):
        data=fixture()
        data["rules"]["profiles"]["tablet"]=copy.deepcopy(data["rules"]["profiles"]["desktop"])
        self.assertEqual(self.evaluate(data)["structure"]["status"],"failed")
    def test_form_factor_must_match_profile_key(self):
        data=fixture()
        data["rules"]["profiles"]["desktop"]["formFactor"]="mobile"
        self.assertEqual(self.evaluate(data)["structure"]["status"],"failed")
    def test_fixed_breakpoint_cannot_change(self):
        data=fixture();data["rules"]["classification"]["breakpoint"]=769
        self.assertEqual(self.evaluate(data)["structure"]["status"],"failed")
    def test_additional_width_mode_allowed(self):
        data=fixture()
        data["rules"]["profiles"]["desktop"]["modes"]=[{"id":"wide","when":{"width":[1024,None]}}]
        self.assert_valid(data)
    def test_touching_width_modes_allowed(self):
        data=fixture()
        data["rules"]["profiles"]["desktop"]["modes"]=[
            {"id":"compact","when":{"width":[768,1024]}},
            {"id":"wide","when":{"width":[1024,None]}}]
        self.assert_valid(data)
    def test_overlapping_width_modes_rejected(self):
        data=fixture()
        data["rules"]["profiles"]["desktop"]["modes"]=[
            {"id":"compact","when":{"width":[768,1100]}},
            {"id":"wide","when":{"width":[1024,None]}}]
        self.assertEqual(self.evaluate(data)["structure"]["status"],"failed")
    def test_empty_width_mode_rejected(self):
        data=fixture()
        data["rules"]["profiles"]["desktop"]["modes"]=[
            {"id":"empty","when":{"width":[1024,1024]}}]
        self.assertEqual(self.evaluate(data)["structure"]["status"],"failed")
    def test_mode_outside_profile_rejected(self):
        for category,bounds in [("mobile",[768,1024]),("desktop",[None,768])]:
            with self.subTest(category=category):
                data=fixture(category)
                data["rules"]["profiles"][category]["modes"]=[{"id":"unreachable","when":{"width":bounds}}]
                self.assertEqual(self.evaluate(data)["structure"]["status"],"failed")
    def test_disjoint_width_theme_modes_allowed(self):
        data=fixture()
        data["rules"]["profiles"]["desktop"]["modes"]=[
            {"id":"compact-light","when":{"width":[768,1024],"theme":"light"}},
            {"id":"compact-dark","when":{"width":[768,1024],"theme":"dark"}}]
        self.assert_valid(data)
    def test_overlapping_width_and_theme_modes_rejected(self):
        data=fixture()
        data["rules"]["profiles"]["desktop"]["modes"]=[
            {"id":"compact","when":{"width":[768,1024]}},
            {"id":"dark","when":{"theme":"dark"}}]
        self.assertEqual(self.evaluate(data)["structure"]["status"],"failed")
    def test_undeclared_adaptive_field_rejected(self):
        data=fixture("mobile")
        data["rules"]["profiles"]["mobile"]["modes"]=[{"id":"compact","when":{"width":[None,400]}}]
        data["document"]["tree"]["policy"]["adaptive"]=["sizing"]
        data["document"]["tree"]["responsive"]=[
            {"modeId":"compact","overrides":{"layout":{"gap":24}}}]
        report=self.evaluate(data)
        self.assertEqual(report["structure"]["status"],"failed")
        self.assertTrue(any("undeclared adaptive field" in item for item in report["structure"]["failures"]))
    def test_documented_grid_example(self):
        guide=(Path(__file__).resolve().parents[1]/"references"/"layout-rules.md").read_text(encoding="utf-8")
        section=guide.split("## 4. 尺寸、样式与响应式对齐规范",1)[1]
        example=json.loads(re.search(r"```json\n(.*?)\n```",section,re.S).group(1))
        data=fixture()
        data["rules"]["profiles"]["desktop"]["modes"]=example["modes"]
        data["document"]["tree"].update(example["node"])
        self.assert_valid(data)
    def test_height_does_not_change_category(self):
        for category,height in [("mobile",180),("desktop",10000)]:
            with self.subTest(category=category):
                data=fixture(category);data["document"]["referenceSize"]["height"]=height
                self.assert_valid(data)
    def test_unconverted_units_rejected(self):
        data=fixture("mobile");data["rules"]["profiles"]["mobile"]["units"]["layout"]="dp"
        self.assertEqual(self.evaluate(data)["structure"]["status"],"failed")
    def test_unknown_width_stays_draft_without_third_class(self):
        data=fixture();data["manifest"]["authority"]="draft"
        data["manifest"]["issues"]=[{"id":"width-unknown","documentId":None,
                                    "message":"Source scale and logical width are unknown",
                                    "critical":True,"status":"open","resolution":None}]
        data["rules"]["profiles"]={};data["documents"]=[]
        report=self.evaluate(data)
        self.assertEqual(report["structure"]["status"],"passed",report)
        self.assertEqual(report["readiness"]["status"],"blocked",report)
        self.assertEqual(report["counts"]["documents"],0)
    def test_canonical_requires_classified_documents(self):
        data=fixture();data["rules"]["profiles"]={};data["documents"]=[]
        self.assertEqual(self.evaluate(data)["structure"]["status"],"failed")
    def test_both_profiles_in_one_package(self):
        data=fixture();mobile=fixture("mobile")
        data["rules"]["profiles"].update(mobile["rules"]["profiles"])
        doc=mobile["document"];doc["id"]="mobile-example";doc["title"]="Mobile example"
        doc["tree"]["id"]="mobile-root"
        doc["tree"]["children"][0].update(id="mobile-title",parentId="mobile-root")
        data["documents"]=[data["document"],doc]
        report=self.evaluate(data)
        self.assertEqual(report["structure"]["status"],"passed",report)
        self.assertEqual(report["readiness"]["status"],"ready",report)
        self.assertEqual(report["counts"]["documents"],2)
    def test_overlay_anchor(self):
        data=fixture()
        root=data["document"]["tree"];root["layout"]={"type":"overlay","padding":[0,0,0,0]}
        position=root["children"][0]["placement"]
        position.update(mode="anchored",anchorId="root")
        position["insets"]["top"]=8;position["insets"]["right"]=8
        self.assert_valid(data)
    def test_partial_responsive(self):
        data=fixture("mobile")
        data["rules"]["profiles"][data["document"]["profileId"]]["modes"]=[{"id":"wide","when":{"height":[700,None]}}]
        data["document"]["tree"]["responsive"]=[{"modeId":"wide","overrides":{"layout":{"type":"flex","gap":24}}}]
        self.assert_valid(data)
    def test_parent_child_resolve_same_mode(self):
        data=fixture("mobile")
        data["rules"]["profiles"][data["document"]["profileId"]]["modes"]=[{"id":"wide","when":{"height":[700,None]}}]
        root=data["document"]["tree"]
        root["responsive"]=[{"modeId":"wide","overrides":{"layout":grid()}}]
        child=root["children"][0]
        child["policy"]["adaptive"]=["sizing","placement.gridArea"]
        child["responsive"]=[{"modeId":"wide","overrides":{"placement":{"gridArea":{"row":1,"column":2,"rowSpan":1,"columnSpan":1}}}}]
        self.assert_valid(data)
    def test_touching_mode_boundaries(self):
        data=fixture()
        data["rules"]["profiles"][data["document"]["profileId"]]["modes"]=[
            {"id":"narrow","when":{"height":[0,900]}},{"id":"wide","when":{"height":[900,None]}}]
        self.assert_valid(data)
    def test_overlapping_modes_rejected(self):
        data=fixture()
        data["rules"]["profiles"][data["document"]["profileId"]]["modes"]=[
            {"id":"a","when":{"height":[0,1000]}},{"id":"b","when":{"height":[900,None]}}]
        self.assertEqual(self.evaluate(data)["structure"]["status"],"failed")
    def test_missing_style_rejected(self):
        data=fixture();data["document"]["tree"]["styleRef"]="missing"
        self.assertEqual(self.evaluate(data)["structure"]["status"],"failed")
    def test_duplicate_node_rejected(self):
        data=fixture();data["document"]["tree"]["children"][0]["id"]="root"
        self.assertEqual(self.evaluate(data)["structure"]["status"],"failed")
    def test_wrong_parent_rejected(self):
        data=fixture();data["document"]["tree"]["children"][0]["parentId"]="missing"
        self.assertEqual(self.evaluate(data)["structure"]["status"],"failed")
    def test_layout_alternatives_rejected(self):
        data=fixture();data["document"]["tree"]["layoutOptions"]=[flex(),grid()]
        self.assertEqual(self.evaluate(data)["structure"]["status"],"failed")
    def test_missing_anchor_rejected(self):
        data=fixture();data["document"]["tree"]["children"][0]["placement"].update(mode="anchored",anchorId="missing")
        self.assertEqual(self.evaluate(data)["structure"]["status"],"failed")
    def test_anchor_cycle_rejected(self):
        data=fixture();root=data["document"]["tree"]
        root["placement"].update(mode="anchored",anchorId="title")
        root["children"][0]["placement"].update(mode="anchored",anchorId="root")
        self.assertEqual(self.evaluate(data)["structure"]["status"],"failed")
    def test_locked_override_rejected(self):
        data=fixture();data["rules"]["profiles"][data["document"]["profileId"]]["modes"]=[{"id":"wide","when":{"height":[1000,None]}}]
        data["document"]["tree"]["responsive"]=[{"modeId":"wide","overrides":{"styleRef":"body"}}]
        self.assertEqual(self.evaluate(data)["structure"]["status"],"failed")
    def test_policy_conflict_rejected(self):
        data=fixture();data["document"]["tree"]["policy"]["adaptive"]=["styleRef"]
        self.assertEqual(self.evaluate(data)["structure"]["status"],"failed")
    def test_hash_mismatch_rejected(self):
        def corrupt(base):
            p=base/"documents"/"Example interface.json";p.write_text(p.read_text(encoding="utf-8")+" ",encoding="utf-8")
        self.assertEqual(self.evaluate(fixture(),corrupt)["structure"]["status"],"failed")
    def test_package_path_escape_rejected(self):
        def escape(base):
            p=base/"manifest.json";m=json.loads(p.read_text(encoding="utf-8"));m["documents"][0]["file"]="../outside.json"
            p.write_text(json.dumps(m),encoding="utf-8")
        self.assertEqual(self.evaluate(fixture(),escape)["structure"]["status"],"failed")
    def test_critical_issue_blocks_canonical(self):
        data=fixture();data["manifest"]["issues"]=[{"id":"missing-rule","documentId":"example",
            "message":"A critical rule is not specified","critical":True,"status":"open","resolution":None}]
        self.assertEqual(self.evaluate(data)["readiness"]["status"],"blocked")
    def test_draft_preserves_critical_issue(self):
        data=fixture();data["manifest"]["authority"]="draft"
        data["manifest"]["issues"]=[{"id":"missing-rule","documentId":"example",
            "message":"A critical rule is not specified","critical":True,"status":"open","resolution":None}]
        report=self.evaluate(data)
        self.assertEqual(report["structure"]["status"],"passed",report)
        self.assertEqual(report["readiness"]["status"],"blocked")
    def test_missing_critical_asset_blocks_canonical(self):
        data=fixture();data["library"]["assets"]["font"]={"kind":"font","file":None,"embedded":None,
            "sha256":None,"availability":"missing","critical":True}
        self.assertEqual(self.evaluate(data)["readiness"]["status"],"blocked")
    def test_embedded_vector_asset(self):
        data=fixture();child=data["document"]["tree"]["children"][0]
        child.update(kind="vector",content={"type":"vector","assetRef":"icon"})
        data["library"]["assets"]["icon"]={"kind":"vector","file":None,"embedded":{"viewBox":[0,0,24,24],"path":"M0 0L24 24"},
            "sha256":None,"availability":"available","critical":True}
        self.assert_valid(data)
    def test_visual_pass_needs_evidence(self):
        data=fixture();data["manifest"]["verification"]["baselineVisual"]="passed"
        self.assertEqual(self.evaluate(data)["structure"]["status"],"failed")
    def test_deprecated_platform_field_rejected(self):
        data=fixture();data["rules"]["profiles"]["desktop"]["platform"]="web"
        self.assertEqual(self.evaluate(data)["structure"]["status"],"failed")
    def test_size_conflict_rejected(self):
        data=fixture();data["document"]["tree"]["sizing"]["width"].update(min=600,max=300)
        self.assertEqual(self.evaluate(data)["structure"]["status"],"failed")

    def test_cli_accepts_ready_package(self):
        with tempfile.TemporaryDirectory(prefix="ui-spec-normalizer-tests-",dir=TEST_TEMP_ROOT) as folder:
            base=Path(folder).resolve()
            write_fixture(base,fixture())
            run=subprocess.run([sys.executable,"-X","utf8","-B",str(Path(__file__).with_name("validate_spec.py")),str(base)],
                               capture_output=True,text=True,encoding="utf-8")
            self.assertEqual(run.returncode,0,run.stderr)
            report=json.loads(run.stdout)
            self.assertEqual(report["structure"]["status"],"passed")
            self.assertEqual(report["baselineVisual"],"not-tested")
    def test_cli_blocks_canonical_without_conflating_structure(self):
        with tempfile.TemporaryDirectory(prefix="ui-spec-normalizer-tests-",dir=TEST_TEMP_ROOT) as folder:
            base=Path(folder).resolve();data=fixture()
            data["manifest"]["issues"]=[{"id":"pending","documentId":"example","message":"Critical unknown",
                                         "critical":True,"status":"open","resolution":None}]
            write_fixture(base,data)
            run=subprocess.run([sys.executable,"-X","utf8","-B",str(Path(__file__).with_name("validate_spec.py")),str(base)],
                               capture_output=True,text=True,encoding="utf-8")
            self.assertEqual(run.returncode,1,run.stderr)
            report=json.loads(run.stdout)
            self.assertEqual(report["structure"]["status"],"passed")
            self.assertEqual(report["readiness"]["status"],"blocked")
    def test_cli_preserves_valid_draft(self):
        with tempfile.TemporaryDirectory(prefix="ui-spec-normalizer-tests-",dir=TEST_TEMP_ROOT) as folder:
            base=Path(folder).resolve();data=fixture()
            data["manifest"]["authority"]="draft"
            data["manifest"]["issues"]=[{"id":"pending","documentId":"example","message":"Critical unknown",
                                         "critical":True,"status":"open","resolution":None}]
            write_fixture(base,data)
            run=subprocess.run([sys.executable,"-X","utf8","-B",str(Path(__file__).with_name("validate_spec.py")),str(base)],
                               capture_output=True,text=True,encoding="utf-8")
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertEqual(json.loads(run.stdout)["readiness"]["status"],"blocked")

if __name__=="__main__":
    parser=argparse.ArgumentParser(add_help=False)
    parser.add_argument("--temp-root")
    args,remaining=parser.parse_known_args()
    if args.temp_root:
        TEST_TEMP_ROOT=str(Path(args.temp_root).resolve())
        Path(TEST_TEMP_ROOT).mkdir(parents=True,exist_ok=True)
    unittest.main(argv=[sys.argv[0],*remaining],verbosity=2)
