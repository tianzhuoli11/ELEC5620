"""Shared data contracts used by the five smart-home domains."""

from .events import Event, SensorReading
from .explanations import ExplanationRequest, ExplanationFact, ExplanationResult
from .context import (
    DeviceObservation,
    EnergyProfile,
    HomeContext,
    HomeEnvironment,
    HomeMode,
    UserPreference,
)
from .workflow import (
    ActionRequest,
    ActionResult,
    AuditEntry,
    ConfirmationReply,
    GoalInterpretation,
    GoalPlan,
    MonitoringDecision,
    NotificationRequest,
    NotificationResult,
    PendingConfirmation,
    RiskAssessment,
    WorkflowResult,
)

__all__ = [
    "ExplanationRequest", "ExplanationFact", "ExplanationResult",
    "Event", "SensorReading", "RiskAssessment", "ActionRequest", "ActionResult",
    "NotificationRequest", "NotificationResult", "MonitoringDecision", "AuditEntry",
    "WorkflowResult",
    "GoalInterpretation", "GoalPlan",
    "HomeEnvironment", "UserPreference", "EnergyProfile", "HomeMode",
    "DeviceObservation", "HomeContext",
    "PendingConfirmation", "ConfirmationReply",
]
