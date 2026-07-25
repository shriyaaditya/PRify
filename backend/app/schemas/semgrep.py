from typing import Optional

from pydantic import BaseModel, Field


class SemgrepFinding(BaseModel):
    """
    Normalized static analysis finding produced by Semgrep.
    """

    rule_id: str = Field(
        description="Semgrep rule identifier (e.g. python.lang.security.audit.sqli)"
    )
    file_path: str = Field(
        description="Relative path of the file where the finding occurred"
    )
    line_number: int = Field(description="Line number where the finding was triggered")
    severity: str = Field(description="Semgrep severity level (INFO, WARNING, ERROR)")
    message: str = Field(description="Rule explanation or warning message")
    code_snippet: Optional[str] = Field(
        default=None, description="Triggering code snippet"
    )
