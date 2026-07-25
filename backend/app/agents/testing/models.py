from typing import List, Optional

from pydantic import BaseModel, Field


class TestingFinding(BaseModel):
    """
    Structured finding output from the Testing Review Agent.
    Requires evidence from code changes and optional test or repository testing documentation.
    """

    __test__ = False
    title: str = Field(description="Concise title of the testing finding.")
    category: str = Field(
        description="Category (Missing Unit Tests, Untested Edge Case, Untested Error Path, Public API Missing Tests, Insufficient Regression Test)."
    )
    severity: str = Field(description="Severity level (Low, Medium, High, Critical).")
    confidence: float = Field(description="Confidence score (0.0 to 1.0).")
    summary: str = Field(description="Short summary of the testing gap.")
    reason: str = Field(
        description="Technical explanation of why testing is insufficient for the changed behavior."
    )
    impact: str = Field(
        description="Potential risk of unverified behavior or undetected regression."
    )
    recommendation: str = Field(
        description="Guidance on how to properly test the change."
    )
    code_evidence: str = Field(
        description="Snippet/line evidence of changed production code."
    )
    test_evidence: Optional[str] = Field(
        default=None,
        description="Optional snippet/line evidence from changed or existing test code.",
    )
    docs_evidence: Optional[str] = Field(
        default=None, description="Optional repository testing guidelines reference."
    )
    file_path: str = Field(description="Relative file path.")
    line_number: Optional[int] = Field(
        default=None, description="Optional line number."
    )
    suggested_test: Optional[str] = Field(
        default=None,
        description="Optional description of test scenarios/cases that should be added.",
    )


class TestingReviewResult(BaseModel):
    """
    Structured output expected from the LLM when performing a testing review.
    """

    __test__ = False
    summary: str = Field(description="High-level summary of test coverage analysis.")
    findings: List[TestingFinding] = Field(
        default_factory=list, description="List of validated testing findings."
    )
