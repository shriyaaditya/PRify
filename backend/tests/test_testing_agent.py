import pytest
import json
import asyncio
from unittest.mock import AsyncMock
from pydantic import ValidationError

from app.agents.testing.models import TestingFinding, TestingReviewResult
from app.agents.testing.formatter import TestingContextFormatter
from app.agents.testing.agent import TestingAgent
from app.agents.base.context import ReviewContext
from app.workflows.github_review.state import NormalizedRepository, NormalizedPullRequest
from app.parsers.tree_sitter.models import ChangedFile, Symbol
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
        title="Add email validation and user creation",
        description="Implements email check and user endpoint",
        state="open",
        head_branch="feature",
        base_branch="main",
        author_id="user-1",
        author_login="dev"
    )
    changed_files = [
        ChangedFile(
            filename="app/services/user_service.py",
            filepath="app/services/user_service.py",
            language="python",
            content="def create_user(email):\n    if not is_valid(email):\n        raise ValueError('Invalid email')\n    return db.save(email)",
            patch="def create_user(email):\n    if not is_valid(email):\n        raise ValueError('Invalid email')\n    return db.save(email)"
        ),
        ChangedFile(
            filename="tests/test_user_service.py",
            filepath="tests/test_user_service.py",
            language="python",
            content="def test_create_user_happy_path():\n    assert create_user('a@b.com')",
            patch="def test_create_user_happy_path():\n    assert create_user('a@b.com')"
        ),
    ]
    symbols = [
        Symbol(name="create_user", kind="function", file_path="app/services/user_service.py", start_line=1, end_line=4),
        Symbol(name="test_create_user_happy_path", kind="function", file_path="tests/test_user_service.py", start_line=1, end_line=2),
    ]
    return ReviewContext(
        repository=repo,
        pull_request=pr,
        changed_files=changed_files,
        symbol_tables=symbols,
        retrieved_context=[{
            "content": "def test_user_service_existing():\n    pass",
            "source": "tests/test_user_service.py",
            "document_type": "TEST_FILE"
        }]
    )


def test_testing_review_result_validation():
    """Verify TestingReviewResult validates properly and handles optional suggested_test."""
    raw_json = json.dumps({
        "summary": "Found missing unit test for invalid input.",
        "findings": [
            {
                "title": "Missing Unit Test for Email Validation",
                "category": "Missing Unit Tests",
                "severity": "High",
                "confidence": 0.9,
                "summary": "Validation branch untested.",
                "reason": "Invalid email string branch has no test.",
                "impact": "Uncaught regressions in validation.",
                "recommendation": "Add unit test verifying ValueError is raised.",
                "code_evidence": "user_service.py: line 2 `raise ValueError`",
                "test_evidence": "test_user_service.py: happy path only",
                "docs_evidence": "docs/testing.md: test validation logic",
                "file_path": "app/services/user_service.py",
                "line_number": 2,
                "suggested_test": "test_create_user_invalid_email_raises_value_error"
            }
        ]
    })
    result = TestingReviewResult.model_validate_json(raw_json)
    assert result.summary == "Found missing unit test for invalid input."
    assert len(result.findings) == 1
    assert result.findings[0].category == "Missing Unit Tests"
    assert result.findings[0].suggested_test == "test_create_user_invalid_email_raises_value_error"


def test_context_formatter_correlation_and_ordering(mock_review_context):
    """Verify TestingContextFormatter orders files and presents retrieved TEST_FILE context properly."""
    formatted = TestingContextFormatter.format_for_testing(mock_review_context, max_files=10)

    # All source components present
    assert "[Source: GitHub PR Metadata]" in formatted
    assert "[Source: GitHub Diff]" in formatted
    assert "[Source: Tree-sitter AST]" in formatted
    assert "[Source: Qdrant Vector DB] Existing Repository Test Files & Guidelines" in formatted

    # Both production and test changed files must be present
    assert "app/services/user_service.py" in formatted
    assert "tests/test_user_service.py" in formatted

    # Test file signals correctly identified
    assert TestingContextFormatter.is_test_file("tests/test_user_service.py")
    assert TestingContextFormatter.is_test_file("src/foo.test.ts")
    assert TestingContextFormatter.is_test_file("src/__tests__/foo.js")
    assert not TestingContextFormatter.is_test_file("app/services/user_service.py")


def test_confidence_filtering(mock_review_context):
    """Verify findings below min_confidence_threshold (0.7) are filtered out."""
    mock_llm = AsyncMock(spec=LLMProvider)
    llm_payload = json.dumps({
        "summary": "Review complete.",
        "findings": [
            {
                "title": "High confidence missing test finding",
                "category": "Missing Unit Tests",
                "severity": "High",
                "confidence": 0.9,
                "summary": "Validation branch lacks test.",
                "reason": "No test exercises error path.",
                "impact": "High risk of regression.",
                "recommendation": "Add error path unit test.",
                "code_evidence": "user_service.py:2",
                "file_path": "app/services/user_service.py",
                "line_number": 2
            },
            {
                "title": "Low confidence speculative finding",
                "category": "Untested Edge Case",
                "severity": "Low",
                "confidence": 0.4,  # Below 0.7 threshold
                "summary": "Might need edge case test.",
                "reason": "Unsure if existing test covers this.",
                "impact": "Uncertain.",
                "recommendation": "Investigate.",
                "code_evidence": "user_service.py:1",
                "file_path": "app/services/user_service.py",
                "line_number": 1
            }
        ]
    })
    mock_llm.generate.return_value = LLMResponse(
        content=llm_payload,
        token_usage={"total_tokens": 150},
        model_name="gpt-4o"
    )

    agent = TestingAgent(llm_provider=mock_llm, min_confidence_threshold=0.7)
    res = asyncio.run(agent.review(mock_review_context))

    assert len(res.findings) == 1
    assert res.findings[0].title == "High confidence missing test finding"


def test_malformed_llm_response_and_retry(mock_review_context):
    """Verify malformed LLM response triggers exactly 1 retry with validation error feedback."""
    mock_llm = AsyncMock(spec=LLMProvider)

    # First attempt: invalid JSON missing required fields
    invalid_response = LLMResponse(
        content='{"summary": "incomplete", "findings": [{"title": "bad"}]}',
        token_usage={"total_tokens": 50},
        model_name="gpt-4o"
    )

    # Second attempt: valid JSON
    valid_payload = json.dumps({
        "summary": "Valid after retry",
        "findings": [
            {
                "title": "Untested Error Path in Validation",
                "category": "Untested Error Path",
                "severity": "Medium",
                "confidence": 0.85,
                "summary": "Error branch untested.",
                "reason": "Exception path has no test.",
                "impact": "Unverified error handling.",
                "recommendation": "Add exception test.",
                "code_evidence": "user_service.py:3",
                "file_path": "app/services/user_service.py",
                "line_number": 3
            }
        ]
    })
    valid_response = LLMResponse(
        content=valid_payload,
        token_usage={"total_tokens": 120},
        model_name="gpt-4o"
    )

    mock_llm.generate.side_effect = [invalid_response, valid_response]

    agent = TestingAgent(llm_provider=mock_llm)
    res = asyncio.run(agent.review(mock_review_context))

    assert mock_llm.generate.call_count == 2
    assert res.summary == "Valid after retry"
    assert len(res.findings) == 1
    assert res.findings[0].title == "Untested Error Path in Validation"


def test_positive_case_missing_test_for_new_validation_logic(mock_review_context):
    """Verify positive case where new validation logic lacks test coverage."""
    mock_llm = AsyncMock(spec=LLMProvider)
    llm_payload = json.dumps({
        "summary": "PR adds email validation logic but lacks tests for invalid email strings.",
        "findings": [
            {
                "title": "Missing Test for Invalid Email Format",
                "category": "Missing Unit Tests",
                "severity": "High",
                "confidence": 0.95,
                "summary": "No unit test covers the invalid email format branch in user_service.py.",
                "reason": "Function raises ValueError on bad email, but existing tests only test valid emails.",
                "impact": "Validation regression would pass CI undetected.",
                "recommendation": "Add test_create_user_invalid_email in test_user_service.py.",
                "code_evidence": "app/services/user_service.py: line 2 `if not is_valid(email): raise ValueError`",
                "test_evidence": "tests/test_user_service.py: test_create_user_happy_path only",
                "file_path": "app/services/user_service.py",
                "line_number": 2,
                "suggested_test": "def test_create_user_invalid_email(): with pytest.raises(ValueError): create_user('bad_email')"
            }
        ]
    })
    mock_llm.generate.return_value = LLMResponse(
        content=llm_payload,
        token_usage={"total_tokens": 180},
        model_name="gpt-4o"
    )

    agent = TestingAgent(llm_provider=mock_llm)
    res = asyncio.run(agent.review(mock_review_context))

    assert len(res.findings) == 1
    assert res.findings[0].category.startswith("testing:")
    assert res.findings[0].title == "Missing Test for Invalid Email Format"


def test_negative_case_internal_refactor_with_existing_test_coverage(mock_review_context):
    """Verify internal refactoring with existing test coverage yields 0 findings."""
    mock_llm = AsyncMock(spec=LLMProvider)
    llm_payload = json.dumps({
        "summary": "Internal refactor of user service. Existing test suite covers the behavior.",
        "findings": []
    })
    mock_llm.generate.return_value = LLMResponse(
        content=llm_payload,
        token_usage={"total_tokens": 90},
        model_name="gpt-4o"
    )

    agent = TestingAgent(llm_provider=mock_llm)
    res = asyncio.run(agent.review(mock_review_context))

    assert len(res.findings) == 0
    assert "Existing test suite covers" in res.summary


def test_existing_test_awareness_no_pr_test_diff(mock_review_context):
    """Verify PR modifying production code without test diff yields 0 findings if retrieved context has test files covering it."""
    context = ReviewContext(
        repository=mock_review_context.repository,
        pull_request=mock_review_context.pull_request,
        changed_files=[
            ChangedFile(
                filename="app/services/payment_service.py",
                filepath="app/services/payment_service.py",
                language="python",
                content="def process_payment(amount):\n    if amount <= 0:\n        raise ValueError('Invalid amount')\n    return True",
                patch="def process_payment(amount):\n    if amount <= 0:\n        raise ValueError('Invalid amount')\n    return True"
            )
        ],
        symbol_tables=[],
        retrieved_context=[
            {
                "content": "def test_process_payment_negative_amount():\n    with pytest.raises(ValueError):\n        process_payment(-1)",
                "source": "tests/test_payment_service.py",
                "document_type": "TEST_FILE"
            }
        ]
    )

    mock_llm = AsyncMock(spec=LLMProvider)
    llm_payload = json.dumps({
        "summary": "PR updates payment service logic. Existing test in tests/test_payment_service.py retrieved from vector DB already covers negative amounts.",
        "findings": []
    })
    mock_llm.generate.return_value = LLMResponse(
        content=llm_payload,
        token_usage={"total_tokens": 110},
        model_name="gpt-4o"
    )

    agent = TestingAgent(llm_provider=mock_llm)
    res = asyncio.run(agent.review(context))

    assert len(res.findings) == 0
    assert "retrieved from vector DB" in res.summary


def test_insufficient_context_case(mock_review_context):
    """Verify insufficient context produces 0 findings."""
    mock_llm = AsyncMock(spec=LLMProvider)
    llm_payload = json.dumps({
        "summary": "Insufficient context to determine test coverage for modified internal utility method.",
        "findings": []
    })
    mock_llm.generate.return_value = LLMResponse(
        content=llm_payload,
        token_usage={"total_tokens": 80},
        model_name="gpt-4o"
    )

    agent = TestingAgent(llm_provider=mock_llm)
    res = asyncio.run(agent.review(mock_review_context))

    assert len(res.findings) == 0
    assert "Insufficient context" in res.summary
