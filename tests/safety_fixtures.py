"""Create safety evidence by running actual domain workflows, never preset results."""
from pathlib import Path
from tempfile import TemporaryDirectory
from services.safety_state import SafetyState
from domains.home_security.integration import monitor_security_workflow
from simulation.security_scenarios import make_security_scenario
from domains.elderly_safety.integration import build_workflow, run_elderly_safety, resume_elderly_safety
from domains.elderly_safety import default_devices
from simulation.devices import SimulatedDeviceTool
from simulation.elderly_scenarios import make_fall_scenario


def safety_fixture(blocked=False):
    safety = SafetyState()
    with TemporaryDirectory() as folder:
        security = monitor_security_workflow(make_security_scenario("smoke" if blocked else "normal"), record_path=Path(folder) / "security.jsonl")
        safety.observe(security.workflow)
    engine, handler = build_workflow(device_tool=SimulatedDeviceTool(default_devices()))
    result = run_elderly_safety(make_fall_scenario("medium_wait"), workflow=engine, handler=handler, record_path=None)
    result = resume_elderly_safety(result, "I'm fine, I just sat down.", workflow=engine, handler=handler, record_path=None)
    safety.observe(result)
    return safety
