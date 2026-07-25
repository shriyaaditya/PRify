import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from app.agents.base.context import ReviewContext
from app.agents.performance.agent import PerformanceAgent
from app.agents.performance.formatter import PerformanceContextFormatter
from app.agents.performance.models import PerformanceReviewResult
from app.llm.provider import LLMProvider, LLMResponse
from app.parsers.tree_sitter.models import ChangedFile, Symbol
from app.workflows.github_review.state import (
    NormalizedPullRequest,
    NormalizedRepository,
)


@pytest.fixture
def mock_review_context():
    repo = NormalizedRepository(
        id="repo-1",
        github_repo_id="123",
        name="test-repo",
        full_name="org/test-repo",
        owner_id="owner-1",
        owner_login="org",
        default_branch="main",
    )
    pr = NormalizedPullRequest(
        id="pr-1",
        github_pr_number=42,
        title="Add user query and loop processing",
        description="Implements user lookup endpoint",
        state="open",
        head_branch="feature",
        base_branch="main",
        author_id="user-1",
        author_login="dev",
    )
    changed_files = [
        ChangedFile(
            filename="src/utils/helpers.py",
            filepath="src/utils/helpers.py",
            language="python",
            content="def format_name(name):\n    return name.strip().title()",
            patch="def format_name(name):\n    return name.strip().title()",
        ),
        ChangedFile(
            filename="src/db/user_repo.py",
            filepath="src/db/user_repo.py",
            language="python",
            content="def get_all(user_ids):\n    for uid in user_ids:\n        db.execute('SELECT * FROM users WHERE id = %s', uid)",
            patch="def get_all(user_ids):\n    for uid in user_ids:\n        db.execute('SELECT * FROM users WHERE id = %s', uid)",
        ),
    ]
    symbols = [
        Symbol(
            name="format_name",
            kind="function",
            file_path="src/utils/helpers.py",
            start_line=1,
            end_line=2,
        ),
        Symbol(
            name="get_all",
            kind="function",
            file_path="src/db/user_repo.py",
            start_line=1,
            end_line=3,
        ),
    ]
    return ReviewContext(
        repository=repo,
        pull_request=pr,
        changed_files=changed_files,
        symbol_tables=symbols,
        retrieved_context=[
            {
                "page_content": "Avoid N+1 queries by using bulk SQL operations.",
                "metadata": {"source": "docs/perf.md"},
            }
        ],
    )


def test_performance_review_result_validation():
    """Verify PerformanceReviewResult validates properly and handles optional suggested_fix."""
    raw_json = json.dumps(
        {
            "summary": "Found N+1 query issue.",
            "findings": [
                {
                    "title": "N+1 Database Query",
                    "category": "N+1 Query",
                    "severity": "High",
                    "confidence": 0.95,
                    "summary": "Database executed inside loop.",
                    "reason": "Loop dispatches N individual queries.",
                    "impact": "High DB latency.",
                    "recommendation": "Use bulk fetch.",
                    "code_evidence": "user_repo.py: line 2 `db.execute(...)`",
                    "docs_evidence": "docs/perf.md: Avoid N+1 queries.",
                    "file_path": "src/db/user_repo.py",
                    "line_number": 2,
                    "suggested_fix": None,
                }
            ],
        }
    )
    result = PerformanceReviewResult.model_validate_json(raw_json)
    assert result.summary == "Found N+1 query issue."
    assert len(result.findings) == 1
    assert result.findings[0].category == "N+1 Query"
    assert result.findings[0].suggested_fix is None


def test_context_formatter_prioritization_ordering(mock_review_context):
    """Verify PerformanceContextFormatter prioritizes performance-sensitive files first without dropping ordinary files."""
    formatted = PerformanceContextFormatter.format_for_performance(
        mock_review_context, max_files=10
    )

    # Both files must be in the formatted output
    assert "src/db/user_repo.py" in formatted
    assert "src/utils/helpers.py" in formatted

    # Performance-sensitive file (user_repo.py containing 'db' / 'execute') must appear BEFORE ordinary file (helpers.py)
    pos_perf = formatted.find("src/db/user_repo.py")
    pos_ordinary = formatted.find("src/utils/helpers.py")
    assert pos_perf < pos_ordinary, (
        "Performance-relevant file should be ordered before ordinary file"
    )


def test_confidence_filtering(mock_review_context):
    """Verify findings below the min_confidence_threshold (0.7) are filtered out."""
    mock_llm = AsyncMock(spec=LLMProvider)
    llm_payload = json.dumps(
        {
            "summary": "Review complete.",
            "findings": [
                {
                    "title": "High confidence issue",
                    "category": "N+1 Query",
                    "severity": "High",
                    "confidence": 0.9,
                    "summary": "Unbounded query loop.",
                    "reason": "Query inside loop.",
                    "impact": "High latency.",
                    "recommendation": "Batch fetch.",
                    "code_evidence": "user_repo.py:2",
                    "file_path": "src/db/user_repo.py",
                    "line_number": 2,
                },
                {
                    "title": "Low confidence speculation",
                    "category": "High Time Complexity",
                    "severity": "Low",
                    "confidence": 0.4,  # Below 0.7 threshold
                    "summary": "Nested loop on unknown data size.",
                    "reason": "Might be slow if data is large.",
                    "impact": "Uncertain.",
                    "recommendation": "Investigate data bounds.",
                    "code_evidence": "helpers.py:1",
                    "file_path": "src/utils/helpers.py",
                    "line_number": 1,
                },
            ],
        }
    )
    mock_llm.generate.return_value = LLMResponse(
        content=llm_payload, token_usage={"total_tokens": 150}, model_name="gpt-4o"
    )

    agent = PerformanceAgent(llm_provider=mock_llm, min_confidence_threshold=0.7)
    res = asyncio.run(agent.review(mock_review_context))

    assert len(res.findings) == 1
    assert res.findings[0].title == "High confidence issue"


def test_malformed_llm_response_and_retry(mock_review_context):
    """Verify malformed LLM response triggers exactly 1 retry with validation error feedback."""
    mock_llm = AsyncMock(spec=LLMProvider)

    # First attempt: invalid JSON missing required fields
    invalid_response = LLMResponse(
        content='{"summary": "incomplete", "findings": [{"title": "bad"}]}',
        token_usage={"total_tokens": 50},
        model_name="gpt-4o",
    )

    # Second attempt: valid JSON
    valid_payload = json.dumps(
        {
            "summary": "Valid after retry",
            "findings": [
                {
                    "title": "Blocking I/O in Async Function",
                    "category": "Blocking Async Call",
                    "severity": "Medium",
                    "confidence": 0.85,
                    "summary": "Synchronous file open in async endpoint.",
                    "reason": "Blocks event loop.",
                    "impact": "Degraded throughput.",
                    "recommendation": "Use aiofiles.",
                    "code_evidence": "main.py:10",
                    "file_path": "main.py",
                    "line_number": 10,
                }
            ],
        }
    )
    valid_response = LLMResponse(
        content=valid_payload, token_usage={"total_tokens": 120}, model_name="gpt-4o"
    )

    mock_llm.generate.side_effect = [invalid_response, valid_response]

    agent = PerformanceAgent(llm_provider=mock_llm)
    res = asyncio.run(agent.review(mock_review_context))

    assert mock_llm.generate.call_count == 2
    assert res.summary == "Valid after retry"
    assert len(res.findings) == 1
    assert res.findings[0].title == "Blocking I/O in Async Function"


def test_negative_case_unsupported_speculation_unreported(mock_review_context):
    """Verify a suspicious-looking pattern (e.g. bounded loop over small constant) produces 0 findings when LLM yields none."""
    mock_llm = AsyncMock(spec=LLMProvider)
    llm_payload = json.dumps(
        {
            "summary": "Code reviewed. No performance issues found for small constant iteration.",
            "findings": [],
        }
    )
    mock_llm.generate.return_value = LLMResponse(
        content=llm_payload, token_usage={"total_tokens": 100}, model_name="gpt-4o"
    )

    agent = PerformanceAgent(llm_provider=mock_llm)
    res = asyncio.run(agent.review(mock_review_context))

    assert len(res.findings) == 0
    assert "No performance issues found" in res.summary


def test_non_performance_findings_avoided(mock_review_context):
    """Verify findings category is mapped with performance prefix."""
    mock_llm = AsyncMock(spec=LLMProvider)
    llm_payload = json.dumps(
        {
            "summary": "Performance review completed.",
            "findings": [
                {
                    "title": "Redundant Computation in Loop",
                    "category": "Redundant Computation",
                    "severity": "Medium",
                    "confidence": 0.8,
                    "summary": "Computing static value inside loop.",
                    "reason": "Re-evaluates constant expression on every iteration.",
                    "impact": "Unnecessary CPU cycles.",
                    "recommendation": "Hoist calculation outside loop.",
                    "code_evidence": "helpers.py:5",
                    "file_path": "src/utils/helpers.py",
                    "line_number": 5,
                }
            ],
        }
    )
    mock_llm.generate.return_value = LLMResponse(
        content=llm_payload, token_usage={"total_tokens": 110}, model_name="gpt-4o"
    )

    agent = PerformanceAgent(llm_provider=mock_llm)
    res = asyncio.run(agent.review(mock_review_context))

    assert len(res.findings) == 1
    assert res.findings[0].category.startswith("performance:")
