# Integrated prototype control review

Work items: SCRUM-32 (Energy control), SCRUM-35 / SCRUM-38 (scenario acceptance), SCRUM-39 (integration), SCRUM-42 (safety).

## User-visible behavior

Smart Home Control clarifies English/Chinese negation before asking the model, including paraphrases beyond its rule parser. A model proposal cannot reverse a recognized positive command or change its recognized home-mode intent; conflicting proposals fall back to the user's deterministic target. This intentionally asks for clarification for some complex requests containing negation.

Energy & Comfort keeps its assessment-only button and adds **Run a simulated adjustment**. Select a context above, explicitly approve the adjustment, first obtain fresh assessments from both safety pages, and optionally select a device fault. No approval, unknown/conflicting/stale safety, insufficient input or an in-range reading produces no device action.

- Occupied and too warm: close the existing bedroom curtain and set the existing living-room AC to the upper comfort boundary.
- Occupied and too cold: set that AC to the lower comfort boundary. The existing simulated inventory has a generic comfort mode; this does not establish physical heating capability.
- Comfort boundaries outside 18–28 C are blocked rather than silently clamped.
- Unoccupied and above the configured power limit: only the specifically observed, available, powered bedroom light may be switched off after explicit approval. Whole-home watts are not device-level power attribution.
- Shared agents dispatch idempotent set-state commands, allow at most two attempts, continue independent steps after failure and independently verify returned state. Partial/failed results remain visible.
- Post-action **room** temperature, occupancy, and whole-home power are **`UNKNOWN_NOT_MEASURED`** unless a separate probe is supplied (`domains/energy_comfort/post_action.py`); device readback success does not claim comfort or energy savings.
- Protective Elderly/Security devices and door locks are outside this plan's target set. No safety feed or approval is inferred from an event dictionary.

The page uses three UI modes: **`ASSESSMENT_ONLY`** (formal integration checklist), **`EXPLICIT_SIMULATION`** (approved panel with live session SafetyState), and **`FORMAL_CONTROL_PENDING`** for unchecked M2/M4 automatic contracts. Eligibility worksheet fields are demo-only and do not replace SafetyState.

The page saves inputs, the approval, cross-domain safety evidence, planned count and actual workflow results to ignored `data/runtime/energy_comfort.jsonl`. Results disappear on rerun when inputs change, preventing a previous outcome being shown as the result of new inputs.

## Repeatable review

29 October verification: **275 repository tests passed, zero skips**, with the real campus fall/reply test enabled over VPN. The actual cross-page Streamlit test runs both safety pages, verifies successful energy adjustment, then triggers Smoke in Home Security and verifies zero subsequent energy actions. Separate tests cover stale/missing evidence, pending confirmation, active warning retention and safety changes between device commands.

1. Home Security: assess Normal. Elderly Safety: run the medium fall and answer “I'm fine”. Both actual workflow results must be clear.
2. Energy & Comfort: choose Too warm (occupied), approve and run adjustment. Expect two verified actions, COMPLETE and recorded safety event IDs.
3. Return to Home Security and assess Smoke, or leave a medium observation waiting for confirmation. Return to Energy: zero actions, with the blocking source explained.
4. Reassess Security Normal; clear the elderly event through its safe-reply flow if necessary. Select AC offline in Energy: curtain verifies, AC fails and the result is PARTIAL.
5. Edit/reset a safety input without running it: its previous clearance is invalidated. Wait five minutes: clearance expires and a new assessment is required.
6. Assess a relevant external emergency warning: it blocks energy until its validated expiry, even if another unrelated/invalid warning or normal home-security observation follows.
7. Smart Home: a negated command asks for clarification before AI; an explicit positive command cannot be reversed by an incorrect model proposal.

All sensor inputs, devices and notifications remain simulated. The safety state is local to the current browser session: a new/restarted session begins unknown and blocks control. It is not persistent monitoring of a real home. Changing safety mid-plan blocks subsequent dispatches; the UI audit saves both initial and final safety snapshots. Acknowledging a caregiver alert alone does not establish that a hazard has cleared.

The legacy approval/readiness APIs remain for historical assessment tests; no fabricated teammate approval flags were set. Reviewers should review the executable simulation contract and device mapping in this PR. Physical sensors, measured post-action temperature improvements and energy savings are not claimed.
