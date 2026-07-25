from typing import List, Optional

from pydantic import BaseModel, Field


class ConsensusFinding(BaseModel):
    """
    Structured finding output from the Consensus Agent.
    Represents a consolidated, deduplicated, and evidence-verified finding merged across specialist agents.
    """

    __test__ = False

    title: str = Field(description="Concise title for the consolidated finding.")
    category: str = Field(
        description="Consolidated category (e.g. security:sql-injection, performance:n+1-query, architecture:boundary-violation, testing:missing-unit-tests)."
    )
    severity: str = Field(
        description="Normalized severity level (Low, Medium, High, Critical)."
    )
    confidence: float = Field(
        description="Consolidated confidence score (0.0 to 1.0) reflecting evidence quality."
    )
    summary: str = Field(description="Short summary of the consolidated finding.")
    reason: str = Field(
        description="Detailed technical rationale explaining why this finding is valid."
    )
    impact: str = Field(description="Expected real-world impact if unaddressed.")
    recommendation: str = Field(
        description="Actionable consolidated advice to resolve the issue."
    )
    file_path: str = Field(
        description="Primary relative file path where the issue resides."
    )
    line_number: Optional[int] = Field(
        default=None, description="Optional line number where the issue is located."
    )
    evidence: str = Field(
        description="Verified code, doc, or static analysis evidence supporting the finding."
    )
    source_agents: List[str] = Field(
        description="List of specialist agent names that produced or corroborated this finding (e.g. ['ArchitectureAgent', 'PerformanceAgent'])."
    )
    suggested_fix: Optional[str] = Field(
        default=None,
        description="Optional code snippet or suggested fix if supported by evidence.",
    )


class ConsensusReviewResult(BaseModel):
    """
    Structured output expected from the LLM when consolidating review results across specialist agents.
    """

    __test__ = False

    summary: str = Field(
        description="Comprehensive high-level summary of the consolidated Pull Request review."
    )
    findings: List[ConsensusFinding] = Field(
        default_factory=list,
        description="List of validated, deduplicated consensus findings.",
    )
