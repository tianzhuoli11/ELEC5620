import copy
from dataclasses import asdict
import json
import os
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from agents.coordinator import HomeCoordinatorAgent
from domains.base import DomainRegistry
from domains.energy_comfort.control import run_energy_control
from domains.pet_care.integration import monitor_pet_workflow
from domains.smart_home_control import run_smart_home_control, default_device_states
from models import ExplanationRequest
from services.explanations import digest, explain_record, load_sources, load_history, submit_explanation, review_explanation
from simulation.devices import SimulatedDeviceTool
from simulation.events import make_user_goal_event
from simulation.pet_demo import make_pet_scenario
from simulation.energy_comfort_demo import example_contexts, make_energy_comfort_event
from safety_fixtures import safety_fixture


def request(record, question='Why was this decision made?'):
    workflow = record.get('workflow',record)
    return ExplanationRequest(str(uuid4()),workflow['event']['event_id'],digest(record),question)


def energy_record(*, blocked=False, offline=False):
    event = make_energy_comfort_event(example_contexts()['adjustment_needed'])
    tool = SimulatedDeviceTool(default_device_states())
    if offline:
        tool.offline.add('living-room-ac')
    result = run_energy_control(event,approved=True,safety_state=safety_fixture(blocked=blocked),device_tool=tool)
    return {'record_type':'energy_comfort_control','event':event.to_dict(),
            'workflow':result.workflow.to_dict(),'assessment':result.assessment.to_dict(),
            'selected_plan':[asdict(p) for p in result.selected_plan], 'approval':True,
            'safety_snapshot':result.safety_before,'safety_after':result.safety_after}


class ExplanationTests(unittest.TestCase):
    def test_rejected_review_is_logged_without_replacing_the_source_record(self):
        record=energy_record(blocked=True)
        original=copy.deepcopy(record)
        with TemporaryDirectory() as folder:
            path=Path(folder)/'history.jsonl'
            pending=submit_explanation(request(record),record,history_path=path)
            rejected=review_explanation(pending.request.request_id,approved=False,operator_role='Human Founder/Operator',history_path=path)
            self.assertEqual(rejected['review_status'],'REJECTED')
            self.assertEqual(record,original)

    def test_foreign_notification_cannot_be_explained_as_part_of_this_event(self):
        record=energy_record()
        record['workflow']['notification_result']={'event_id':'other','status':'SIMULATED'}
        probe=Mock()
        self.assertEqual(explain_record(request(record),record,probe).evidence_status,'CONFLICTING')
        probe.assert_not_called()

    def test_shared_explanation_transport_has_no_key_in_prompt(self):
        from services.campus_proxy import propose_explanation_order,CampusProxyConfig
        response={'choices':[{'message':{'content':'{"fact_ids":["f0"]}'}}]}
        with patch('services.campus_proxy.urlopen',return_value=BytesIO(json.dumps(response).encode())) as send:
            result=propose_explanation_order({'topic':'tradeoff','style':'brief','facts':[{'fact_id':'f0','category':'safety'}]},CampusProxyConfig(api_key='test-only-key'))
        body=json.loads(send.call_args.args[0].data)
        self.assertNotIn('test-only-key',json.dumps(body))
        self.assertEqual(result,{'fact_ids':['f0']})

    @unittest.skipUnless(os.getenv('ELEC5620_RUN_REAL_PROXY')=='1' and os.getenv('ELEC5620_API_KEY','').strip(),'opt-in live campus explanation test')
    def test_live_explanation_organizer_retains_only_supported_facts(self):
        from services.campus_proxy import CampusProxyConfig,propose_explanation_order
        record=energy_record()
        config=CampusProxyConfig.from_environment()
        baseline=explain_record(request(record),record)
        result=explain_record(request(record,'Explain the comfort and energy trade-off'),record,lambda p:propose_explanation_order(p,config))
        self.assertEqual(set(result.facts),set(baseline.facts))
        self.assertEqual(result.evidence_status,'CONSISTENT')
        self.assertIn(result.ai_status,('USED','INVALID_FALLBACK','TIMEOUT_FALLBACK','ERROR_FALLBACK'))
        print('Live campus explanation status:',result.ai_status,'; evidence cards:',len(result.facts))

    def test_invalid_source_event_id_is_skipped_instead_of_breaking_page(self):
        record=energy_record()
        record['workflow']['event']['event_id']=123
        with TemporaryDirectory() as folder:
            (Path(folder)/'energy_comfort.jsonl').write_text(json.dumps(record),encoding='utf-8')
            self.assertEqual(load_sources(Path(folder)),[])

    def test_high_risk_review_requires_explicit_operator_and_is_persisted_once(self):
        record=energy_record(blocked=True)
        with TemporaryDirectory() as folder:
            path=Path(folder)/'history.jsonl'
            result=submit_explanation(request(record),record,history_path=path)
            self.assertEqual(result.review_status,'PENDING')
            with self.assertRaises(ValueError):
                review_explanation(result.request.request_id,approved=True,operator_role='LLM',history_path=path)
            reviewed=review_explanation(result.request.request_id,approved=True,operator_role='Human Founder/Operator',history_path=path)
            self.assertEqual(reviewed['review_status'],'APPROVED')
            self.assertEqual(load_history(path)[0]['review_status'],'APPROVED')
            with self.assertRaises(ValueError):
                review_explanation(result.request.request_id,approved=False,operator_role='Human Founder/Operator',history_path=path)

    def test_simpler_response_uses_same_source_and_retains_failures_and_uncertainty(self):
        record=energy_record(offline=True)
        detailed=explain_record(request(record),record)
        req=request(record)
        simple=explain_record(ExplanationRequest(req.request_id,req.event_id,req.source_sha256,req.question,'brief'),record)
        self.assertLess(len(simple.facts),len(detailed.facts))
        self.assertTrue(set(simple.facts).issubset(set(detailed.facts)))
        self.assertTrue(any(f.category=='failure' for f in simple.facts))
        self.assertTrue(any('energy savings are unknown' in f.text for f in simple.facts))

    def test_incomplete_assessment_preserves_supported_action_facts(self):
        record=energy_record()
        del record['workflow']['assessment']
        result=explain_record(request(record),record)
        self.assertEqual(result.evidence_status,'PARTIAL')
        self.assertTrue(any('risk assessment is missing' in f.text for f in result.facts))
        self.assertTrue(any(f.category=='execution' for f in result.facts))
        self.assertEqual(result.review_status,'PENDING')

    def test_private_source_text_is_not_echoed_in_explanation_facts(self):
        record=energy_record()
        record['workflow']['assessment']['rationale']='Jane at 123 Secret Street; key=private-token'
        record['workflow']['action_results'][0]['returned_state']['private_contact']='Jane@example.com'
        result=explain_record(request(record),record)
        text=' '.join(f.text for f in result.facts)
        for private in ('Jane','Secret Street','private-token','example.com'):
            self.assertNotIn(private,text)

    def test_all_five_domains_and_escalation_stages_have_coordinator_explanations(self):
        from domains.home_security.integration import monitor_security_workflow
        from simulation.security_scenarios import make_security_scenario
        from domains.elderly_safety.integration import build_workflow,run_elderly_safety,start_escalation,acknowledgement_timeout
        from domains.elderly_safety import default_devices
        from simulation.elderly_scenarios import make_fall_scenario
        with TemporaryDirectory() as folder:
            path=Path(folder)/'elderly_safety.jsonl'
            engine,handler=build_workflow(device_tool=SimulatedDeviceTool(default_devices()))
            result=run_elderly_safety(make_fall_scenario('high_floor'),workflow=engine,handler=handler,record_path=path)
            state=start_escalation(result,workflow=engine,record_path=path)
            acknowledgement_timeout(state,workflow=engine,record_path=path)
            sources=load_sources(Path(folder))
            self.assertTrue(any('escalation' in s['record'] for s in sources))
            for source in sources:
                self.assertEqual(explain_record(request(source['record']),source['record']).evidence_status,'CONSISTENT')
            explained=explain_record(request(sources[0]['record']),sources[0]['record'])
            self.assertTrue(any('ack timeout' in f.text for f in explained.facts))
            security=monitor_security_workflow(make_security_scenario('smoke'),record_path=Path(folder)/'security_events.jsonl')
            doc={'workflow':security.workflow.to_dict()}
            self.assertEqual(explain_record(request(doc),doc).domain,'home_security')

    def test_coordinator_reads_a_specific_record_without_dispatch(self):
        record = energy_record()
        before = copy.deepcopy(record)
        result = HomeCoordinatorAgent(DomainRegistry([])).explain(request(record),record=record)
        self.assertEqual(result.evidence_status,'CONSISTENT')
        self.assertEqual(record,before)
        self.assertTrue(any(f.category=='strategy' for f in result.facts))
        self.assertTrue(all(f.source_fields for f in result.facts))
        self.assertIn('HomeCoordinatorAgent:evidence_bound_explanation',result.trace)

    def test_energy_tradeoff_records_inputs_strategy_verification_and_unknown_effect(self):
        record=energy_record()
        result=explain_record(request(record,'Why this comfort and energy trade-off?'),record)
        text=' '.join(f.text for f in result.facts)
        for expected in ('27.0','24.0','Selected strategy','independently verified','Safety takes priority','energy savings are unknown'):
            self.assertIn(expected,text)

    def test_partial_device_failure_is_never_hidden_by_ai_selection(self):
        record=energy_record(offline=True)
        result=explain_record(request(record),record,lambda _: {'fact_ids':['f0']})
        self.assertEqual(result.ai_status,'USED')
        self.assertTrue(any(f.category=='failure' and 'offline' in f.text for f in result.facts))
        self.assertTrue(any('not independently verified as successful' in f.text for f in result.facts))

    def test_blocked_energy_explains_safety_and_absence_of_action(self):
        record=energy_record(blocked=True)
        result=explain_record(request(record),record)
        self.assertTrue(any(f.category=='safety' and 'blocked/unknown' in f.text for f in result.facts))
        self.assertTrue(any('No device action result' in f.text for f in result.facts))

    def test_model_cannot_supply_hallucinated_prose_or_fact_ids(self):
        record=energy_record()
        for proposal in ({'fact_ids':['nonexistent']},{'fact_ids':['f0'],'text':'Saved 100 kWh'}, {'fact_ids':['f0','f0']},None):
            result=explain_record(request(record),record,lambda _,p=proposal:p)
            self.assertEqual(result.ai_status,'INVALID_FALLBACK')
            self.assertNotIn('100 kWh',str(result.to_dict()))

    def test_model_timeout_and_error_return_all_local_facts(self):
        record=energy_record()
        baseline=explain_record(request(record),record)
        for exc,status in ((TimeoutError(),'TIMEOUT_FALLBACK'),(ConnectionError(),'ERROR_FALLBACK')):
            result=explain_record(request(record),record,Mock(side_effect=exc))
            self.assertEqual(result.ai_status,status)
            self.assertEqual(result.facts,baseline.facts)

    def test_no_private_question_or_source_text_reaches_provider(self):
        record=energy_record()
        record['workflow']['assessment']['rationale']='Private resident: Jane; 123 Secret Street'
        probe=Mock(side_effect=lambda p:{'fact_ids':[p['facts'][0]['fact_id']]})
        explain_record(request(record,'Explain this for Jane at 123 Secret Street'),record,probe)
        payload=json.dumps(probe.call_args.args[0])
        for forbidden in ('Jane','Secret','event_id','rationale','27.0'):
            self.assertNotIn(forbidden,payload)

    def test_record_hash_change_or_foreign_event_is_rejected_before_model(self):
        record=energy_record()
        original=request(record)
        record['workflow']['assessment']['risk_level']='HIGH'
        probe=Mock()
        self.assertEqual(explain_record(original,record,probe).evidence_status,'CONFLICTING')
        record['workflow']['action_results'][0]['event_id']='other'
        self.assertEqual(explain_record(request(record),record,probe).evidence_status,'CONFLICTING')
        probe.assert_not_called()

    def test_missing_record_is_persisted_without_guessing(self):
        req=ExplanationRequest('request','absent','0'*64,'Why?')
        with TemporaryDirectory() as folder:
            path=Path(folder)/'history.jsonl'
            result=submit_explanation(req,None,history_path=path)
            self.assertEqual(result.evidence_status,'MISSING')
            self.assertEqual(load_history(path)[0]['request']['event_id'],'absent')

    def test_direct_smart_home_record_and_pet_nested_record_are_supported(self):
        smart=run_smart_home_control(make_user_goal_event('Good night'),device_tool=SimulatedDeviceTool(default_device_states()),record_path=None).to_dict()
        with TemporaryDirectory() as folder:
            path=Path(folder)/'pet_events.jsonl'
            monitor_pet_workflow(make_pet_scenario('empty_bowl'),record_path=path)
            pet=json.loads(path.read_text(encoding='utf-8'))
        for record in (smart,pet):
            self.assertEqual(explain_record(request(record),record).evidence_status,'CONSISTENT')

    def test_loader_handles_bad_lines_and_preserves_stages_with_same_event_id(self):
        record=energy_record()
        changed=copy.deepcopy(record)
        changed['approval']=False
        with TemporaryDirectory() as folder:
            p=Path(folder)/'energy_comfort.jsonl'
            p.write_text('bad json\n'+json.dumps(record)+'\n'+json.dumps(changed)+'\n',encoding='utf-8')
            sources=load_sources(Path(folder))
            self.assertEqual(len(sources),2)
            self.assertNotEqual(sources[0]['sha256'],sources[1]['sha256'])

    def test_history_can_be_read_after_new_request_objects_and_ignores_corruption(self):
        record=energy_record()
        with TemporaryDirectory() as folder:
            path=Path(folder)/'explanations.jsonl'
            submit_explanation(request(record),record,history_path=path)
            with path.open('a',encoding='utf-8') as f:f.write('null\n{"record_type":"explanation"}\n')
            history=load_history(path)
            self.assertEqual(len(history),1)
            self.assertEqual(history[0]['request']['source_sha256'],digest(record))

    def test_spoofed_success_flag_does_not_override_verification_flags(self):
        record=energy_record(offline=True)
        record['workflow']['action_results'][-1]['success']=True
        result=explain_record(request(record),record)
        self.assertTrue(any(f.category=='failure' for f in result.facts))
