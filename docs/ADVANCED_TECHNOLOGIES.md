# Technology integration and evidence

The supplied rubric requires at least five advanced technologies for Good and six for Excellent, with effective integration and data. The teaching team decides what counts as a distinct advanced technology. This table does not split one model's prompting, JSON output and fallback into three technologies, or describe simulated sensors as new physical hardware.

| Technology / technique | Actual integration | Evidence and effect | Limits |
| --- | --- | --- | --- |
| LangGraph orchestration | Shared coordinator, monitoring and automation graph used across domains | Integration tests assert routes/agent trace, confirmation and failure behavior | Three roles share one model provider; not three independently trained models |
| Streamlit application framework | One six-view dashboard (Overview plus five domain pages), callbacks and session state | Actual AppTest input/navigation/control tests; cross-page smoke incident blocks energy execution | UI tests do not establish that every screen is visually polished |
| Campus Qwen structured LLM integration | De-identified risk advice and bounded goal interpretation behind validated domain policy | [Measured AI evaluation](AI_EVALUATION.md): 19 real calls, 20 curated cases; Smart Home intent agreement 4/6 without model versus 6/6 with it in this sample | No general accuracy/safety improvement claim; Elderly risk agreement was lower with model, documented honestly |
| GitHub Actions continuous integration | Python 3.11/3.13 offline suites, evaluation artifact and Docker verification | Real branch Actions run must pass before being claimed as verified; links are added after completion | Public runners do not have campus VPN or the personal key |
| Docker container deployment | Non-root image, excluded credentials, health endpoint and pinned direct requirements | CI builds, starts and tests the same image | A host VPN does not guarantee container subnet access; venv remains the primary demo route |
| Stateful device simulation and fault-injection technique (candidate for assessor judgment) | In-memory device state with independent readback; offline, timeout, mismatch and changing-safety cases | Controlled failure runs, Pet feeder regression, cross-domain interlock tests | This is a simulation/testing technique, not physical IoT equipment; it may not be accepted as a sixth advanced technology |

## What the data supports

Actual independent verification of executable commit `986de17` completed successfully on 30 October: [PR CI run](https://github.com/tianzhuoli11/ELEC5620/actions/runs/41048545525), [push CI run](https://github.com/tianzhuoli11/ELEC5620/actions/runs/41048539820). Both Python matrix jobs passed, and the Docker job passed image build, HTTP health check and tests inside the non-root container. Offline CI intentionally skips the one campus/VPN test; it reports 277 run, 276 passed and one skip. The local live run below includes that case.

The 30 October local full suite passed **277 tests with zero skips**, including the opt-in real campus fall/reply test. The separate AI evaluation measured 20 fictional cases, 19 model calls, 18 final policy/curated-intent agreements and a mean end-to-end assessment time of about 4195.6 ms. Safety tests establish specific rejected commands and preserved verified outcomes; they do not establish real-home certification or scalability.

CI adds a repeatable independent environment gate, and Docker adds one reproducible packaging route. Neither is claimed to improve runtime response latency. Their measurable outcomes are build/test/health-check success and reproducibility on the recorded runner. No invented percentage improvement, cloud scalability result, deployed Kubernetes service, physical sensor or fine-tuned model is claimed.

The present implementation has five clearly named platform/model/deployment technologies plus one simulator technique whose rubric eligibility needs assessor judgment. Adding unused libraries or relabeling ordinary Python features would not substantiate Excellent.
