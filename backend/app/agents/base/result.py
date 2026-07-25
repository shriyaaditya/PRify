from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class Finding(BaseModel):
    """
    Represents a single issue, recommendation, or finding discovered by an agent.
    """

    title: str
    description: str
    severity: str
    confidence: float
    recommendation: str
    file_path: str
    line_number: Optional[int] = None
    category: str
    evidence: Optional[str] = None


class AgentResult(BaseModel):
    """
    The standardized output format returned by every agent.
    """

    agent_name: str
    summary: str
    findings: List[Finding] = Field(default_factory=list)


class AgentExecution(BaseModel):
    """
    Captures execution metadata for an agent run.
    """

    agent_name: str
    start_time: float
    duration_ms: float
    status: str
    errors: List[str] = Field(default_factory=list)
    token_usage: Dict[str, int] = Field(default_factory=dict)
    cost: Optional[float] = None
