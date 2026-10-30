"""UC-06 request/response contracts, independent of UI and device execution."""
from dataclasses import asdict, dataclass
import re


@dataclass(frozen=True)
class ExplanationRequest:
    request_id: str
    event_id: str
    source_sha256: str
    question: str
    style: str = 'detailed'

    def __post_init__(self):
        if not all(isinstance(value,str) for value in (self.request_id,self.event_id,self.source_sha256,self.question)):
            raise ValueError("Explanation request fields must be text")
        if not self.request_id or not self.event_id or not self.question.strip() or len(self.question) > 300:
            raise ValueError("Explanation needs an ID, event and a question of 1–300 characters")
        if re.fullmatch(r'[0-9a-f]{64}', self.source_sha256) is None:
            raise ValueError("Explanation must identify a specific stored record hash")
        if self.style not in ('detailed','brief'):
            raise ValueError("Explanation style must be detailed or brief")


@dataclass(frozen=True)
class ExplanationFact:
    fact_id: str
    category: str
    text: str
    source_fields: tuple[str, ...]


@dataclass(frozen=True)
class ExplanationResult:
    request: ExplanationRequest
    domain: str
    evidence_status: str
    ai_status: str
    facts: tuple[ExplanationFact, ...]
    trace: tuple[str, ...]
    review_status: str = 'NOT_REQUIRED'

    def to_dict(self):
        return asdict(self)
