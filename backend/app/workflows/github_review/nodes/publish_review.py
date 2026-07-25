import logging
from typing import Dict, Any
from langchain_core.runnables import RunnableConfig

from app.workflows.github_review.state import GitHubReviewState
from app.services.github.review_publisher import review_publisher_service

logger = logging.getLogger(__name__)

async def publish_review(state: GitHubReviewState, config: RunnableConfig) -> Dict[str, Any]:
    """
    LangGraph node to publish the ConsensusReviewResult as a GitHub PR Review.
    Does not perform any AI reasoning.
    """
    logger.info("Node: publish_review starting...")
    logs = ["Node: publish_review started"]
    errors = []

    if not state.consensus_result:
        logs.append("No consensus_result found in state. Skipping review publication.")
        return {"logs": logs}

    if not state.repository or not state.pull_request:
        errors.append("Repository or Pull Request context missing in state. Cannot publish review.")
        return {"errors": errors, "logs": logs}

    # Extract repository owner and name
    owner_login = state.repository.owner_login
    repo_name = state.repository.name
    pr_number = state.pull_request.github_pr_number
    installation_id = state.installation_id or state.repository.installation_id

    if not installation_id:
        errors.append("Installation ID missing in state. Cannot authenticate with GitHub API.")
        return {"errors": errors, "logs": logs}

    # Extract commit SHA / head_sha if available from raw_payload or state
    head_sha = getattr(state.pull_request, 'head_sha', None)
    if not head_sha:
        head_sha = state.raw_payload.get("pull_request", {}).get("head", {}).get("sha")

    db = config.get("configurable", {}).get("db_session") if config else None

    # Execute review publisher
    result = await review_publisher_service.publish_review(
        installation_id=str(installation_id),
        repo_owner=owner_login,
        repo_name=repo_name,
        pr_number=pr_number,
        pull_request_id=state.pull_request.id,
        head_sha=head_sha,
        consensus_result=state.consensus_result,
        changed_files=state.changed_files,
        db=db
    )

    if result.get("published"):
        github_review_id = result.get("github_review_id")
        logs.append(f"Successfully published GitHub review {github_review_id} for PR #{pr_number}.")
        return {
            "published_review_id": github_review_id,
            "logs": logs
        }
    elif result.get("skipped"):
        logs.append(f"Review publishing skipped: {result.get('reason')}")
        return {
            "published_review_id": result.get("github_review_id"),
            "logs": logs
        }
    else:
        err_msg = result.get("error", "Unknown error during review publishing")
        errors.append(err_msg)
        return {
            "errors": errors,
            "logs": logs
        }
