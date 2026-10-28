# Integrated prototype control review

Work items: SCRUM-32 (Energy control), SCRUM-35 / SCRUM-38 (scenario acceptance), SCRUM-39 (integration), SCRUM-42 (safety).

## User-visible behavior

Smart Home Control clarifies English/Chinese negation before asking the model, including paraphrases beyond its rule parser. A model proposal cannot reverse a recognized positive command or change its recognized home-mode intent; conflicting proposals fall back to the user's deterministic target. This intentionally asks for clarification for some complex requests containing negation.

Energy & Comfort keeps its assessment-only button and adds **Run a simulated adjustment**. Select a context above, explicitly approve the adjustment, select a fictional safety snapshot, and optionally select a device fault. No approval, unknown/conflicting safety, insufficient input or an in-range reading produces no device action.

- Occupied and too warm: close the existing bedroom curtain and set the existing living-room AC to the upper comfort boundary.
- Occupied and too cold: set that AC to the lower comfort boundary. The existing simulated inventory has a generic comfort mode; this does not establish physical heating capability.
- Comfort boundaries outside 18–28 C are blocked rather than silently clamped.
- Unoccupied and above the configured power limit: only the specifically observed, available, powered bedroom light may be switched off after explicit approval. Whole-home watts are not device-level power attribution.
- Shared agents dispatch idempotent set-state commands, allow at most two attempts, continue independent steps after failure and independently verify returned state. Partial/failed results remain visible.
- Protective Elderly/Security devices and door locks are outside this plan's target set. No safety feed or approval is inferred from an event dictionary.

The page saves inputs, the approval, fictional safety snapshot, planned count and actual workflow results to ignored `data/runtime/energy_comfort.jsonl`. Results disappear on rerun when inputs change, preventing a previous outcome being shown as the result of new inputs.

## Boundaries for reviewers

The manual safety snapshot is simulation input, not automatic integration with Elderly Safety or Home Security. The previous `evaluate_formal_control_attempt` route and its unchecked team-approval gates remain assessment-only; this PR does not fabricate teammate approvals. Review the new `run_energy_control` contract and its reuse of the existing M2 device IDs before merging. No physical devices, external notifications, measured energy savings or post-action temperature improvements are claimed. Automatic safety arbitration, post-action sensor observations and general replanning remain future work.

## Repeatable review

Verification on 29 October 2026: all **268 tests passed with zero skips**, including the opt-in real campus fall/reply test over VPN. A separate live Smart Home request returned a campus structured proposal, completed the light-on action and verified the returned state; a negated request returned `CLARIFICATION_REQUIRED` with zero actions. The new Energy page AppTest exercised unknown safety, successful cooling, offline AC (`PARTIAL`) and conflicting safety (zero actions). Existing Pet Care, Home Security, Elderly Safety and Energy assessment tests still pass.

Install `requirements.txt`, run `python -m unittest discover -s tests -q`, then `python -m streamlit run app.py`.

1. Energy & Comfort → Too warm (occupied) → approve + Clear → run adjustment: two verified actions and COMPLETE.
2. Change fault to AC offline: curtain verifies, AC fails after two attempts, PARTIAL.
3. Select Conflict or Unknown: zero actions. Repeat with approval unchecked.
4. Select Occupancy unknown: zero actions. Review saved control audit.
5. Smart Home Control → request “Do not turn off the bedroom light” with AI enabled: clarification, zero device calls. Test a positive light-on request: verified light on.

Tests additionally cover wrong model proposals, cold rooms, out-of-policy preference bounds, protected device observations, real-event rejection and mismatched state readback. Runtime credentials and logs are excluded from commits. See the PR for the actual final suite and live-AI results.

Performance evidence must separate rule-only classification from optional model latency. The earlier live smoke classification measured about 4.2 seconds; do not describe this as a subsecond AI response. Before final demonstration, record the team's chosen prototype response budget and rehearse the exact Canvas source archive on the demonstration machine.
