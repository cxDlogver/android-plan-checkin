#!/usr/bin/env python3
"""Atomic derivation, source binding, exact adjacency and HTML integration tests."""
import argparse
import contextlib
import copy
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from analyze import canonical, digest, execute as state_execute, load_json
from atomic import build, derive, evaluate, execute, output_path
from test_analyze import model_fixture

TEMP_ROOT=None

class AtomicContracts(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="atomic-contract-",dir=TEMP_ROOT)
        self.base=Path(self.temp.name);self.state,self.graph=model_fixture(self.base);self.path=output_path(self.graph)
        self.model=derive(self.state,self.graph,self.path)
    def tearDown(self): self.temp.cleanup()
    def gate(self,name): return next(c for c in evaluate(self.model,self.path,self.base)["checks"] if c["id"]==name)["status"]
    def save_state(self):
        self.graph.write_text(json.dumps(self.state,ensure_ascii=False)+"\n",encoding="utf-8")
        self.model=derive(self.state,self.graph,self.path)
    def cyclic(self):
        for ident,source in (("BACK_S","S"),("BACK_F","F")):
            self.state["transitions"].append({"id":ident,"from":source,"to":"D","operation":{"label":"返回草稿","actor":"用户"},"source":copy.deepcopy(self.state["states"][0]["source"][:1])})
        self.save_state()
    def test_one_transition_one_requirement_including_result_branches(self):
        self.assertEqual(len(self.model["requirements"]),2)
        self.assertEqual({r["transitionId"] for r in self.model["requirements"]},{"ES","EF"})
        self.assertEqual(self.gate("one-to-one"),"passed")
        self.assertEqual([e["kind"] for e in self.model["edges"]],["restart"])
    def test_only_selected_route_pairs_are_retained(self):
        self.cyclic();sequence=self.model["coverage"]["sequence"]
        expected=set(zip(sequence,sequence[1:]))
        self.assertEqual({(e["from"],e["to"]) for e in self.model["edges"]},expected)
        self.assertEqual(self.model["coverage"]["visitCount"],4);self.assertEqual(self.gate("selected-edges"),"passed")
    def test_same_title_different_state_id_does_not_form_a_handoff(self):
        for s in self.state["states"]: s["title"]="同一标题"
        self.save_state();self.assertTrue(all(e["kind"]=="restart" for e in self.model["edges"]))
    def test_state_self_loop_is_covered_without_an_unused_requirement_self_link(self):
        loop={"id":"LOOP","from":"D","to":"D","operation":{"label":"检查并更新计数","actor":"用户"},"source":copy.deepcopy(self.state["states"][0]["source"][:1]),"effects":[{"statement":"检查次数已增加","assertion":{"path":"after.count","op":"eq","value":1}}]}
        self.state["transitions"].append(loop);self.save_state()
        self.assertEqual(self.model["coverage"]["sequence"].count("R-LOOP"),1)
        self.assertFalse(any(e["from"]==e["to"]=="R-LOOP" for e in self.model["edges"]))
        self.assertEqual(self.gate("selected-edges"),"passed")
    def test_isolated_initial_state_does_not_create_a_fake_requirement(self):
        self.state["states"]=self.state["states"][:1];self.state["transitions"]=[];self.save_state()
        self.assertEqual(self.model["requirements"],[]);self.assertEqual(self.model["edges"],[]);self.assertEqual(self.model["coverage"]["visitCount"],0);self.assertEqual(evaluate(self.model,self.path,self.base)["status"],"passed")
    def test_requirement_mapping_rejects_missing_duplicate_and_wrong_transition(self):
        original=copy.deepcopy(self.model)
        for edit in (lambda m:m["requirements"].pop(),lambda m:m["requirements"].append(copy.deepcopy(m["requirements"][0])),lambda m:m["requirements"][0].update(transitionId="missing")):
            self.model=copy.deepcopy(original);edit(self.model);self.assertEqual(self.gate("one-to-one"),"failed")
    def test_selected_edges_reject_unused_missing_duplicate_and_wrong_type(self):
        self.cyclic();original=copy.deepcopy(self.model)
        for edit in [lambda m:m["edges"].pop(),lambda m:m["edges"].append(copy.deepcopy(m["edges"][0])),lambda m:m["edges"][0].update(viaStateId="missing-state")]:
            self.model=copy.deepcopy(original);edit(self.model);self.assertEqual(self.gate("selected-edges"),"failed")
        self.model=copy.deepcopy(original);self.model["edges"].append({"id":"EXTRA","from":"R-ES","to":"R-EF","kind":"restart"});self.assertEqual(self.gate("selected-edges"),"failed")
    def test_coverage_rejects_missing_visits_illegal_entry_and_false_optimality(self):
        original=copy.deepcopy(self.model)
        self.model["coverage"]["sequence"].pop();self.assertEqual(self.gate("coverage"),"failed")
        self.model=copy.deepcopy(original);self.model["coverage"]["minimumVisitCount"]+=1;self.assertEqual(self.gate("optimality"),"failed")
        self.model=copy.deepcopy(original);self.model["coverage"]["sequence"].append(self.model["coverage"]["sequence"][-1]);self.model["coverage"]["visitCount"]+=1;self.assertEqual(self.gate("optimality"),"failed")
    def test_nonmatching_noninitial_entry_is_rejected(self):
        self.cyclic();self.model["coverage"]["sequence"]=["R-EF","R-BACK_S","R-ES","R-BACK_F"]
        report=evaluate(self.model,self.path,self.base);check=next(c for c in report["checks"] if c["id"]=="coverage")
        self.assertEqual(check["status"],"failed");self.assertTrue(any("Illegal entry" in note for note in check["findings"]))

    def test_schema_rejects_process_fields_and_copied_operations(self):
        self.model["clarifications"]=[];self.assertEqual(self.gate("schema"),"failed");del self.model["clarifications"]
        self.model["requirements"][0]["operation"]={"label":"另一个动作"};self.assertEqual(self.gate("schema"),"failed")
    def test_state_graph_hash_and_revision_drift(self):
        self.model["stateGraph"]["sha256"]="0"*64;self.assertEqual(self.gate("state-graph"),"failed")
        self.model=derive(self.state,self.graph,self.path);self.model["revision"]+=1;self.assertEqual(self.gate("one-to-one"),"failed")
    def test_upstream_source_drift_fails(self):
        (self.base/"prd.md").write_text("changed",encoding="utf-8");self.assertEqual(self.gate("state-graph"),"failed")
    def test_relative_reference_cannot_escape_workspace(self):
        self.model["stateGraph"]["path"]="../../outside.json";self.assertEqual(self.gate("state-graph"),"failed")
    def test_reordering_input_does_not_change_atomic_ids_or_links(self):
        self.cyclic();before=copy.deepcopy(self.model);self.state["transitions"].reverse();self.save_state()
        self.assertEqual(self.model["requirements"],before["requirements"]);self.assertEqual(self.model["edges"],before["edges"])
    def test_build_check_read_only_and_template_or_embedded_state_drift(self):
        self.cyclic();before=self.graph.read_bytes();self.assertEqual(build(self.graph,self.base)["status"],"passed")
        self.assertEqual(self.graph.read_bytes(),before);atomic_before=self.path.read_bytes()
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(execute("check",self.path,self.base),0)
        self.assertEqual(self.path.read_bytes(),atomic_before)
        html=self.path.with_suffix(".html");text=html.read_text(encoding="utf-8");self.assertIn('id="stateModel"',text)
        html.write_text(text.replace("function toggleSidebar","function obsoleteToggle"),encoding="utf-8")
        self.assertEqual(evaluate(load_json(self.path),self.path,self.base,with_html=True)["status"],"failed")
    def test_embedded_state_snapshot_drift_is_rejected(self):
        self.assertEqual(build(self.graph,self.base)["status"],"passed")
        file=self.path.with_suffix(".html");text=file.read_text(encoding="utf-8");changed=copy.deepcopy(self.state);changed["title"]="changed snapshot"
        file.write_text(text.replace(canonical(self.state),canonical(changed)),encoding="utf-8")
        self.assertEqual(evaluate(load_json(self.path),self.path,self.base,with_html=True)["status"],"failed")

    def test_build_preserves_existing_atomic_outputs_if_upstream_is_invalid(self):
        self.assertEqual(build(self.graph,self.base)["status"],"passed");before=self.path.read_bytes()
        self.state["transitions"][0]["to"]="missing";self.graph.write_text(json.dumps(self.state,ensure_ascii=False),encoding="utf-8");self.assertEqual(build(self.graph,self.base)["status"],"failed");self.assertEqual(self.path.read_bytes(),before)
    @unittest.skipUnless(shutil.which("node"),"Node needed for Canvas simulation")
    def test_shared_canvas_atomic_mode(self):
        self.cyclic();self.assertEqual(build(self.graph,self.base)["status"],"passed")
        result=subprocess.run([shutil.which("node"),str(Path(__file__).with_name("test_canvas.js")),str(self.path.with_suffix(".html"))],capture_output=True,text=True,encoding="utf-8")
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    @unittest.skipUnless(shutil.which("node"),"Node needed for Canvas simulation")
    def test_shared_canvas_with_no_atomic_nodes(self):
        self.state["states"]=self.state["states"][:1];self.state["transitions"]=[];self.save_state()
        self.assertEqual(build(self.graph,self.base)["status"],"passed")
        result=subprocess.run([shutil.which("node"),str(Path(__file__).with_name("test_canvas.js")),str(self.path.with_suffix(".html"))],capture_output=True,text=True,encoding="utf-8")
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
    @unittest.skipUnless(shutil.which("node"),"Node needed for Canvas simulation")
    def test_shared_canvas_with_functional_facts_only_and_no_handoffs(self):
        for s in self.state["states"]:
            s["source"]=[source for source in s["source"] if source["kind"]=="document"];s["visualFacts"]=[]
        self.save_state();self.assertEqual(build(self.graph,self.base)["status"],"passed")
        result=subprocess.run([shutil.which("node"),str(Path(__file__).with_name("test_canvas.js")),str(self.path.with_suffix(".html"))],capture_output=True,text=True,encoding="utf-8")
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--temp-root")
    args,remaining=parser.parse_known_args();TEMP_ROOT=args.temp_root
    unittest.main(argv=[__file__]+remaining,verbosity=2)
