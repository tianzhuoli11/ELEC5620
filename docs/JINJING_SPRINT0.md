# Jinjing Huang: Sprint 0 monitoring demonstration

This records Jinjing's Sprint 0 portion of AR-03 / UC-03 and the shared Sensor/Event input work. The current demonstration also runs through the team's shared agent workflow. The offline scenarios need no API key; install the dependencies in `requirements.txt` before running them.

From the repository root, run:

```powershell
python -m simulation.pet_demo --scenario empty_bowl
python -m simulation.pet_demo --scenario unusual_inactivity
python -m simulation.pet_demo --scenario normal_activity
python -m unittest discover -s tests -v
```

Each command creates a fresh **simulated** event with a unique ID and a timezone-aware timestamp. The demo appends the input, domain assessment and shared workflow outcome to `data/runtime/pet_events.jsonl`. This runtime file is ignored by Git. An attention-worthy reading creates a local **simulated** owner-alert result; no external message or feeding occurs.

The current demonstration thresholds are 10% food level for bowl review, 60 minutes for unusual inactivity, and 120 minutes for a HIGH inactivity flag. These are prototype rules for discussion, not veterinary or medical advice. A missing or invalid sensor value produces a MEDIUM review result without inventing a measurement. The regular demo runs without an LLM; the optional campus proxy connection below can request a proposal, while an invalid, unavailable or conflicting response falls back to the deterministic rule result.

## Optional campus AI connection

The course proxy guide documents `http://10.167.60.148:8000/v1`, model `campus-qwen`, and a personal bearer key. The provisional `services/campus_proxy.py` adapter sends the guide's JSON chat-completions request with Python's standard library. Set `ELEC5620_API_KEY` **locally**; `.env.example` names the variables but this prototype does not load `.env` files automatically. Connect to the campus network or USYD VPN, then run:

```powershell
$env:ELEC5620_API_KEY = "your-personal-key"
python -m simulation.pet_demo --scenario empty_bowl --use-campus-llm
```

The key goes only in the Authorization header. The model prompt includes the event type and numeric sensor readings; it excludes pet IDs and other household context. A matching, valid model proposal is recorded separately as `model_rationale`; the final risk remains rule-based. A timeout, invalid JSON or conflicting proposal falls back to fixed rules. Without a key, run the regular simulated commands above. On 19 October 2026, a personal-key VPN smoke test returned accepted model explanations for the empty-bowl and normal-activity scenarios. The unusual-inactivity model proposal conflicted with the HIGH rule result, so the rule safely prevailed.

On 20 October 2026, a repeat test over USYD VPN reached the live course proxy for all three scenarios through the integrated workflow. Normal activity returned an accepted LOW proposal (`fallback_used=false`); empty bowl and unusual inactivity returned conflicting proposals, so the MEDIUM and HIGH rule results prevailed (`policy_override=true`, `fallback_used=true`). The two attention-worthy scenarios recorded `SIMULATED` alerts; normal activity needed no alert. The output was saved only under ignored `data/runtime/`. Recheck proxy availability on the demonstration machine; never include the personal key in evidence or source control.

Integration contract: `models.Event` and `models.SensorReading` are shared input types. `domains.pet_care.integration.monitor_pet_workflow(event, record_path=..., proposal_provider=...)` routes Pet Care through the shared coordinator and monitoring agent, then records the workflow. The caller may provide a proposal function returning `risk_level` and `rationale`; it must not treat a proposal as permission for a device action. Real owner-message delivery and optional feeder control remain separate tasks.

Suggested Sprint 0 review: demonstrate the three scenarios, show the JSONL record for one event, then discuss the shared Event fields and thresholds with the team. Record actual feedback and any agreed changes in Jira rather than treating this document as a completed review.
