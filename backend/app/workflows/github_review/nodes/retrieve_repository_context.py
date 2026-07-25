import logging
from langchain_core.runnables.config import RunnableConfig

from app.workflows.github_review.state import GitHubReviewState
from app.rag.retrieval.retriever import Retriever

logger = logging.getLogger(__name__)

async def retrieve_repository_context(state: GitHubReviewState, config: RunnableConfig) -> dict:
    """
    Retrieves broad repository context (architecture, guidelines) and populates the workflow state.
    """
    logger.info("Node: retrieve_repository_context")
    
    if not state.repository:
        logger.warning("Repository not found in state, skipping retrieval.")
        return {"logs": ["Skipping retrieval: No repository in state"]}

    retriever = Retriever()
    
    # We do a broad query to fetch architecture, guidelines, and general overview context
    # This will be useful for all downstream agents. Later, specific agents can query Qdrant themselves if they need more.
    query = "architecture guidelines best practices overview"
    
    # Targeted test retrieval query based on changed files and symbols
    changed_names = []
    if state.changed_files:
        for cf in state.changed_files:
            base_name = cf.filename.split("/")[-1].split(".")[0]
            if base_name:
                changed_names.append(base_name)
    if state.symbol_tables:
        for sym in state.symbol_tables[:5]:
            if sym.name:
                changed_names.append(sym.name)

    test_query = f"test {' '.join(changed_names)}" if changed_names else "test unit integration specification"
    
    try:
        results = await retriever.retrieve(
            query=query,
            repo_fullname=state.repository.full_name,
            limit=10
        )
        
        test_results = await retriever.retrieve(
            query=test_query,
            repo_fullname=state.repository.full_name,
            limit=10
        )
        
        # Deduplicate results while serializing context for the state
        seen_keys = set()
        retrieved_context = []
        
        for res in results + test_results:
            key = (res.source_path, res.content[:50])
            if key in seen_keys:
                continue
            seen_keys.add(key)
            
            retrieved_context.append({
                "content": res.content,
                "score": res.score,
                "source": res.source_path,
                "document_type": res.metadata.document_type
            })
            
        logger.info(f"Retrieved {len(retrieved_context)} context chunks for {state.repository.full_name}")
        
        return {
            "retrieved_context": retrieved_context,
            "logs": [f"Retrieved {len(retrieved_context)} context chunks for {state.repository.full_name}"]
        }
        
    except Exception as e:
        logger.error(f"Error during repository context retrieval: {str(e)}")
        # We don't fail the workflow if retrieval fails.
        return {"errors": [f"Retrieval failed: {str(e)}"]}
