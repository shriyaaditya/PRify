from typing import List, Optional
from pydantic import BaseModel, Field

class ArchitectureFinding(BaseModel):
    """
    Structured finding output from the Architecture Agent.
    Requires evidence from both code changes and retrieved documentation.
    """
    title: str = Field(description="A concise title for the architectural finding.")
    severity: str = Field(description="Severity of the violation (Low, Medium, High, Critical).")
    confidence: float = Field(description="Confidence level of the finding (0.0 to 1.0).")
    reason: str = Field(description="Detailed explanation of the architectural violation.")
    impact: str = Field(description="The potential impact of this violation on the system.")
    recommendation: str = Field(description="Actionable recommendation to fix the violation.")
    code_evidence: str = Field(description="Specific evidence from the changed code (e.g., file paths, class names, line numbers if available).")
    docs_evidence: str = Field(description="Specific evidence cited from the retrieved repository documentation (e.g., Qdrant snippets or architecture docs).")
    file_path: str = Field(description="Primary file path where the violation occurs.")
    line_number: Optional[int] = Field(default=None, description="Line number, if applicable.")
    suggested_fix: Optional[str] = Field(default=None, description="Code snippet demonstrating the suggested fix.")

class ArchitectureReviewResult(BaseModel):
    """
    The structured output expected from the LLM when reviewing architecture.
    """
    summary: str = Field(description="Overall summary of the architecture review.")
    findings: List[ArchitectureFinding] = Field(description="List of architectural findings.")
