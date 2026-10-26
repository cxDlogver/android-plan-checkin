#!/usr/bin/env python3
"""Separate work-schema validation and cleanup tests."""
import argparse
import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from analyze import SKILL_DIR, raw_hash, execute as graph_execute, load_json, schema_errors
from work import REVIEW_NAMES, check_work, execute, work_file
from test_analyze import model_fixture

TEMP_ROOT=None

def make_work(model,graph):
    document=copy.deepcopy(model["states"][0]["source"][0]);ui=copy.deepcopy(model["states"][0]["source"][1])
    actions=[]
    if model["transitions"]:
        edge=model["transitions"][0]
        actions=[{"from":edge["from"],"operation":copy.deepcopy(edge["operation"]),"basis":"explicit",
                  "change":"未保存草稿经保存后，按实际响应进入记录已保存或失败保留草稿的结果。",
                  "disposition":"modeled","expectedTargets":list(dict.fromkeys(e["to"] for e in model["transitions"])),
                  "transitionIds":[e["id"] for e in model["transitions"]],"reason":"PRD明确保存动作及成功、失败两种可观察结果。"}]
    return {"workSchemaVersion":"1.0.0","graphSha256":raw_hash(graph.read_bytes()),
      "documents":[{"source":document,"role":"prd","authorization":"当前测试PRD","version":None},
                   {"source":ui,"role":"ui","authorization":"测试PRD引用的UI","version":None}],
      "requirements":[{"source":document,"classification":"included","reason":"本次验收全部保存结果及草稿呈现",
                       "targets":[{"collection":key,"id":e["id"]} for key in ("states","transitions","constraints") for e in model[key]],
                       "actionAnalysis":{"status":"passed","evidence":"按PRD逐句核对草稿呈现、保存动作及成功/失败结果。","actions":actions}}],
      "entries":[{"stateId":"D","kind":"prepared","source":document,"method":"按PRD先准备未保存的阅读草稿，在编辑界面观察草稿内容。"}],
      "clarifications":[],"reviews":{key:{"status":"passed","evidence":"逐项核对测试PRD明示的草稿和保存成功/失败结果；测试模型范围与来源一致。"} for key in REVIEW_NAMES}}

class WorkContracts(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="analysis-work-tests-",dir=TEMP_ROOT)
        self.base=Path(self.temp.name);self.model,self.graph=model_fixture(self.base)
        self.work=make_work(self.model,self.graph)
    def tearDown(self): self.temp.cleanup()
    def report(self): return check_work(self.work,self.graph,self.base)
    def gate(self,name): return next(c for c in self.report()["checks"] if c["id"]==name)["status"]
    def save_work(self):
        file=work_file(self.graph);file.parent.mkdir(exist_ok=True);file.write_text(json.dumps(self.work,ensure_ascii=False)+"\n",encoding="utf-8")
    def command(self,name):
        with contextlib.redirect_stdout(io.StringIO()): return execute(name,self.graph,self.base)
    def render(self):
        with contextlib.redirect_stdout(io.StringIO()): return graph_execute("render",self.graph,self.base)
    def question(self):
        return {"question":"失败时是否保留草稿？","impact":"影响终态事实","status":"open","answer":None,"resolution":None}
    def test_separate_schemas_keep_work_out_of_final_graph(self):
        graph_schema=load_json(SKILL_DIR/"assets"/"state-transitions.schema.json")
        work_schema=load_json(SKILL_DIR/"assets"/"analysis-work.schema.json")
        self.assertEqual(schema_errors(self.model,graph_schema),[])
        self.assertEqual(schema_errors(self.work,work_schema),[])
        self.assertTrue(schema_errors(self.work,graph_schema))
        leaked=copy.deepcopy(self.model);leaked["analysisWork"]=self.work
        self.assertTrue(schema_errors(leaked,graph_schema))
        for name in ("analysisWork","analysisDocument","analysisRequirement","clarification","analysisReview"):
            self.assertNotIn(name,graph_schema["$defs"])
    def test_complete_work_is_separate_from_graph(self):
        self.assertEqual(self.report()["status"],"passed")
        self.assertNotIn("documents",load_json(self.graph));self.assertNotIn("clarifications",load_json(self.graph))
    def test_init_uses_pending_schema_defaults(self):
        self.assertEqual(self.command("init"),0)
        draft=load_json(work_file(self.graph))
        self.assertEqual(draft["documents"],[]);self.assertIsNone(draft["graphSha256"])
        self.assertEqual(draft["entries"],[])
        self.assertTrue(all(r["status"]=="pending" for r in draft["reviews"].values()))
        with self.assertRaises(FileExistsError): self.command("init")
    def test_included_requirement_needs_target(self):
        self.work["requirements"][0]["targets"]=[]
        self.assertEqual(self.gate("scope-mapping"),"failed")
    def test_excluded_and_context_cannot_create_graph_entities(self):
        for classification in ("excluded","context"):
            self.work["requirements"][0]["classification"]=classification
            self.work["requirements"][0].pop("actionAnalysis",None)
            self.assertEqual(self.gate("scope-mapping"),"failed")
    def test_target_must_exist(self):
        self.work["requirements"][0]["targets"][0]["id"]="MISSING"
        self.assertEqual(self.gate("scope-mapping"),"failed")
    def test_every_graph_entity_needs_included_mapping(self):
        self.work["requirements"][0]["targets"].pop()
        self.assertEqual(self.gate("scope-mapping"),"failed")
    def test_graph_and_requirements_sources_must_be_registered(self):
        self.work["documents"]=self.work["documents"][:1]
        self.assertEqual(self.gate("documents"),"failed")
    def test_source_hash_drift_is_detected(self):
        self.work["documents"][0]["source"]["sha256"]="0"*64
        self.assertEqual(self.gate("documents"),"failed")
    def test_open_question_blocks_completion(self):
        self.work["clarifications"]=[self.question()]
        self.assertEqual(self.gate("clarifications"),"blocked")
    def test_resolved_question_requires_actual_answer_and_resolution(self):
        q=self.question();q["status"]="resolved";self.work["clarifications"]=[q]
        self.assertEqual(self.gate("clarifications"),"failed")
        q["answer"]={"text":"保留草稿","conversationRef":"测试中的用户实际回答"};q["resolution"]="按PRD保留草稿，终态不变。"
        self.assertEqual(self.gate("clarifications"),"passed")
    def test_pending_review_blocks_completion(self):
        self.work["reviews"]["coverage"]["status"]="pending"
        self.assertEqual(self.gate("reviews"),"blocked")
    def test_passed_review_needs_evidence(self):
        self.work["reviews"]["facts"]["evidence"]=""
        self.assertEqual(self.gate("reviews"),"failed")
    def test_graph_changes_require_new_review_hash(self):
        changed=load_json(self.graph);changed["title"]="语义变化后的图"
        self.graph.write_text(json.dumps(changed),encoding="utf-8")
        self.assertEqual(self.gate("graph-version"),"blocked")
    def test_check_does_not_modify_either_file(self):
        self.save_work();graph_before=self.graph.read_bytes();work_before=work_file(self.graph).read_bytes()
        self.assertEqual(self.command("check"),0)
        self.assertEqual(self.graph.read_bytes(),graph_before);self.assertEqual(work_file(self.graph).read_bytes(),work_before)
    def test_finalize_requires_matching_html_then_removes_only_work(self):
        self.save_work();before=self.graph.read_bytes()
        self.assertEqual(self.command("finalize"),1);self.assertTrue(work_file(self.graph).is_file())
        self.assertEqual(self.render(),0);self.assertEqual(self.command("finalize"),0)
        self.assertEqual(self.graph.read_bytes(),before);self.assertFalse(work_file(self.graph).parent.exists())
        self.assertEqual({f.name for f in self.graph.parent.iterdir()},{"state-transitions.json","state-transitions.html"})
        self.assertTrue((self.base/"prd.md").is_file());self.assertTrue((self.base/"design.png").is_file())
    def test_unresolved_question_is_not_deleted(self):
        self.work["clarifications"]=[self.question()];self.save_work();self.render()
        self.assertEqual(self.command("finalize"),2);self.assertTrue(work_file(self.graph).exists())
    def test_unknown_work_files_are_preserved(self):
        self.save_work();self.render();extra=work_file(self.graph).parent/"user-note.md";extra.write_text("用户资料",encoding="utf-8")
        self.assertEqual(self.command("finalize"),1);self.assertTrue(extra.is_file());self.assertTrue(work_file(self.graph).is_file())
    def test_workspace_escape_is_rejected(self):
        with self.assertRaises(ValueError): execute("init",self.base.parent/"outside.json",self.base)

    def action(self): return self.work["requirements"][0]["actionAnalysis"]["actions"][0]
    def write_model(self):
        self.graph.write_text(json.dumps(self.model,ensure_ascii=False)+"\n",encoding="utf-8")
        self.work["graphSha256"]=raw_hash(self.graph.read_bytes())
    def static_model(self,text="验收入口直接显示未保存草稿，草稿内容可见且只读，本轮没有其他动作。"):

        (self.base/"prd.md").write_text(text,encoding="utf-8")
        self.model["states"]=self.model["states"][:1];self.model["transitions"]=[]
        source=self.model["states"][0]["source"][0]
        source.update(quote=text,sha256=raw_hash((self.base/"prd.md").read_bytes()))
        self.write_model();self.work=make_work(self.model,self.graph)
        self.work["requirements"][0]["actionAnalysis"]["evidence"]="逐句核对PRD：直接展示只读草稿，本轮没有进入后的动作。"
        self.work["entries"][0].update(kind="direct",method="从PRD指定的验收入口直接进入只读草稿界面。")
    def test_summary_pass_cannot_replace_entry_evidence(self):
        self.work["entries"]=[]
        self.assertEqual(self.gate("reviews"),"passed")
        self.assertEqual(self.gate("entry-evidence"),"blocked")
    def test_initial_flags_do_not_make_unreviewed_islands_acceptable(self):
        for state in self.model["states"]: state["isInitial"]=True
        self.model["transitions"]=[];self.write_model();self.work=make_work(self.model,self.graph)
        self.assertEqual(self.gate("graph"),"passed")
        self.assertEqual(self.gate("entry-evidence"),"blocked")
    def test_duplicate_or_noninitial_entry_evidence_is_rejected(self):
        self.work["entries"].append(copy.deepcopy(self.work["entries"][0]))
        self.assertEqual(self.gate("entry-evidence"),"failed")
        self.work["entries"][1]["stateId"]="S"
        self.assertEqual(self.gate("entry-evidence"),"failed")
    def test_ui_existence_is_not_entry_evidence(self):
        self.work["entries"][0]["source"]=self.model["states"][0]["source"][1]
        self.assertEqual(self.gate("work-schema"),"failed")
    def test_entry_needs_located_quote_and_method(self):
        entry=self.work["entries"][0]
        for field in ("source","method"):
            original=entry.pop(field)
            self.assertEqual(self.gate("work-schema"),"failed")
            entry[field]=original
        entry["source"]["locator"]="$"
        self.assertEqual(self.gate("work-schema"),"failed")
    def test_entry_quote_is_checked_against_original_document(self):
        self.work["entries"][0]["source"]=copy.deepcopy(self.work["entries"][0]["source"])
        self.work["entries"][0]["source"]["quote"]="原文中不存在的独立入口"
        self.assertEqual(self.gate("documents"),"failed")
    def test_entry_source_is_preserved_in_final_state_sources(self):
        entry=self.work["entries"][0];entry["source"]=copy.deepcopy(entry["source"])
        entry["source"]["locator"]="用户在未保存草稿上保存"
        self.assertEqual(self.gate("documents"),"passed")
        self.assertEqual(self.gate("entry-evidence"),"failed")
    def test_isolated_state_needs_independent_acceptance_reason(self):
        self.static_model()
        self.assertEqual(self.gate("entry-evidence"),"blocked")
        self.work["entries"][0]["isolationReason"]="PRD限定为独立只读草稿展示，无范围内前驱或后继动作。"
        self.assertEqual(self.report()["status"],"passed")
    def test_isolation_reason_is_not_added_to_connected_states(self):
        self.work["entries"][0]["isolationReason"]="占位说明"
        self.assertEqual(self.gate("entry-evidence"),"failed")
    def test_included_requirement_needs_its_own_action_analysis(self):
        del self.work["requirements"][0]["actionAnalysis"]
        self.assertEqual(self.gate("work-schema"),"failed")
    def test_excluded_requirement_does_not_carry_action_analysis(self):
        self.work["requirements"].append({"source":self.work["documents"][0]["source"],"classification":"excluded","reason":"范围外","targets":[],"actionAnalysis":{"status":"passed","evidence":"占位","actions":[]}})
        self.assertEqual(self.gate("work-schema"),"failed")
    def test_pending_or_failed_action_analysis_blocks_summary_pass(self):
        analysis=self.work["requirements"][0]["actionAnalysis"]
        analysis["status"]="pending";self.assertEqual(self.gate("action-coverage"),"blocked")
        analysis["status"]="failed";self.assertEqual(self.gate("action-coverage"),"failed")
        analysis["status"]="passed";analysis["evidence"]=""
        self.assertEqual(self.gate("action-coverage"),"failed")
    def test_mapping_existing_entities_does_not_replace_action_inventory(self):
        self.work["requirements"][0]["actionAnalysis"]["actions"]=[]
        self.assertEqual(self.gate("scope-mapping"),"passed")
        self.assertEqual(self.gate("action-coverage"),"failed")
    def test_missing_candidate_transition_or_result_is_rejected(self):
        action=self.action();action["transitionIds"]=["EF"]
        self.assertEqual(self.gate("action-coverage"),"failed")
        action["transitionIds"]=["ES","EF"];action["expectedTargets"]=["S"]
        self.assertEqual(self.gate("action-coverage"),"failed")
        action["expectedTargets"]=["S","F"];action["transitionIds"]=["MISSING"]
        self.assertEqual(self.gate("action-coverage"),"failed")
    def test_action_must_match_initial_state_actor_label_and_input(self):
        for key,value in (("label","删除"),("actor","其他执行者"),("input",{"title":"其他内容"})):
            action=self.action();original=copy.deepcopy(action["operation"])
            action["operation"][key]=value
            self.assertEqual(self.gate("action-coverage"),"failed")
            action["operation"]=original
        self.action()["from"]="S"
        self.assertEqual(self.gate("action-coverage"),"failed")
    def test_action_matching_uses_existing_normalization(self):
        action=self.action();action["operation"]["label"]=" 保存  "
        action["operation"]["actor"]=" 用户 "
        self.assertEqual(self.report()["status"],"passed")
    def test_action_transition_needs_requirement_mapping_and_same_source(self):
        requirement=self.work["requirements"][0]
        requirement["targets"]=[t for t in requirement["targets"] if t["id"]!="ES"]
        self.assertEqual(self.gate("action-coverage"),"failed")
        requirement["targets"].append({"collection":"transitions","id":"ES"})
        requirement["source"]=copy.deepcopy(self.model["states"][0]["source"][1])
        self.assertEqual(self.gate("documents"),"passed")
        self.assertEqual(self.gate("action-coverage"),"failed")
    def test_action_has_no_independent_id_or_empty_input(self):
        action=self.action();action["operation"]["id"]="SAVE"
        self.assertEqual(self.gate("work-schema"),"failed")
        del action["operation"]["id"];action["operation"]["input"]={}
        self.assertEqual(self.gate("work-schema"),"failed")
    def test_duplicate_action_assessment_is_rejected(self):
        self.work["requirements"][0]["actionAnalysis"]["actions"].append(copy.deepcopy(self.action()))
        self.assertEqual(self.gate("action-coverage"),"failed")
    def test_unresolved_candidate_blocks_completion(self):
        action=copy.deepcopy(self.action());action.update(disposition="open",expectedTargets=[],transitionIds=[])
        action["operation"]["label"]="确认结果尚不明确"
        self.work["requirements"][0]["actionAnalysis"]["actions"].append(action)
        self.assertEqual(self.gate("action-coverage"),"blocked")
    def test_excluded_candidate_needs_quoted_scope_evidence(self):
        action=copy.deepcopy(self.action());action.update(disposition="excluded",expectedTargets=[],transitionIds=[])
        action["operation"]["label"]="范围外的动作"
        self.work["requirements"][0]["actionAnalysis"]["actions"].append(action)
        self.assertEqual(self.gate("action-coverage"),"failed")
    def test_rule_disposition_needs_an_existing_mapped_constraint(self):
        action=copy.deepcopy(self.action());action.update(disposition="constraint",expectedTargets=[],transitionIds=[],constraintIds=["MISSING"])
        action["operation"]["label"]="改变字号"
        self.work["requirements"][0]["actionAnalysis"]["actions"].append(action)
        self.assertEqual(self.gate("action-coverage"),"failed")
    def test_finalize_preserves_work_when_entry_evidence_is_missing(self):
        self.work["entries"]=[];self.save_work();self.render()
        self.assertEqual(self.command("finalize"),2)
        self.assertTrue(work_file(self.graph).is_file())
    def test_invalid_graph_does_not_report_unexecuted_evidence_checks_passed(self):
        self.model["states"][0]["unexpected"]=True;self.write_model()
        self.assertEqual(self.gate("graph"),"failed")
        self.assertEqual(self.gate("entry-evidence"),"not-tested")

    def test_quoted_exclusion_keeps_a_legitimate_static_scope(self):
        self.static_model("验收入口直接显示未保存草稿，草稿内容可见且只读，本轮不包含保存功能。")
        self.work["entries"][0]["isolationReason"]="本轮独立验收只读草稿，保存效果明确排除，无范围内迁移。"
        source=self.work["requirements"][0]["source"]
        analysis=self.work["requirements"][0]["actionAnalysis"]
        analysis.update(evidence="原文只要求只读草稿展示，并明确排除保存功能。",actions=[{
            "from":"D","operation":{"label":"保存","actor":"用户"},"basis":"explicit",
            "change":"将未保存草稿提交为记录。","disposition":"excluded","expectedTargets":[],"transitionIds":[],
            "reason":"PRD明确保存功能不属于本轮范围。","resolutionSource":copy.deepcopy(source)}])
        self.assertEqual(self.report()["status"],"passed")
        analysis["actions"][0]["resolutionSource"]["quote"]="原文中不存在的排除条款"
        self.assertEqual(self.gate("documents"),"failed")
    def test_existing_global_rule_can_cover_adaptation_checks(self):
        self.static_model("验收入口直接显示未保存草稿，草稿内容可见且只读；字号变化按规则R换行和增高，只验收该规则，不设独立结果状态。")
        source=copy.deepcopy(self.model["states"][0]["source"][0])
        self.model["constraints"]=[{"id":"R","statement":"字号变化按规则R换行和增高。","source":[source]}]
        self.write_model();self.work=make_work(self.model,self.graph)
        self.work["entries"][0].update(kind="direct",method="从PRD指定的验收入口直接进入只读草稿界面。")
        self.work["entries"][0]["isolationReason"]="草稿独立展示；字号参数由规则R验收，没有独立结果状态。"
        self.work["requirements"][0]["actionAnalysis"]={"status":"passed","evidence":"PRD明确字号输入只验证既有规则R，不构成单独迁移。","actions":[{
            "from":"D","operation":{"label":"设置字号","actor":"验收操作者","input":{"fontScale":1.3}},"basis":"explicit",
            "change":"文字按既定规则重排，沿用同一状态验收标准。","disposition":"constraint","expectedTargets":[],"transitionIds":[],
            "reason":"规则R已定义本次字号输入的适配要求。","constraintIds":["R"]}]}
        self.assertEqual(self.report()["status"],"passed")
    def test_finalize_does_not_delete_unprocessed_action_evidence(self):
        self.work["requirements"][0]["actionAnalysis"]["actions"]=[];self.save_work();self.render()
        self.assertEqual(self.command("finalize"),1)
        self.assertTrue(work_file(self.graph).is_file())

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--temp-root")
    args,remaining=parser.parse_known_args();TEMP_ROOT=args.temp_root
    unittest.main(argv=[__file__]+remaining,verbosity=2)
