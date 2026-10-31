# AI evaluation: measured sample and limitations

Run: 2026-10-30T11:21:27.300966+00:00. Python 3.13.5. Base c4c8ebe029bb92c01496d6cdd3c2c320a802bdbf. Exact runner hash is in the JSON; the runner was added in the evidence worktree. Inputs are fictional, and only response proposals and timings were retained.

[Live results](evidence/ai_live.json) · [Controlled failure results](evidence/ai_offline.json)

## Method

20 curated scenarios across four domains, one repetition each. 19 provider calls were made; negation was blocked before the provider. Compare final risk against a fixed policy reference, or goal intent against a small manually labeled sample. This is not a clinical dataset, a general language benchmark, or proof that AI improves safety over the rules. No devices were executed by this evaluation.

| Domain | Cases | No-model reference agreements | Live final reference agreements | Mean provider latency (ms) |
| --- | --- | --- | --- | --- |
| pet | 3 | 3/3 | 3/3 | 3090.924 |
| elderly | 5 | 4/5 | 3/5 | 5800.767 |
| security | 6 | 6/6 | 6/6 | 4238.349 |
| smart_home | 6 | 4/6 | 6/6 | 4040.688 |

## Interpretation

- All 19 live provider requests completed without a transport/parse exception. Four final cases used a fallback/guard path; inspect their stored proposals rather than interpreting this as four network failures.
- Final reference agreement was 18/20. In two Elderly cases the model raised the risk above the fixed rule reference. This is conservative disagreement, not automatically an error or an improvement.
- The Elderly no-model baseline deliberately raises LOW to MEDIUM when a model is unavailable. Consequently baseline disagreement is not a generic classifier accuracy measure.
- The Smart Home sample includes two curated paraphrases outside the small deterministic phrase list. The table reports whether AI resolved those particular intents; six examples cannot establish broad improvement.
- Real case latency ranged from 0.003 to 9435.654 ms, including the provider-bypassed negation case. Do not claim subsecond AI classification.
- Forty offline cases inject invalid output or raise TimeoutError immediately. Their timing measures recovery overhead after the exception, not the duration of a real 15-second HTTP timeout.

## Feedback used for refinement

| Evidence | Observation | Refinement | Retest |
| --- | --- | --- | --- |
| PR #8 actual requested-changes review | Feeder read timeout blocked unrelated monitoring/notification | Optional adapter failure boundary and regression stubs | Reviewer approval after 134 tests; linked in AGILE.md |
| PR #17 integration inspection | Wrong model proposal could reverse negation; Energy lacked safety evidence | Pre-model negation guard, explicit-target consistency and fresh cross-domain interlocks | Faulty-proposal and cross-page regression tests; live command smoke test |
| This evaluation | Some valid model risk proposals disagree with domain policy | Existing fixed risk floors/strict-match guards retained; disagreements documented | Raw per-case final outcomes preserve the fixed security/pet policies |

## Elderly Safety: resident-reply interpretation

After a medium-risk fall the resident is asked "Are you okay?" and, if the answer is unclear, "Do you need me to contact your family?". The verdict (safe / help / unclear) decides whether the event closes, the question is repeated, or the caregiver is alerted and the light switched on. `simulation/elderly_reply_evaluation.py` compares the rule interpreter with rules + model on 20 fictional replies labelled by the domain owner. It calls the same `interpret()` the workflow uses; no device or person is involved. [Raw results](evidence/elderly_reply_eval_live.json).

**Model used:** `qwen3.7-plus` via the DashScope OpenAI-compatible endpoint, **not** campus-qwen. The personal course key available on 31 Oct was rejected by the proxy (HTTP 401), so this run used the domain owner's own provider account through the existing `ELEC5620_BASE_URL` / `ELEC5620_MODEL` settings. Only the fictional reply text and attempt number were sent. Results may differ for campus-qwen.

| Metric (20 replies) | Rules before fix | Rules after fix | Rules + qwen3.7-plus |
| --- | --- | --- | --- |
| Verdict matches label | 11 | 15 | **18** |
| **Help needed but event closed (must be 0)** | **1** | 0 | 0 |
| Help needed but delayed by an extra question | 3 | 0 | 0 |
| Clear reply but asked again | 7 | 4 | **0** |
| Resident fine but caregiver alerted | 1 | 1 | 2 |
| Mean / max time per reply | <1 ms | <1 ms | 2818 / 4850 ms |

Interpretation:

- **The evaluation found a safety gap in the rules.** On the second question, "No, I can't move" was closed as safe because the reply starts with "No"; "I'm not okay", "I can't move my leg" and "I fell and I feel faint" needed an extra question before help was sent. Adding "can't move", "unable to", "not ok" and "faint" to the help phrases removed both problems. This fix also protects the default demonstration, which runs without a model.
- **With the model,** four natural replies the rules cannot parse ("Everything is under control", "I sat down on purpose", "I'm back on my feet", "I just slipped a little") were understood, so no clear reply needed a second question.
- **The guard held.** For "Please don't, I'm fine" the rules say help (the reply starts with "please"); the model's different verdict was not accepted because a model may never turn a rule "help" into "safe". The case therefore stays a false alert by design.
- **The model is more cautious in one case.** A bare "No" to the second question was classed unclear, which escalates on the last attempt. The model did not close any help request as safe.
- Model latency (about 3 s on average) is spent inside the 30 s confirmation window.
- **This table measures the reply step in isolation, not the end-to-end page.** A reply is only interpreted when the fall itself is assessed MEDIUM. In a Streamlit run on 31 Oct with the same model, "Fall, then not moving (30 s)" was raised from MEDIUM to HIGH (model rationale: impact followed by 30 s of immobility), so the caregiver was alerted and the light switched on without asking the resident. Policy allows a model to raise risk, never lower it. With this model the reply improvement therefore applies to fewer events, and the trade-off is more caregiver alerts. In the earlier campus-qwen run (table above) two of the three MEDIUM fall scenarios stayed MEDIUM, so the effect depends on the model.

| Evidence | Observation | Refinement | Retest |
| --- | --- | --- | --- |
| Reply evaluation, rules only | A help reply was closed as safe; three help replies were delayed | Help phrases extended (`confirmation.py`) | Help closed or delayed: 4 → 0; offline test guards it |
| First live run | A rejected key made every call fall back silently, producing a table with no model involvement | One test call before a live run; stop with the reason | Rejected key now stops with "HTTP 401" |
| Second live run | The thinking model spent the whole token budget on reasoning and returned empty text | Opt-in `ELEC5620_DISABLE_THINKING=1` sends `enable_thinking=false`; empty answers raise a clear error | 19/20 model verdicts used |

## Reproduce

`python -m simulation.ai_evaluation --output data/runtime/offline.json`

On campus/VPN with the key already set: `python -m simulation.ai_evaluation --live --repeats 1 --output data/runtime/live.json`.

Elderly reply interpretation: `python -m simulation.elderly_reply_evaluation` (rules only), or add `--live` with a configured model. For a thinking model on another OpenAI-compatible provider also set `ELEC5620_DISABLE_THINKING=1`.

New runs may differ because model outputs, server load and network latency vary. Commit only the fictional, reviewed output; never headers or credentials. The evaluation does not claim Energy uses AI: that domain currently uses deterministic control and evidence-bound explanations.
