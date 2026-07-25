from typing import List, Optional

from pydantic import BaseModel, Field


class SecurityFinding(BaseModel):
    """
    Structured finding output from the Security Agent.
    Requires evidence from code changes, repository security documentation, and optional Semgrep analysis.
    """

    title: str = Field(description="Concise title for the security finding.")
    category: str = Field(
        description="Security vulnerability category (e.g., SQL Injection, XSS, Hardcoded Secrets, Missing Auth)."
    )
    severity: str = Field(
        description="Vulnerability severity (Low, Medium, High, Critical)."
    )
    confidence: float = Field(
        description="Confidence level of the finding (0.0 to 1.0)."
    )
    summary: str = Field(description="Short summary of the vulnerability.")
    reason: str = Field(
        description="Detailed explanation of the security risk and why the code is vulnerable."
    )
    impact: str = Field(
        description="Potential security impact if exploited (e.g. data breach, RCE, privilege escalation)."
    )
    recommendation: str = Field(
        description="Actionable mitigation or remediation advice."
    )
    code_evidence: str = Field(
        description="Specific evidence from the changed code (file path, snippet, line number)."
    )
    docs_evidence: str = Field(
        description="Specific evidence from repository security guidelines or architecture docs."
    )
    semgrep_evidence: Optional[str] = Field(
        default=None,
        description="Supporting evidence cited from Semgrep static analysis findings, if applicable.",
    )
    file_path: str = Field(
        description="Primary file path where the vulnerability exists."
    )
    line_number: Optional[int] = Field(
        default=None, description="Line number where the vulnerability is located."
    )
    suggested_fix: Optional[str] = Field(
        default=None, description="Code snippet demonstrating the secure fix."
    )


class SecurityReviewResult(BaseModel):
    """
    Structured output expected from the LLM when performing a security review.
    """

    summary: str = Field(description="Overall summary of the security analysis.")
    findings: List[SecurityFinding] = Field(
        default_factory=list, description="List of validated security findings."
    )
