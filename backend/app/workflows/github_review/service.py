import logging
from typing import Any, Dict, Optional

from langchain_core.runnables import RunnableConfig

from app.db.session import AsyncSessionLocal
from app.workflows.github_review.graph import graph
from app.workflows.github_review.state import GitHubReviewState

logger = logging.getLogger(__name__)


async def process_github_review(
    event_type: str,
    action: Optional[str],
    installation_id: Optional[str],
    raw_payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Background worker function that executes the LangGraph PR review workflow.
    Creates, commits/rolls back, and closes its own independent database session.
    """
    repo_fullname = raw_payload.get("repository", {}).get("full_name", "Unknown Repo")
    pr_number = raw_payload.get("pull_request", {}).get("number", "Unknown PR")

    logger.info(
        f"Starting background GitHub PR review workflow for repo '{repo_fullname}', PR #{pr_number}, action '{action}'."
    )

    initial_state = GitHubReviewState(
        event_type=event_type,
        action=action,
        installation_id=installation_id,
        raw_payload=raw_payload,
    )

    async with AsyncSessionLocal() as session:
        config = RunnableConfig(configurable={"db_session": session})
        try:
            final_state = await graph.ainvoke(initial_state, config=config)

            if final_state.get("errors"):
                logger.error(
                    f"Background review workflow for repo '{repo_fullname}', PR #{pr_number} completed with errors: {final_state['errors']}"
                )
                await session.rollback()
                return final_state
            else:
                await session.commit()
                logger.info(
                    f"Background review workflow for repo '{repo_fullname}', PR #{pr_number} completed successfully."
                )
                return final_state
        except Exception as e:
            logger.exception(
                f"Unhandled exception during background review workflow for repo '{repo_fullname}', PR #{pr_number}: {e}"
            )
            await session.rollback()
            raise
