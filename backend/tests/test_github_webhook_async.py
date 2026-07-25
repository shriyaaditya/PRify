import hashlib
import hmac
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.workflows.github_review.service import process_github_review

client = TestClient(app)

SECRET = "test-secret"


def generate_signature(body: bytes, secret: str = SECRET) -> str:
    hash_obj = hmac.new(secret.encode("utf-8"), msg=body, digestmod=hashlib.sha256)
    return "sha256=" + hash_obj.hexdigest()


# --- Test A & E: Webhook endpoint validation and immediate background scheduling ---


def test_webhook_invalid_signature():
    response = client.post(
        "/api/github/webhook",
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": "sha256=invalid",
        },
        json={"action": "opened"},
    )
    assert response.status_code == 401


def test_webhook_missing_event_header():
    body = b'{"action": "opened"}'
    with patch.object(settings, "GITHUB_WEBHOOK_SECRET", SECRET):
        sig = generate_signature(body)
        response = client.post(
            "/api/github/webhook",
            headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"},
            content=body,
        )
    assert response.status_code == 400


def test_webhook_unsupported_event():
    body = b'{"action": "created"}'
    with patch.object(settings, "GITHUB_WEBHOOK_SECRET", SECRET):
        sig = generate_signature(body)
        response = client.post(
            "/api/github/webhook",
            headers={
                "X-GitHub-Event": "issue_comment",
                "X-Hub-Signature-256": sig,
                "Content-Type": "application/json",
            },
            content=body,
        )
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"


def test_webhook_unsupported_action():
    body = b'{"action": "closed"}'
    with patch.object(settings, "GITHUB_WEBHOOK_SECRET", SECRET):
        sig = generate_signature(body)
        response = client.post(
            "/api/github/webhook",
            headers={
                "X-GitHub-Event": "pull_request",
                "X-Hub-Signature-256": sig,
                "Content-Type": "application/json",
            },
            content=body,
        )
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"


def test_webhook_schedules_background_task_immediately():
    """Test A: Verify endpoint schedules task and returns HTTP 202 without awaiting workflow directly."""
    body = b'{"action": "opened", "installation": {"id": 12345}, "repository": {"full_name": "owner/repo"}, "pull_request": {"number": 1}}'
    with (
        patch.object(settings, "GITHUB_WEBHOOK_SECRET", SECRET),
        patch("app.api.github.process_github_review"),
    ):
        sig = generate_signature(body)
        response = client.post(
            "/api/github/webhook",
            headers={
                "X-GitHub-Event": "pull_request",
                "X-Hub-Signature-256": sig,
                "Content-Type": "application/json",
            },
            content=body,
        )

        assert response.status_code == 202
        assert response.json()["status"] == "accepted"


# --- Test B, C, D: Background review workflow execution, independent session, error handling ---


@pytest.mark.anyio
async def test_background_workflow_executes_and_manages_db_session():
    """Test B & C: Verify process_github_review creates its own session and invokes graph.ainvoke."""
    payload = {
        "action": "opened",
        "installation": {"id": 12345},
        "repository": {"full_name": "owner/repo"},
        "pull_request": {"number": 1},
    }

    mock_session = AsyncMock()
    mock_session_local = MagicMock()
    mock_session_local.return_value.__aenter__.return_value = mock_session

    with (
        patch(
            "app.workflows.github_review.service.AsyncSessionLocal", mock_session_local
        ),
        patch("app.workflows.github_review.service.graph") as mock_graph,
    ):
        mock_graph.ainvoke = AsyncMock(return_value={"errors": []})

        res = await process_github_review("pull_request", "opened", "12345", payload)

        assert res == {"errors": []}
        # Verify graph.ainvoke called with expected initial state
        assert mock_graph.ainvoke.call_count == 1
        initial_state = mock_graph.ainvoke.call_args[0][0]
        assert initial_state.event_type == "pull_request"
        assert initial_state.installation_id == "12345"

        # Verify DB session commit and session context manager used
        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()


@pytest.mark.anyio
async def test_background_workflow_handles_exception_and_rolls_back():
    """Test D: Verify exception during graph.ainvoke triggers rollback and log without swallowing unhandled error."""
    payload = {"repository": {"full_name": "owner/repo"}, "pull_request": {"number": 1}}

    mock_session = AsyncMock()
    mock_session_local = MagicMock()
    mock_session_local.return_value.__aenter__.return_value = mock_session

    with (
        patch(
            "app.workflows.github_review.service.AsyncSessionLocal", mock_session_local
        ),
        patch("app.workflows.github_review.service.graph") as mock_graph,
    ):
        mock_graph.ainvoke = AsyncMock(
            side_effect=RuntimeError("LangGraph unexpected failure")
        )

        with pytest.raises(RuntimeError, match="LangGraph unexpected failure"):
            await process_github_review("pull_request", "opened", "12345", payload)

        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()
