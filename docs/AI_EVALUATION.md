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

## Reproduce

`python -m simulation.ai_evaluation --output data/runtime/offline.json`

On campus/VPN with the key already set: `python -m simulation.ai_evaluation --live --repeats 1 --output data/runtime/live.json`.

New runs may differ because model outputs, server load and network latency vary. Commit only the fictional, reviewed output; never headers or credentials. The evaluation does not claim Energy uses AI: that domain currently uses deterministic control and evidence-bound explanations.
