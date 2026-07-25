from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field

from app.parsers.tree_sitter.models import ChangedFile, ParsedFile, Symbol
from app.schemas.semgrep import SemgrepFinding
from app.workflows.github_review.state import (
    NormalizedPullRequest,
    NormalizedRepository,
)


class ReviewContext(BaseModel):
    """
    Immutable context passed to all review agents.
    Aggregates data from the LangGraph workflow state so agents don't have to query external data sources.
    """

    model_config = ConfigDict(frozen=True)

    repository: NormalizedRepository
    pull_request: NormalizedPullRequest

    # Raw source files changed
    changed_files: List[ChangedFile] = Field(default_factory=list)

    # Tree-sitter parsed ASTs and Statistics
    parsed_files: List[ParsedFile] = Field(default_factory=list)

    # Extracted code symbols (classes, functions, etc.)
    symbol_tables: List[Symbol] = Field(default_factory=list)

    # Semgrep static analysis findings
    semgrep_findings: List[SemgrepFinding] = Field(default_factory=list)

    # Relevant architectural guidelines and documentation from Qdrant RAG
    retrieved_context: List[Dict[str, Any]] = Field(default_factory=list)

    # Workflow tracking (e.g. event type)
    metadata: Dict[str, Any] = Field(default_factory=dict)
