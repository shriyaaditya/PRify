from typing import Optional, List, Dict, Any, Annotated
import operator
from pydantic import BaseModel, Field
from app.parsers.tree_sitter.models import (
    ChangedFile, ParsedFile, Symbol, RepositoryStatistics
)
from app.schemas.semgrep import SemgrepFinding
from app.agents.base.result import AgentResult, AgentExecution

# Normalized Context Models (Pydantic)
class NormalizedRepository(BaseModel):
    id: str
    github_repo_id: str
    name: str
    full_name: str
    owner_id: str
    owner_login: str
    default_branch: str
    installation_id: Optional[str] = None

class NormalizedPullRequest(BaseModel):
    id: str
    github_pr_number: int
    title: str
    description: Optional[str] = None
    state: str
    head_branch: str
    base_branch: str
    author_id: str
    author_login: str
    head_sha: Optional[str] = None

from app.agents.consensus.models import ConsensusReviewResult

# Workflow State Model
class GitHubReviewState(BaseModel):
    """
    State representing the entire execution of a GitHub Pull Request Review workflow.
    """
    # Webhook Data
    event_type: Optional[str] = None
    action: Optional[str] = None
    installation_id: Optional[str] = None
    raw_payload: Dict[str, Any] = Field(default_factory=dict)
    
    # Context ( normalized objects after syncing)
    repository: Optional[NormalizedRepository] = None
    pull_request: Optional[NormalizedPullRequest] = None

    # Code Intelligence Fields
    changed_files: List[ChangedFile] = Field(default_factory=list)
    parsed_files: List[ParsedFile] = Field(default_factory=list)
    symbol_tables: List[Symbol] = Field(default_factory=list)
    semgrep_findings: List[SemgrepFinding] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    repository_statistics: Optional[RepositoryStatistics] = None

    # RAG Context (Phase 5+)
    retrieved_context: List[Any] = Field(default_factory=list)
    indexed_documents: List[str] = Field(default_factory=list)
    repository_summary: Optional[str] = None
    
    # Agent Results & Consensus (Phases 7-12)
    ast_data: Optional[Dict[str, Any]] = None
    agent_results: Annotated[List[AgentResult], operator.add] = Field(default_factory=list)
    execution_metadata: Annotated[List[AgentExecution], operator.add] = Field(default_factory=list)
    consensus_result: Optional[ConsensusReviewResult] = None
    published_review_id: Optional[str] = None
    
    # Execution Tracking
    errors: Annotated[List[str], operator.add] = Field(default_factory=list)
    logs: Annotated[List[str], operator.add] = Field(default_factory=list)
