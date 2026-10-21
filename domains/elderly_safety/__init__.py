"""Elderly Safety domain (owner: Yuanbo Zhang). AR-01 / UC-01, optional OR-04.

`ElderlySafetyHandler` plugs into the shared `SmartHomeWorkflow`:

    from agents.graph import SmartHomeWorkflow
    from domains.elderly_safety import ElderlySafetyHandler, default_devices
    from simulation.devices import SimulatedDeviceTool
    from simulation.notifications import SimulatedNotificationService

    workflow = SmartHomeWorkflow([ElderlySafetyHandler()], SimulatedDeviceTool(default_devices()),
                                 notifier=SimulatedNotificationService())
    result = workflow.run(event)

No Streamlit, no device access, no LLM client here; the proposal provider is
injected by the caller (services/).
"""

from domains.elderly_safety.assessment import FallAssessment, assess_fall
from domains.elderly_safety.handler import ElderlySafetyHandler, default_devices

__all__ = ["ElderlySafetyHandler", "FallAssessment", "assess_fall", "default_devices"]
