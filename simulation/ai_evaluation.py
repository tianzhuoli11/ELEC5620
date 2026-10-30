"""Small reproducible policy-agreement/latency evaluation; fictional inputs only.

Offline fault injection does not measure a real network timeout. Live agreement
with a fixed policy is not evidence of general AI accuracy or improvement.
"""
import argparse
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import statistics
import subprocess
from time import perf_counter

from domains.pet_care.monitoring import assess_pet_event
from domains.elderly_safety.assessment import assess_fall
from domains.elderly_safety.context import collect_context
from domains.elderly_safety.rules import assess_by_rules
from domains.home_security.monitoring import assess_security_event
from services.smart_home_goals import SmartHomeGoalInterpreter, interpret_smart_home_goal_by_rules
from simulation.events import make_user_goal_event
from simulation.pet_demo import make_pet_scenario
from simulation.elderly_scenarios import make_fall_scenario
from simulation.security_scenarios import make_security_scenario


def cases():
    result = []
    for name in ('empty_bowl', 'normal_activity', 'unusual_inactivity'):
        event = make_pet_scenario(name)
        result.append(('pet', name, event, assess_pet_event, assess_pet_event(event).risk_level))
    for name in ('high_floor', 'medium_wait', 'low_dropped_object', 'medium_missing_duration', 'medium_night_uplift'):
        event = make_fall_scenario(name)
        result.append(('elderly', name, event, assess_fall, assess_by_rules(collect_context(event)).risk_level))
    for name in ('normal', 'smoke', 'gas', 'unusual_door', 'suspected_intrusion', 'water_leak'):
        event = make_security_scenario(name)
        result.append(('security', name, event, assess_security_event, assess_security_event(event).risk_level))
    for text, expected in (("Good night", 'night_mode'), ('Turn on the bedroom light', 'direct_control'),
                           ('Do not turn off the bedroom light', 'clarify'),
                           ('Make the house better', 'clarify'),
                           ('Prepare the house for me to retire for the evening', 'night_mode'),
                           ('Please secure the home while I am out for the day', 'away_mode')):
        event = make_user_goal_event(text)
        result.append(('smart_home', text, event, lambda e, p=None: SmartHomeGoalInterpreter(p).interpret(e), expected))
    return result


def value(result):
    return getattr(result, 'risk_level', getattr(result, 'intent', None))


def run(*, live=False, repeats=1):
    providers = {}
    if live:
        from services.campus_proxy import CampusProxyConfig, propose_pet_risk, propose_smart_home_goal
        from services.elderly_llm import propose_fall_risk
        from domains.home_security.llm import propose_security_risk
        config = CampusProxyConfig.from_environment()
        providers = {'pet': lambda e: propose_pet_risk(e, config),
                     'elderly': lambda view: propose_fall_risk(view, config),
                     'security': lambda e: propose_security_risk(e, config),
                     'smart_home': lambda e: propose_smart_home_goal(e, config)}
    rows = []
    for repeat in range(repeats):
        for domain, name, event, evaluate, expected in cases():
            start = perf_counter()
            baseline = evaluate(event)
            baseline_ms = (perf_counter() - start) * 1000
            modes = ('live',) if live else ('invalid_output', 'injected_timeout')
            for mode in modes:
                calls = []
                def probe(observation):
                    begin = perf_counter()
                    entry = {}
                    try:
                        if mode == 'injected_timeout':
                            raise TimeoutError('controlled evaluation failure')
                        proposal = providers[domain](observation) if live else {'risk_level': 'INVALID', 'intent': 'INVALID'}
                        # Responses only; never configuration, headers or credentials.
                        entry['proposal'] = proposal
                        return proposal
                    except Exception as exc:
                        entry['error_type'] = type(exc).__name__
                        raise
                    finally:
                        entry['elapsed_ms'] = round((perf_counter() - begin) * 1000, 3)
                        calls.append(entry)
                begin = perf_counter()
                final = evaluate(event, probe)
                elapsed = (perf_counter() - begin) * 1000
                evidence = getattr(final, 'evidence', '')
                fallback = getattr(final, 'fallback_used', 'fallback' in evidence.lower())
                rows.append({'domain': domain, 'scenario': name, 'repeat': repeat + 1, 'mode': mode,
                             'policy_reference_or_curated_intent': expected, 'baseline': value(baseline),
                             'baseline_ms': round(baseline_ms, 3), 'final': value(final),
                             'agrees_with_reference': value(final) == expected,
                             'elapsed_ms': round(elapsed, 3), 'fallback_used': fallback,
                             'policy_override': getattr(final, 'policy_override', False), 'calls': calls})
    called = [c for row in rows for c in row['calls']]
    return {'run_at_utc': datetime.now(timezone.utc).isoformat(), 'python': platform.python_version(),
            'live': live, 'repeats': repeats, 'cases': rows,
            'summary': {'cases': len(rows), 'provider_calls': len(called),
                        'provider_errors': sum('error_type' in c for c in called),
                        'fallback_cases': sum(r['fallback_used'] for r in rows),
                        'reference_agreements': sum(r['agrees_with_reference'] for r in rows),
                        'mean_workflow_ms': round(statistics.mean(r['elapsed_ms'] for r in rows), 3)},
            'limitations': 'Curated fictional sample; reference agreement is not general accuracy. Baseline uses actual no-model behavior, including the Elderly MEDIUM fallback. Injected timeout measures recovery overhead, not a 15-second network wait. Negation may bypass the provider entirely. No device execution occurs in this assessment evaluation.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--repeats', type=int, default=1)
    parser.add_argument('--output', type=Path, default=Path('data/runtime/ai_evaluation.json'))
    args = parser.parse_args()
    if not 1 <= args.repeats <= 10:
        parser.error('repeats must be between 1 and 10')
    report = run(live=args.live, repeats=args.repeats)
    try:
        report['git_commit'] = subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        report['git_commit'] = 'source-archive'
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(report['summary']))
    print('Saved fictional evaluation results to ' + str(args.output))


if __name__ == '__main__':
    main()
