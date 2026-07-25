import pytest
import uuid
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import Response

from app.agents.consensus.models import ConsensusFinding, ConsensusReviewResult
from app.parsers.tree_sitter.models import ChangedFile
from app.github.review_formatter import GitHubReviewFormatter
from app.services.github.review_publisher import ReviewPublisherService
from app.models.enums import ReviewStatus
from app.models.review import Review


@pytest.fixture
def sample_changed_files():
    patch_content = (
        "@@ -10,6 +10,8 @@ def process(data):\n"
        "     start()\n"
        "+    # Valid added line at 11\n"
        "+    val = validate(data)\n"
        "     return val\n"
    )
    return [
        ChangedFile(
            filename="src/app.py",
            filepath="src/app.py",
            language="python",
            content="...",
            patch=patch_content
        )
    ]


@pytest.fixture
def sample_consensus_result():
    return ConsensusReviewResult(
        summary="PR analysis identified 2 findings.",
        findings=[
            ConsensusFinding(
                title="Valid Line Finding",
                category="security:input-validation",
                severity="High",
                confidence=0.9,
                summary="Unsanitized input.",
                reason="Input data passed directly to validate function.",
                impact="Potential injection.",
                recommendation="Sanitize input.",
                file_path="src/app.py",
                line_number=11,  # Valid line in diff patch
                evidence="val = validate(data)",
                source_agents=["SecurityAgent"]
            ),
            ConsensusFinding(
                title="Invalid Line Finding (Unmapped)",
                category="performance:loop-optimization",
                severity="Medium",
                confidence=0.8,
                summary="Inefficient operation.",
                reason="Operation outside diff scope.",
                impact="Minor performance overhead.",
                recommendation="Refactor loop.",
                file_path="src/app.py",
                line_number=999,  # Line 999 does not exist in patch -> must fall back to body
                evidence="loop logic",
                source_agents=["PerformanceAgent"]
            )
        ]
    )


def test_is_line_in_diff_conservative():
    """Verify is_line_in_diff returns True ONLY for valid RIGHT-side added or context lines in diff patch."""
    patch_str = (
        "@@ -1,4 +1,5 @@\n"
        " line1\n"
        "-line2_deleted\n"
        "+line2_added\n"
        " line3\n"
    )

    # Line 1 (context line ' line1', starts at 1) -> True
    assert GitHubReviewFormatter.is_line_in_diff(patch_str, 1) is True

    # Line 2 (added line '+line2_added', new line 2) -> True
    assert GitHubReviewFormatter.is_line_in_diff(patch_str, 2) is True

    # Line 3 (context line ' line3', new line 3) -> True
    assert GitHubReviewFormatter.is_line_in_diff(patch_str, 3) is True

    # Line 99 (outside hunk) -> False
    assert GitHubReviewFormatter.is_line_in_diff(patch_str, 99) is False

    # Empty patch or None line -> False
    assert GitHubReviewFormatter.is_line_in_diff("", 1) is False
    assert GitHubReviewFormatter.is_line_in_diff(patch_str, None) is False


def test_partial_inline_mapping_fallback(sample_consensus_result, sample_changed_files):
    """
    Verify that when a PR has 1 valid inline line and 1 invalid line number:
    - Valid line number (11) is converted to an inline comment.
    - Invalid line number (999) falls back to the review summary body.
    - Both findings are preserved and payload construction succeeds.
    """
    payload = GitHubReviewFormatter.format_github_review_payload(
        consensus_result=sample_consensus_result,
        changed_files=sample_changed_files
    )

    # Exactly 1 inline comment mapped (for line 11)
    assert len(payload["comments"]) == 1
    assert payload["comments"][0]["path"] == "src/app.py"
    assert payload["comments"][0]["line"] == 11

    # Overall review body contains fallback for line 999
    body = payload["body"]
    assert "Invalid Line Finding (Unmapped)" in body
    assert "src/app.py:999" in body
    assert "Critical:" in body or "High:" in body


def test_zero_findings_clean_review_summary():
    """Verify zero findings produces a clean review summary without fake findings or errors."""
    empty_result = ConsensusReviewResult(
        summary="Clean review.",
        findings=[]
    )
    payload = GitHubReviewFormatter.format_github_review_payload(
        consensus_result=empty_result,
        changed_files=[]
    )

    assert len(payload["comments"]) == 0
    assert "No actionable issues were identified" in payload["body"]


def test_github_api_publishing_success(sample_consensus_result, sample_changed_files):
    """Verify successful review publishing via GitHub API mock."""
    publisher = ReviewPublisherService()

    mock_resp = Response(
        status_code=200,
        json={"id": 987654321, "state": "COMMENTED"}
    )

    with patch("app.github.client.GitHubClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp

        res = asyncio.run(publisher.publish_review(
            installation_id="12345",
            repo_owner="test-owner",
            repo_name="test-repo",
            pr_number=42,
            pull_request_id=str(uuid.uuid4()),
            head_sha="abc123def456",
            consensus_result=sample_consensus_result,
            changed_files=sample_changed_files
        ))

        assert res["published"] is True
        assert res["github_review_id"] == "987654321"
        assert res["inline_comments_count"] == 1
        assert mock_post.call_count == 1


def test_github_api_failure_handling(sample_consensus_result, sample_changed_files):
    """Verify HTTP error from GitHub API is handled gracefully without throwing unhandled exceptions."""
    publisher = ReviewPublisherService()

    mock_resp = Response(
        status_code=403,
        json={"message": "Resource not accessible by integration"}
    )

    with patch("app.github.client.GitHubClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp

        res = asyncio.run(publisher.publish_review(
            installation_id="12345",
            repo_owner="test-owner",
            repo_name="test-repo",
            pr_number=42,
            pull_request_id=str(uuid.uuid4()),
            head_sha="abc123def456",
            consensus_result=sample_consensus_result,
            changed_files=sample_changed_files
        ))

        assert res["published"] is False
        assert "GitHub API review creation failed with HTTP 403" in res["error"]


def test_postgresql_idempotency_prevents_duplicate_publishing(sample_consensus_result, sample_changed_files):
    """Verify PostgreSQL-based idempotency check skips publishing if a review for (pull_request_id, head_sha) is already COMPLETED."""
    publisher = ReviewPublisherService()
    mock_db = AsyncMock()

    pr_uuid = uuid.uuid4()
    commit_sha = "sha_already_published"

    # Mock existing completed review in PostgreSQL
    existing_review = Review(
        id=uuid.uuid4(),
        pull_request_id=pr_uuid,
        commit_sha=commit_sha,
        status=ReviewStatus.COMPLETED,
        github_review_id="review_112233"
    )

    with patch("app.services.review.review_service.get_by_pull_request_and_commit_sha", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = existing_review

        with patch("app.github.client.GitHubClient.post", new_callable=AsyncMock) as mock_post:
            res = asyncio.run(publisher.publish_review(
                installation_id="12345",
                repo_owner="test-owner",
                repo_name="test-repo",
                pr_number=42,
                pull_request_id=str(pr_uuid),
                head_sha=commit_sha,
                consensus_result=sample_consensus_result,
                changed_files=sample_changed_files,
                db=mock_db
            ))

            assert res["published"] is False
            assert res["skipped"] is True
            assert res["github_review_id"] == "review_112233"
            # Ensure no HTTP POST call was made to GitHub API
            assert mock_post.call_count == 0
