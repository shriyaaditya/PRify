from typing import List, Optional

from pydantic import BaseModel, Field


class PerformanceFinding(BaseModel):
    """
    Structured finding output from the Performance Agent.
    Requires evidence from code changes and optional repository performance documentation.
    """

    title: str = Field(description="Concise title for the performance finding.")
    category: str = Field(
        description="Performance category (e.g., N+1 Query, High Time Complexity, Blocking Async Call, Unnecessary I/O, Missing Pagination, Redundant Computation)."
    )
    severity: str = Field(
        description="Vulnerability or bottleneck severity (Low, Medium, High, Critical)."
    )
    confidence: float = Field(
        description="Confidence level of the finding (0.0 to 1.0)."
    )
    summary: str = Field(description="Short summary of the performance issue.")
    reason: str = Field(
        description="Detailed technical explanation of why the code is inefficient."
    )
    impact: str = Field(
        description="Potential scalability or latency impact if unoptimized."
    )
    recommendation: str = Field(description="Actionable optimization advice.")
    code_evidence: str = Field(
        description="Specific evidence from the changed code (file path, snippet, line number)."
    )
    docs_evidence: Optional[str] = Field(
        default=None,
        description="Specific evidence from repository performance guidelines or architecture docs, if applicable.",
    )
    file_path: str = Field(
        description="Primary file path where the performance issue exists."
    )
    line_number: Optional[int] = Field(
        default=None, description="Line number where the bottleneck is located."
    )
    suggested_fix: Optional[str] = Field(
        default=None,
        description="Code snippet demonstrating the optimized fix, if sufficient context exists to safely provide code.",
    )


class PerformanceReviewResult(BaseModel):
    """
    Structured output expected from the LLM when performing a performance review.
    """

    summary: str = Field(
        description="Overall summary of the performance and scalability analysis."
    )
    findings: List[PerformanceFinding] = Field(
        default_factory=list, description="List of validated performance findings."
    )
