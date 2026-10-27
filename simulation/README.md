# Event and device simulation

`events.py` creates simulated sensor and direct user-goal events. `goals.py` contains the original exact-phrase framework interpreter; it is not campus AI. `devices.py` holds in-memory simulated devices with explicit offline/unknown-device failures. `framework_demo.py` exercises the shared contracts, while `smart_home_demo.py` runs Yang Yang's complete four-device UC-02 success, failure and safety scenarios. Jinjing Huang integrates Sensor/Event generation; Yang Yang integrates devices; all domain owners provide further scenarios.

- Send inputs conforming to `models/` into the shared monitoring flow.
- Keep static fictional fixtures in `data/samples/`; keep generators and state-transition code here.
- Include normal and abnormal fall, pet, security and temperature inputs.
- Support offline, failed-action and state-mismatch device scenarios.
- Do not represent simulated state or notifications as real device/recipient responses.

Domain rules belong in `domains/`, common device entry points in `tools/`, and shared agent orchestration in `agents/`.

`events.py` makes shared simulated sensor events, and `pet_demo.py` provides three repeatable Pet Care scenarios. Run the core path with `python -m simulation.pet_demo --scenario empty_bowl`, then the optional simulated feeder with `python -m simulation.pet_demo --scenario empty_bowl --enable-feeding --feed-grams 20`. Add `--feeder-offline` or `--stale-readback` to demonstrate failure reporting without automatic repeat dispensing. See `docs/JINJING_SPRINT2.md` for expected outcomes.
