"""Evidence-bound UC-06 explanations of a specific immutable audit record.

LLM assistance orders evidence cards. It cannot supply factual prose, omit
failures or create a fact absent from the record. Device interfaces are absent.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import math

from models.explanations import ExplanationFact, ExplanationRequest, ExplanationResult

DOMAINS = frozenset(('pet_care', 'elderly_safety', 'home_security', 'smart_home_control', 'energy_comfort'))
DEFAULT_HISTORY = Path('data/runtime/explanations.jsonl')
SOURCE_FILES = ('pet_events.jsonl', 'elderly_safety.jsonl', 'security_events.jsonl', 'smart_home_control.jsonl', 'energy_comfort.jsonl')
DEVICE_IDS = frozenset(('bedroom-light','bedroom-curtain','front-door-lock','living-room-ac','pet-feeder','bathroom_light','bedroom_light','living_light','kitchen_light','appliance','gas_valve','water_valve','security_lights','siren','emergency_mode'))


def safe_value(value):
    return isinstance(value,(bool,int,float)) and (not isinstance(value,float) or math.isfinite(value)) or isinstance(value,str) and value in ('on','off','open','closed','comfort','sleep','eco','upright','floor','unknown')


def safe_state(state):
    return {k:v for k,v in state.items() if k in ('power','mode','temperature_c','brightness','position','locked','open','active','available','last_dispensed_g','dispense_count') and safe_value(v)}


def digest(record):
    return hashlib.sha256(json.dumps(record, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def workflow_of(record):
    if not isinstance(record, dict):
        return None
    return record.get('workflow', record if 'action_results' in record else None)


def _facts(record, workflow):
    facts = []
    def add(category, text, *fields):
        facts.append(ExplanationFact('f' + str(len(facts)), category, text, tuple(fields)))
    assessment = workflow.get('assessment')
    if assessment:
        add('assessment', f"The recorded {workflow['domain'].replace('_', ' ')} risk classification is {assessment['risk_level']}.", 'workflow.assessment.risk_level')
    else:
        add('unknown', 'The risk assessment is missing; no risk level or reason is invented.', 'workflow.assessment (absent)')
    readings = record.get('event',workflow['event']).get('readings', [])
    types = {'food_level_percent','inactive_minutes','fall_impact','seconds_without_motion','posture','smoke_alarm','gas_alarm','water_leak','door_open','window_open','motion_detected','appliance_overheat_alarm','appliance_unexpected_run','smart_lock_access_anomaly'}
    for index,r in enumerate(readings):
        if isinstance(r,dict) and r.get('reading_type') in types and safe_value(r.get('value')):
            add('reason', f"Recorded {r['reading_type'].replace('_',' ')}: {r['value']}.", f'workflow.event.readings[{index}]')
    goal = workflow.get('goal')
    if isinstance(goal,dict) and goal.get('intent') in ('night_mode','away_mode','relax_mode','direct_control','unlock_door','clarify'):
        add('reason', 'Recorded requested response: ' + goal['intent'].replace('_',' ') + '.', 'workflow.goal.intent')
    if not any(f.category == 'reason' for f in facts) and workflow['domain'] != 'energy_comfort':
        add('unknown', 'Input observations or the interpreted goal are missing; the underlying reason cannot be reconstructed.', 'workflow.event.readings', 'workflow.goal')
    if workflow['event'].get('event_type') == 'simulated_external_warning':
        original = record.get('assessment',{})
        warning = workflow['event'].get('context',{}).get('warning',{})
        hazard = warning.get('hazard_type')
        if hazard in ('EARTHQUAKE','FLOOD','SEVERE_STORM','BUSHFIRE'):
            add('reason','Recorded fictional external hazard: ' + hazard.replace('_',' ') + '.', 'workflow.event.context.warning.hazard_type')
        if isinstance(original.get('valid'),bool) and isinstance(original.get('relevant'),bool):
            add('reason',f"Recorded source/time validation passed: {original['valid']}; warning affects the configured simulated home area: {original['relevant']}.", 'assessment.valid','assessment.relevant')
    actions = workflow.get('action_results', [])
    for index, action in enumerate(actions):
        success = action.get('accepted') is True and action.get('verified') is True
        status = 'accepted and independently verified' if success else 'not independently verified as successful'
        device = action.get('device_id') if action.get('device_id') in DEVICE_IDS else 'unidentified device'
        add('execution', f"Device {device}: its recorded action was {status}.", f'workflow.action_results[{index}].accepted', f'workflow.action_results[{index}].verified')
        if not success:
            error = str(action.get('error','')).lower()
            detail = 'the simulated device was offline.' if 'offline' in error else 'the returned state did not match.' if 'match' in error else 'execution or independent verification did not succeed.'
            add('failure', 'Recorded device failure: ' + detail, f'workflow.action_results[{index}].error')
        if isinstance(action.get('returned_state'), dict):
            add('returned_state', 'Observed returned device state: ' + json.dumps(safe_state(action['returned_state']), ensure_ascii=False, sort_keys=True), f'workflow.action_results[{index}].returned_state')
    if not actions:
        add('execution', 'No device action result is recorded for this stage of the event.', 'workflow.action_results')
    pending = workflow.get('pending_confirmation')
    if pending:
        add('confirmation', 'This stage is waiting for confirmation; the request is not a completed device operation.', 'workflow.pending_confirmation')
    notice = workflow.get('notification_result')
    if notice:
        status = notice.get('status') if notice.get('status') in ('SIMULATED','SENT','FAILED','UNAVAILABLE') else 'UNKNOWN'
        add('failure' if status in ('FAILED','UNAVAILABLE') else 'notification', 'Recorded notification status: ' + status + '. A simulated notification is not a message to a real recipient.', 'workflow.notification_result.status')
    else:
        add('notification', 'No notification outcome is recorded for this stage.', 'workflow.notification_result')
    if 'feeding' in record:
        status = record['feeding'].get('status')
        if status not in ('NOT_REQUESTED','DISABLED','UNAVAILABLE','REJECTED','VERIFIED','UNVERIFIED','FAILED','READY'):status='UNKNOWN'
        add('failure' if status in ('UNAVAILABLE','UNVERIFIED','FAILED','REJECTED') else 'feeding', 'Optional feeding status: ' + status + '.', 'feeding.status')
    escalation = record.get('escalation')
    if isinstance(escalation,dict):
        status = escalation.get('status')
        if status not in ('AWAITING_ACK','RESOLVED','ESCALATION_FAILED','CLOSED_BY_OPERATOR'):status='UNKNOWN'
        add('escalation','Recorded escalation stage: ' + status + '. A sent alert alone is not caregiver acknowledgement.', 'escalation.status')
        for index,attempt in enumerate(escalation.get('attempts', [])):
            level = attempt.get('level')
            state = attempt.get('outcome')
            if isinstance(level,int) and state in ('awaiting_ack','acknowledged','ack_timeout','send_failed','operator_informed'):
                add('failure' if state in ('ack_timeout','send_failed') else 'escalation',f"Contact level {level}: {state.replace('_',' ')}; acknowledgement recorded: {attempt.get('acknowledged') is True}.", f'escalation.attempts[{index}].outcome', f'escalation.attempts[{index}].acknowledged')
    if workflow['domain'] == 'energy_comfort':
        event = record.get('event', workflow['event'])
        readings = event.get('readings', [])
        context = event.get('context', {}).get('energy_comfort', {})
        allowed = [r for r in readings if r.get('reading_type') in ('indoor_temperature', 'occupancy') and safe_value(r.get('value'))]
        for r in allowed:
            add('comfort', f"Recorded {r['reading_type']}: {r.get('value')} {r.get('unit', '')}.", 'event.readings')
        for field in ('preference', 'energy'):
            if isinstance(context.get(field), dict):
                keys = ('temperature_min_c','temperature_max_c') if field == 'preference' else ('current_power_w','unoccupied_power_limit_w')
                data = {k:v for k,v in context[field].items() if k in keys and safe_value(v)}
                add('comfort' if field == 'preference' else 'energy', f"Recorded {field}: " + json.dumps(data, sort_keys=True) + '.', 'event.context.energy_comfort.' + field)
            else:
                add('unknown', f"{field.capitalize()} context was not recorded; no value is inferred.", 'event.context.energy_comfort.' + field)
        safety = record.get('safety_snapshot')
        if isinstance(safety, dict):
            clear = safety.get('clear') is True
            add('safety', 'Safety takes priority over comfort and energy saving. Recorded clearance was ' + ('clear.' if clear else 'blocked/unknown, so automatic adjustment was not authorized by safety evidence.'), 'safety_snapshot.clear')
        else:
            add('unknown', 'Executable safety clearance was not supplied by this assessment-only record.', 'safety_snapshot')
        if 'approval' in record:
            add('approval', 'Explicit adjustment approval was ' + ('recorded.' if record['approval'] is True else 'not granted.'), 'approval')
        for index, step in enumerate(record.get('selected_plan', [])):
            device = step['device_id'] if step['device_id'] in DEVICE_IDS else 'unidentified device'
            add('strategy', f"Selected strategy step for {device}: " + json.dumps(safe_state(step['parameters']), sort_keys=True) + '.', f'selected_plan[{index}]')
        if not record.get('selected_plan'):
            add('unknown', 'No executable selected plan was stored in this record; historical targets are not reconstructed from current code.', 'selected_plan')
        add('tradeoff', 'Comfort preferences and the unoccupied-power policy determine whether an adjustment is needed; safety clearance and explicit approval constrain whether it can run. Device verification confirms returned state, not measured comfort improvement or energy savings.', 'workflow.assessment', 'event.context.energy_comfort', 'safety_snapshot', 'approval')
        add('unknown', 'Post-action temperature, device-level power attribution and energy savings are unknown because no post-action environmental measurements were recorded.', 'post_action_observations (absent)')
    add('scope', 'This explanation describes the selected recorded stage only. It does not execute, retry or authorize an action.', 'workflow.event.event_id')
    return tuple(facts)


def explain_record(request, record, proposal_provider=None):
    trace = ('HomeCoordinatorAgent:explanation_request',)
    def unavailable(status, text):
        return ExplanationResult(request, 'unknown', status, 'NOT_REQUESTED', (ExplanationFact('unavailable', 'unknown', text, ('source_record',)),), trace + ('HomeCoordinatorAgent:explanation_unavailable',))
    if record is None:
        return unavailable('MISSING', 'No matching stored record was found; the decision cannot be reconstructed.')
    workflow = workflow_of(record)
    try:
        if request.source_sha256 != digest(record) or not isinstance(workflow, dict):
            raise ValueError('record hash or workflow mismatch')
        if workflow.get('domain') not in DOMAINS or workflow['event']['event_id'] != request.event_id:
            raise ValueError('event mismatch')
        assessment = workflow.get('assessment')
        if assessment is not None and (assessment['event_id'] != request.event_id or assessment['domain'] != workflow['domain'] or assessment['risk_level'] not in ('LOW','MEDIUM','HIGH')):
            raise ValueError('assessment mismatch')
        if record.get('event', workflow['event']).get('event_id') != request.event_id:
            raise ValueError('outer event mismatch')
        if record.get('assessment',assessment) is not None and record.get('assessment',assessment).get('event_id') != request.event_id:
            raise ValueError('outer assessment mismatch')
        actions = workflow.get('action_results', [])
        if not isinstance(actions, list) or any(not isinstance(a,dict) or a.get('event_id') != request.event_id for a in actions):
            raise ValueError('action mismatch')
        plan = record.get('selected_plan', [])
        if not isinstance(plan,list) or any(not isinstance(p,dict) or p.get('event_id') != request.event_id or not isinstance(p.get('parameters'),dict) for p in plan):
            raise ValueError('plan mismatch')
        if 'escalation' in record and record['escalation'].get('event_id') != request.event_id:
            raise ValueError('escalation mismatch')
        for key in ('notification_result','pending_confirmation'):
            if workflow.get(key) is not None and workflow[key].get('event_id') != request.event_id:
                raise ValueError('related result belongs to another event')
        facts = _facts(record, workflow)
        if request.style == 'brief':
            facts = tuple(f for f in facts if f.category not in ('returned_state','notification','feeding','approval','comfort','energy'))
    except (ValueError, TypeError, KeyError, AttributeError):
        return unavailable('CONFLICTING', 'Stored evidence is malformed or belongs to a different event/version; no factual explanation was generated.')
    ai_status = 'NOT_REQUESTED'
    if proposal_provider is not None:
        question = request.question.casefold()
        topic = 'tradeoff' if re.search('comfort|energy|trade|saving|舒适|节能', question) else 'execution' if re.search('action|device|fail|设备|失败',question) else 'decision'
        # No raw question, rationale, identity, contact, event ID or sensor values leave the host.
        payload = {'topic': topic, 'style':request.style, 'facts': [{'fact_id': f.fact_id, 'category': f.category} for f in facts]}
        try:
            proposal = proposal_provider(payload)
            ids = proposal.get('fact_ids') if isinstance(proposal, dict) and set(proposal) == {'fact_ids'} else None
            known = {f.fact_id:f for f in facts}
            if not isinstance(ids,list) or not ids or any(not isinstance(i,str) or i not in known for i in ids) or len(set(ids)) != len(ids):
                raise ValueError('invalid explanation proposal')
            facts = tuple(known[i] for i in ids) + tuple(f for f in facts if f.fact_id not in ids)
            ai_status = 'USED'
        except TimeoutError:
            ai_status = 'TIMEOUT_FALLBACK'
        except (ValueError, KeyError, TypeError):
            ai_status = 'INVALID_FALLBACK'
        except Exception:
            ai_status = 'ERROR_FALLBACK'
    snapshot = record.get('safety_snapshot')
    review = ('PENDING' if assessment is None or assessment.get('risk_level') == 'HIGH' or assessment.get('requires_human_review') is True
              or workflow.get('pending_confirmation') or workflow.get('outcome') == 'CLARIFICATION_REQUIRED'
              or any(f.category == 'failure' for f in facts)
              or (isinstance(snapshot,dict) and snapshot.get('clear') is False) else 'NOT_REQUIRED')
    evidence_status = 'PARTIAL' if assessment is None or 'action_results' not in workflow else 'CONSISTENT'
    return ExplanationResult(request, workflow['domain'], evidence_status, ai_status, facts, trace + ('HomeCoordinatorAgent:evidence_bound_explanation',), review)


def submit_explanation(request, record, *, history_path=DEFAULT_HISTORY, proposal_provider=None):
    from agents.coordinator import HomeCoordinatorAgent
    from domains.base import DomainRegistry
    result = HomeCoordinatorAgent(DomainRegistry([])).explain(request, record=record, proposal_provider=proposal_provider)
    path = Path(history_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a',encoding='utf-8') as stream:
        stream.write(json.dumps({'record_type':'explanation','recorded_at':datetime.now(timezone.utc).isoformat(), **result.to_dict()},ensure_ascii=False,allow_nan=False) + '\n')
    return result


def load_sources(directory=Path('data/runtime')):
    entries = []
    for name in SOURCE_FILES:
        path = Path(directory) / name
        if not path.exists():
            continue
        stages = {}
        with path.open(encoding='utf-8') as stream:
            for line_number, line in enumerate(stream, 1):
                try:
                    record = json.loads(line)
                    workflow = workflow_of(record)
                    if isinstance(workflow,dict) and workflow.get('domain') in DOMAINS:
                        if not isinstance(workflow.get('event'),dict) or not isinstance(workflow['event'].get('event_id'),str) or not workflow['event']['event_id']:
                            continue
                        stages[workflow['event']['event_id']] = workflow
                    elif isinstance(record,dict) and record.get('record_type') == 'elderly_escalation':
                        escalation = record.get('escalation',{})
                        workflow = stages.get(escalation.get('event_id'))
                        record = {'workflow':workflow, 'escalation':escalation}
                    if isinstance(workflow,dict) and workflow.get('domain') in DOMAINS:
                        entries.append({'source':name, 'line':line_number, 'sha256':digest(record), 'record':record,
                                        'event_id':workflow['event']['event_id'], 'domain':workflow['domain']})
                except (ValueError, KeyError, TypeError, AttributeError):
                    continue
    return list(reversed(entries))


def load_history(path=DEFAULT_HISTORY, limit=15):
    history = []
    path = Path(path)
    if not path.exists():
        return history
    with path.open(encoding='utf-8') as stream:
        for line in stream:
            try:
                item = json.loads(line)
                if item.get('record_type') not in ('explanation','explanation_review') or not isinstance(item.get('request'),dict):
                    continue
                if not all(k in item for k in ('evidence_status','ai_status','facts','trace')) or not isinstance(item['facts'],list):
                    continue
                if not all(isinstance(f,dict) and isinstance(f.get('text'),str) and isinstance(f.get('source_fields'),list) and all(isinstance(p,str) for p in f['source_fields']) for f in item['facts']):
                    continue
                history.append(item)
            except (ValueError, AttributeError, TypeError):
                continue
    return list(reversed(history[-limit:]))


def review_explanation(request_id, *, approved, operator_role, history_path=DEFAULT_HISTORY):
    """Explicit local demo-operator action; never accepts approval from an LLM.

    Deployment is a single trusted local operator prototype, not a multi-user
    identity/authentication service. The UI makes this assumption explicit.
    """
    if operator_role != 'Human Founder/Operator' or not isinstance(approved,bool):
        raise ValueError('An explicit demo operator decision is required')
    candidates = [r for r in load_history(history_path,limit=10**9) if r['request'].get('request_id') == request_id]
    if not candidates or candidates[0].get('review_status') != 'PENDING':
        raise ValueError('No pending explanation review exists for this request')
    result = dict(candidates[0])
    result.update(record_type='explanation_review',review_status='APPROVED' if approved else 'REJECTED',
                  operator_role=operator_role,recorded_at=datetime.now(timezone.utc).isoformat())
    result['trace'] = list(result['trace']) + ['Human Founder/Operator:' + result['review_status'].lower()]
    with Path(history_path).open('a',encoding='utf-8') as stream:
        stream.write(json.dumps(result,ensure_ascii=False,allow_nan=False)+'\n')
    return result
