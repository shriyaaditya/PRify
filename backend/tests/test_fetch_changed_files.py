from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.runnables import RunnableConfig

from app.workflows.github_review.nodes.fetch_changed_files import fetch_changed_files
from app.workflows.github_review.state import (
    GitHubReviewState,
    NormalizedPullRequest,
    NormalizedRepository,
)


@pytest.mark.anyio
async def test_fetch_changed_files_top_level_file():
    """Test fetching a top-level file (e.g. main.py)."""
    state = GitHubReviewState(
        installation_id="12345",
        repository=NormalizedRepository(
            id="11111111-1111-1111-1111-111111111111",
            github_repo_id="999",
            name="test-repo",
            full_name="owner/test-repo",
            owner_id="222",
            owner_login="owner",
            default_branch="main",
        ),
        pull_request=NormalizedPullRequest(
            id="33333333-3333-3333-3333-333333333333",
            github_pr_number=42,
            title="PR 42",
            state="open",
            head_branch="feature",
            base_branch="main",
            author_id="444",
            author_login="author",
            head_sha="sha123",
        ),
        raw_payload={"pull_request": {"head": {"sha": "sha123"}}},
    )
    config = RunnableConfig(configurable={})

    files_response = MagicMock()
    files_response.status_code = 200
    files_response.json.return_value = [
        {"filename": "main.py", "status": "modified", "patch": "@@ -1 +1 @@"}
    ]

    content_response = MagicMock()
    content_response.status_code = 200
    content_response.text = "print('hello')"

    with patch(
        "app.workflows.github_review.nodes.fetch_changed_files.GitHubClient"
    ) as mock_gh_client_cls:
        mock_client = AsyncMock()
        mock_gh_client_cls.return_value = mock_client
        mock_client.get.side_effect = [files_response, content_response]

        result = await fetch_changed_files(state, config)

        # Verify endpoints called
        assert mock_client.get.call_count == 2

        # 1. files endpoint call
        files_call = mock_client.get.call_args_list[0]
        assert files_call[0][0] == "/repos/owner/test-repo/pulls/42/files"

        # 2. content endpoint call - verify exact full relative path passed
        content_call = mock_client.get.call_args_list[1]
        assert content_call[0][0] == "/repos/owner/test-repo/contents/main.py"
        assert content_call[1]["params"] == {"ref": "sha123"}

        # Verify ChangedFile object
        assert len(result["changed_files"]) == 1
        cf = result["changed_files"][0]
        assert cf.filename == "main.py"
        assert cf.filepath == "main.py"


@pytest.mark.anyio
async def test_fetch_changed_files_single_nested_directory():
    """Test fetching a single nested file (e.g. app/main.py)."""
    state = GitHubReviewState(
        installation_id="12345",
        repository=NormalizedRepository(
            id="11111111-1111-1111-1111-111111111111",
            github_repo_id="999",
            name="test-repo",
            full_name="owner/test-repo",
            owner_id="222",
            owner_login="owner",
            default_branch="main",
        ),
        pull_request=NormalizedPullRequest(
            id="33333333-3333-3333-3333-333333333333",
            github_pr_number=42,
            title="PR 42",
            state="open",
            head_branch="feature",
            base_branch="main",
            author_id="444",
            author_login="author",
            head_sha="sha123",
        ),
        raw_payload={"pull_request": {"head": {"sha": "sha123"}}},
    )
    config = RunnableConfig(configurable={})

    files_response = MagicMock()
    files_response.status_code = 200
    files_response.json.return_value = [
        {"filename": "app/main.py", "status": "modified", "patch": "@@ -1 +1 @@"}
    ]

    content_response = MagicMock()
    content_response.status_code = 200
    content_response.text = "import sys"

    with patch(
        "app.workflows.github_review.nodes.fetch_changed_files.GitHubClient"
    ) as mock_gh_client_cls:
        mock_client = AsyncMock()
        mock_gh_client_cls.return_value = mock_client
        mock_client.get.side_effect = [files_response, content_response]

        result = await fetch_changed_files(state, config)

        assert mock_client.get.call_count == 2
        content_call = mock_client.get.call_args_list[1]

        # Verify exact path passed to GitHub Contents API
        assert content_call[0][0] == "/repos/owner/test-repo/contents/app/main.py"

        assert len(result["changed_files"]) == 1
        cf = result["changed_files"][0]
        assert cf.filename == "app/main.py"
        assert cf.filepath == "app/main.py"


@pytest.mark.anyio
async def test_fetch_changed_files_deeply_nested_file():
    """Test fetching a deeply nested file (e.g. app/services/auth/service.py)."""
    state = GitHubReviewState(
        installation_id="12345",
        repository=NormalizedRepository(
            id="11111111-1111-1111-1111-111111111111",
            github_repo_id="999",
            name="test-repo",
            full_name="owner/test-repo",
            owner_id="222",
            owner_login="owner",
            default_branch="main",
        ),
        pull_request=NormalizedPullRequest(
            id="33333333-3333-3333-3333-333333333333",
            github_pr_number=42,
            title="PR 42",
            state="open",
            head_branch="feature",
            base_branch="main",
            author_id="444",
            author_login="author",
            head_sha="sha123",
        ),
        raw_payload={"pull_request": {"head": {"sha": "sha123"}}},
    )
    config = RunnableConfig(configurable={})

    files_response = MagicMock()
    files_response.status_code = 200
    files_response.json.return_value = [
        {
            "filename": "app/services/auth/service.py",
            "status": "added",
            "patch": "@@ -0,0 +1 @@",
        }
    ]

    content_response = MagicMock()
    content_response.status_code = 200
    content_response.text = "class AuthService: pass"

    with patch(
        "app.workflows.github_review.nodes.fetch_changed_files.GitHubClient"
    ) as mock_gh_client_cls:
        mock_client = AsyncMock()
        mock_gh_client_cls.return_value = mock_client
        mock_client.get.side_effect = [files_response, content_response]

        result = await fetch_changed_files(state, config)

        assert mock_client.get.call_count == 2
        content_call = mock_client.get.call_args_list[1]

        # Verify exact path passed to GitHub Contents API
        assert (
            content_call[0][0]
            == "/repos/owner/test-repo/contents/app/services/auth/service.py"
        )

        assert len(result["changed_files"]) == 1
        cf = result["changed_files"][0]
        assert cf.filename == "app/services/auth/service.py"
        assert cf.filepath == "app/services/auth/service.py"
