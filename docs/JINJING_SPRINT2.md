# Jinjing Huang — Pet Care Sprint 2 acceptance evidence

This document records the Pet Care work completed ahead of the planned Sprint 2 window (28–31 October 2026). It covers AR-03 / UC-03 core monitoring and simulated owner alerts, plus optional OR-01 simulated feeding. It does not claim a real owner message or physical feeder operation.

## Implemented flow

1. A simulated bowl-level or inactivity event enters the shared HomeCoordinatorAgent and MonitoringAgent.
2. Fixed rules assess the reading. A valid campus AI proposal may add an explanation, but it cannot lower the rule-based risk or request feeding. Timeout, malformed or conflicting proposals use the rule result.
3. MEDIUM/HIGH observations create a local simulated owner-alert outcome. LOW observations need no alert. The event, assessment, workflow, alert result and separate feeding result are appended to ignored `data/runtime/pet_events.jsonl`.
4. Optional feeding requires an explicit 1–50 g goal, the feature flag, a simulated bowl reading at or below 10%, and an available simulated feeder. Only then does the shared DeviceAutomationAgent dispatch one action and compare the returned feeder state with the expected event ID and portion. An uncertain readback is recorded as `UNVERIFIED`; no blind repeat is attempted. Replaying the same event against the same feeder cannot dispense twice.
5. Disabling or failing the optional feeder does not prevent the core assessment, alert and record from completing. Alert and feeder outcomes remain separate in the record and UI.

## Repeatable demonstrations

Run these from the repository root after installing `requirements.txt`:

| Scenario | Command | Expected evidence |
| --- | --- | --- |
| Core without feeder | `python -m simulation.pet_demo --scenario empty_bowl` | MEDIUM, simulated owner alert, `feeding.status=NOT_REQUESTED`, no device action |
| Normal reading | `python -m simulation.pet_demo --scenario normal_activity` | LOW, no alert or device action |
| Verified optional feed | `python -m simulation.pet_demo --scenario empty_bowl --enable-feeding --feed-grams 20` | One verified simulated dispense, `feeding.status=VERIFIED`, simulated alert |
| Feeder unavailable | Add `--feeder-offline` to the prior command | `feeding.status=UNAVAILABLE`, no dispatch; alert and record still complete |
| Readback mismatch | Add `--stale-readback` to the verified-feed command | One dispatch, `feeding.status=UNVERIFIED`; no automatic retry or success claim |

The Pet Care page has the same editable scenarios and an **Optional feeding demo** panel. Enable the simulated feeder and explicitly request a portion to run the optional path. Turn on **Simulate feeder offline** for the unavailable path. All inputs are fictional.

## Verification performed on 24 October 2026

- `python -m unittest discover -s tests -q`: **122 tests passed**, including Pet Care acceptance/failure tests and a Streamlit UI test of verified and unavailable feeding.
- Clean-source rehearsal: copied 93 source files into a separate directory without `.git` or `.env`, created a new virtual environment, installed the pinned `requirements.txt`, and reran all **122 tests successfully**.
- Started `streamlit run app.py` from that clean directory and received **HTTP 200** from its local dashboard URL.
- Over the connected USYD VPN, a fictional normal-activity event received an accepted live `campus-qwen` explanation (`risk=LOW`, `fallback_used=false`, `workflow.outcome=ASSESSED`, `feeding=NOT_REQUESTED`). No API key or model response was committed.
- After PR #7 was merged into `main`, the combined repository suite passed **132 tests**. A separate browser session then verified the Pet Care page and its saved JSONL records: an explicit 20 g simulated feed was independently verified; an offline feeder produced `UNAVAILABLE` with zero verified device actions while the simulated owner alert still completed; and a normal-activity request displayed an accepted live campus AI explanation without alert or feeding.
- The automated tests use simulated devices and controlled AI failures. Repeat the live campus AI request on the final demonstration machine; this local smoke test does not prove VPN availability at the venue.

## PR review follow-up — 25 October 2026

- A feeder preflight timeout or malformed state now reports `UNAVAILABLE` so the rule assessment, simulated owner alert and event record can complete. Regression tests cover a timeout-raising adapter and a malformed returned state.
- The Pet Care reset now initializes the portion widget through Session State without also supplying a widget default, avoiding Streamlit's conflicting-default warning.
- The 11 Pet Care Sprint 2 tests and all 121 non-UI repository tests passed locally. The full run reached a Streamlit `AppTest` case but did not finish in this terminal session; the UI change still needs a completed interactive or `AppTest` check on the review machine.
- Jira work items: [SCRUM-36 Pet Care scenario acceptance](https://f1orestyinlem.atlassian.net/browse/SCRUM-36) and [SCRUM-29 optional automatic feeding](https://f1orestyinlem.atlassian.net/browse/SCRUM-29).

## Remaining team delivery steps

- Add the actual commit or pull-request link, test output and UI screenshots to the relevant Jira Story before marking it Done.
- Re-run the complete clean-source rehearsal after the remaining domains are merged, using the exact Canvas submission archive. Check the campus AI connection and any selected optional functions on the demonstration network.
- Keep `ELEC5620_API_KEY` out of the archive, screenshots and logs. A clean deployment can run the simulated paths without it.
