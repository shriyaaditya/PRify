import logging
from typing import Any, Dict

from langchain_core.runnables import RunnableConfig

from app.workflows.github_review.state import GitHubReviewState

logger = logging.getLogger(__name__)


async def finish(state: GitHubReviewState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Finalize the workflow and log completion or errors.
    """
    logs = ["Node: Finish started"]

    if state.errors:
        logs.append("Workflow completed with errors")
        logger.error(f"GitHub Review Workflow failed: {state.errors}")
    else:
        logs.append("Workflow completed successfully")
        pr_number = (
            state.pull_request.github_pr_number if state.pull_request else "Unknown"
        )
        repo_name = state.repository.full_name if state.repository else "Unknown"
        logger.info(
            f"GitHub Review Workflow completed successfully for PR #{pr_number} in {repo_name}"
        )

    # Output detailed logs in debug mode if needed
    for log_msg in state.logs:
        logger.debug(f"[Graph Log] {log_msg}")

    return {"logs": logs}
