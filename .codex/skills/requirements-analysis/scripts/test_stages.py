"""Synthetic contract regressions; test reports are never real semantic review."""
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import analyze as workflow
import render_review


def fixture():
    ui = {'applicability': 'applicable', 'reason': '', 'refs': [{'sourceId': 'P', 'locator': 'dialog specification'}],
          'constraints': [{'target': 'dialog title', 'expected': 'title follows the source text', 'sourceIds': ['P']}]}
    state = {'schemaVersion': 1,
             'scope': {'objective': 'Synthetic modal interaction', 'included': ['open and close'], 'excluded': ['save'],
                       'abstraction': {'object': 'screen', 'level': 'page with dialog', 'dimensions': ['dialog visibility'], 'parameters': []}},
             'sources': [{'id': 'P', 'kind': 'prd', 'uri': 'source.txt', 'locator': 'modal section', 'summary': 'open and close rules'}],
             'features': [{'id': 'F', 'title': 'Dialog', 'sourceIds': ['P']}], 'entryStateIds': ['A'],
             'states': [{'id': sid, 'title': title, 'featureIds': ['F'], 'definition': fact,
                         'facts': [fact], 'ui': copy.deepcopy(ui), 'sourceIds': ['P']}
                        for sid, title, fact in [('A', 'Page', 'dialog absent'), ('B', 'Dialog', 'dialog visible')]],
             'transitions': [{'id': tid, 'featureIds': ['F'], 'from': a, 'to': b, 'event': event,
                              'guard': 'true', 'effects': [effect], 'sourceIds': ['P']}
                             for tid, a, b, event, effect in [('T1', 'A', 'B', 'open', 'dialog appears'), ('T2', 'B', 'A', 'close', 'dialog disappears')]],
             'coverage': [{'sourceId': 'P', 'locator': 'modal section', 'obligation': 'open and close the dialog',
                           'disposition': 'mapped', 'stateIds': ['A', 'B'], 'transitionIds': ['T1', 'T2'], 'reason': ''}],
             'clarifications': []}
    checks = {'applicability': 'applicable', 'reason': '', 'checks': [
        {'given': 'at source state', 'when': 'perform source event', 'then': ['reach target state'], 'sourceIds': ['P']}]}
    na = {'applicability': 'not_applicable', 'reason': 'synthetic source defines no such obligation', 'checks': []}
    requirements = {'schemaVersion': 1, 'stateDigest': workflow.digest(state),
                    'requirementTraversal': {'restartPolicy': 'none'}, 'requirements': [], 'graph': {}}
    for i, transition in enumerate(state['transitions']):
        row = {'id': 'R' + str(i + 1), 'title': transition['event'], 'transitionId': transition['id'],
               'featureIds': ['F'], 'sourceIds': ['P'], 'functionalAcceptance': copy.deepcopy(checks),
               'visualAcceptance': copy.deepcopy(na)}
        if i == 1:
            row['functionalAcceptance'] = copy.deepcopy(na)
            row['visualAcceptance'] = copy.deepcopy(checks)
            row['visualAcceptance']['checks'][0]['uiRefs'] = [{'sourceId': 'P', 'locator': 'modal section'}]
        requirements['requirements'].append(row)
    return state, requirements


def synthetic_report(path, stage, result):
    targets = result['reviewTargets']
    evidence = [{'sourceId': source_id, 'locator': 'synthetic modal section'}
                for source_id in targets['sourceIds']]
    workflow.save(path, {'stage': stage, 'inputDigest': result['inputDigest'], 'contractDigest': result['contractDigest'],
        'analyzerContext': result['analyzerContext'], 'sourceIds': targets['sourceIds'],
        'reviewer': {'independent': True, 'context': 'SYNTHETIC REVIEWER, NEVER A REAL SEMANTIC REVIEW'},
        'objects': [{'id': entity_id, 'status': 'passed', 'reason': 'synthetic object fixture',
                     'evidence': evidence} for entity_id in targets['objectIds']],
        'closure': {'openItems': [], 'reason': 'synthetic exhaustive fixture'},
        'criteria': [{'id': i, 'status': 'passed', 'reason': 'synthetic validator fixture',
                      'evidence': evidence} for i in workflow.CONTRACT[stage]['semantic']],
        'findings': []})


class StageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.run = Path(self.temp.name)
        workflow.initialize(self.run, 'SYNTHETIC ANALYZER CONTEXT')
        (self.run / 'source.txt').write_text('Synthetic source: open and close modal.', encoding='utf-8')
        self.state, self.requirements = fixture()
        self.sr = self.run / '_process/state-review.json'
        self.rr = self.run / '_process/requirements-review.json'

    def state_pass(self):
        result = workflow.state_gate(self.run, self.state, self.sr)
        synthetic_report(self.sr, 'state', result)
        result = workflow.state_gate(self.run, self.state, self.sr)
        self.assertEqual('passed', result['status'], result)
        return result

    def requirements_pass(self):
        state_result = self.state_pass()
        self.requirements['graph'] = workflow.derive_graph(self.state, self.requirements)
        result = workflow.requirements_gate(self.state, self.requirements, state_result, self.rr)
        synthetic_report(self.rr, 'requirements', result)
        result = workflow.requirements_gate(self.state, self.requirements, state_result, self.rr)
        self.assertEqual('passed', result['status'], result)
        return state_result, result

    def test_stage_one_has_no_dependency_on_atomic_requirements(self):
        self.assertNotIn('requirements', self.state)
        result = self.state_pass()
        self.assertEqual(['T1'], result['derived']['pathsByEntry']['A']['B'])
        self.assertEqual('passed', result['derived']['transitionValidation']['status'])

    def test_missing_or_self_review_stays_pending(self):
        result = workflow.state_gate(self.run, self.state, self.sr)
        self.assertEqual('pending', result['status'])
        synthetic_report(self.sr, 'state', result)
        report = workflow.load(self.sr)
        report['reviewer']['independent'] = False
        workflow.save(self.sr, report)
        self.assertEqual('pending', workflow.state_gate(self.run, self.state, self.sr)['status'])

    def test_structure_checks_do_not_accept_empty_templates(self):
        template = workflow.load(workflow.ASSETS / 'state.template.json')
        result = workflow.state_gate(self.run, template, self.sr)
        self.assertEqual('failed', result['status'])

    def test_unreachable_state_or_false_endpoint_is_rejected(self):
        self.state['states'].append({**copy.deepcopy(self.state['states'][0]), 'id': 'C'})
        self.assertEqual('failed', workflow.state_gate(self.run, self.state, self.sr)['status'])
        self.state['transitions'][0]['to'] = 'nonexistent'
        self.assertEqual('failed', workflow.state_gate(self.run, self.state, self.sr)['status'])

    def test_open_human_question_blocks_completion_until_documented(self):
        self.state['clarifications'] = [{'id': 'Q', 'question': 'close behavior?', 'affectedIds': ['T2'],
                                        'status': 'open', 'resolution': '', 'humanReference': ''}]
        result = workflow.state_gate(self.run, self.state, self.sr)
        self.assertEqual('failed', result['status'])
        self.state['clarifications'][0].update(status='resolved', resolution='close the dialog', humanReference='synthetic answer')
        self.state['clarificationDocument'] = '_process/clarification.md'
        self.assertEqual('failed', workflow.state_gate(self.run, self.state, self.sr)['status'])
        (self.run / '_process/clarification.md').write_text('Q: synthetic answer confirms close the dialog.', encoding='utf-8')
        self.state_pass()

    def test_local_source_or_clarification_change_invalidates_review(self):
        self.state_pass()
        (self.run / 'source.txt').write_text('Changed synthetic rule.', encoding='utf-8')
        self.assertEqual('pending', workflow.state_gate(self.run, self.state, self.sr)['status'])
        self.state['clarificationDocument'] = '_process/answers.md'
        (self.run / '_process/answers.md').write_text('confirmed', encoding='utf-8')
        self.state_pass()
        (self.run / '_process/answers.md').write_text('different answer', encoding='utf-8')
        self.assertEqual('pending', workflow.state_gate(self.run, self.state, self.sr)['status'])

    def test_nontrivial_unencoded_guard_is_not_proven(self):
        self.state['transitions'][0]['guard'] = 'eligible user'
        result = workflow.state_gate(self.run, self.state, self.sr)
        check = next(x for x in result['checks'] if x['id'] == 'S-PATHS')
        self.assertEqual('pending', check['status'])

    def test_preview_changes_invalidate_bound_semantic_report(self):
        self.state['states'][0]['ui']['refs'][0]['previewPath'] = 'preview.png'
        (self.run / 'preview.png').write_bytes(b'synthetic preview one')
        self.state_pass()
        (self.run / 'preview.png').write_bytes(b'synthetic preview two')
        self.assertEqual('pending', workflow.state_gate(self.run, self.state, self.sr)['status'])

    def test_both_acceptance_structures_exist_but_either_can_be_inapplicable(self):
        self.requirements_pass()
        self.assertEqual('not_applicable', self.requirements['requirements'][0]['visualAcceptance']['applicability'])
        self.assertEqual('not_applicable', self.requirements['requirements'][1]['functionalAcceptance']['applicability'])

    def test_duplicate_or_missing_transition_requirement_is_rejected(self):
        result = self.state_pass()
        self.requirements['requirements'][1]['transitionId'] = 'T1'
        checked = workflow.requirements_gate(self.state, self.requirements, result, self.rr)
        self.assertEqual('failed', checked['status'])

    def test_feasible_unproven_route_can_pass_coverage_gate(self):
        self.state['states'].append({**copy.deepcopy(self.state['states'][0]), 'id': 'C', 'title': 'Other outcome'})
        self.state['transitions'].append({'id': 'T3', 'featureIds': ['F'], 'from': 'A', 'to': 'C',
            'event': 'finish', 'guard': 'x is zero', 'effects': ['other outcome'], 'sourceIds': ['P']})
        self.state['transitions'][0]['guard'] = 'x is zero'
        self.state['pathContext'] = {'domains': {'x': {'values': ['0', '1'], 'labels': {'0': 'zero', '1': 'one'},
                                                     'description': 'synthetic condition'}},
            'entryContexts': {'A': {'x': ['0']}}, 'transitionRules': {}}
        for t in self.state['transitions']:
            self.state['pathContext']['transitionRules'][t['id']] = {
                'cases': [{'set': {'x': ['1']}} if t['id'] == 'T2' else {'requires': {'x': ['0']}}],
                'reason': 'synthetic condition rule', 'sourceRefs': [{'sourceId': 'P', 'locator': 'synthetic rule'}]}
        self.state['coverage'][0]['transitionIds'].append('T3')
        self.state['coverage'][0]['stateIds'].append('C')
        self.requirements['stateDigest'] = workflow.digest(self.state)
        self.requirements['requirementTraversal'] = {'restartPolicy': 'documented_entries', 'authorization': 'synthetic permitted entry scenario'}
        third = copy.deepcopy(self.requirements['requirements'][0])
        third.update(id='R3', transitionId='T3', title='finish')
        self.requirements['requirements'].append(third)
        self.requirements_pass()
        self.assertEqual('not_proven', self.requirements['graph']['traversal']['optimality'])
        self.assertEqual('feasible', self.requirements['graph']['traversal']['status'])

    def test_forged_graph_or_unsupported_restart_is_rejected(self):
        sr, _ = self.requirements_pass()
        self.requirements['graph']['edges'] = []
        self.assertEqual('failed', workflow.requirements_gate(self.state, self.requirements, sr, self.rr)['status'])
        self.requirements['requirementTraversal'] = {'restartPolicy': 'documented_entries'}
        with self.assertRaises(ValueError):
            workflow.derive_graph(self.state, self.requirements)

    def test_requirement_changes_invalidate_only_downstream_review(self):
        sr, _ = self.requirements_pass()
        self.requirements['requirements'][0]['functionalAcceptance']['checks'][0]['then'] = ['new expectation']
        checked = workflow.requirements_gate(self.state, self.requirements, sr, self.rr)
        self.assertEqual('pending', checked['status'])
        self.assertEqual('passed', workflow.state_gate(self.run, self.state, self.sr)['status'])

    def test_html_only_change_preserves_semantic_reports(self):
        sr, rr = self.requirements_pass()
        html = self.run / 'review.html'
        self.assertEqual('passed', workflow.html_gate(self.run, self.state, self.requirements, sr, rr, html, True)['status'])
        clone = self.run / 'skill-clone'
        shutil.copytree(workflow.SKILL, clone, ignore=shutil.ignore_patterns('__pycache__'))
        template = clone / 'assets/review.html'
        template.write_text(template.read_text(encoding='utf-8').replace('#f3f6fa', '#f4f7fb'), encoding='utf-8')
        with patch.object(workflow, 'SKILL', clone), patch.object(render_review, 'SKILL', clone):
            self.assertEqual('passed', workflow.state_gate(self.run, self.state, self.sr)['status'])
            self.assertEqual('passed', workflow.requirements_gate(self.state, self.requirements, sr, self.rr)['status'])
            self.assertEqual('failed', workflow.html_gate(self.run, self.state, self.requirements, sr, rr, html)['status'])
            self.assertEqual('passed', workflow.html_gate(self.run, self.state, self.requirements, sr, rr, html, True)['status'])

    def test_html_projection_does_not_solve_requirement_graph_again(self):
        sr, rr = self.requirements_pass()
        with patch.object(workflow, 'derive_graph', side_effect=AssertionError('must not solve in renderer')):
            result = workflow.html_gate(self.run, self.state, self.requirements, sr, rr, self.run / 'review.html', True)
        self.assertEqual('passed', result['status'])
        self.assertEqual('not_performed_static_only', result['browserVerification'])

    def test_json_embedding_is_safe_and_preserves_all_data(self):
        sr, _ = self.requirements_pass()
        payload = render_review.presentation(self.run, self.state, self.requirements, sr['derived'])
        payload['scope']['objective'] = '</script><script>alert(1)</script>\u2028'
        html = render_review.render(payload)
        self.assertNotIn('</script><script>alert(1)', html)
        self.assertEqual(payload, render_review.extract_payload(html))

    def test_cli_final_reuses_reports_and_rejects_stale_html(self):
        self.requirements_pass()
        workflow.save(self.run / 'state-graph.json', self.state)
        workflow.save(self.run / 'requirements.json', self.requirements)
        command = [sys.executable, str(workflow.SKILL / 'scripts/analyze.py')]
        for action in ['html', 'final']:
            result = subprocess.run(command + [action, str(self.run)], capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        checked = workflow.load(self.run / 'gate-result.json')
        self.assertEqual('passed', checked['status'])
        with (self.run / 'review.html').open('a', encoding='utf-8') as output:
            output.write('<!-- changed -->')
        result = subprocess.run(command + ['final', str(self.run)], capture_output=True, text=True)
        self.assertEqual(1, result.returncode)

    def test_init_preserves_existing_files_and_has_no_html(self):
        state = self.run / 'state-graph.json'
        state.write_text('user data', encoding='utf-8')
        workflow.initialize(self.run)
        self.assertEqual('user data', state.read_text(encoding='utf-8'))
        self.assertFalse((self.run / 'review.html').exists())

    def test_missing_reviews_keep_final_pending_and_do_not_generate_html(self):
        workflow.save(self.run / 'state-graph.json', self.state)
        workflow.save(self.run / 'requirements.json', self.requirements)
        command = [sys.executable, str(workflow.SKILL / 'scripts/analyze.py'), 'final', str(self.run)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        self.assertEqual('pending', workflow.load(self.run / 'gate-result.json')['status'])
        self.assertFalse((self.run / 'review.html').exists())

    def test_same_actual_context_cannot_pass_by_claiming_independence(self):
        result = self.state_pass()
        report = workflow.load(self.sr)
        report['reviewer']['context'] = report['analyzerContext']
        workflow.save(self.sr, report)
        self.assertEqual('failed', workflow.state_gate(self.run, self.state, self.sr)['status'])

    def test_analyzer_context_must_be_registered_and_match_report(self):
        self.state_pass()
        context_path = self.run / '_process/analysis-context.json'
        context_path.unlink()
        self.assertEqual('pending', workflow.state_gate(self.run, self.state, self.sr)['status'])
        workflow.initialize(self.run, 'SYNTHETIC DIFFERENT ANALYZER')
        self.assertEqual('pending', workflow.state_gate(self.run, self.state, self.sr)['status'])

    def test_aggregate_pass_does_not_hide_missing_object_review(self):
        self.state_pass()
        report = workflow.load(self.sr)
        report['objects'].pop()
        workflow.save(self.sr, report)
        self.assertEqual('pending', workflow.state_gate(self.run, self.state, self.sr)['status'])

    def test_duplicate_or_retired_review_object_is_rejected(self):
        self.state_pass()
        report = workflow.load(self.sr)
        report['objects'][0]['id'] = report['objects'][1]['id']
        workflow.save(self.sr, report)
        self.assertEqual('pending', workflow.state_gate(self.run, self.state, self.sr)['status'])

    def test_object_failure_overrides_overall_pass(self):
        self.state_pass()
        report = workflow.load(self.sr)
        report['objects'][0].update(status='failed', reason='synthetic incorrect state boundary')
        workflow.save(self.sr, report)
        self.assertEqual('failed', workflow.state_gate(self.run, self.state, self.sr)['status'])

    def test_unknown_source_and_unlocatable_evidence_do_not_pass(self):
        self.state_pass()
        report = workflow.load(self.sr)
        report['objects'][0]['evidence'] = [{'sourceId': 'not-in-current-sources', 'locator': 'section'}]
        workflow.save(self.sr, report)
        self.assertEqual('pending', workflow.state_gate(self.run, self.state, self.sr)['status'])
        report['objects'][0]['evidence'] = [{'sourceId': 'P', 'locator': ''}]
        workflow.save(self.sr, report)
        self.assertEqual('pending', workflow.state_gate(self.run, self.state, self.sr)['status'])

    def test_open_analysis_item_blocks_convergence(self):
        self.state_pass()
        report = workflow.load(self.sr)
        report['closure']['openItems'] = ['synthetic unchecked permission boundary']
        workflow.save(self.sr, report)
        self.assertEqual('failed', workflow.state_gate(self.run, self.state, self.sr)['status'])

    def test_missing_requirement_review_cannot_pass_on_criteria_alone(self):
        sr, _ = self.requirements_pass()
        report = workflow.load(self.rr)
        report['objects'].pop()
        workflow.save(self.rr, report)
        self.assertEqual('pending', workflow.requirements_gate(self.state, self.requirements, sr, self.rr)['status'])

    def test_source_review_set_is_not_a_file_count(self):
        self.state_pass()
        report = workflow.load(self.sr)
        report['sourceIds'] = ['synthetic-unreviewed-source']
        workflow.save(self.sr, report)
        self.assertEqual('pending', workflow.state_gate(self.run, self.state, self.sr)['status'])


if __name__ == '__main__':
    unittest.main()
