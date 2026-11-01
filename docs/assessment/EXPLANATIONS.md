# OR-03 / UC-06 / OR-05 explanation workflow

The sidebar **Decision explanations** page is the shared user-request entry point for all five domains. It reads persisted decisions rather than reconstructing actions from current code or transient UI state. `ExplanationRequest` identifies the exact event and SHA-256 record version. `HomeCoordinatorAgent.explain` collects recorded assessment, selected strategy, action/verification results and relevant context into source-referenced evidence cards. Request and outcome are appended to ignored `data/runtime/explanations.jsonl`; the page reloads history after a fresh app session.

## Supported user flow

1. Run a domain scenario, then open Decision explanations.
2. Select the stored event stage. Initial/resumed decisions with the same event ID remain distinct by record hash and source line.
3. Ask why the decision or action occurred. For Energy use a comfort/energy trade-off question. Choose Detailed or Simpler and optionally campus AI.
4. The response shows known observations, classification, permitted response, actual execution/notification/feeding outcome and explicit unknowns, each with source fields. Explanation requests have no device interface and cannot execute or retry an action.
5. High-risk, incomplete, pending-confirmation, safety-blocked or failed-action explanations enter `PENDING` review. The page withholds the final answer until the local demo Human Founder/Operator previews and approves it. Rejection and approval are separately persisted; repeated review of the same completed request is rejected.
6. Revisit the history to see the request, evidence references and review outcome. A simpler request creates its own audit entry against the same source version, retaining failures, safety and missing-evidence statements.

The app is a single-household local prototype operated by an authorized user. The demo-operator review switch is an explicit local human action, not multi-user authentication or an independently verified identity service. A model proposal or event dictionary cannot approve a review.

## AI assistance and privacy

The campus model receives only a derived topic/style and anonymous fact IDs/categories. It selects up to three relevant cards to prioritize. Its response must contain only valid unique fact IDs; every remaining fact is appended locally, so it cannot hide a failure or uncertainty. Final factual wording is deterministic and evidence-bound, not unconstrained generated prose. Raw questions, resident/contact details, recorded rationale, event IDs, sensor values, device IDs and API keys are not included in this prompt.

Malformed output, nonexistent/duplicate IDs, attempted factual prose, timeout or network failure uses the local complete fact set and an explicit fallback status. A real initial model call was rejected by the strict JSON path; reducing the model task to bounded selection and allowing a 2048-token response budget produced an accepted `USED` result in the follow-up live test. This is a recorded feedback refinement, not a guarantee of valid responses on every call.

Returned evidence cards do not echo arbitrary recorded rationale/error text, raw contacts or arbitrary device-state fields. Safe typed observations and known state fields are used instead. Raw user questions are retained locally as part of their own request history; do not enter sensitive information during public demonstrations.

## Energy trade-offs

New Energy control audit records include the full selected simulated plan and the domain assessment, in addition to context, approval, before/after safety snapshots and independently verified results. The explanation links recorded temperature/occupancy, preference and power policy, selected AC/curtain/light targets, safety priority, actual failure/readback evidence and unknown environmental effects. Assessment-only or older records with no selected plan explicitly say the plan is unavailable; no historical plan is guessed from current implementation.

Temperature improvement, measured energy savings and device-level attribution remain unknown without post-action sensor measurements. Explaining those unknowns is part of OR-05; it does not claim that the underlying UC-05 prototype measures physical effects. Legacy assessment-only helper APIs remain compatible.

## Source and failure handling

- Supported sources are the fixed local Pet, Elderly, Home Security, Smart Home and Energy JSONL files, not a user-supplied filesystem path.
- Elderly escalation stages are joined only to an earlier stored workflow with the same event ID in the same file; contact identities are not exposed. Orphan stages without a matching workflow are excluded.
- A missing record produces `MISSING`; malformed or mismatched event/action/notification/plan evidence produces `CONFLICTING`. Supported action facts remain available when an assessment is absent, with `PARTIAL` evidence and operator review.
- Hashes detect selection/version changes; they are not signatures or protection against a trusted local operator editing every audit file.
- Requests/reviews are shown as saved only after the append succeeds. Corrupt history lines are ignored. A write failure is displayed and does not operate a device.

## Reproduce

Local verification on 30 October: **305 repository tests passed, zero skips**, including the real campus fall/reply test and the new explanation organizer test. The organizer returned `USED` and preserved all 17 supported evidence cards. There are 28 new explanation/service/page tests; fault injection is not mislabeled as a real network request. Public CI intentionally skips the two campus/VPN cases.

Run `python -m unittest discover -s tests -p "test_explanation*.py" -q`, then the full suite. On VPN with the existing campus key, set `ELEC5620_RUN_REAL_PROXY=1` to include the live explanation and Elderly tests.

For a short demo: run Pet Care empty bowl, request its explanation, then choose Simpler. For a review case use a failed Energy AC action, open the explanation, observe PENDING, enable demo-operator controls and explicitly approve/reject it. For OR-05 successful context/strategy evidence, run the fresh clear safety flows followed by the Energy adjustment and select that stored control record.
