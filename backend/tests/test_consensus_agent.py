import pytest
import json
import asyncio
from unittest.mock import AsyncMock

from app.agents.consensus.models import ConsensusFinding, ConsensusReviewResult
from app.agents.consensus.formatter import ConsensusContextFormatter
from app.agents.consensus.agent import ConsensusAgent
from app.agents.base.context import ReviewContext
from app.agents.base.result import AgentResult, Finding
from app.workflows.github_review.state import NormalizedRepository, NormalizedPullRequest
from app.parsers.tree_sitter.models import ChangedFile
from app.llm.provider import LLMProvider, LLMResponse


@pytest.fixture
def mock_review_context():
    repo = NormalizedRepository(
        id="repo-1",
        github_repo_id="123",
        name="test-repo",
        full_name="org/test-repo",
        owner_id="owner-1",
        owner_login="org",
        default_branch="main"
    )
    pr = NormalizedPullRequest(
        id="pr-1",
        github_pr_number=42,
        title="Add user query and SQL execution",
        description="Implements DB queries and API routes",
        state="open",
        head_branch="feature",
        base_branch="main",
        author_id="user-1",
        author_login="dev"
    )
    changed_files = [
        ChangedFile(
            filename="src/db/user_repo.py",
            filepath="src/db/user_repo.py",
            language="python",
            content="def get_users(ids):\n    for uid in ids:\n        db.execute('SELECT * FROM users WHERE id = %s' + uid)",
            patch="def get_users(ids):\n    for uid in ids:\n        db.execute('SELECT * FROM users WHERE id = %s' + uid)"
        ),
    ]
    return ReviewContext(
        repository=repo,
        pull_request=pr,
        changed_files=changed_files,
        symbol_tables=[],
        retrieved_context=[]
    )


def test_consensus_review_result_validation():
    """Verify ConsensusReviewResult validates properly with source_agents."""
    raw_json = json.dumps({
        "summary": "Consolidated findings across Architecture and Performance agents.",
        "findings": [
            {
                "title": "N+1 Database Query in Controller Loop",
                "category": "performance:n+1-query",
                "severity": "High",
                "confidence": 0.95,
                "summary": "Database lookup executed inside loop.",
                "reason": "Repeated synchronous SQL executions.",
                "impact": "High DB latency inflation.",
                "recommendation": "Batch fetch user records.",
                "file_path": "src/db/user_repo.py",
                "line_number": 2,
                "evidence": "user_repo.py:2 db.execute",
                "source_agents": ["ArchitectureAgent", "PerformanceAgent"],
                "suggested_fix": None
            }
        ]
    })
    result = ConsensusReviewResult.model_validate_json(raw_json)
    assert result.summary.startswith("Consolidated findings")
    assert len(result.findings) == 1
    assert result.findings[0].source_agents == ["ArchitectureAgent", "PerformanceAgent"]
    assert result.findings[0].severity == "High"


def test_empty_specialist_results_produce_empty_consensus(mock_review_context):
    """Verify empty specialist results immediately produce an empty consensus result without LLM calls."""
    mock_llm = AsyncMock(spec=LLMProvider)
    agent = ConsensusAgent(llm_provider=mock_llm)

    empty_agent_results = [
        AgentResult(agent_name="ArchitectureAgent", summary="No findings", findings=[]),
        AgentResult(agent_name="SecurityAgent", summary="No findings", findings=[])
    ]

    res = asyncio.run(agent.consolidate(empty_agent_results, mock_review_context))

    assert len(res.findings) == 0
    assert "No issues were flagged" in res.summary
    assert mock_llm.generate.call_count == 0


def test_malformed_llm_response_and_retry(mock_review_context):
    """Verify malformed LLM response triggers exactly 1 retry fallback."""
    mock_llm = AsyncMock(spec=LLMProvider)

    # Attempt 1: invalid JSON missing source_agents
    invalid_response = LLMResponse(
        content='{"summary": "incomplete", "findings": [{"title": "bad"}]}',
        token_usage={"total_tokens": 50},
        model_name="gpt-4o"
    )

    # Attempt 2: valid JSON
    valid_payload = json.dumps({
        "summary": "Valid after retry",
        "findings": [
            {
                "title": "SQL Injection Vulnerability",
                "category": "security:sql-injection",
                "severity": "Critical",
                "confidence": 0.95,
                "summary": "String concatenation in raw SQL execution.",
                "reason": "Unsanitized input.",
                "impact": "Arbitrary query execution.",
                "recommendation": "Use parameterized query.",
                "file_path": "src/db/user_repo.py",
                "line_number": 3,
                "evidence": "user_repo.py:3 db.execute(... + uid)",
                "source_agents": ["SecurityAgent"]
            }
        ]
    })
    valid_response = LLMResponse(
        content=valid_payload,
        token_usage={"total_tokens": 120},
        model_name="gpt-4o"
    )

    mock_llm.generate.side_effect = [invalid_response, valid_response]

    agent_results = [
        AgentResult(
            agent_name="SecurityAgent",
            summary="Found SQL injection",
            findings=[
                Finding(
                    title="SQL Injection",
                    description="Unsanitized string format",
                    severity="critical",
                    confidence=0.95,
                    recommendation="Use params",
                    file_path="src/db/user_repo.py",
                    line_number=3,
                    category="security:sql-injection",
                    evidence="db.execute(... + uid)"
                )
            ]
        )
    ]

    agent = ConsensusAgent(llm_provider=mock_llm)
    res = asyncio.run(agent.consolidate(agent_results, mock_review_context))

    assert mock_llm.generate.call_count == 2
    assert res.summary == "Valid after retry"
    assert len(res.findings) == 1
    assert res.findings[0].source_agents == ["SecurityAgent"]


def test_duplicate_findings_consolidated_and_source_agents_preserved(mock_review_context):
    """Verify duplicate findings from ArchitectureAgent and PerformanceAgent are consolidated into one."""
    mock_llm = AsyncMock(spec=LLMProvider)

    llm_payload = json.dumps({
        "summary": "Merged duplicate findings on user lookup query.",
        "findings": [
            {
                "title": "N+1 Database Query in Controller Loop",
                "category": "performance:n+1-query",
                "severity": "High",
                "confidence": 0.92,
                "summary": "Database lookup executed inside loop.",
                "reason": "Repeated synchronous SQL executions inside controller loop.",
                "impact": "High DB latency inflation.",
                "recommendation": "Batch fetch user records.",
                "file_path": "src/db/user_repo.py",
                "line_number": 2,
                "evidence": "user_repo.py:2 db.execute",
                "source_agents": ["ArchitectureAgent", "PerformanceAgent"]
            }
        ]
    })
    mock_llm.generate.return_value = LLMResponse(
        content=llm_payload,
        token_usage={"total_tokens": 160},
        model_name="gpt-4o"
    )

    agent_results = [
        AgentResult(
            agent_name="ArchitectureAgent",
            summary="Direct DB access in loop",
            findings=[
                Finding(
                    title="DB Access in Controller Loop",
                    description="Controller loops over query",
                    severity="medium",
                    confidence=0.8,
                    recommendation="Use repository layer",
                    file_path="src/db/user_repo.py",
                    line_number=2,
                    category="architecture:layering",
                    evidence="db.execute inside loop"
                )
            ]
        ),
        AgentResult(
            agent_name="PerformanceAgent",
            summary="N+1 query",
            findings=[
                Finding(
                    title="N+1 Query in Loop",
                    description="Loop dispatches N queries",
                    severity="high",
                    confidence=0.92,
                    recommendation="Batch fetch with IN clause",
                    file_path="src/db/user_repo.py",
                    line_number=2,
                    category="performance:n+1-query",
                    evidence="db.execute inside loop"
                )
            ]
        )
    ]

    agent = ConsensusAgent(llm_provider=mock_llm)
    res = asyncio.run(agent.consolidate(agent_results, mock_review_context))

    assert len(res.findings) == 1
    assert set(res.findings[0].source_agents) == {"ArchitectureAgent", "PerformanceAgent"}
    assert res.findings[0].severity == "High"


def test_same_location_different_concerns_remain_separate(mock_review_context):
    """Verify distinct concerns on the same line (SQL Injection vs N+1 Query) remain separate."""
    mock_llm = AsyncMock(spec=LLMProvider)

    llm_payload = json.dumps({
        "summary": "Evaluated findings on user_repo.py line 3.",
        "findings": [
            {
                "title": "SQL Injection Vulnerability",
                "category": "security:sql-injection",
                "severity": "Critical",
                "confidence": 0.96,
                "summary": "Concatenating user input directly into SQL statement.",
                "reason": "String format allows attacker SQL injection.",
                "impact": "Unsanitized database access.",
                "recommendation": "Use parameterized SQL placeholders.",
                "file_path": "src/db/user_repo.py",
                "line_number": 3,
                "evidence": "db.execute('... WHERE id = ' + uid)",
                "source_agents": ["SecurityAgent"]
            },
            {
                "title": "N+1 Database Query in Loop",
                "category": "performance:n+1-query",
                "severity": "High",
                "confidence": 0.90,
                "summary": "Executing query inside loop for every ID.",
                "reason": "Individual query roundtrips inside loop.",
                "impact": "High DB latency.",
                "recommendation": "Use bulk query IN clause.",
                "file_path": "src/db/user_repo.py",
                "line_number": 3,
                "evidence": "for uid in ids: db.execute(...)",
                "source_agents": ["PerformanceAgent"]
            }
        ]
    })
    mock_llm.generate.return_value = LLMResponse(
        content=llm_payload,
        token_usage={"total_tokens": 200},
        model_name="gpt-4o"
    )

    agent_results = [
        AgentResult(
            agent_name="SecurityAgent",
            summary="Found SQL injection",
            findings=[
                Finding(
                    title="SQL Injection",
                    description="Concatenation in query",
                    severity="critical",
                    confidence=0.96,
                    recommendation="Parameterize query",
                    file_path="src/db/user_repo.py",
                    line_number=3,
                    category="security:sql-injection",
                    evidence="db.execute + uid"
                )
            ]
        ),
        AgentResult(
            agent_name="PerformanceAgent",
            summary="Found N+1 query",
            findings=[
                Finding(
                    title="N+1 Query",
                    description="Query inside loop",
                    severity="high",
                    confidence=0.90,
                    recommendation="Batch query",
                    file_path="src/db/user_repo.py",
                    line_number=3,
                    category="performance:n+1-query",
                    evidence="for uid in ids: db.execute"
                )
            ]
        )
    ]

    agent = ConsensusAgent(llm_provider=mock_llm)
    res = asyncio.run(agent.consolidate(agent_results, mock_review_context))

    assert len(res.findings) == 2
    categories = [f.category for f in res.findings]
    assert "security:sql-injection" in categories
    assert "performance:n+1-query" in categories


def test_unsupported_finding_suppression(mock_review_context):
    """Verify weak or unsupported specialist findings are suppressed."""
    mock_llm = AsyncMock(spec=LLMProvider)

    llm_payload = json.dumps({
        "summary": "Evaluated testing finding. Suppressed weak finding regarding logger initialization.",
        "findings": []
    })
    mock_llm.generate.return_value = LLMResponse(
        content=llm_payload,
        token_usage={"total_tokens": 90},
        model_name="gpt-4o"
    )

    agent_results = [
        AgentResult(
            agent_name="TestingAgent",
            summary="Weak finding",
            findings=[
                Finding(
                    title="Missing Unit Test for Logger",
                    description="Standard logger declaration lacks unit test",
                    severity="high",
                    confidence=0.98,
                    recommendation="Add logger unit test",
                    file_path="src/utils/logger.py",
                    line_number=1,
                    category="testing:missing-unit-tests",
                    evidence="logger = logging.getLogger(__name__)"
                )
            ]
        )
    ]

    agent = ConsensusAgent(llm_provider=mock_llm)
    res = asyncio.run(agent.consolidate(agent_results, mock_review_context))

    assert len(res.findings) == 0
    assert "Suppressed weak finding" in res.summary
