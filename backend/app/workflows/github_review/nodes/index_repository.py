import logging
import uuid
from langchain_core.runnables.config import RunnableConfig

from app.workflows.github_review.state import GitHubReviewState
from app.github.client import GitHubClient
from app.rag.indexing.indexer import Indexer

logger = logging.getLogger(__name__)

async def index_repository(state: GitHubReviewState, config: RunnableConfig) -> dict:
    """
    Lazily indexes the repository's documentation if it hasn't been indexed or if documents have changed.
    """
    logger.info("Node: index_repository")
    
    if not state.repository:
        logger.warning("Repository not found in state, skipping indexing.")
        return {"logs": ["Skipping indexing: No repository in state"]}

    session = config["configurable"].get("db_session")
    installation_id = state.installation_id
    
    if not session or not installation_id:
        logger.error("Database session or installation_id missing in configuration.")
        return {"errors": ["Missing DB session or installation_id for indexing"]}

    gh_client = GitHubClient(installation_id=installation_id)
    indexer = Indexer(gh_client=gh_client, session=session)
    
    repo_id = uuid.UUID(state.repository.id)
    
    try:
        # Note: index_repository internally handles checksums and only updates what changed
        await indexer.index_repository(
            repository_id=repo_id,
            repo_fullname=state.repository.full_name,
            branch=state.repository.default_branch
        )
        return {"logs": [f"Repository {state.repository.full_name} indexed successfully (or already up-to-date)"]}
    except Exception as e:
        logger.error(f"Error during repository indexing: {str(e)}")
        # We don't fail the workflow if indexing fails, just log it.
        return {"errors": [f"Indexing failed: {str(e)}"]}
