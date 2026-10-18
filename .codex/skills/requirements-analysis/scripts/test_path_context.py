"""Finite-domain regressions use synthetic business facts, not actual acceptance."""
import copy
import unittest
from path_context import advance, paths_for_start, validate_context
from render_review import presentation, requirement_graph, token_css
from requirement_graph import full_requirement_graph, verify_coverage


def fixture():
    model={"phase":"analyzing","scope":{},"requirementTraversal":{"restartPolicy":"documented_entries","authorization":"test"},"entryStateIds":["A","E"],"features":[],"sources":[{"id":"P"}],"questions":[],
           "states":[{"id":x,"title":x,"facts":[x],"sourceIds":["P"],"uiRefs":[]} for x in "ABCDE"],
           "transitions":[{"id":x,"from":a,"to":b,"requirementId":"R"+x,"sourceIds":["P"],"event":x,"guard":"true"} for x,a,b in [("AB","A","B"),("BC","B","C"),("AD","A","D"),("DC","D","C"),("EC","E","C")]],
           "requirements":[]}
    model["pathContext"]={"domains":{"type":{"values":["loop","once"],"labels":{"loop":"循环","once":"一次性"},"description":"所选计划类型"}},"entryContexts":{"A":{"type":["loop"]},"E":{"type":["once"]}},"transitionRules":{}}
    for e in model["transitions"]:
        model["pathContext"]["transitionRules"][e["id"]]={"cases":[{}],"reason":"合成来源允许的路径", "sourceRefs":[{"sourceId":"P","locator":"合成规则"}]}
    model["pathContext"]["transitionRules"]["BC"]["cases"]=[{"requires":{"type":["once"]}}]
    model["pathContext"]["transitionRules"]["AD"]["cases"]=[{"set":{"type":["once"]}}]
    return model


class ContextTests(unittest.TestCase):
    def test_conflicting_path_does_not_win_shortest_tie(self):
        routes,meta=paths_for_start(fixture(),"A")
        self.assertEqual(["AD","DC"],routes["C"])
        self.assertTrue(meta["complete"])
    def test_multiple_roots_keep_independent_context(self):
        model=fixture();self.assertEqual(["EC"],paths_for_start(model,"E")[0]["C"])
        self.assertEqual([],paths_for_start(model,"A")[0]["A"])
    def test_exhausted_search_reports_unreachable_without_new_root(self):
        model=fixture();model["pathContext"]["transitionRules"]["AD"]["cases"]=[{}]
        model["pathContext"]["transitionRules"]["DC"]["cases"]=[{"requires":{"type":["once"]}}]
        self.assertIsNone(paths_for_start(model,"A")[0]["C"])
    def test_conditions_narrow_domains_instead_of_assuming_true(self):
        spec=fixture()["pathContext"]
        self.assertEqual([],advance(spec,{"type":{"loop"}},{"requires":{"type":["once"]}}))
    def test_copy_preserves_correlated_values(self):
        spec={"domains":{"a":{"values":["x","y"]},"b":{"values":["x","y"]}}}
        outcomes=advance(spec,{"a":{"x","y"},"b":{"x","y"}},{"setFrom":{"b":"a"}})
        self.assertEqual(2,len(outcomes))
        self.assertTrue(all(row["a"]==row["b"] and len(row["a"])==1 for row in outcomes))
    def test_disjunction_does_not_merge_incompatible_assignments(self):
        spec={"domains":{"type":{"values":["loop","once"]},"mode":{"values":["ordinary","backfill"]}}}
        initial={"type":{"loop","once"},"mode":{"ordinary","backfill"}}
        cases=[{"set":{"type":["loop"],"mode":["backfill"]}},{"set":{"type":["once"],"mode":["ordinary"]}}]
        outcomes=[row for case in cases for row in advance(spec,initial,case)]
        self.assertFalse(any(row["type"]=={"once"} and row["mode"]=={"backfill"} for row in outcomes))
    def test_rule_coverage_and_reference_validation(self):
        model=fixture();self.assertEqual([],validate_context(model))
        del model["pathContext"]["transitionRules"]["AB"]
        self.assertTrue(any("exactly" in x for x in validate_context(model)))
    def test_unknown_value_and_effect_conflicts_fail(self):
        model=fixture();rule=model["pathContext"]["transitionRules"]["AB"]
        rule["cases"]=[{"set":{"type":["alien"]},"forget":["type"]}]
        self.assertTrue(validate_context(model))
    def test_search_limit_is_not_reported_as_unreachable(self):
        with self.assertRaisesRegex(ValueError,"incomplete"):
            paths_for_start(fixture(),"A",max_configurations=1)
    def test_invalid_state_constraints_are_diagnostics_not_crashes(self):
        for row in [None,[],{'requires':[]},{'requires':{},'sourceRefs':['bad'],'reason':'test'}]:
            model=fixture();model['pathContext']['stateConstraints']={'B':row}
            self.assertTrue(validate_context(model))
    def test_formula_is_reduced_to_verified_continuous_route_support(self):
        model=fixture();g=requirement_graph(model);full=full_requirement_graph(model)
        self.assertEqual(len(model["transitions"]),len(g["nodes"]))
        expected={(a["requirementId"],b["requirementId"]) for a in model["transitions"] for b in model["transitions"] if a["to"]==b["from"]}
        self.assertEqual(expected,{(e["from"],e["to"]) for e in full["edges"]})
        self.assertEqual([],verify_coverage(model,g))
    def test_css_design_values_come_only_from_registered_tokens(self):
        css=token_css({"colors":{"text":"#123456"},"font":{"body":17},"radius":{"card":6},"layout":{"pageInset":23}})
        self.assertIn("#123456",css);self.assertIn("17px",css);self.assertIn("6px",css);self.assertIn("23px",css)
        self.assertNotIn("box-shadow",css)
    def test_css_filters_unsupported_values_without_executing_them(self):
        css=token_css({"colors":{"text":"</script>"},"font":{"body":"eval(1)"}})
        self.assertNotIn("</script>",css);self.assertNotIn("eval(1)",css)

if __name__=="__main__":unittest.main(verbosity=2)
