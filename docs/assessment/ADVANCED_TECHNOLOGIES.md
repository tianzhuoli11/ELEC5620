# Technology integration and evidence

Six technologies are integrated in the prototype. Each row names where it is used and the evidence for it. One model's prompting, JSON output and fallback are counted as a single technology.

| Technology / technique | Actual integration | Evidence and effect | Limits |
| --- | --- | --- | --- |
| LangGraph orchestration | Shared coordinator, monitoring and automation graph used across domains | Integration tests assert routes/agent trace, confirmation and failure behavior | Three roles share one model provider; not three independently trained models |
| Streamlit application framework | One shared dashboard (Overview plus five domain pages), callbacks and session state | Actual AppTest input/navigation/control tests; cross-page smoke incident blocks energy execution | Single local dashboard; no multi-user deployment |
| Campus Qwen structured LLM integration | De-identified risk advice and bounded goal interpretation behind validated domain policy | [Measured AI evaluation](AI_EVALUATION.md): 19 real calls, 20 curated cases; Smart Home intent agreement 4/6 without model versus 6/6 with it in this sample | Elderly reply evaluation: 20/26 rules versus 24/26 rules + model; help closed as safe 6 → 0 |
| GitHub Actions continuous integration | Python 3.11/3.13 offline suites, evaluation artifact and Docker verification | Every push and pull request runs the pipeline; verified runs are linked below | Public runners do not have campus VPN or the personal key |
| Docker container deployment | Non-root image, excluded credentials, health endpoint and pinned direct requirements | CI builds, starts and tests the same image | A host VPN does not guarantee container subnet access; venv remains the primary demo route |
| Stateful device simulation with fault injection | In-memory device state with independent readback; offline, timeout, mismatch and changing-safety cases | Controlled failure runs, Pet feeder regression, cross-domain interlock tests | Simulated equipment, not physical IoT hardware (Stage 1 allows simulated devices for the prototype) |

## What the data supports

Actual independent verification of executable commit `986de17` completed successfully on 30 October: [PR CI run](https://github.com/tianzhuoli11/ELEC5620/actions/runs/41048545525), [push CI run](https://github.com/tianzhuoli11/ELEC5620/actions/runs/41048539820). Both Python matrix jobs passed, and the Docker job passed image build, HTTP health check and tests inside the non-root container. Public CI has no campus VPN, so the opt-in live campus tests are skipped there.

On 1 November the integrated `main` (after PR #31) passed **338 tests** locally on Windows, with the two opt-in live-network tests skipped (earlier: 277 tests at `986de17` on 30 October, including the live campus fall/reply test). The separate AI evaluation measured 20 fictional cases, 19 model calls, 18 final policy/curated-intent agreements and a mean end-to-end assessment time of about 4195.6 ms. Safety tests cover specific rejected commands and verified outcomes in the simulated home.

CI adds a repeatable, independent verification gate on every push, and Docker adds a reproducible packaging route; their measured outcomes are build, test and health-check success on a clean runner. Kubernetes, physical sensors and fine-tuning are not used.

In total: five platform, model and deployment technologies (LangGraph, Streamlit, structured LLM integration, GitHub Actions, Docker) and a stateful fault-injection device simulator, each with test or run evidence above.
