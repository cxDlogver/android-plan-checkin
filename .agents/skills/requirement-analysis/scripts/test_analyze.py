#!/usr/bin/env python3
"""Contract tests for final-only graphs, direct sources and real result branches."""
import argparse
import contextlib
import copy
import hashlib
import io
import json
import shutil
import struct
import subprocess
import tempfile
import unittest
import zlib
from pathlib import Path
from analyze import evaluate, execute, check_html, load_json, canonical

TEMP_ROOT=None
PRD="用户在未保存草稿上保存。成功时记录已保存；失败时草稿保留并显示失败。草稿内容可见。"
def h(raw): return hashlib.sha256(raw).hexdigest()
def assertion(p,v): return {"path":p,"op":"eq","value":v}
def observation(): return {"method":"观察界面及查询当前记录","locator":"当前草稿对应项"}
def fact(text,p,v): return {"statement":text,"assertion":assertion(p,v),"observation":observation()}
def model_fixture(base):
    prd=base/"prd.md";prd.write_text(PRD,encoding="utf-8")
    doc={"kind":"document","path":"../prd.md","locator":"L1","quote":PRD,"sha256":h(prd.read_bytes())}
    ui={"id":"UI1","tree":{"id":"root","children":[]}}
    (base/"ui.json").write_text(json.dumps(ui),encoding="utf-8")
    def chunk(k,p): return struct.pack(">I",len(p))+k+p+struct.pack(">I",zlib.crc32(k+p)&0xffffffff)
    png=b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",1,1,8,2,0,0,0))+chunk(b"IDAT",zlib.compress(b"\x00\x00\x00\x00"))+chunk(b"IEND",b"")
    (base/"design.png").write_bytes(png)
    uref={"kind":"ui","structurePath":"../ui.json","documentId":"UI1","nodeIds":["root"],"structureSha256":h((base/"ui.json").read_bytes()),"screenshotPath":"../design.png","screenshotSha256":h(png)}
    def state(i,text,initial,p,v):
        return {"id":i,"title":text,"statement":text,"isInitial":initial,"source":[copy.deepcopy(doc)],"functionalFacts":[fact(text,p,v)],"visualFacts":[]}
    model={"schemaVersion":"2.0.0","title":"保存草稿的结果","revision":1,
      "states":[state("D","草稿未保存",True,"plan.saved",False),state("S","记录已保存",False,"plan.saved",True),state("F","草稿保留且失败可见",False,"save.result","failure")],"transitions":[],"constraints":[]}
    model["states"][0]["source"].append(uref)
    model["states"][0]["visualFacts"]=[{"statement":"草稿内容可见","assertion":{"path":"ui.presentation","op":"matches-ui","value":{k:uref[k] for k in ("documentId","nodeIds","structureSha256")}},"observation":observation()}]
    for i,target,status in (("ES","S","success"),("EF","F","failure")):
        model["transitions"].append({"id":i,"from":"D","to":target,
          "operation":{"label":"保存","actor":"用户","input":{"title":"阅读"}},"source":[copy.deepcopy(doc)],
          "condition":{"statement":"保存结果为"+status,"match":{"outcome.status":[status]},"sampleOutcome":{"outcome":{"status":status}},"observation":observation()}})
    output=base/"analysis";output.mkdir();path=output/"state-transitions.json"
    path.write_text(json.dumps(model,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return model,path

class Contracts(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="graph-contract-",dir=TEMP_ROOT)
        self.base=Path(self.temp.name);self.model,self.path=model_fixture(self.base)
    def tearDown(self): self.temp.cleanup()
    def report(self): return evaluate(self.model,self.path,self.base)
    def gate(self,name): return next(c for c in self.report()["checks"] if c["id"]==name)["status"]
    def command(self,name):
        with contextlib.redirect_stdout(io.StringIO()): return execute(name,self.path,self.base)
    def save(self): self.path.write_text(json.dumps(self.model,ensure_ascii=False)+"\n",encoding="utf-8")
    def unconditional(self):
        self.model["states"]=self.model["states"][:2];self.model["transitions"]=self.model["transitions"][:1]
        del self.model["transitions"][0]["condition"]
    def test_disjoint_result_branches_pass(self): self.assertEqual(self.report()["status"],"passed")
    def test_unconditional_transition_has_no_condition(self):
        self.unconditional();self.assertEqual(self.report()["status"],"passed")
    def test_condition_requires_alternative_branch(self):
        self.model["transitions"]=self.model["transitions"][:1]
        self.assertEqual(self.gate("branch"),"failed")
    def test_conditions_must_change_result(self):
        self.model["transitions"][1]["to"]="S"
        self.assertEqual(self.gate("branch"),"failed")
    def test_overlapping_conditions_rejected(self):
        self.model["transitions"][1]["condition"]=copy.deepcopy(self.model["transitions"][0]["condition"])
        self.assertEqual(self.gate("branch"),"failed")
    def test_missing_condition_in_branch_group_rejected(self):
        del self.model["transitions"][1]["condition"]
        self.assertEqual(self.gate("branch"),"failed")
    def test_precondition_is_not_result_condition(self):
        self.model["transitions"][0]["condition"]["match"]={"input.valid":[True]}
        self.assertEqual(self.gate("branch"),"failed")
    def test_sample_must_satisfy_condition(self):
        self.model["transitions"][0]["condition"]["sampleOutcome"]={"outcome":{"status":"unknown"}}
        self.assertEqual(self.gate("branch"),"failed")
    def test_old_always_placeholder_rejected(self):
        self.unconditional();self.model["transitions"][0]["condition"]={"kind":"always"}
        self.assertEqual(self.gate("schema"),"failed")
    def test_duplicate_deterministic_edges_rejected(self):
        self.unconditional();edge=copy.deepcopy(self.model["transitions"][0]);edge["id"]="OTHER";self.model["transitions"].append(edge)
        self.assertEqual(self.gate("branch"),"failed")
    def test_action_key_normalizes_whitespace_case_and_numbers(self):
        self.model["transitions"][0]["operation"].update(label=" Save ",actor=" USER ",input={"a":1,"b":2})
        self.model["transitions"][1]["operation"].update(label="save",actor="user",input={"b":2,"a":1.0})
        self.model["transitions"][1]["condition"]=copy.deepcopy(self.model["transitions"][0]["condition"])
        self.assertEqual(self.gate("branch"),"failed")
    def test_process_fields_are_not_final_graph_fields(self):
        for field in ("clauses","clarifications","operations","sources","gates","semanticReviews","entries","actionAnalysis","scope","status"):
            with self.subTest(field=field):
                model=copy.deepcopy(self.model);model[field]=[]
                self.assertEqual(evaluate(model,self.path,self.base)["checks"][0]["status"],"failed")
    def test_operation_has_no_id(self):
        self.model["transitions"][0]["operation"]["id"]="SAVE"
        self.assertEqual(self.gate("schema"),"failed")
    def test_operation_id_reference_rejected(self):
        self.model["transitions"][0]["operationId"]="SAVE"
        self.assertEqual(self.gate("schema"),"failed")
    def test_no_input_is_valid_but_empty_input_is_omitted(self):
        for e in self.model["transitions"]: del e["operation"]["input"]
        self.assertEqual(self.gate("operation"),"passed")
        self.model["transitions"][0]["operation"]["input"]={}
        self.assertEqual(self.gate("operation"),"failed")
    def test_source_must_be_direct_document_or_ui(self):
        self.model["states"][0]["source"]=[{"id":"C1"}]
        self.assertEqual(self.gate("schema"),"failed")
    def test_document_quote_locator_and_hash(self):
        self.model["states"][1]["source"][0]["locator"]="L5"
        self.assertEqual(self.gate("source"),"failed")
    def test_source_revision_drift_detected(self):
        (self.base/"prd.md").write_text("changed",encoding="utf-8")
        self.assertEqual(self.gate("source"),"failed")
    def test_json_pointer_source_is_direct(self):
        self.model["constraints"]=[{"id":"C","statement":"UI根节点按既定结构验收","source":[{"kind":"document","path":"../ui.json","locator":"/tree","sha256":h((self.base/"ui.json").read_bytes())}]}]
        self.assertEqual(self.gate("source"),"passed")
        self.model["constraints"][0]["source"][0]["locator"]="/missing"
        self.assertEqual(self.gate("source"),"failed")
    def test_reference_cannot_escape_workspace(self):
        self.model["states"][0]["source"][0]["path"]="../../outside.md"
        self.assertEqual(self.gate("source"),"failed")
    def test_visual_fact_needs_direct_ui_source(self):
        self.model["states"][0]["source"]=self.model["states"][0]["source"][:1]
        self.assertEqual(self.gate("facts"),"failed")
    def test_ui_nodes_and_screenshot_hash_checked(self):
        self.model["states"][0]["source"][1]["screenshotSha256"]="0"*64
        self.assertEqual(self.gate("source"),"failed")
    def test_ui_assertion_matches_state_source(self):
        self.model["states"][0]["visualFacts"][0]["assertion"]["value"]["nodeIds"]=["missing"]
        self.assertEqual(self.gate("facts"),"failed")
    def test_visual_only_state_is_valid(self):
        self.model["states"]=self.model["states"][:1];self.model["states"][0]["functionalFacts"]=[];self.model["transitions"]=[]
        self.assertEqual(self.report()["status"],"passed")
    def test_empty_state_rejected(self):
        self.model["states"][0].update(functionalFacts=[],visualFacts=[])
        self.assertEqual(self.gate("facts"),"failed")
    def test_unreachable_state_rejected(self):
        self.model["transitions"]=self.model["transitions"][:1]
        self.assertEqual(self.gate("reachability"),"failed")
    def test_self_loop_requires_real_observable_relation(self):
        self.model["transitions"][0]["to"]="D"
        self.assertEqual(self.gate("operation"),"failed")
        self.model["transitions"][0]["effects"]=[{"statement":"记录本次结果","assertion":{"path":"after.result","op":"eq-ref","value":"outcome.status"}}]
        self.assertEqual(self.gate("operation"),"passed")
    def test_duplicate_global_constraint_rejected(self):
        c={"id":"C","statement":"统一规则","source":[copy.deepcopy(self.model["states"][0]["source"][0])]}
        self.model["constraints"]=[c,{**copy.deepcopy(c),"id":"C2"}]
        self.assertEqual(self.gate("constraints"),"failed")
    def test_state_fact_not_repeated_as_global_constraint(self):
        self.model["constraints"]=[{"id":"C","statement":self.model["states"][0]["visualFacts"][0]["statement"],"source":[copy.deepcopy(self.model["states"][0]["source"][0])]}]
        self.assertEqual(self.gate("constraints"),"failed")
    def test_commands_do_not_mutate_graph_json(self):
        before=self.path.read_bytes()
        self.assertEqual(self.command("validate"),0);self.assertEqual(self.command("render"),0);self.assertEqual(self.command("check"),0)
        self.assertEqual(before,self.path.read_bytes())
        self.assertEqual({p.name for p in self.path.parent.iterdir()},{"state-transitions.json","state-transitions.html"})
    def test_html_sync_drift_and_escaping(self):
        self.model["title"]="</script><script>unsafe()</script>";self.save();self.command("render")
        html=self.path.with_suffix(".html");text=html.read_text(encoding="utf-8")
        self.assertNotIn("</script><script>unsafe()",text);self.assertEqual(check_html(self.model,self.path),[])
        html.write_text(text.replace('id="model"','id="wrong"'),encoding="utf-8")
        self.assertTrue(check_html(self.model,self.path))
    def test_html_template_drift_detected_even_when_embedded_model_matches(self):
        self.command("render");file=self.path.with_suffix(".html");text=file.read_text(encoding="utf-8")
        file.write_text(text.replace("function toggleSidebar", "function staleSidebar"),encoding="utf-8")
        self.assertTrue(check_html(self.model,self.path))

    @unittest.skipUnless(shutil.which("node"),"Node needed for Canvas simulation")
    def test_canvas_interaction_and_process_removal(self):
        self.command("render")
        result=subprocess.run([shutil.which("node"),str(Path(__file__).with_name("test_canvas.js")),str(self.path.with_suffix(".html"))],capture_output=True,text=True,encoding="utf-8")
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--temp-root")
    args,remaining=parser.parse_known_args();TEMP_ROOT=args.temp_root
    unittest.main(argv=[__file__]+remaining,verbosity=2)
